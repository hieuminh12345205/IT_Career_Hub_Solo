from pathlib import Path

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET
from django.views.generic import TemplateView, UpdateView

from .forms import (
    CandidateProfileForm,
    CandidateSignUpForm,
    RecruiterProfileForm,
    RecruiterSignUpForm,
    UserUpdateForm,
)
from .models import CandidateProfile, RecruiterProfile, User


class RoleRequiredMixin(UserPassesTestMixin):
    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class CandidateRequiredMixin(RoleRequiredMixin):
    def test_func(self):
        return self.request.user.role == User.Role.CANDIDATE


class RecruiterRequiredMixin(RoleRequiredMixin):
    def test_func(self):
        return self.request.user.role == User.Role.RECRUITER


def signup_choice(request):
    return render(request, "users/signup.html")


def candidate_signup(request):
    if request.method == "POST":
        form = CandidateSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Đăng ký Candidate thành công.")
            return redirect("users:candidate_profile")
    else:
        form = CandidateSignUpForm()
    return render(
        request,
        "users/signup_form.html",
        {"form": form, "title": "Đăng ký Candidate"},
    )


def recruiter_signup(request):
    if request.method == "POST":
        form = RecruiterSignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Đăng ký Recruiter thành công.")
            return redirect("companies:manage_company")
    else:
        form = RecruiterSignUpForm()
    return render(
        request,
        "users/signup_form.html",
        {"form": form, "title": "Đăng ký Recruiter"},
    )


@require_GET
@login_required
def candidate_cv(request):
    """Stream the current candidate's CV only to that authenticated user."""
    if request.user.role != User.Role.CANDIDATE:
        raise PermissionDenied
    profile = getattr(request.user, "candidate_profile", None)
    if not profile or not profile.cv_file:
        raise Http404
    return FileResponse(
        profile.cv_file.open("rb"),
        as_attachment=False,
        filename=Path(profile.cv_file.name).name,
        content_type="application/pdf",
    )


class ProfileRedirectView(LoginRequiredMixin, TemplateView):
    def get(self, request, *args, **kwargs):
        if request.user.is_staff or request.user.role == User.Role.ADMIN:
            return redirect("admin:index")
        if request.user.role == User.Role.RECRUITER:
            return redirect("users:recruiter_profile")
        return redirect("users:candidate_profile")


class CandidateProfileUpdateView(
    LoginRequiredMixin, CandidateRequiredMixin, UpdateView
):
    model = CandidateProfile
    form_class = CandidateProfileForm
    template_name = "users/candidate_profile_form.html"
    success_url = reverse_lazy("users:candidate_profile")

    def get_object(self, queryset=None):
        profile, _ = CandidateProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            context["user_form"] = UserUpdateForm(
                self.request.POST,
                self.request.FILES,
                instance=self.request.user,
            )
        else:
            context["user_form"] = UserUpdateForm(instance=self.request.user)
        return context

    def form_valid(self, form):
        user_form = UserUpdateForm(
            self.request.POST,
            self.request.FILES,
            instance=self.request.user,
        )
        if not user_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            user_form.save()
            response = super().form_valid(form)
        messages.success(self.request, "Đã cập nhật hồ sơ Candidate.")
        return response


class RecruiterProfileUpdateView(
    LoginRequiredMixin, RecruiterRequiredMixin, UpdateView
):
    model = RecruiterProfile
    form_class = RecruiterProfileForm
    template_name = "users/recruiter_profile_form.html"
    success_url = reverse_lazy("users:recruiter_profile")

    def get_object(self, queryset=None):
        profile, _ = RecruiterProfile.objects.get_or_create(user=self.request.user)
        return profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.method == "POST":
            context["user_form"] = UserUpdateForm(
                self.request.POST,
                self.request.FILES,
                instance=self.request.user,
            )
        else:
            context["user_form"] = UserUpdateForm(instance=self.request.user)
        return context

    def form_valid(self, form):
        user_form = UserUpdateForm(
            self.request.POST,
            self.request.FILES,
            instance=self.request.user,
        )
        if not user_form.is_valid():
            return self.form_invalid(form)
        with transaction.atomic():
            user_form.save()
            response = super().form_valid(form)
        messages.success(self.request, "Đã cập nhật hồ sơ Recruiter.")
        return response
