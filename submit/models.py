from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import random, string


# ===== 학생 프로필(선택) =====
class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, verbose_name="사용자")
    student_id = models.CharField("학번", max_length=20, unique=True)

    def __str__(self): return f"{self.user.username}({self.student_id})"

    class Meta:
        verbose_name = "학생 프로필"
        verbose_name_plural = "학생 프로필"


# ===== 팀(소그룹) =====
class Team(models.Model):
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="owned_teams", verbose_name="소유자(교수)"
    )
    name = models.CharField("팀명", max_length=100)
    description = models.TextField("설명", blank=True)

    # 전역 유니크 팀코드(6자리 숫자)
    join_code = models.CharField("팀코드", max_length=6, unique=True, editable=False)
    join_code_generated_at = models.DateTimeField("팀코드 발급일시", auto_now_add=True)

    created_at = models.DateTimeField("생성일시", auto_now_add=True)
    updated_at = models.DateTimeField("수정일시", auto_now=True)

    class Meta:
        verbose_name = "팀"
        verbose_name_plural = "팀"
        constraints = [
            models.UniqueConstraint(fields=["owner", "name"], name="uq_team_owner_name"),
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.name}"

    @staticmethod
    def _generate_code():
        return ''.join(random.choices(string.digits, k=6))

    def regen_join_code(self, save=True):
        # 유니크 보장 루프
        while True:
            code = self._generate_code()
            if not Team.objects.filter(join_code=code).exists():
                self.join_code = code
                self.join_code_generated_at = timezone.now()
                if save:
                    self.save(update_fields=["join_code", "join_code_generated_at"])
                return self.join_code

    def save(self, *args, **kwargs):
        if not self.join_code:
            self.regen_join_code(save=False)
        super().save(*args, **kwargs)


# ===== 팀 멤버십(가입 요청/승인/참가) =====
class TeamMembership(models.Model):
    STATUS = (
        ("PENDING", "대기"),
        ("APPROVED", "승인"),
        ("REJECTED", "거절"),
        ("LEFT", "탈퇴"),
    )
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="memberships", verbose_name="팀")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="team_memberships", verbose_name="학생")
    status = models.CharField("상태", max_length=10, choices=STATUS, default="PENDING")
    role = models.CharField("팀 역할", max_length=20, default="member", blank=True)

    requested_at = models.DateTimeField("요청일시", default=timezone.now)
    decided_at = models.DateTimeField("결정일시", null=True, blank=True)
    decided_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="decided_team_requests", verbose_name="결정자(교수)"
    )
    joined_at = models.DateTimeField("최종참가일시", null=True, blank=True)

    class Meta:
        verbose_name = "팀 멤버십"
        verbose_name_plural = "팀 멤버십"
        constraints = [
            models.UniqueConstraint(fields=["team", "student"], name="uq_team_student"),
        ]
        indexes = [
            models.Index(fields=["team", "status"]),
            models.Index(fields=["student", "status"]),
        ]

    def __str__(self):
        return f"{self.team} - {self.student.username} ({self.get_status_display()})"

    def approve(self, by_user):
        self.status = "APPROVED"
        now = timezone.now()
        self.decided_at = now
        self.decided_by = by_user
        # ✅ 승인과 동시에 합류 처리
        self.joined_at = now
        self.save(update_fields=["status", "decided_at", "decided_by", "joined_at"])


    def reject(self, by_user):
        self.status = "REJECTED"
        self.decided_at = timezone.now()
        self.decided_by = by_user
        self.save(update_fields=["status", "decided_at", "decided_by"])

    def join(self):
        if self.status != "APPROVED":
            raise ValueError("승인된 요청만 참가할 수 있습니다.")
        if not self.joined_at:
            self.joined_at = timezone.now()
            self.save(update_fields=["joined_at"])


# ===== 과제(팀 게시물) =====
class Assignment(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="assignments", verbose_name="팀")
    title = models.CharField("제목", max_length=120)
    description = models.TextField("설명", blank=True)
    due_at = models.DateTimeField("마감일시")

    max_score = models.PositiveIntegerField("배점", default=100)
    late_policy = models.CharField("지연 정책", max_length=50, blank=True)   # 예: "accept -10/day"
    file_rules = models.CharField("파일 규칙", max_length=100, blank=True)   # 예: "pdf,zip; 20MB"

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name="등록자(교수)")
    created_at = models.DateTimeField("생성일시", auto_now_add=True)
    updated_at = models.DateTimeField("수정일시", auto_now=True)

    is_closed = models.BooleanField("마감됨", default=False)

    def __str__(self): return f"{self.title} [{self.team.name}]"

    class Meta:
        verbose_name = "과제"
        verbose_name_plural = "과제"
        ordering = ["due_at"]


# ===== 제출/파일/성적 =====
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
        constraints = [
            models.UniqueConstraint(fields=["assignment", "student"], name="uq_assignment_student"),
        ]
    def __str__(self): return f"{self.assignment} / {self.student.username}"


class SubmissionFile(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="files", verbose_name="제출")
    file = models.FileField("파일", upload_to="submissions/")
    version = models.PositiveIntegerField("버전", default=1)
    size = models.PositiveIntegerField("크기(Byte)", default=0)

    def __str__(self): return f"{self.submission} v{self.version}"

    class Meta:
        verbose_name = "제출 파일"
        verbose_name_plural = "제출 파일"
        ordering = ["submission_id", "version"]


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


# ===== 알림 =====
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="대상 사용자")
    type = models.CharField("유형", max_length=30)  # 예: "team_join_request", "team_join_approved", "due_soon", "graded"
    payload = models.JSONField("추가 데이터", default=dict, blank=True)
    read_at = models.DateTimeField("읽은 시각", null=True, blank=True)
    created_at = models.DateTimeField("생성일시", auto_now_add=True)

    def __str__(self): return f"{self.type} -> {self.user.username}"

    class Meta:
        verbose_name = "알림"
        verbose_name_plural = "알림"
        indexes = [
            models.Index(fields=["user", "type"]),
            models.Index(fields=["created_at"]),
        ]
