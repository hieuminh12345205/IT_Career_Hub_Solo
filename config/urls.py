from django.conf import settings
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path

from apps.core.views import private_media_not_found, public_media

urlpatterns = [
    path("admin/", admin.site.urls),
    # Đây là route đăng nhập duy nhất của dự án (trùng với settings.LOGIN_URL).
    path(
        "accounts/login/",
        auth_views.LoginView.as_view(template_name="users/login.html"),
        name="login",
    ),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("", include("apps.core.urls")),
    path("users/", include("apps.users.urls")),
    path("jobs/", include("apps.jobs.urls")),
    path("companies/", include("apps.companies.urls")),
    path("applications/", include("apps.applications.urls")),
    # CV luôn phải đi qua view có kiểm quyền, kể cả khi DEBUG bật static handler.
    re_path(
        r"^media/(?:application_cvs|cvs)/(?P<path>.*)$",
        private_media_not_found,
    ),
    # Ảnh public phục vụ được ở cả dev lẫn prod (DEBUG=False vẫn hiện logo/avatar).
    re_path(r"^media/(?P<path>.*)$", public_media),
]

if settings.DEBUG and "debug_toolbar" in settings.INSTALLED_APPS:
    urlpatterns.insert(0, path("__debug__/", include("debug_toolbar.urls")))
