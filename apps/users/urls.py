from django.contrib.auth import views as auth_views
from django.urls import path

from .views import (
    CandidateProfileUpdateView,
    ProfileRedirectView,
    RecruiterProfileUpdateView,
    candidate_cv,
    candidate_signup,
    recruiter_signup,
    signup_choice,
)

app_name = "users"

urlpatterns = [
    path(
        "login/",
        auth_views.LoginView.as_view(template_name="users/login.html"),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("signup/", signup_choice, name="signup"),
    path("signup/candidate/", candidate_signup, name="candidate_signup"),
    path("signup/recruiter/", recruiter_signup, name="recruiter_signup"),
    path("candidate/cv/", candidate_cv, name="candidate_cv"),
    path("profile/", ProfileRedirectView.as_view(), name="profile"),
    path(
        "candidate/profile/",
        CandidateProfileUpdateView.as_view(),
        name="candidate_profile",
    ),
    path(
        "recruiter/profile/",
        RecruiterProfileUpdateView.as_view(),
        name="recruiter_profile",
    ),
]
