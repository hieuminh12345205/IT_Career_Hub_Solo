from django.urls import path

from .views import CompanyDetailView, CompanyListView, ManageCompanyView

app_name = "companies"

urlpatterns = [
    path("", CompanyListView.as_view(), name="list"),
    path("manage/", ManageCompanyView.as_view(), name="manage_company"),
    path("<int:pk>/", CompanyDetailView.as_view(), name="detail"),
]
