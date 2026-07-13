from django.urls import path

from .views import (
    ApplicationCreateView,
    JobApplicantsView,
    MyApplicationsView,
    MyBookmarksView,
    download_application_cv,
    toggle_bookmark,
    update_application_status,
)

app_name = "applications"

urlpatterns = [
    path(
        "jobs/<int:job_pk>/apply/",
        ApplicationCreateView.as_view(),
        name="apply",
    ),
    path("mine/", MyApplicationsView.as_view(), name="my_applications"),
    path("bookmarks/", MyBookmarksView.as_view(), name="my_bookmarks"),
    path(
        "jobs/<int:job_pk>/bookmark/",
        toggle_bookmark,
        name="toggle_bookmark",
    ),
    path(
        "jobs/<int:job_pk>/applicants/",
        JobApplicantsView.as_view(),
        name="job_applicants",
    ),
    path("<int:pk>/cv/", download_application_cv, name="download_cv"),
    path(
        "<int:pk>/status/",
        update_application_status,
        name="update_status",
    ),
]
