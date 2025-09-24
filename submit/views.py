
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction

from .models import StudentProfile,Course, Assignment, Submission, SubmissionFile

# --- 회원가입 폼 (이메일 필수 + 중복 체크) ---
class SignupForm(UserCreationForm):
    full_name = forms.CharField(label="이름", max_length=50)
    username = forms.EmailField(label="아이디(이메일 형식)", max_length=150)
    student_id = forms.CharField(label="학번", max_length=20)

    class Meta:
        model = User
        fields = ("full_name", "username", "student_id", "password1", "password2")

    def clean_username(self):
        username = self.cleaned_data.get("username")
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("이미 사용 중인 아이디입니다.")
        return username

    def clean_student_id(self):
        student_id = self.cleaned_data.get("student_id")
        if StudentProfile.objects.filter(student_id=student_id).exists():
            raise forms.ValidationError("이미 등록된 학번입니다.")
        return student_id

    def save(self, commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data["username"]
        user.first_name = self.cleaned_data["full_name"]  # 이름 저장
        if commit:
            user.save()
            StudentProfile.objects.create(
                user=user,
                student_id=self.cleaned_data["student_id"]
            )
        return user

def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()          # User 생성
            login(request, user)        # ✅ 자동 로그인
            messages.success(request, "회원가입이 완료되었습니다.")
            return redirect("dashboard")
    else:
        form = SignupForm()
    return render(request, "registration/signup.html", {"form": form})

@login_required
def grading(request):
    return render(request, 'grading.html')

@login_required
def notifications(request):
    return render(request, 'notifications.html')


@login_required
def dashboard(request):
    return render(request, 'dashboard.html')

@login_required
def assignments_list(request):
    assignments = list(
        Assignment.objects.select_related("course").order_by("-created_at")
    )
    subs = Submission.objects.filter(
        student=request.user, assignment__in=assignments
    ).select_related("assignment")

    sub_by_aid = {s.assignment_id: s for s in subs}
    for a in assignments:
        a.user_submission = sub_by_aid.get(a.id)  # ← 템플릿에서 a.user_submission 로 접근

    return render(request, "assignments_list.html", {"assignments": assignments})

@login_required
def assignment_detail(request, pk):
    a = get_object_or_404(Assignment.objects.select_related("course"), pk=pk)
    user_submission = Submission.objects.filter(assignment=a, student=request.user).first()
    return render(request, "assignment_detail.html", {"a": a, "course": a.course, "user_submission": user_submission})


# ── 제출 폼: 코멘트(+ 파일 1개) ─────────────────────────────────────────
class SubmissionFormForm(forms.ModelForm):
    file = forms.FileField(required=True, help_text="PDF/ZIP 권장, 20MB 이하")

    class Meta:
        model = Submission
        fields = ("comment",)

    # (선택) 간단한 확장자/크기 검증
    def clean_file(self):
        f = self.files.get("file")
        if not f:
            return f
        if f.size > 20 * 1024 * 1024:
            raise forms.ValidationError("파일은 20MB 이하여야 합니다.")
        allowed = (".pdf", ".zip")
        name = f.name.lower()
        if not any(name.endswith(ext) for ext in allowed):
            raise forms.ValidationError("PDF 또는 ZIP 형식만 허용합니다.")
        return f

@login_required
def submission_form(request, assignment_id):
    a = get_object_or_404(Assignment, pk=assignment_id)
    sub, _ = Submission.objects.get_or_create(assignment=a, student=request.user)

    if request.method == "POST":
        form = SubmissionFormForm(request.POST, request.FILES, instance=sub)
        if form.is_valid():
            sub = form.save(commit=False)
            now = timezone.now()
            sub.submitted_at = now
            sub.status = "late" if (a.due_at and now > a.due_at) else "submitted"
            sub.save()
            # 파일 저장 로직 그대로…
            up = request.FILES["file"]
            SubmissionFile.objects.create(
                submission=sub, file=up, version=sub.files.count()+1, size=up.size
            )
            messages.success(request, "제출이 완료되었습니다.")
            return redirect("assignment_detail", pk=a.pk)
    else:
        form = SubmissionFormForm(instance=sub, initial={"comment": ""})

    return render(request, "submission_form.html", {"form": form, "a": a, "sub": sub})

@login_required
def submission_file_delete(request, assignment_id, file_id):
    """
    사용자가 자신의 제출물 파일을 삭제.
    - 해당 과제의 자신의 Submission에 속한 파일만 삭제 허용
    - 파일 스토리지에서 실제 파일도 제거
    """
    a = get_object_or_404(Assignment, pk=assignment_id)
    sub = get_object_or_404(Submission, assignment=a, student=request.user)
    f = get_object_or_404(SubmissionFile, pk=file_id, submission=sub)

    if request.method == "POST":
        # 스토리지에서 파일 삭제
        try:
            f.file.delete(save=False)
        except Exception:
            pass
        # DB 레코드 삭제
        f.delete()
        messages.success(request, "파일을 삭제했습니다.")
    else:
        messages.error(request, "잘못된 요청입니다.")

    return redirect("submission_form", assignment_id=a.pk)

# ── 제출 취소 ─────────────────────────────────────────
@require_POST
@login_required
@transaction.atomic
def cancel_submission(request, assignment_id):
    a = get_object_or_404(Assignment, pk=assignment_id)
    sub = get_object_or_404(Submission, assignment=a, student=request.user)

    # (정책) 채점완료는 취소 불가로 유지
    if sub.status == "graded":
        messages.error(request, "채점완료 상태는 제출 취소가 불가합니다.")
        return redirect("assignment_detail", pk=a.pk)

    # 1) 업로드 파일 실제 스토리지에서 삭제
    files = list(sub.files.all())
    for f in files:
        try:
            # 실제 파일(디스크/스토리지) 삭제
            f.file.delete(save=False)
        except Exception:
            pass  # 파일이 이미 없거나 오류여도 트랜잭션 유지

    # 2) 파일 레코드 삭제
    sub.files.all().delete()

    # 3) 제출 상태/시간 초기화 (미제출)
    sub.status = "not_submitted"
    sub.submitted_at = None
    sub.save(update_fields=["status", "submitted_at"])

    messages.success(request, "제출을 취소하고 첨부 파일을 모두 삭제했습니다.")
    return redirect("assignment_detail", pk=a.pk)

def is_teacher(user):
    return user.is_authenticated and (user.is_staff or user.groups.filter(name="teacher").exists())

from functools import wraps
def teacher_required(view_func):
    @wraps(view_func)
    def _wrapped(*args, **kwargs):
        return login_required(user_passes_test(is_teacher)(view_func))(*args, **kwargs)
    return _wrapped

# ── 교수자 대시보드 ───────────────────────────────────────────
@teacher_required
def teacher_dashboard(request):
    courses = Course.objects.filter(teacher=request.user).order_by("code")
    # 최근 과제 5개
    recent_assignments = Assignment.objects.filter(course__teacher=request.user).select_related("course").order_by("-created_at")[:5]
    return render(request, "teacher/dashboard.html", {
        "courses": courses,
        "recent_assignments": recent_assignments,
    })

# ── 과제 생성 폼 ──────────────────────────────────────────────
class AssignmentForm(forms.ModelForm):
    class Meta:
        model = Assignment
        fields = ("course", "title", "description", "due_at", "max_score", "late_policy", "file_rules")
        widgets = {
            "due_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        # 현재 교수자가 담당하는 과목만 선택 가능
        if user:
            self.fields["course"].queryset = Course.objects.filter(teacher=user)

@teacher_required
def teacher_assignment_create(request):
    if request.method == "POST":
        form = AssignmentForm(request.POST, user=request.user)
        if form.is_valid():
            a = form.save()
            messages.success(request, "과제가 생성되었습니다.")
            return redirect("teacher_dashboard")
    else:
        form = AssignmentForm(user=request.user)
    return render(request, "teacher/assignment_form.html", {"form": form})

# ── 특정 과제의 제출 목록(학생별) ─────────────────────────────
@teacher_required
def teacher_submissions(request, pk):
    a = get_object_or_404(Assignment.objects.select_related("course"), pk=pk, course__teacher=request.user)
    subs = Submission.objects.filter(assignment=a).select_related("student").prefetch_related("files").order_by("-submitted_at")
    return render(request, "teacher/submissions_list.html", {"a": a, "submissions": subs})