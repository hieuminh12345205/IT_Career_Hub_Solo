from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import CandidateProfile, RecruiterProfile, User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = (
        "username",
        "email",
        "role",
        "phone",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = ("role", "is_staff", "is_active", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name", "phone")
    readonly_fields = ("created_at",)
    fieldsets = UserAdmin.fieldsets + (
        (
            "IT Career Hub",
            {
                "fields": (
                    "role",
                    "phone",
                    "avatar",
                    "bio",
                    "created_at",
                )
            },
        ),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "IT Career Hub",
            {
                "classes": ("wide",),
                "fields": ("role", "phone"),
            },
        ),
    )


@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "full_name",
        "experience_years",
        "location",
        "updated_at",
    )
    list_filter = ("experience_years", "location", "updated_at")
    list_select_related = ("user",)
    search_fields = ("user__username", "user__email", "full_name", "location")
    filter_horizontal = ("skills",)


@admin.register(RecruiterProfile)
class RecruiterProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company", "position", "updated_at")
    list_filter = ("company", "updated_at")
    list_select_related = ("user", "company")
    search_fields = (
        "user__username",
        "user__email",
        "company__name",
        "position",
    )
