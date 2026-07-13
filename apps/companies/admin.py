from django.contrib import admin

from .models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "recruiter", "location", "website", "created_at")
    list_filter = ("location", "created_at")
    search_fields = (
        "name",
        "description",
        "location",
        "recruiter__username",
        "recruiter__email",
    )
    autocomplete_fields = ("recruiter",)
    list_select_related = ("recruiter",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)
