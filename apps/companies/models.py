from django.db import models
from django.conf import settings


class Company(models.Model):

    recruiter = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    name = models.CharField(max_length=255)

    description = models.TextField()

    website = models.URLField(blank=True)

    logo = models.ImageField(
        upload_to="company_logos/",
        blank=True,
        null=True,
    )

    location = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name