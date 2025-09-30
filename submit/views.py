from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.utils import timezone
from django.urls import reverse_lazy
from django.core.files.base import ContentFile
from django.db.models import Q, Count
from django.utils.dateparse import parse_datetime
from django.db import transaction
from django.db import IntegrityError
import datetime
import re

from .models import (
    Team, TeamMembership,
    Assignment, Submission, SubmissionFile,
    Grade,
    # 과제/제출 뷰 추가 예정이면 사용
    # Grade, Notification
)

def root(request):
    return redirect('teacher_team_list' if request.user.is_authenticated else 'login')

# ===== 인증 (기본 로그인/로그아웃만 유지) =====
class MyLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get(self, request, *args, **kwargs):
        # ✅ 로그인 화면에 들어올 때 이전 페이지에서 온 메시지(예: '로그아웃되었습니다.') 비움
        list(messages.get_messages(request))
        return super().get(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy("teacher_team_list")

def logout_view(request):
    # GET/POST 모두 허용해서 버전 차이 이슈 제거
    logout(request)
    messages.info(request, "로그아웃되었습니다.")
    return redirect("login")

# ====== (내장) 회원가입 폼: forms.py 없이 views.py 안에 선언 ======
class SimpleSignupForm(UserCreationForm):
    email = forms.EmailField(required=False, label="이메일")
    # 원하면 학번도 함께 수집(선택) — 필요없으면 이 필드 지워도 됨
    student_id = forms.CharField(required=False, max_length=20, label="학번")

    class Meta(UserCreationForm.Meta):
        fields = ("username",)  # password1/password2는 UserCreationForm에 이미 포함

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get("email", "")
        # 핵심: 기본은 학생 → 교수자 아님
        user.is_staff = False
        if commit:
            user.save()
            sid = (self.cleaned_data.get("student_id") or "").strip()
            if sid:
                StudentProfile = apps.get_model("submit", "StudentProfile")
                StudentProfile.objects.get_or_create(user=user, defaults={"student_id": sid})
        return user


def signup(request):
    if request.method == "GET":
        # 로그인/로그아웃 잔여 메시지 비우고 싶으면 유지, 아니면 이 두 줄 삭제
        list(messages.get_messages(request))

    if request.method == "POST":
        form = SimpleSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "회원가입이 완료되었습니다.")  # ← 임포트만 있으면 정상
            return redirect("teacher_team_list")
    else:
        form = SimpleSignupForm()
    return render(request, "registration/signup.html", {"form": form})

# ===== 교수: 내 팀 목록 =====
@login_required
def teacher_team_list(request):
    # 내가 소유한 팀 OR 내가 승인된 멤버인 팀
    teams = (
        Team.objects.filter(
            Q(owner=request.user) |
            Q(memberships__student=request.user, memberships__status="APPROVED")
        )
        .distinct()
        .order_by("name")
    )
    return render(request, "teams/teacher_team_list.html", {"teams": teams})

