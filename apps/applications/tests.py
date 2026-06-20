import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.companies.models import Company
from apps.jobs.models import Job
from apps.users.models import User

from .models import Application, Bookmark


class ApplicationModelDefinitionTests(SimpleTestCase):
    def test_unique_constraint_on_candidate_and_job(self):
        constraint_names = [c.name for c in Application._meta.constraints]

        self.assertIn("unique_application_per_candidate_job", constraint_names)

    def test_application_has_candidate_and_job_relationships(self):
        candidate_field = Application._meta.get_field("candidate")
        job_field = Application._meta.get_field("job")

        self.assertTrue(candidate_field.many_to_one)
        self.assertTrue(job_field.many_to_one)
        self.assertEqual(candidate_field.remote_field.related_name, "applications")
        self.assertEqual(job_field.remote_field.related_name, "applications")

    def test_new_application_defaults_to_pending(self):
        status_field = Application._meta.get_field("status")

        self.assertEqual(status_field.default, Application.Status.PENDING)

    def test_cv_upload_path_and_validator(self):
        cv_field = Application._meta.get_field("cv")

        self.assertEqual(cv_field.upload_to, "application_cvs/")
        self.assertEqual(len(cv_field.validators), 1)
        self.assertEqual(cv_field.validators[0].allowed_extensions, ["pdf"])

    def test_ordering_is_by_applied_at_descending(self):
        self.assertEqual(Application._meta.ordering, ["-applied_at"])

    def test_str_format(self):
        class MockInstance:
            candidate = "alice"
            job = "Backend Developer"

        result = Application.__str__(MockInstance)
        self.assertEqual(result, "alice - Backend Developer")


class BookmarkModelDefinitionTests(SimpleTestCase):
    def test_unique_constraint_on_candidate_and_job(self):
        constraint_names = [c.name for c in Bookmark._meta.constraints]

        self.assertIn("unique_bookmark_per_candidate_job", constraint_names)

    def test_bookmark_has_candidate_and_job_relationships(self):
        candidate_field = Bookmark._meta.get_field("candidate")
        job_field = Bookmark._meta.get_field("job")

        self.assertTrue(candidate_field.many_to_one)
        self.assertTrue(job_field.many_to_one)
        self.assertEqual(candidate_field.remote_field.related_name, "bookmarks")
        self.assertEqual(job_field.remote_field.related_name, "bookmarks")

    def test_ordering_is_by_created_at_descending(self):
        self.assertEqual(Bookmark._meta.ordering, ["-created_at"])

    def test_str_format(self):
        class MockInstance:
            candidate = "alice"
            job = "Backend Developer"

        result = Bookmark.__str__(MockInstance)
        self.assertEqual(result, "alice - Backend Developer")


class ApplicationViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.media_root = tempfile.mkdtemp()
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls.media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)

    def setUp(self):
        self.candidate = User.objects.create_user(
            username="candidate",
            password="test-password",
            role=User.Role.CANDIDATE,
        )
        self.other_candidate = User.objects.create_user(
            username="other-candidate",
            password="test-password",
            role=User.Role.CANDIDATE,
        )
        self.recruiter = User.objects.create_user(
            username="recruiter",
            password="test-password",
            role=User.Role.RECRUITER,
        )
        self.other_recruiter = User.objects.create_user(
            username="other-recruiter",
            password="test-password",
            role=User.Role.RECRUITER,
        )
        self.company = Company.objects.create(
            recruiter=self.recruiter,
            name="Alpha Tech",
            description="Company description",
            location="Ha Noi",
        )
        self.other_company = Company.objects.create(
            recruiter=self.other_recruiter,
            name="Beta Tech",
            description="Company description",
            location="Ho Chi Minh City",
        )
        self.job = self.create_job(self.company, "Django Developer")
        self.closed_job = self.create_job(
            self.company,
            "Closed Job",
            is_active=False,
        )
        self.other_job = self.create_job(self.other_company, "Other Job")

    @staticmethod
    def create_job(company, title, is_active=True):
        return Job.objects.create(
            company=company,
            title=title,
            description="Job description",
            requirement="Job requirement",
            location="Ha Noi",
            job_type=Job.JobType.FULL_TIME,
            experience_level=Job.ExperienceLevel.JUNIOR,
            is_active=is_active,
        )

    @staticmethod
    def pdf_file(name="cv.pdf", content=b"%PDF-1.4 test"):
        return SimpleUploadedFile(
            name,
            content,
            content_type="application/pdf",
        )

    def create_application(self, candidate=None, job=None):
        return Application.objects.create(
            candidate=candidate or self.candidate,
            job=job or self.job,
            cv=self.pdf_file(),
        )

    def test_candidate_can_apply_to_active_job(self):
        self.client.force_login(self.candidate)

        response = self.client.post(
            reverse("applications:apply", kwargs={"job_pk": self.job.pk}),
            {"cover_letter": "I would like to apply.", "cv": self.pdf_file()},
        )

        self.assertRedirects(
            response,
            reverse("applications:my_applications"),
        )
        application = Application.objects.get()
        self.assertEqual(application.candidate, self.candidate)
        self.assertEqual(application.job, self.job)
        self.assertEqual(application.status, Application.Status.PENDING)

    def test_candidate_cannot_apply_twice_to_same_job(self):
        self.create_application()
        self.client.force_login(self.candidate)

        response = self.client.post(
            reverse("applications:apply", kwargs={"job_pk": self.job.pk}),
            {"cover_letter": "Apply again", "cv": self.pdf_file("second.pdf")},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bạn đã ứng tuyển công việc này rồi.")
        self.assertEqual(Application.objects.count(), 1)

    def test_candidate_cannot_apply_to_closed_job(self):
        self.client.force_login(self.candidate)

        response = self.client.post(
            reverse(
                "applications:apply",
                kwargs={"job_pk": self.closed_job.pk},
            ),
            {"cover_letter": "Apply", "cv": self.pdf_file()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Công việc này đã đóng ứng tuyển.")
        self.assertFalse(Application.objects.exists())

    def test_cv_must_be_pdf_and_not_larger_than_5mb(self):
        self.client.force_login(self.candidate)
        url = reverse("applications:apply", kwargs={"job_pk": self.job.pk})

        non_pdf_response = self.client.post(
            url,
            {
                "cover_letter": "Apply",
                "cv": SimpleUploadedFile(
                    "cv.txt",
                    b"not a pdf",
                    content_type="text/plain",
                ),
            },
        )
        large_file_response = self.client.post(
            url,
            {
                "cover_letter": "Apply",
                "cv": self.pdf_file(content=b"x" * (5 * 1024 * 1024 + 1)),
            },
        )

        self.assertEqual(non_pdf_response.status_code, 200)
        self.assertEqual(large_file_response.status_code, 200)
        self.assertContains(large_file_response, "CV không được lớn hơn 5MB.")
        self.assertFalse(Application.objects.exists())

    def test_my_applications_only_shows_current_candidate_records(self):
        own_application = self.create_application()
        other_application = self.create_application(
            candidate=self.other_candidate,
            job=self.other_job,
        )
        self.client.force_login(self.candidate)

        response = self.client.get(reverse("applications:my_applications"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(own_application, response.context["applications"])
        self.assertNotIn(other_application, response.context["applications"])

    def test_recruiter_only_sees_applicants_for_owned_job(self):
        application = self.create_application()
        self.client.force_login(self.recruiter)

        response = self.client.get(
            reverse(
                "applications:job_applicants",
                kwargs={"job_pk": self.job.pk},
            )
        )
        forbidden_response = self.client.get(
            reverse(
                "applications:job_applicants",
                kwargs={"job_pk": self.other_job.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(application, response.context["applications"])
        self.assertEqual(forbidden_response.status_code, 404)

    def test_recruiter_can_update_application_status(self):
        application = self.create_application()
        self.client.force_login(self.recruiter)

        response = self.client.post(
            reverse(
                "applications:update_status",
                kwargs={"pk": application.pk},
            ),
            {"status": Application.Status.ACCEPTED},
        )

        self.assertRedirects(
            response,
            reverse(
                "applications:job_applicants",
                kwargs={"job_pk": self.job.pk},
            ),
        )
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.ACCEPTED)

    def test_candidate_cannot_update_application_status(self):
        application = self.create_application()
        self.client.force_login(self.candidate)

        response = self.client.post(
            reverse(
                "applications:update_status",
                kwargs={"pk": application.pk},
            ),
            {"status": Application.Status.REJECTED},
        )

        self.assertEqual(response.status_code, 403)
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.PENDING)

    def test_invalid_status_is_rejected(self):
        application = self.create_application()
        self.client.force_login(self.recruiter)

        response = self.client.post(
            reverse(
                "applications:update_status",
                kwargs={"pk": application.pk},
            ),
            {"status": "invalid"},
        )

        self.assertEqual(response.status_code, 400)
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.PENDING)
