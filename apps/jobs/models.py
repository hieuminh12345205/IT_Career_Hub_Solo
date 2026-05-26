from django.db import models
from apps.companies.models import Company


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Job(models.Model):

    class JobType(models.TextChoices):
        FULL_TIME = "full_time", "Full Time"
        PART_TIME = "part_time", "Part Time"
        INTERN = "intern", "Intern"

    class ExperienceLevel(models.TextChoices):
        INTERN = "intern", "Intern"
        JUNIOR = "junior", "Junior"
        MIDDLE = "middle", "Middle"
        SENIOR = "senior", "Senior"

    company = models.ForeignKey(
        Company,
        on_delete=models.CASCADE,
    )

    title = models.CharField(max_length=255)

    description = models.TextField()

    requirement = models.TextField()

    skills = models.ManyToManyField(Skill)

    salary_min = models.IntegerField(
        null=True,
        blank=True,
    )

    salary_max = models.IntegerField(
        null=True,
        blank=True,
    )

    location = models.CharField(max_length=255)

    job_type = models.CharField(
        max_length=20,
        choices=JobType.choices,
    )

    experience_level = models.CharField(
        max_length=20,
        choices=ExperienceLevel.choices,
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title