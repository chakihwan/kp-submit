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
from django.contrib.auth import views as auth_views
from submit import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # 앱 뷰
    path("", views.dashboard, name="dashboard"),  # <- 반드시 루트에 연결!
    path("assignments/", views.assignments_list, name="assignments_list"),
    # path("submissions/new/", views.submission_form, name="submission_form"),
    path("grading/", views.grading, name="grading"),
    path("notifications/", views.notifications, name="notifications"),

    # 인증
    path("accounts/login/",  auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/signup/", views.signup, name="signup"),  # 회원가입 

    path("assignments/<int:pk>/", views.assignment_detail, name="assignment_detail"),
    path("assignments/<int:assignment_id>/submit/", views.submission_form, name="submission_form"),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)