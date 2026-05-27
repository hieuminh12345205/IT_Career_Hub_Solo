from django.contrib import admin

from .models import Application, CandidateProfile, RecruiterProfile


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ("full_name", "user", "phone", "created_at")
    search_fields = ("full_name", "user__username", "user__email", "phone")
    filter_horizontal = ("skills",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "position", "created_at")
    search_fields = ("user__username", "user__email", "company__name", "position")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("candidate", "job", "status", "applied_at")
    list_filter = ("status", "applied_at")
    search_fields = ("candidate__full_name", "job__title")
    readonly_fields = ("applied_at",)

