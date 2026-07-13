from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.applications.models import Application, Bookmark
from apps.companies.models import Company
from apps.users.models import User

from .forms import JobFilterForm, JobForm
from .models import Job, Skill


class JobTestMixin:
    def create_user(self, username, role):
        return User.objects.create_user(
            username=username,
            password="test-password",
            role=role,
        )

    def create_job(self, company, title, **kwargs):
        defaults = {
            "description": "Mô tả",
            "requirement": "Yêu cầu",
            "salary_min": 10_000_000,
            "salary_max": 20_000_000,
            "location": "Hà Nội",
            "job_type": Job.JobType.FULL_TIME,
            "experience_level": Job.ExperienceLevel.JUNIOR,
            "is_active": True,
        }
        defaults.update(kwargs)
        return Job.objects.create(company=company, title=title, **defaults)


class JobValidationTests(JobTestMixin, TestCase):
    def setUp(self):
        self.recruiter = self.create_user("recruiter", User.Role.RECRUITER)
        self.company = Company.objects.create(
            recruiter=self.recruiter,
            name="Alpha Tech",
            description="Mô tả công ty",
            location="Hà Nội",
        )

    def test_model_rejects_negative_and_reversed_salary_ranges(self):
        negative_job = self.create_job(
            self.company,
            "Negative",
            salary_min=-1,
        )
        reversed_job = self.create_job(
            self.company,
            "Reversed",
            salary_min=30_000_000,
            salary_max=20_000_000,
        )

        with self.assertRaises(ValidationError):
            negative_job.full_clean()
        with self.assertRaises(ValidationError):
            reversed_job.full_clean()

    def test_job_form_rejects_reversed_salary_range(self):
        form = JobForm(
            data={
                "company": self.company.pk,
                "title": "Backend Developer",
                "description": "Mô tả",
                "requirement": "Yêu cầu",
                "salary_min": 30_000_000,
                "salary_max": 20_000_000,
                "location": "Hà Nội",
                "job_type": Job.JobType.FULL_TIME,
                "experience_level": Job.ExperienceLevel.JUNIOR,
                "is_active": True,
            },
            recruiter=self.recruiter,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("salary_max", form.errors)

    def test_filter_form_rejects_negative_or_reversed_salary(self):
        negative_form = JobFilterForm({"salary_min": "-1"})
        reversed_form = JobFilterForm(
            {"salary_min": "30000000", "salary_max": "20000000"}
        )

        self.assertFalse(negative_form.is_valid())
        self.assertFalse(reversed_form.is_valid())
        self.assertIn("salary_max", reversed_form.errors)

    def test_salary_display_uses_vietnamese_number_format(self):
        job = self.create_job(self.company, "Backend Developer")

        self.assertEqual(job.salary_display, "10.000.000 - 20.000.000 VNĐ")


class JobViewTests(JobTestMixin, TestCase):
    def setUp(self):
        self.candidate = self.create_user("candidate", User.Role.CANDIDATE)
        self.owner = self.create_user("owner", User.Role.RECRUITER)
        self.assigned_recruiter = self.create_user(
            "assigned",
            User.Role.RECRUITER,
        )
        self.other_recruiter = self.create_user("other", User.Role.RECRUITER)
        self.company = Company.objects.create(
            recruiter=self.owner,
            name="Alpha Tech",
            description="Mô tả",
            location="Hà Nội",
        )
        self.other_company = Company.objects.create(
            recruiter=self.other_recruiter,
            name="Beta Tech",
            description="Mô tả",
            location="TP. Hồ Chí Minh",
        )
        self.assigned_recruiter.recruiter_profile.company = self.company
        self.assigned_recruiter.recruiter_profile.save(update_fields=["company"])
        self.python = Skill.objects.create(name="Python")
        self.javascript = Skill.objects.create(name="JavaScript")
        self.open_job = self.create_job(self.company, "Python Developer")
        self.open_job.skills.add(self.python)
        self.closed_job = self.create_job(
            self.company,
            "Closed Python Job",
            is_active=False,
        )
        self.other_open_job = self.create_job(
            self.other_company,
            "Frontend Developer",
            salary_min=25_000_000,
            salary_max=35_000_000,
            location="TP. Hồ Chí Minh",
            job_type=Job.JobType.PART_TIME,
            experience_level=Job.ExperienceLevel.SENIOR,
        )
        self.other_open_job.skills.add(self.javascript)
        self.other_closed_job = self.create_job(
            self.other_company,
            "Other Closed Job",
            is_active=False,
        )

    def test_closed_job_is_private_to_managing_recruiters(self):
        closed_url = reverse("jobs:detail", kwargs={"pk": self.closed_job.pk})

        self.assertEqual(self.client.get(closed_url).status_code, 404)
        self.client.force_login(self.other_recruiter)
        self.assertEqual(self.client.get(closed_url).status_code, 404)

        for recruiter in (self.owner, self.assigned_recruiter):
            with self.subTest(recruiter=recruiter.username):
                self.client.force_login(recruiter)
                response = self.client.get(closed_url)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["can_manage_job"])

    def test_non_owner_can_view_active_job_but_not_management_controls(self):
        self.client.force_login(self.other_recruiter)

        response = self.client.get(
            reverse("jobs:detail", kwargs={"pk": self.open_job.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context["can_manage_job"])
        self.assertNotContains(response, reverse("jobs:edit", args=[self.open_job.pk]))

    def test_candidate_can_revisit_closed_job_after_applying_or_bookmarking(self):
        Application.objects.create(
            candidate=self.candidate,
            job=self.closed_job,
            cv="application_cvs/candidate.pdf",
        )
        Bookmark.objects.create(
            candidate=self.candidate,
            job=self.other_closed_job,
        )
        self.client.force_login(self.candidate)

        applied_response = self.client.get(
            reverse("jobs:detail", args=[self.closed_job.pk])
        )
        bookmarked_response = self.client.get(
            reverse("jobs:detail", args=[self.other_closed_job.pk])
        )

        self.assertEqual(applied_response.status_code, 200)
        self.assertTrue(applied_response.context["has_applied"])
        self.assertEqual(bookmarked_response.status_code, 200)
        self.assertTrue(bookmarked_response.context["is_bookmarked"])

    def test_advanced_filters_can_be_combined(self):
        response = self.client.get(
            reverse("jobs:list"),
            {
                "location": "Hà Nội",
                "skill": self.python.pk,
                "salary_min": 15_000_000,
                "salary_max": 25_000_000,
                "job_type": Job.JobType.FULL_TIME,
                "experience_level": Job.ExperienceLevel.JUNIOR,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["jobs"]), [self.open_job])

    def test_pagination_preserves_active_filters(self):
        for index in range(10):
            self.create_job(self.company, f"API Developer {index}")

        response = self.client.get(reverse("jobs:list"), {"q": "Developer"})

        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(response.context["query_string"], "q=Developer")
        self.assertContains(response, "q=Developer&amp;page=2")

    def test_dashboard_only_counts_managed_jobs_and_applications(self):
        statuses = (
            Application.Status.PENDING,
            Application.Status.REVIEWING,
            Application.Status.ACCEPTED,
            Application.Status.REJECTED,
        )
        for index, status in enumerate(statuses):
            candidate = self.create_user(f"candidate-{index}", User.Role.CANDIDATE)
            Application.objects.create(
                candidate=candidate,
                job=self.open_job,
                cv=f"application_cvs/{index}.pdf",
                status=status,
            )
        Application.objects.create(
            candidate=self.candidate,
            job=self.other_open_job,
            cv="application_cvs/other.pdf",
        )
        self.client.force_login(self.assigned_recruiter)

        response = self.client.get(reverse("jobs:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["total_jobs"], 2)
        self.assertEqual(response.context["open_jobs"], 1)
        self.assertEqual(response.context["total_applications"], 4)
        self.assertEqual(response.context["pending_applications"], 1)
        self.assertEqual(response.context["reviewing_applications"], 1)
        self.assertEqual(response.context["accepted_applications"], 1)
        self.assertEqual(response.context["rejected_applications"], 1)

    def test_candidate_cannot_access_recruiter_dashboard(self):
        self.client.force_login(self.candidate)

        response = self.client.get(reverse("jobs:dashboard"))

        self.assertEqual(response.status_code, 403)