# ===== 팀 생성 =====
@login_required
def create_team(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        desc = (request.POST.get("description") or "").strip()
        cover = request.FILES.get("cover")  # ← 추가

        if not name:
            return render(request, "teams/create.html", {"error": "팀명을 입력하세요."})

        t = Team(owner=request.user, name=name, description=desc)
        if cover:
            t.cover = cover
        t.save()
        return redirect("team_detail", team_id=t.id)
    return render(request, "teams/create_team.html")

# ===== 학생: 팀 코드로 가입 페이지 =====
# 팀 참가(코드 입력 화면 + 내 요청 목록)
@login_required
def join_page(request):
    my_requests = TeamMembership.objects.filter(student=request.user).select_related("team").order_by("-requested_at")
    return render(request, "teams/join.html", {"my_requests": my_requests})

# ===== 교수: 팀 코드 재발급 =====
@login_required
def regen_team_code(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if request.user != team.owner:
        return HttpResponseForbidden("권한이 없습니다.")
    team.regen_join_code()
    messages.success(request, f"새 팀코드: {team.join_code}")
    return redirect('team_detail', team_id=team.id)


# ===== 공통: 팀 상세 =====
@login_required
def team_detail(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    is_owner = (team.owner_id == request.user.id)
    is_member = TeamMembership.objects.filter(
        team=team, student=request.user, status="APPROVED"
    ).exists()

    if not (is_owner or is_member):
        return HttpResponseForbidden("팀 구성원만 접근할 수 있습니다.")

    assigns = Assignment.objects.filter(team=team).order_by('-due_at')
    my_submissions = {}
    if not is_owner:
        my_submissions = {
            s.assignment_id: s
            for s in Submission.objects.filter(assignment__team=team, student=request.user)
        }

    return render(request, "teams/team_detail.html", {
        "team": team,
        "assignments": assigns,
        "my_submissions": my_submissions,
        "is_owner": is_owner,
    })


# 팀 코드로 참가 요청(POST)
@login_required
@require_POST
def request_join_by_code(request):
    join_code = (request.POST.get("join_code") or "").strip()

    # 공통: 내 요청 목록(재렌더용)
    def _render_join(error=None, info=None):
        my_requests = TeamMembership.objects.filter(student=request.user)\
                         .select_related("team").order_by("-requested_at")
        ctx = {"my_requests": my_requests, "error": error, "info": info, "join_code": join_code}
        return render(request, "teams/join.html", ctx)

    # 1) 빈 값
    if not join_code:
        return _render_join(error="팀 코드를 입력하세요.")

    # 2) 포맷 체크 (6자리 숫자)
    if not re.fullmatch(r"\d{6}", join_code):
        return _render_join(error="팀 코드는 6자리 숫자여야 합니다.")

    # 3) 팀 조회 (없으면 친절 메시지)
    team = Team.objects.filter(join_code=join_code).first()
    if not team:
        return _render_join(error="유효하지 않은 팀 코드입니다. 코드를 다시 확인하세요.")

    # 4) 본인이 팀장일 경우 → 바로 팀 상세
    if request.user == team.owner:
        return redirect("team_detail", team_id=team.id)

    # 5) 멤버십 처리
    mship, created = TeamMembership.objects.get_or_create(
        team=team, student=request.user,
        defaults={"status": "PENDING", "requested_at": timezone.now()}
    )

    # 이미 존재하는 경우 상태별 대응
    if not created:
        if mship.status == "APPROVED":
            # 승인 정책: 우리가 '승인 즉시 합류' 로 바꿨으므로 곧바로 팀으로
            return redirect("team_detail", team_id=team.id)
        elif mship.status == "PENDING":
            return _render_join(info=f"이미 '{team.name}' 팀에 참가 요청을 보냈습니다. 승인 대기 중입니다.")
        elif mship.status in ("REJECTED", "LEFT"):
            # 재요청 허용
            mship.status = "PENDING"
            mship.requested_at = timezone.now()
            mship.decided_at = None
            mship.decided_by = None
            mship.joined_at = None
            mship.save(update_fields=["status", "requested_at", "decided_at", "decided_by", "joined_at"])
            return _render_join(info=f"'{team.name}' 팀에 재요청을 보냈습니다.")

    # 새 요청 생성됨
    return _render_join(info=f"'{team.name}' 팀에 참가 요청을 보냈습니다.")

# ===== 팀장 가입요청 목록 =====
@login_required
def team_requests(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if request.user != team.owner:
        return HttpResponseForbidden("권한이 없습니다.")
    pending = TeamMembership.objects.filter(team=team, status="PENDING").select_related("student").order_by("requested_at")
    recent  = TeamMembership.objects.filter(team=team).exclude(status="PENDING").select_related("student").order_by("-requested_at")[:50]
    return render(request, "teams/requests.html", {"team": team, "pending": pending, "recent": recent})

@login_required
@require_POST
def approve_team_request(request, membership_id):
    m = get_object_or_404(TeamMembership, pk=membership_id)
    team = m.team
    if request.user != team.owner:
        return HttpResponseForbidden("권한이 없습니다.")
    try:
        m.approve(by_user=request.user)   # models.py의 approve()가 joined_at도 찍도록 구성
    except Exception:
        m.status = "APPROVED"
        now = timezone.now()
        m.decided_at = now
        m.decided_by = request.user
        m.joined_at  = now
        m.save(update_fields=["status","decided_at","decided_by","joined_at"])
    return redirect("team_requests", team_id=team.id)

@login_required
@require_POST
def reject_team_request(request, membership_id):
    m = get_object_or_404(TeamMembership, pk=membership_id)
    team = m.team
    if request.user != team.owner:
        return HttpResponseForbidden("권한이 없습니다.")
    try:
        m.reject(by_user=request.user)
    except Exception:
        m.status = "REJECTED"
        m.decided_at = timezone.now()
        m.decided_by = request.user
        m.save(update_fields=["status","decided_at","decided_by"])
    return redirect("team_requests", team_id=team.id)

# ===== 학생: 승인 후 최종 참가 =====
@login_required
def join_team(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    membership = get_object_or_404(TeamMembership, team=team, student=request.user)
    if membership.status != "APPROVED":
        return HttpResponseForbidden("승인된 요청만 참가할 수 있습니다.")
    if membership.joined_at:
        messages.info(request, "이미 참가 완료된 팀입니다.")
        return redirect('team_detail', team_id=team.id)
    membership.join()
    messages.success(request, f"'{team.name}' 팀에 참가 완료!")
    return redirect('team_detail', team_id=team.id)

def _is_team_member(user, team: Team):
    if user == team.owner:
        return True
    return TeamMembership.objects.filter(
        team=team, student=user, status="APPROVED", joined_at__isnull=False
    ).exists()

@login_required
def team_detail(request, team_id):
    team = get_object_or_404(Team, pk=team_id)

    # ✅ 팀장 여부
    is_owner = (team.owner_id == request.user.id)

    # ✅ 승인 + 참가완료 멤버 여부
    is_member = TeamMembership.objects.filter(
        team=team,
        student=request.user,
        status="APPROVED"
    ).exists()

    # ✅ 팀장 또는 멤버만 접근 허용
    if not (is_owner or is_member):
        return HttpResponseForbidden("팀 구성원만 접근할 수 있습니다.")

    # 이하 기존 로직 유지
    assigns = Assignment.objects.filter(team=team).order_by('-due_at')
    my_submissions = {}
    if not is_owner:
        my_submissions = {
            s.assignment_id: s
            for s in Submission.objects.filter(assignment__team=team, student=request.user)
        }

    ctx = {
        "team": team,
        "assignments": assigns,
        "my_submissions": my_submissions,
        "is_owner": is_owner,
    }
    return render(request, 'teams/team_detail.html', ctx)

@login_required
def team_edit(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if request.user != team.owner:
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        desc = (request.POST.get("description") or "").strip()
        cover = request.FILES.get("cover")

        if not name:
            return render(request, "teams/edit.html", {"team": team, "error": "팀명을 입력하세요."})

        team.name = name
        team.description = desc
        if cover:
            team.cover = cover
        team.save()
        return redirect("team_detail", team_id=team.id)

    return render(request, "teams/edit.html", {"team": team})


@login_required
def team_delete(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if request.user != team.owner:
        return HttpResponseForbidden("팀장만 삭제할 수 있습니다.")

    if request.method == "POST":
        with transaction.atomic():
            team.delete()  # CASCADE로 과제/제출/파일/멤버십 등 일괄 삭제
        # messages.success(request, "팀이 삭제되었습니다.")
        return redirect("teacher_team_list")

    # 삭제 전 간단 안내(선택: 개수 보여주기)
    assignment_cnt = Assignment.objects.filter(team=team).count()
    member_cnt = TeamMembership.objects.filter(team=team).count()
    return render(request, "teams/delete_confirm.html", {
        "team": team,
        "assignment_cnt": assignment_cnt,
        "member_cnt": member_cnt,
    })

@login_required
def assignment_create(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if request.user != team.owner:
        return HttpResponseForbidden("권한이 없습니다.")

    if request.method == "POST":
        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()
        max_score = int(request.POST.get("max_score") or 100)

        due_raw = (request.POST.get("due_at") or "").strip()  # ex) "2025-10-01T23:59"
        if not due_raw:
            return render(request, "assignments/create.html", {
                "team": team,
                "error": "마감일시는 필수입니다.",
                "default_due": timezone.now() + datetime.timedelta(days=7),
            })

        # ✅ datetime-local 포맷 파싱
        try:
            # Python 3.11+: fromisoformat은 "YYYY-MM-DDTHH:MM" 지원
            due_dt = datetime.datetime.fromisoformat(due_raw)
        except ValueError:
            # 공백/다른 포맷으로 오는 경우 보정
            try:
                due_dt = datetime.datetime.strptime(due_raw.replace(" ", "T"), "%Y-%m-%dT%H:%M")
            except ValueError:
                return render(request, "assignments/create.html", {
                    "team": team,
                    "error": "마감일시는 날짜 선택기를 이용해 정확히 입력하세요.",
                    "default_due": timezone.now() + datetime.timedelta(days=7),
                })

        # ✅ timezone-aware 로 변환 (서버 TZ 기준)
        if timezone.is_naive(due_dt):
            due_dt = timezone.make_aware(due_dt, timezone.get_current_timezone())

        a = Assignment.objects.create(
            team=team,
            title=title,
            description=description,
            due_at=due_dt,
            max_score=max_score,
            created_by=request.user,  # 필드가 있으면 세팅, 없으면 제거
        )
        return redirect("assignment_detail", team_id=team.id, assignment_id=a.id)

    # GET: 기본값(일주일 뒤 23:59 등)
    default_due = timezone.localtime(timezone.now() + datetime.timedelta(days=7)).replace(second=0, microsecond=0)
    return render(request, "assignments/create.html", {
        "team": team,
        "default_due": default_due,
    })


@login_required
def assignment_detail(request, team_id, assignment_id):
    team = get_object_or_404(Team, pk=team_id)
    a = get_object_or_404(Assignment, pk=assignment_id, team=team)

    is_owner = (request.user.id == team.owner_id)
    is_member = TeamMembership.objects.filter(
        team=team, student=request.user, status="APPROVED", joined_at__isnull=False
    ).exists() if not is_owner else False

    if not (is_owner or is_member):
        return HttpResponseForbidden("권한이 없습니다.")

    my_sub = None
    my_grade = None
    can_edit = False

    if not is_owner:
        my_sub = Submission.objects.filter(assignment=a, student=request.user).first()
        if my_sub:
            # 학생 편집 가능 여부
            now = timezone.now()
            can_edit = (not a.is_closed) and (not (a.due_at and now > a.due_at)) and (my_sub.status != "graded")
            # 내 채점
            if hasattr(my_sub, "grade"):
                my_grade = my_sub.grade

    ctx = {
        "team": team, "a": a, "my_sub": my_sub, "my_grade": my_grade,
        "is_owner": is_owner, "can_edit": can_edit,
    }
    return render(request, 'assignments/detail.html', ctx)

@login_required
def assignment_submit(request, team_id, assignment_id):
    team = get_object_or_404(Team, pk=team_id)
    a = get_object_or_404(Assignment, pk=assignment_id, team=team)

    # 팀 접근 권한 체크(팀장 또는 승인된 멤버)
    is_owner = (team.owner_id == request.user.id)
    is_member = TeamMembership.objects.filter(team=team, student=request.user, status="APPROVED").exists()
    if not (is_owner or is_member):
        return HttpResponseForbidden("팀 구성원만 접근할 수 있습니다.")

    # # 팀장은 제출하지 않도록 막고 싶다면(선택)
    # if is_owner:
    #     return HttpResponseForbidden("팀장은 제출할 수 없습니다.")

    # 마감된 과제면 수정/제출 불가
    if getattr(a, "is_closed", False):
        return HttpResponseForbidden("마감된 과제입니다.")

    # 내 제출 가져오기(없으면 생성)
    sub, _ = Submission.objects.get_or_create(
        assignment=a, student=request.user,
        defaults={"status": "not_submitted"}
    )

    if request.method == "POST":
        # 코멘트
        sub.comment = (request.POST.get("comment") or "").strip()

        # ✅ 기존 파일 전부 삭제 (레코드+실제 파일)
        for f in list(sub.files.all()):
            f.delete()

        # 새 파일 저장
        uploaded_files = request.FILES.getlist("files")
        for idx, uf in enumerate(uploaded_files, start=1):
            SubmissionFile.objects.create(
                submission=sub,
                file=uf,
                version=idx,
                size=uf.size or 0,
            )

        # 상태/시간 갱신
        sub.status = "submitted"
        sub.submitted_at = timezone.now()
        sub.save(update_fields=["comment", "status", "submitted_at"])

        return redirect("assignment_detail", team_id=team.id, assignment_id=a.id)

    # GET: 제출 폼
    return render(request, "assignments/submit.html", {
        "team": team,
        "a": a,
        "my_sub": sub,
    })

@login_required
def assignment_submissions(request, team_id, assignment_id):
    team = get_object_or_404(Team, pk=team_id)
    a = get_object_or_404(Assignment, pk=assignment_id, team=team)
    if request.user != team.owner:
        return HttpResponseForbidden("팀장만 확인할 수 있습니다.")
    subs = Submission.objects.filter(assignment=a).select_related("student").prefetch_related("files")
    return render(request, 'assignments/submissions.html', {"team": team, "a": a, "subs": subs})

class GradeForm(forms.Form):
    score = forms.IntegerField(min_value=0, label="점수")
    feedback_text = forms.CharField(required=False, widget=forms.Textarea, label="피드백")

@login_required
def grade_submission(request, team_id, assignment_id, submission_id):
    team = get_object_or_404(Team, pk=team_id)
    a = get_object_or_404(Assignment, pk=assignment_id, team=team)
    if request.user != team.owner:
        return HttpResponseForbidden("팀장만 채점할 수 있습니다.")

    sub = get_object_or_404(Submission, pk=submission_id, assignment=a)

    initial = {}
    if hasattr(sub, "grade"):
        initial = {"score": sub.grade.score, "feedback_text": sub.grade.feedback_text}

    if request.method == "POST":
        form = GradeForm(request.POST)
        if form.is_valid():
            score = form.cleaned_data["score"]
            feedback_text = form.cleaned_data["feedback_text"]
            grade_obj, _ = Grade.objects.update_or_create(
                submission=sub,
                defaults={
                    "score": score,
                    "feedback_text": feedback_text,
                    "grader": request.user
                }
            )
            sub.status = "graded"
            sub.save(update_fields=["status"])
            # messages.success(request, "채점 저장되었습니다.")
            return redirect("assignment_submissions", team_id=team.id, assignment_id=a.id)
    else:
        form = GradeForm(initial=initial)

    return render(request, "assignments/grade.html", {"team": team, "a": a, "sub": sub, "form": form})

@login_required
def assignment_close(request, team_id, assignment_id):
    team = get_object_or_404(Team, pk=team_id)
    a = get_object_or_404(Assignment, pk=assignment_id, team=team)
    if request.user != team.owner:
        return HttpResponseForbidden("권한이 없습니다.")
    a.is_closed = True
    a.save(update_fields=["is_closed"])
    messages.info(request, "과제를 마감했습니다.")
    return redirect("assignment_detail", team_id=team.id, assignment_id=a.id)

@login_required
def assignment_reopen(request, team_id, assignment_id):
    team = get_object_or_404(Team, pk=team_id)
    a = get_object_or_404(Assignment, pk=assignment_id, team=team)
    if request.user != team.owner:
        return HttpResponseForbidden("권한이 없습니다.")
    a.is_closed = False
    a.save(update_fields=["is_closed"])
    messages.info(request, "과제 마감을 해제했습니다.")
    return redirect("assignment_detail", team_id=team.id, assignment_id=a.id)

@login_required
def assignment_list(request, team_id):
    team = get_object_or_404(Team, id=team_id)
    assignments = Assignment.objects.filter(team=team).order_by("-created_at")
    return render(request, "assignments/assignment_list.html", {"team": team, "assignments": assignments})