from django.conf import settings
from django.db import models


class Company(models.Model):
    # SET_NULL: xóa tài khoản recruiter không được kéo theo công ty, tin tuyển
    # dụng và toàn bộ đơn ứng tuyển của ứng viên.
    recruiter = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="owned_company",
        verbose_name="Nhà tuyển dụng sở hữu",
    )

    name = models.CharField(max_length=255, verbose_name="Tên công ty")

    description = models.TextField(verbose_name="Giới thiệu")

    website = models.URLField(blank=True, verbose_name="Website")

    logo = models.ImageField(
        upload_to="company_logos/",
        blank=True,
        null=True,
        verbose_name="Logo",
    )

    location = models.CharField(max_length=255, verbose_name="Địa điểm")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Công ty"
        verbose_name_plural = "Công ty"
        indexes = [
            models.Index(fields=["name"], name="company_name_idx"),
        ]

    def __str__(self):
        return self.name
