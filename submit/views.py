
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django import forms
from django.contrib.auth.models import User
from .models import StudentProfile,Course, Assignment, Submission, SubmissionFile
from django.views.decorators.http import require_POST
from django.utils import timezone

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
    qs = Assignment.objects.select_related("course").order_by("-created_at")
    return render(request, "assignments_list.html", {"assignments": qs})

@login_required
def assignment_detail(request, pk):
    a = get_object_or_404(Assignment.objects.select_related("course"), pk=pk)
    user_submission = Submission.objects.filter(assignment=a, student=request.user).first()
    return render(request, "assignment_detail.html", {"a": a, "course": a.course, "user_submission": user_submission})

# 제출 폼
class SubmissionForm(forms.ModelForm):
    file = forms.FileField(required=True, help_text="PDF/ZIP 권장, 20MB 이하")
    class Meta:
        model = Submission
        fields = ("comment",)

@login_required
def submission_form(request, assignment_id):
    a = get_object_or_404(Assignment, pk=assignment_id)
    sub, _ = Submission.objects.get_or_create(assignment=a, student=request.user)

    if request.method == "POST":
        form = SubmissionForm(request.POST, request.FILES, instance=sub)
        if form.is_valid():
            sub = form.save(commit=False)
            sub.status = "submitted"
            sub.submitted_at = timezone.now()
            sub.save()

            up = request.FILES["file"]
            SubmissionFile.objects.create(
                submission=sub, file=up, version=sub.files.count()+1, size=up.size
            )
            return redirect("assignment_detail", pk=a.pk)
    else:
        form = SubmissionForm(instance=sub)

    return render(request, "submission_form.html", {"form": form, "a": a})