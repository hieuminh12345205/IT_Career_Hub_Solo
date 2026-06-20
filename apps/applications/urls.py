from django.urls import path

from .views import (
    ApplicationCreateView,
    JobApplicantsView,
    MyApplicationsView,
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
    path(
        "jobs/<int:job_pk>/applicants/",
        JobApplicantsView.as_view(),
        name="job_applicants",
    ),
    path(
        "<int:pk>/status/",
        update_application_status,
        name="update_status",
    ),
]
