from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path, re_path

from apps.core.views import private_media_not_found

urlpatterns = [
    path("admin/", admin.site.urls),
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
]

if settings.DEBUG:
    urlpatterns += [
        re_path(
            r"^media/(?:application_cvs|cvs)/(?P<path>.*)$",
            private_media_not_found,
        ),
    ]
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )
