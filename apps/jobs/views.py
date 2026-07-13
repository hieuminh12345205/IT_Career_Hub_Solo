from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import (
    CreateView,
    DeleteView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)

from apps.applications.models import Application, Bookmark
from apps.users.models import User

from .forms import JobFilterForm, JobForm
from .models import Job
from .services import is_admin, is_recruiter_or_admin, jobs_managed_by


class RecruiterRequiredMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not is_recruiter_or_admin(request.user):
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


class JobListView(ListView):
    model = Job
    template_name = "jobs/job_list.html"
    context_object_name = "jobs"
    paginate_by = 9

    def get_filter_form(self):
        if not hasattr(self, "filter_form"):
            self.filter_form = JobFilterForm(self.request.GET or None)
        return self.filter_form

    def get_queryset(self):
        queryset = (
            Job.objects.filter(is_active=True)
            .select_related("company")
            .prefetch_related("skills")
            .order_by("-created_at")
        )
        form = self.get_filter_form()
        if form.is_valid():
            q = form.cleaned_data.get("q")
            location = form.cleaned_data.get("location")
            skill = form.cleaned_data.get("skill")
            salary_min = form.cleaned_data.get("salary_min")
            salary_max = form.cleaned_data.get("salary_max")
            job_type = form.cleaned_data.get("job_type")
            experience_level = form.cleaned_data.get("experience_level")
            if q:
                queryset = queryset.filter(
                    Q(title__icontains=q)
                    | Q(description__icontains=q)
                    | Q(company__name__icontains=q)
                    | Q(skills__name__icontains=q)
                )
            if location:
                queryset = queryset.filter(location__icontains=location)
            if skill:
                queryset = queryset.filter(skills=skill)
            if salary_min is not None:
                queryset = queryset.filter(
                    Q(salary_max__gte=salary_min)
                    | Q(salary_max__isnull=True, salary_min__isnull=False)
                )
            if salary_max is not None:
                queryset = queryset.filter(
                    Q(salary_min__lte=salary_max)
                    | Q(salary_min__isnull=True, salary_max__isnull=False)
                )
            if job_type:
                queryset = queryset.filter(job_type=job_type)
            if experience_level:
                queryset = queryset.filter(experience_level=experience_level)
        return queryset.distinct()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.get_filter_form()
        query_params = self.request.GET.copy()
        query_params.pop("page", None)
        context["query_string"] = query_params.urlencode()
        return context


class JobDetailView(DetailView):
    model = Job
    template_name = "jobs/job_detail.html"
    context_object_name = "job"

    def get_queryset(self):
        queryset = Job.objects.select_related("company").prefetch_related("skills")
        user = self.request.user

        if is_admin(user):
            return queryset
        if not user.is_authenticated:
            return queryset.filter(is_active=True)
        if user.role == User.Role.RECRUITER:
            return queryset.filter(
                Q(is_active=True) | Q(pk__in=jobs_managed_by(user).values("pk"))
            ).distinct()
        if user.role == User.Role.CANDIDATE:
            return queryset.filter(
                Q(is_active=True)
                | Q(applications__candidate=user)
                | Q(bookmarks__candidate=user)
            ).distinct()
        return queryset.filter(is_active=True)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context["is_bookmarked"] = False
        context["has_applied"] = False
        context["can_manage_job"] = False
        if user.is_authenticated and user.role == User.Role.CANDIDATE:
            context["is_bookmarked"] = Bookmark.objects.filter(
                candidate=user,
                job=self.object,
            ).exists()
            context["has_applied"] = Application.objects.filter(
                candidate=user,
                job=self.object,
            ).exists()
        if is_recruiter_or_admin(user):
            context["can_manage_job"] = (
                jobs_managed_by(user)
                .filter(
                    pk=self.object.pk,
                )
                .exists()
            )
        return context


class RecruiterDashboardView(RecruiterRequiredMixin, TemplateView):
    template_name = "jobs/recruiter_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        managed_jobs = jobs_managed_by(self.request.user)
        job_stats = managed_jobs.aggregate(
            total_jobs=Count("id"),
            open_jobs=Count("id", filter=Q(is_active=True)),
        )
        application_stats = Application.objects.filter(job__in=managed_jobs).aggregate(
            total_applications=Count("id"),
            pending_applications=Count(
                "id",
                filter=Q(status=Application.Status.PENDING),
            ),
            reviewing_applications=Count(
                "id",
                filter=Q(status=Application.Status.REVIEWING),
            ),
            accepted_applications=Count(
                "id",
                filter=Q(status=Application.Status.ACCEPTED),
            ),
            rejected_applications=Count(
                "id",
                filter=Q(status=Application.Status.REJECTED),
            ),
        )
        context.update(job_stats)
        context.update(application_stats)
        context["recent_jobs"] = managed_jobs.select_related("company").order_by(
            "-created_at"
        )[:5]
        return context


class RecruiterJobListView(RecruiterRequiredMixin, ListView):
    model = Job
    template_name = "jobs/recruiter_job_list.html"
    context_object_name = "jobs"
    paginate_by = 10

    def get_queryset(self):
        return (
            jobs_managed_by(self.request.user)
            .select_related("company")
            .order_by("-created_at")
        )


class RecruiterJobMixin(RecruiterRequiredMixin):
    model = Job
    form_class = JobForm
    template_name = "jobs/job_form.html"
    success_url = reverse_lazy("jobs:manage")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if not is_admin(self.request.user):
            kwargs["recruiter"] = self.request.user
        return kwargs

    def form_valid(self, form):
        if (
            not is_admin(self.request.user)
            and not form.fields["company"]
            .queryset.filter(pk=form.instance.company_id)
            .exists()
        ):
            raise PermissionDenied
        messages.success(self.request, "Đã lưu tin tuyển dụng.")
        return super().form_valid(form)


class JobCreateView(RecruiterJobMixin, CreateView):
    pass


class JobUpdateView(RecruiterJobMixin, UpdateView):
    def get_queryset(self):
        return jobs_managed_by(self.request.user)


class JobDeleteView(RecruiterRequiredMixin, DeleteView):
    model = Job
    template_name = "jobs/job_confirm_delete.html"
    success_url = reverse_lazy("jobs:manage")

    def get_queryset(self):
        return jobs_managed_by(self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Đã xóa tin tuyển dụng.")
        return super().form_valid(form)
