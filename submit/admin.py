from django.contrib import admin
from .models import (
    StudentProfile,
    Team, TeamMembership,
    Assignment, Submission, SubmissionFile, Grade,
    Notification,
)

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "student_id")
    search_fields = ("user__username", "student_id")

@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "owner", "join_code", "join_code_generated_at", "created_at")
    search_fields = ("name", "join_code", "owner__username")
    list_filter = ("owner",)
    ordering = ("name",)

@admin.register(TeamMembership)
class TeamMembershipAdmin(admin.ModelAdmin):
    list_display = ("id", "team", "student", "status", "requested_at", "decided_at", "joined_at")
    list_filter = ("status", "team", "team__owner")
    search_fields = ("student__username", "team__name", "team__join_code")

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "team", "due_at", "max_score", "created_by", "created_at")
    list_filter = ("team", "team__owner")
    search_fields = ("title", "team__name")

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "assignment", "student", "status", "submitted_at")
    list_filter = ("status", "assignment__team")
    search_fields = ("assignment__title", "student__username")

@admin.register(SubmissionFile)
class SubmissionFileAdmin(admin.ModelAdmin):
    list_display = ("id", "submission", "version", "size")

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("id", "submission", "score", "grader", "graded_at")
    list_filter = ("grader",)

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "type", "created_at", "read_at")
    list_filter = ("type", "user")
    search_fields = ("user__username", "type")
