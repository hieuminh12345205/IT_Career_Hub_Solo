from pathlib import Path, PurePosixPath

from django.conf import settings
from django.db.models import Count, Q
from django.http import Http404
from django.views.generic import TemplateView
from django.views.static import serve

from apps.applications.models import Application
from apps.companies.models import Company
from apps.jobs.models import Job, Skill

# Thư mục media chứa dữ liệu riêng tư, tuyệt đối không phục vụ qua URL công khai.
PRIVATE_MEDIA_PREFIXES = ("cvs", "application_cvs")

# Thư mục media công khai (ảnh hiển thị trên giao diện).
PUBLIC_MEDIA_PREFIXES = ("avatars", "company_logos")


def private_media_not_found(request, path=""):
    """Never expose CV storage through Django's development media handler."""
    raise Http404


def public_media(request, path):
    """Phục vụ ảnh public trong media/ ở cả dev lẫn prod.

    Chỉ nhận đúng các tiền tố trong PUBLIC_MEDIA_PREFIXES, nên không thể dùng
    view này để với tới thư mục CV. Ở môi trường thật nên đặt Nginx/CDN phía
    trước để không phải đẩy file tĩnh qua Python.
    """
    # Kiểm tra cả đường dẫn chuẩn hóa, không chỉ tiền tố trước dấu '/'.
    # Trên Windows, dấu '\\' cũng là dấu phân cách thư mục.
    parts = PurePosixPath(path.replace("\\", "/")).parts
    if not parts or parts[0] not in PUBLIC_MEDIA_PREFIXES or ".." in parts:
        raise Http404
    public_root = Path(settings.MEDIA_ROOT).resolve() / parts[0]
    target = public_root.joinpath(*parts[1:]).resolve()
    if public_root.is_symlink() or not target.is_relative_to(public_root):
        raise Http404
    return serve(
        request, str(target.relative_to(public_root)), document_root=public_root
    )


class HomeView(TemplateView):
    """Trang chủ hiển thị số liệu và tin tuyển dụng thật thay vì dữ liệu mẫu."""

    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        active_jobs = Job.objects.filter(is_active=True)
        context["latest_jobs"] = (
            active_jobs.select_related("company")
            .prefetch_related("skills")
            .order_by("-created_at")[:6]
        )
        context["top_companies"] = (
            Company.objects.annotate(
                open_job_count=Count("job", filter=Q(job__is_active=True))
            )
            .filter(open_job_count__gt=0)
            .order_by("-open_job_count", "name")[:6]
        )
        context["stat_open_jobs"] = active_jobs.count()
        context["stat_companies"] = Company.objects.count()
        context["stat_skills"] = Skill.objects.count()
        context["stat_applications"] = Application.objects.count()
        return context
