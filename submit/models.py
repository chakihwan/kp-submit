from django.db import models

# Create your models here.

from django.contrib.auth.models import User

# submit/models.py
from django.db import models
from django.contrib.auth.models import User

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="사용자")
    student_id = models.CharField("학번", max_length=20, unique=True)

    def __str__(self): return f"{self.user.username}({self.student_id})"

    class Meta:
        verbose_name = "학생 프로필"
        verbose_name_plural = "학생 프로필"

class Course(models.Model):
    title = models.CharField("과목명", max_length=100)
    code = models.CharField("과목코드", max_length=20, unique=True)
    teacher = models.ForeignKey(User, on_delete=models.CASCADE, related_name="teaching_courses", verbose_name="담당교원")

    def __str__(self): return f"{self.code} {self.title}"

    class Meta:
        verbose_name = "과목"
        verbose_name_plural = "과목"

class Enrollment(models.Model):
    ROLE_CHOICES = (
        ("student", "학생"),
        ("ta", "조교"),
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="사용자")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="과목")
    role_in_course = models.CharField("역할", max_length=10, choices=ROLE_CHOICES, default="student")

    class Meta:
        verbose_name = "수강 등록"
        verbose_name_plural = "수강 등록"
        unique_together = ("user", "course")

class Assignment(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name="과목")
    title = models.CharField("제목", max_length=120)
    description = models.TextField("설명", blank=True)
    due_at = models.DateTimeField("마감일시")
    max_score = models.PositiveIntegerField("배점", default=100)
    late_policy = models.CharField("지연 정책", max_length=50, blank=True)   # ex) "accept -10/day"
    file_rules = models.CharField("파일 규칙", max_length=100, blank=True)   # ex) "pdf,zip; 20MB"
    created_at = models.DateTimeField("생성일시", auto_now_add=True)

    def __str__(self): return f"{self.title} ({self.course.code})"

    class Meta:
        verbose_name = "과제"
        verbose_name_plural = "과제"

class Submission(models.Model):
    STATUS = (
        ("not_submitted", "미제출"),
        ("late", "지연제출"),
        ("submitted", "제출됨"),
        ("graded", "채점완료"),
    )
    assignment = models.ForeignKey(Assignment, on_delete=models.CASCADE, verbose_name="과제")
    student = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="학생")
    status = models.CharField("상태", max_length=20, choices=STATUS, default="not_submitted")
    comment = models.TextField("제출 메모", blank=True)
    submitted_at = models.DateTimeField("제출일시", null=True, blank=True)
    class Meta:
        verbose_name = "제출"
        verbose_name_plural = "제출"
        unique_together = ("assignment", "student")

class SubmissionFile(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="files", verbose_name="제출")
    file = models.FileField("파일", upload_to="submissions/")
    version = models.PositiveIntegerField("버전", default=1)
    size = models.PositiveIntegerField("크기(Byte)", default=0)

    def __str__(self): return f"{self.submission} v{self.version}"

    class Meta:
        verbose_name = "제출 파일"
        verbose_name_plural = "제출 파일"

class Grade(models.Model):
    submission = models.OneToOneField(Submission, on_delete=models.CASCADE, verbose_name="제출")
    score = models.PositiveIntegerField("점수")
    feedback_text = models.TextField("피드백", blank=True)
    grader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="채점자")
    graded_at = models.DateTimeField("채점일시", auto_now=True)

    def __str__(self): return f"{self.submission} = {self.score}"

    class Meta:
        verbose_name = "성적"
        verbose_name_plural = "성적"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="대상 사용자")
    type = models.CharField("유형", max_length=30)  # 예: "due_soon", "graded"
    payload = models.JSONField("추가 데이터", default=dict, blank=True)
    read_at = models.DateTimeField("읽은 시각", null=True, blank=True)
    created_at = models.DateTimeField("생성일시", auto_now_add=True)

    def __str__(self): return f"{self.type} -> {self.user.username}"

    class Meta:
        verbose_name = "알림"
        verbose_name_plural = "알림"
