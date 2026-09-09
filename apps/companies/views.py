from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Prefetch, Q
from django.urls import reverse_lazy
from django.views.generic import DetailView, ListView, UpdateView

from apps.jobs.models import Job
from apps.jobs.services import is_recruiter_or_admin

from .forms import CompanyForm
from .models import Company


class RecruiterRequiredMixin(LoginRequiredMixin):
    """Chỉ Recruiter (và Admin) mới vào được trang quản lý công ty."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not is_recruiter_or_admin(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class CompanyListView(ListView):
    model = Company
    template_name = "companies/company_list.html"
    context_object_name = "companies"
    paginate_by = 12

    def get_queryset(self):
        return (
            Company.objects.select_related("recruiter")
            .annotate(open_job_count=Count("job", filter=Q(job__is_active=True)))
            .order_by("name")
        )


class CompanyDetailView(DetailView):
    model = Company
    template_name = "companies/company_detail.html"
    context_object_name = "company"

    def get_queryset(self):
        # Lọc tin đang tuyển ngay ở tầng query để {% empty %} trong template
        # phản ánh đúng "không có tin nào đang mở".
        return Company.objects.select_related("recruiter").prefetch_related(
            Prefetch(
                "job_set",
                queryset=Job.objects.filter(is_active=True)
                .prefetch_related("skills")
                .order_by("-created_at"),
                to_attr="open_jobs",
            )
        )


class ManageCompanyView(RecruiterRequiredMixin, UpdateView):
    model = Company
    form_class = CompanyForm
    template_name = "companies/company_form.html"
    success_url = reverse_lazy("companies:manage_company")

    def get_object(self, queryset=None):
        # A recruiter can own one company and can also be assigned to another
        # one as a member. Always prefer the owned company so membership can
        # never be used to replace or transfer its owner.
        owned_company = Company.objects.filter(recruiter=self.request.user).first()
        if owned_company:
            return owned_company

        profile = getattr(self.request.user, "recruiter_profile", None)
        if profile and profile.company_id:
            return profile.company

        return Company(recruiter=self.request.user)

    @transaction.atomic
    def form_valid(self, form):
        is_new_company = form.instance.pk is None
        if is_new_company:
            form.instance.recruiter = self.request.user

        response = super().form_valid(form)
        profile = getattr(self.request.user, "recruiter_profile", None)
        # Link a new/unassigned recruiter profile, but preserve an existing
        # membership. In particular, editing an assigned company must not
        # silently turn the member into its owner.
        if profile and profile.company_id is None:
            profile.company = self.object
            profile.save(update_fields=["company", "updated_at"])
        messages.success(self.request, "Đã lưu thông tin công ty.")
        return response
