from django.urls import path

from .views import (
    JobCreateView,
    JobDeleteView,
    JobDetailView,
    JobListView,
    JobUpdateView,
    RecruiterDashboardView,
    RecruiterJobListView,
)

app_name = "jobs"

urlpatterns = [
    path("", JobListView.as_view(), name="list"),
    path("dashboard/", RecruiterDashboardView.as_view(), name="dashboard"),
    path("manage/", RecruiterJobListView.as_view(), name="manage"),
    path("create/", JobCreateView.as_view(), name="create"),
    path("<int:pk>/", JobDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", JobUpdateView.as_view(), name="edit"),
    path("<int:pk>/delete/", JobDeleteView.as_view(), name="delete"),
]
