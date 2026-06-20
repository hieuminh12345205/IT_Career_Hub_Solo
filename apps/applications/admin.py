from django.contrib import admin

from .models import Application, Bookmark


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("candidate", "job", "status", "applied_at")
    list_filter = ("status", "applied_at")
    list_select_related = ("candidate", "job")
    search_fields = ("candidate__username", "candidate__email", "job__title")
    readonly_fields = ("applied_at",)


@admin.register(Bookmark)
class BookmarkAdmin(admin.ModelAdmin):
    list_display = ("candidate", "job", "created_at")
    list_filter = ("created_at",)
    list_select_related = ("candidate", "job")
    search_fields = ("candidate__username", "candidate__email", "job__title")
    readonly_fields = ("created_at",)
