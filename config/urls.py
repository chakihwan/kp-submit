"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from submit import views
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.teacher_team_list, name='root'), 

    # 인증
    path('accounts/login/', views.MyLoginView.as_view(), name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/signup/', views.signup, name='signup'),

    # 팀
    path('teams', views.teacher_team_list, name='teacher_team_list'),
    path('teams/create', views.create_team, name='create_team'),
    path('teams/join', views.join_page, name='team_join_page'),
    path('teams/<int:team_id>', views.team_detail, name='team_detail'),
    path('teams/<int:team_id>/regen_code', views.regen_team_code, name='regen_team_code'),
    path('teams/<int:team_id>/requests', views.list_team_requests, name='team_request_list'),
    path('teams/requests/<int:membership_id>/approve', views.approve_team_request, name='team_request_approve'),
    path('teams/requests/<int:membership_id>/reject', views.reject_team_request, name='team_request_reject'),
    path('teams/request_by_code', views.request_join_by_code, name='team_request_by_code'),
    path('teams/<int:team_id>/join', views.join_team, name='team_join'),
    path('teams/<int:team_id>/delete', views.team_delete, name='team_delete'),
    
    #  과제: 생성/상세/제출/제출목록
    path('teams/<int:team_id>/assignments/create', views.assignment_create, name='assignment_create'),
    path('teams/<int:team_id>/assignments/<int:assignment_id>', views.assignment_detail, name='assignment_detail'),
    path('teams/<int:team_id>/assignments/<int:assignment_id>/submit', views.assignment_submit, name='assignment_submit'),
    path('teams/<int:team_id>/assignments/<int:assignment_id>/submissions', views.assignment_submissions, name='assignment_submissions'),
    path("teams/<int:team_id>/assignments/", views.assignment_list, name="assignment_list"),


    # 채점 (단일 제출 채점 페이지)
    path('teams/<int:team_id>/assignments/<int:assignment_id>/grade/<int:submission_id>',
        views.grade_submission, name='grade_submission'),

    # 과제 마감/해제
    path('teams/<int:team_id>/assignments/<int:assignment_id>/close',
        views.assignment_close, name='assignment_close'),
    path('teams/<int:team_id>/assignments/<int:assignment_id>/reopen',
        views.assignment_reopen, name='assignment_reopen'),
]
