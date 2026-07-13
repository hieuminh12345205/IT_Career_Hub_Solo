from django.contrib import admin

from .models import Job, Skill


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "company",
        "job_type",
        "experience_level",
        "location",
        "is_active",
        "created_at",
    )
    list_filter = (
        "is_active",
        "job_type",
        "experience_level",
        "company",
    )
    search_fields = ("title", "description", "company__name", "location")
    autocomplete_fields = ("company", "skills")
    list_editable = ("is_active",)
    list_select_related = ("company",)
    date_hierarchy = "created_at"
    ordering = ("-created_at",)


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    ordering = ("name",)
