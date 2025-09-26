from django import forms
from django.apps import apps
from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
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

# ===== 교수: 팀 생성 =====
@login_required
def create_team(request):
    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        desc = (request.POST.get("description") or "").strip()
        if not name:
            # 필요시 메시지 대신 그냥 리다이렉트
            return redirect("create_team")

        t = Team(owner=request.user, name=name, description=desc)
        t.save()  # join_code는 모델에서 자동 생성
        return redirect("team_detail", team_id=t.id)

    return render(request, "teams/create.html")

    # GET: 팀 생성 폼
    return render(request, "teams/create_team.html", {})

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
def request_join_by_code(request):
    if request.method != "POST":
        return HttpResponseBadRequest("잘못된 요청입니다.")

    code = (request.POST.get("join_code") or "").strip()
    if not code:
        return redirect("team_join_page")

    team = get_object_or_404(Team, join_code=code)

    # 팀장은 바로 상세로
    if request.user == team.owner:
        return redirect("team_detail", team_id=team.id)

    m, created = TeamMembership.objects.get_or_create(
        team=team, student=request.user, defaults={"status": "PENDING"}
    )
    if not created and m.status in ("PENDING", "APPROVED"):
        # 이미 요청/승인 상태면 참가 페이지로
        return redirect("team_join_page")

    # 새로 대기 상태로 세팅(LEFT/REJECTED 였던 경우 포함)
    m.status = "PENDING"
    m.requested_at = timezone.now()
    m.decided_at = None
    m.decided_by = None
    m.save(update_fields=["status", "requested_at", "decided_at", "decided_by"])

    return redirect("team_join_page")

# ===== 교수: 가입요청 목록 =====
@login_required
def list_team_requests(request, team_id):
    team = get_object_or_404(Team, pk=team_id)
    if request.user != team.owner:
        return HttpResponseForbidden("권한이 없습니다.")
    pending = team.memberships.filter(status="PENDING").select_related("student")
    return render(request, 'teams/request_list.html', {'team': team, 'requests': pending})


# ===== 교수: 승인/거절 =====
@login_required
def approve_team_request(request, membership_id):
    m = get_object_or_404(TeamMembership, pk=membership_id)
    if request.user != m.team.owner:
        return HttpResponseForbidden("권한이 없습니다.")
    m.approve(by_user=request.user)  # ✅ joined_at까지 처리됨
    return redirect("team_request_list", team_id=m.team_id)

@login_required
def reject_team_request(request, membership_id):
    membership = get_object_or_404(TeamMembership, pk=membership_id)
    if request.user != membership.team.owner:
        return HttpResponseForbidden("권한이 없습니다.")
    membership.reject(by_user=request.user)
    messages.info(request, f"{membership.student.username} 거절 처리")
    return redirect('team_request_list', team_id=membership.team_id)


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
        return HttpResponseForbidden("팀장만 과제를 등록할 수 있습니다.")

    if request.method == "POST":
        title = request.POST.get("title", "").strip()
        desc = request.POST.get("description", "").strip()
        due_raw = request.POST.get("due_at", "").strip()  # e.g. "2025-10-10T23:59"
        max_score = int(request.POST.get("max_score", "100") or 100)

        if not title or not due_raw:
            messages.error(request, "제목과 마감일시는 필수입니다.")
            return redirect('assignment_create', team_id=team.id)

        try:
            # 1) 문자열 → naive datetime
            due_naive = datetime.strptime(due_raw, "%Y-%m-%dT%H:%M")
            # 2) settings.TIME_ZONE 기준 aware
            due_dt = timezone.make_aware(due_naive, timezone.get_current_timezone())
        except Exception:
            messages.error(request, "마감일시는 날짜 선택기를 이용해 정확히 입력하세요.")
            return redirect('assignment_create', team_id=team.id)

        a = Assignment.objects.create(
            team=team,
            title=title,
            description=desc,
            due_at=due_dt,
            max_score=max_score,
        )
        messages.success(request, f"과제 '{a.title}'를 생성했습니다.")
        return redirect('team_detail', team_id=team.id)

    # GET: 기본값(지금 시각과 +7일 23:59)을 템플릿으로
    now_local = timezone.localtime()  # Asia/Seoul
    # 기본 마감은 7일 뒤 23:59
    default_due = (now_local + timezone.timedelta(days=7)).replace(hour=23, minute=59, second=0, microsecond=0)

    # datetime-local 형식으로 포맷: YYYY-MM-DDTHH:MM
    ctx = {
        "team": team,
        "now_local": now_local.strftime("%Y-%m-%dT%H:%M"),
        "default_due": default_due.strftime("%Y-%m-%dT%H:%M"),
    }
    return render(request, 'assignments/create.html', ctx)


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

    if request.user == team.owner:
        return HttpResponseForbidden("팀장은 제출 대상이 아닙니다.")

    is_member = TeamMembership.objects.filter(
        team=team, student=request.user, status="APPROVED", joined_at__isnull=False
    ).exists()
    if not is_member:
        return HttpResponseForbidden("권한이 없습니다.")

    sub, _ = Submission.objects.get_or_create(
        assignment=a, student=request.user, defaults={"status": "not_submitted"}
    )

    # ❌ 수정 불가 조건: 과제 마감됨 / 마감시각 지남 / 이미 채점됨
    now = timezone.now()
    if a.is_closed or (a.due_at and now > a.due_at) or sub.status == "graded":
        return HttpResponseForbidden("이 과제는 더 이상 수정/제출할 수 없습니다.")

    if request.method == "POST":
        file = request.FILES.get("file")
        comment = (request.POST.get("comment") or "").strip()

        if file:
            last = sub.files.order_by('-version').first()
            version = (last.version + 1) if last else 1
            SubmissionFile.objects.create(
                submission=sub, file=file, version=version, size=file.size
            )

        sub.comment = comment
        sub.submitted_at = now
        sub.status = "submitted"
        sub.save()

        # messages.success(request, "제출/수정 완료되었습니다.")
        return redirect('assignment_detail', team_id=team.id, assignment_id=a.id)

    return render(request, 'assignments/submit.html', {"team": team, "a": a, "sub": sub})

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