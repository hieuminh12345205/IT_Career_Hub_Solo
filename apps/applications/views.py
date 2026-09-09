import logging
from functools import partial
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.http import FileResponse, Http404, HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import CreateView, ListView

from apps.jobs.models import Job
from apps.jobs.services import is_recruiter_or_admin, jobs_managed_by
from apps.users.models import User

from .forms import ApplicationForm
from .models import Application, Bookmark
from .notifications import (
    notify_candidate_status_changed,
    notify_recruiters_new_application,
)

logger = logging.getLogger(__name__)


class RoleRequiredMixin(UserPassesTestMixin):
    """Redirect anonymous users, but return 403 for an authenticated wrong role."""

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            raise PermissionDenied
        return super().handle_no_permission()


class CandidateRequiredMixin(RoleRequiredMixin):
    """Giới hạn view cho user có role Candidate."""

    def test_func(self):
        return self.request.user.role == User.Role.CANDIDATE


class RecruiterRequiredMixin(RoleRequiredMixin):
    """Giới hạn view cho user có role Recruiter."""

    def test_func(self):
        return is_recruiter_or_admin(self.request.user)


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

    def get_job(self):
        if not hasattr(self, "job"):
            # Do not expose an application form for a job that is already
            # closed. ApplicationForm still checks this invariant to cover a
            # job being closed between this lookup and form submission.
            self.job = get_object_or_404(
                Job,
                pk=self.kwargs["job_pk"],
                is_active=True,
            )
        return self.job

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(candidate=self.request.user, job=self.get_job())
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["job"] = self.get_job()
        context["is_bookmarked"] = Bookmark.objects.filter(
            candidate=self.request.user,
            job=self.get_job(),
        ).exists()
        return context

    def form_valid(self, form):
        form.instance.candidate = self.request.user
        try:
            with transaction.atomic():
                # Đọc lại dưới khóa: tin có thể đã đóng từ lúc form được kiểm tra.
                job = get_object_or_404(
                    Job.objects.select_for_update(), pk=self.get_job().pk
                )
                if not job.is_active:
                    form.add_error(None, "Công việc này đã đóng ứng tuyển.")
                    return self.form_invalid(form)
                if Application.objects.filter(
                    candidate=self.request.user, job=job
                ).exists():
                    form.add_error(None, "Bạn đã ứng tuyển công việc này rồi.")
                    return self.form_invalid(form)
                form.instance.job = job
                response = super().form_valid(form)
                transaction.on_commit(
                    partial(notify_recruiters_new_application, self.object), robust=True
                )
                transaction.on_commit(
                    partial(
                        logger.info,
                        "application_created actor_id=%s application_id=%s job_id=%s",
                        self.request.user.pk,
                        self.object.pk,
                        job.pk,
                    )
                )
        except IntegrityError:
            # Không che các lỗi dữ liệu khác bằng thông báo đơn trùng.
            if not Application.objects.filter(
                candidate=self.request.user, job_id=self.get_job().pk
            ).exists():
                raise
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


class MyBookmarksView(
    LoginRequiredMixin,
    CandidateRequiredMixin,
    ListView,
):
    """Hiển thị các công việc Candidate hiện tại đã lưu."""

    model = Bookmark
    template_name = "applications/my_bookmarks.html"
    context_object_name = "bookmarks"
    paginate_by = 10

    def get_queryset(self):
        return Bookmark.objects.filter(
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
                jobs_managed_by(self.request.user).select_related("company"),
                pk=self.kwargs["job_pk"],
            )
        return self.job

    def get_queryset(self):
        return Application.objects.filter(
            job=self.get_job(),
        ).select_related("candidate", "candidate__candidate_profile")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["job"] = self.get_job()
        context["status_choices"] = Application.Status.choices
        return context


@login_required
@require_GET
def download_application_cv(request, pk):
    """Stream a CV only to recruiters who manage its job, or to an admin."""
    if not is_recruiter_or_admin(request.user):
        raise PermissionDenied

    application = get_object_or_404(
        Application.objects.select_related("job", "job__company"),
        pk=pk,
        job__in=jobs_managed_by(request.user),
    )
    if not application.cv:
        raise Http404

    try:
        application.cv.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        raise Http404 from None

    filename = Path(application.cv.name).name or "cv.pdf"
    response = FileResponse(
        application.cv,
        as_attachment=True,
        filename=filename,
        content_type="application/pdf",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@login_required
@require_POST
def update_application_status(request, pk):
    """Cập nhật trạng thái bằng POST nếu Recruiter sở hữu job tương ứng."""
    if not is_recruiter_or_admin(request.user):
        raise PermissionDenied

    new_status = request.POST.get("status")

    if new_status not in Application.Status.values:
        return HttpResponseBadRequest("Trạng thái không hợp lệ.")

    with transaction.atomic():
        application = get_object_or_404(
            Application.objects.select_for_update(),
            pk=pk,
            job__in=jobs_managed_by(request.user),
        )
        if application.status != new_status:
            old_status = application.status
            application.status = new_status
            application.save(update_fields=["status"])
            transaction.on_commit(
                partial(notify_candidate_status_changed, application), robust=True
            )
            transaction.on_commit(
                partial(
                    logger.info,
                    "application_status_changed actor_id=%s application_id=%s "
                    "old_status=%s new_status=%s",
                    request.user.pk,
                    application.pk,
                    old_status,
                    new_status,
                )
            )
            messages.success(request, "Đã cập nhật trạng thái ứng tuyển.")
        else:
            messages.info(request, "Trạng thái ứng tuyển không thay đổi.")

    return redirect(
        "applications:job_applicants",
        job_pk=application.job_id,
    )


@login_required
@require_POST
def toggle_bookmark(request, job_pk):
    """Thêm hoặc xóa bookmark của Candidate bằng một endpoint POST."""
    if request.user.role != User.Role.CANDIDATE:
        raise PermissionDenied

    with transaction.atomic():
        # Khóa user để hai lần toggle cùng lúc vẫn được xử lý theo thứ tự.
        User.objects.select_for_update().get(pk=request.user.pk)
        job = get_object_or_404(Job, pk=job_pk)
        existing = Bookmark.objects.filter(candidate=request.user, job=job).first()

        if existing:
            existing.delete()
            created = False
        else:
            if not job.is_active:
                raise Http404
            _, created = Bookmark.objects.get_or_create(candidate=request.user, job=job)
    messages.success(
        request, "Đã lưu công việc." if created else "Đã bỏ lưu công việc."
    )

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"bookmarked": created})

    next_url = request.POST.get("next")
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)

    return redirect("applications:my_bookmarks")
