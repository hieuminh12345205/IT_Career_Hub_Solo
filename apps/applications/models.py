from django.db import models
from django.conf import settings
from apps.jobs.models import Job


class Application(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        REVIEWING = "reviewing", "Reviewing"
        ACCEPTED = "accepted", "Accepted"
        REJECTED = "rejected", "Rejected"

    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
    )

    cv = models.FileField(upload_to="cvs/")

    cover_letter = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    applied_at = models.DateTimeField(auto_now_add=True)


class Bookmark(models.Model):

    candidate = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    job = models.ForeignKey(
        Job,
        on_delete=models.CASCADE,
    )

    created_at = models.DateTimeField(auto_now_add=True)