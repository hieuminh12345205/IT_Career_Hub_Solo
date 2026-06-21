from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http import HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView, ListView

from apps.jobs.models import Job
from apps.users.models import User

from .forms import ApplicationForm
from .models import Application


class CandidateRequiredMixin(UserPassesTestMixin):
    """Giới hạn view cho user có role Candidate."""

    raise_exception = True

    def test_func(self):
        return self.request.user.role == User.Role.CANDIDATE


class RecruiterRequiredMixin(UserPassesTestMixin):
    """Giới hạn view cho user có role Recruiter."""

    raise_exception = True

    def test_func(self):
        return self.request.user.role == User.Role.RECRUITER


class ApplicationCreateView(
    LoginRequiredMixin,
    CandidateRequiredMixin,
    CreateView,
):
    """Cho Candidate gửi một đơn ứng tuyển vào job được chọn."""

    model = Application
    form_class = ApplicationForm
    template_name = "applications/apply.html"
    success_url = reverse_lazy("applications:my_applications")

    def dispatch(self, request, *args, **kwargs):
        self.job = get_object_or_404(Job, pk=kwargs["job_pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(candidate=self.request.user, job=self.job)
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["job"] = self.job
        return context

    def form_valid(self, form):
        form.instance.candidate = self.request.user
        form.instance.job = self.job
        try:
            # Savepoint giúp request vẫn dùng được DB sau lỗi unique constraint.
            with transaction.atomic():
                response = super().form_valid(form)
        except IntegrityError:
            form.add_error(None, "Bạn đã ứng tuyển công việc này rồi.")
            return self.form_invalid(form)

        messages.success(self.request, "Ứng tuyển thành công.")
        return response


class MyApplicationsView(
    LoginRequiredMixin,
    CandidateRequiredMixin,
    ListView,
):
    """Hiển thị các đơn của Candidate đang đăng nhập."""

    model = Application
    template_name = "applications/my_applications.html"
    context_object_name = "applications"
    paginate_by = 10

    def get_queryset(self):
        return Application.objects.filter(
            candidate=self.request.user,
        ).select_related("job", "job__company")


class JobApplicantsView(
    LoginRequiredMixin,
    RecruiterRequiredMixin,
    ListView,
):
    """Hiển thị ứng viên của một job thuộc quyền quản lý của Recruiter."""

    model = Application
    template_name = "applications/job_applicants.html"
    context_object_name = "applications"
    paginate_by = 20

    def get_job(self):
        """Lấy job và đồng thời kiểm tra job thuộc công ty của Recruiter."""
        if not hasattr(self, "job"):
            self.job = get_object_or_404(
                Job.objects.select_related("company"),
                pk=self.kwargs["job_pk"],
                company__recruiter=self.request.user,
            )
        return self.job

    def get_queryset(self):
        return Application.objects.filter(
            job=self.get_job(),
        ).select_related("candidate")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["job"] = self.get_job()
        context["status_choices"] = Application.Status.choices
        return context


@login_required
@require_POST
def update_application_status(request, pk):
    """Cập nhật trạng thái bằng POST nếu Recruiter sở hữu job tương ứng."""
    if request.user.role != User.Role.RECRUITER:
        raise PermissionDenied

    application = get_object_or_404(
        Application.objects.select_related("job", "job__company"),
        pk=pk,
        job__company__recruiter=request.user,
    )
    new_status = request.POST.get("status")

    if new_status not in Application.Status.values:
        return HttpResponseBadRequest("Trạng thái không hợp lệ.")

    application.status = new_status
    application.save(update_fields=["status"])
    messages.success(request, "Đã cập nhật trạng thái ứng tuyển.")
    return redirect(
        "applications:job_applicants",
        job_pk=application.job_id,
    )
