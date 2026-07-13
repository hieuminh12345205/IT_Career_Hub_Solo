from django.core.exceptions import ValidationError
from django.db import models

from apps.companies.models import Company


class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class Job(models.Model):
    JOB_TYPE_LABELS_VI = {
        "full_time": "Toàn thời gian",
        "part_time": "Bán thời gian",
        "intern": "Thực tập",
    }
    EXPERIENCE_LABELS_VI = {
        "intern": "Thực tập sinh",
        "junior": "Junior",
        "middle": "Middle",
        "senior": "Senior",
    }

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

    def clean(self):
        """Validate salary bounds for every ModelForm, including Django Admin."""
        super().clean()
        errors = {}

        if self.salary_min is not None and self.salary_min < 0:
            errors["salary_min"] = "Mức lương tối thiểu không được là số âm."
        if self.salary_max is not None and self.salary_max < 0:
            errors["salary_max"] = "Mức lương tối đa không được là số âm."
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            errors["salary_max"] = (
                "Mức lương tối đa phải lớn hơn hoặc bằng mức lương tối thiểu."
            )

        if errors:
            raise ValidationError(errors)

    @staticmethod
    def _format_vnd(value):
        return f"{value:,}".replace(",", ".")

    @property
    def salary_display(self):
        if self.salary_min is not None and self.salary_max is not None:
            if self.salary_min == self.salary_max:
                return f"{self._format_vnd(self.salary_min)} VNĐ"
            return (
                f"{self._format_vnd(self.salary_min)} - "
                f"{self._format_vnd(self.salary_max)} VNĐ"
            )
        if self.salary_min is not None:
            return f"Từ {self._format_vnd(self.salary_min)} VNĐ"
        if self.salary_max is not None:
            return f"Đến {self._format_vnd(self.salary_max)} VNĐ"
        return "Thỏa thuận"

    @property
    def job_type_display_vi(self):
        return self.JOB_TYPE_LABELS_VI.get(self.job_type, self.get_job_type_display())

    @property
    def experience_level_display_vi(self):
        return self.EXPERIENCE_LABELS_VI.get(
            self.experience_level,
            self.get_experience_level_display(),
        )

    def __str__(self):
        return self.title
