from django.contrib import admin

# Register your models here.


admin.site.site_header = "AISW 과제 관리자 시스템"
admin.site.site_title  = "Admin"
admin.site.index_title = "AISW"

# submit/admin.py
from django.contrib import admin
from .models import (
    StudentProfile, Course, Enrollment, Assignment,
    Submission, SubmissionFile, Grade, Notification
)

@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "student_id")
    search_fields = ("user__username", "student_id")

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "teacher")
    search_fields = ("code", "title", "teacher__username")

# @admin.register(Enrollment)
# class EnrollmentAdmin(admin.ModelAdmin):
#     list_display = ("user", "course", "role_in_course")
#     list_filter = ("role_in_course", "course")
#     search_fields = ("user__username", "course__title")

@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ("title", "course", "due_at", "max_score", "created_at")
    list_filter = ("course",)
    search_fields = ("title", "course__title")
    date_hierarchy = "due_at"

@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("assignment", "student", "status", "submitted_at")
    list_filter = ("status", "assignment__course")
    search_fields = ("assignment__title", "student__username")

@admin.register(SubmissionFile)
class SubmissionFileAdmin(admin.ModelAdmin):
    list_display = ("submission", "version", "size")
    search_fields = ("submission__assignment__title", "submission__student__username")

@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = ("submission", "score", "grader", "graded_at")
    list_filter = ("grader",)
    search_fields = ("submission__assignment__title", "submission__student__username")

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("type", "user", "created_at", "read_at")
    list_filter = ("type",)
    search_fields = ("user__username", "type")

