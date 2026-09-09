import shutil
import tempfile
from io import StringIO
from smtplib import SMTPException
from unittest.mock import patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, transaction
from django.forms import modelform_factory
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from apps.companies.models import Company
from apps.jobs.models import Job
from apps.users.models import User

from .forms import ApplicationForm
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
            email="candidate@example.com",
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
            email="recruiter@example.com",
            password="test-password",
            role=User.Role.RECRUITER,
        )
        self.other_recruiter = User.objects.create_user(
            username="other-recruiter",
            password="test-password",
            role=User.Role.RECRUITER,
        )
        self.company_recruiter = User.objects.create_user(
            username="company-recruiter",
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
        self.company_recruiter.recruiter_profile.company = self.company
        self.company_recruiter.recruiter_profile.save()
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

    def test_database_rejects_duplicate_candidate_and_job(self):
        self.create_application()

        with self.assertRaises(IntegrityError), transaction.atomic():
            self.create_application()

    def test_apply_page_is_available_for_candidate_and_open_job(self):
        self.client.force_login(self.candidate)

        response = self.client.get(
            reverse("applications:apply", kwargs={"job_pk": self.job.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["job"], self.job)
        self.assertContains(response, "Django Developer")

    def test_closed_job_does_not_expose_apply_page(self):
        self.client.force_login(self.candidate)

        response = self.client.get(
            reverse(
                "applications:apply",
                kwargs={"job_pk": self.closed_job.pk},
            )
        )

        self.assertEqual(response.status_code, 404)

    def test_recruiter_cannot_access_candidate_views(self):
        self.client.force_login(self.recruiter)

        apply_response = self.client.get(
            reverse("applications:apply", kwargs={"job_pk": self.job.pk})
        )
        mine_response = self.client.get(reverse("applications:my_applications"))

        self.assertEqual(apply_response.status_code, 403)
        self.assertEqual(mine_response.status_code, 403)

    def test_anonymous_user_is_redirected_from_application_views(self):
        responses = (
            (
                "apply",
                self.client.get(
                    reverse(
                        "applications:apply",
                        kwargs={"job_pk": self.job.pk},
                    )
                ),
            ),
            (
                "my_applications",
                self.client.get(reverse("applications:my_applications")),
            ),
            (
                "job_applicants",
                self.client.get(
                    reverse(
                        "applications:job_applicants",
                        kwargs={"job_pk": self.job.pk},
                    )
                ),
            ),
        )

        for view_name, response in responses:
            with self.subTest(view=view_name):
                self.assertEqual(response.status_code, 302)
                self.assertIn("/accounts/login/", response.url)

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

    @patch.object(ApplicationForm, "clean", lambda form: form.cleaned_data)
    def test_duplicate_race_returns_form_error_instead_of_server_error(self):
        # Giả lập đơn khác đã lưu sau bước form.clean() kiểm tra trùng.
        self.create_application()
        self.client.force_login(self.candidate)

        response = self.client.post(
            reverse("applications:apply", kwargs={"job_pk": self.job.pk}),
            {"cover_letter": "Apply", "cv": self.pdf_file()},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bạn đã ứng tuyển công việc này rồi.")
        self.assertNotContains(response, "Ứng tuyển thành công.")

    def test_candidate_cannot_apply_to_closed_job(self):
        self.client.force_login(self.candidate)

        response = self.client.post(
            reverse(
                "applications:apply",
                kwargs={"job_pk": self.closed_job.pk},
            ),
            {"cover_letter": "Apply", "cv": self.pdf_file()},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(Application.objects.exists())

    def test_cv_must_be_pdf_and_not_larger_than_5mb(self):
        self.client.force_login(self.candidate)
        url = reverse("applications:apply", kwargs={"job_pk": self.job.pk})

        non_pdf_response = self.client.post(
            url,
            {
                "cover_letter": "Apply",
                "cv": SimpleUploadedFile(
                    "fake.pdf",
                    b"not a pdf",
                    content_type="application/pdf",
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
        self.assertContains(non_pdf_response, "CV phải là file PDF hợp lệ.")
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

    def test_candidate_cannot_access_job_applicants(self):
        self.client.force_login(self.candidate)

        response = self.client.get(
            reverse(
                "applications:job_applicants",
                kwargs={"job_pk": self.job.pk},
            )
        )

        self.assertEqual(response.status_code, 403)

    def test_company_profile_recruiter_can_view_job_applicants(self):
        application = self.create_application()
        self.client.force_login(self.company_recruiter)

        response = self.client.get(
            reverse(
                "applications:job_applicants",
                kwargs={"job_pk": self.job.pk},
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn(application, response.context["applications"])

    def test_applicant_list_links_to_protected_cv_download(self):
        application = self.create_application()
        self.client.force_login(self.recruiter)

        response = self.client.get(
            reverse(
                "applications:job_applicants",
                kwargs={"job_pk": self.job.pk},
            )
        )

        self.assertContains(
            response,
            reverse("applications:download_cv", kwargs={"pk": application.pk}),
        )
        self.assertNotContains(response, application.cv.url)

    def test_application_cv_is_not_served_from_direct_media_url(self):
        application = self.create_application()

        response = self.client.get(application.cv.url)

        self.assertEqual(response.status_code, 404)

    def test_job_owner_can_download_application_cv(self):
        application = self.create_application()
        self.client.force_login(self.recruiter)

        response = self.client.get(
            reverse("applications:download_cv", kwargs={"pk": application.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        self.assertIn("attachment;", response["Content-Disposition"])
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 test")

    def test_assigned_company_recruiter_can_download_application_cv(self):
        application = self.create_application()
        self.client.force_login(self.company_recruiter)

        response = self.client.get(
            reverse("applications:download_cv", kwargs={"pk": application.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 test")

    def test_other_recruiter_cannot_download_application_cv(self):
        application = self.create_application()
        self.client.force_login(self.other_recruiter)

        response = self.client.get(
            reverse("applications:download_cv", kwargs={"pk": application.pk})
        )

        self.assertEqual(response.status_code, 404)

    def test_candidate_cannot_download_application_cv(self):
        application = self.create_application()
        self.client.force_login(self.candidate)

        response = self.client.get(
            reverse("applications:download_cv", kwargs={"pk": application.pk})
        )

        self.assertEqual(response.status_code, 403)

    def test_anonymous_user_is_redirected_from_application_cv(self):
        application = self.create_application()

        response = self.client.get(
            reverse("applications:download_cv", kwargs={"pk": application.pk})
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    def test_admin_can_download_application_cv(self):
        application = self.create_application()
        admin = User.objects.create_user(
            username="admin",
            password="test-password",
            role=User.Role.ADMIN,
        )
        self.client.force_login(admin)

        response = self.client.get(
            reverse("applications:download_cv", kwargs={"pk": application.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(b"".join(response.streaming_content), b"%PDF-1.4 test")

    def test_admin_can_review_applicants_and_update_status(self):
        application = self.create_application()
        admin = User.objects.create_user(
            username="review-admin",
            password="test-password",
            role=User.Role.ADMIN,
        )
        self.client.force_login(admin)

        applicants_response = self.client.get(
            reverse(
                "applications:job_applicants",
                kwargs={"job_pk": self.job.pk},
            )
        )
        status_response = self.client.post(
            reverse("applications:update_status", kwargs={"pk": application.pk}),
            {"status": Application.Status.ACCEPTED},
        )

        self.assertEqual(applicants_response.status_code, 200)
        self.assertRedirects(
            status_response,
            reverse(
                "applications:job_applicants",
                kwargs={"job_pk": self.job.pk},
            ),
        )
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.ACCEPTED)

    def test_missing_application_cv_file_returns_404(self):
        application = Application.objects.create(
            candidate=self.candidate,
            job=self.job,
            cv="application_cvs/missing.pdf",
        )
        self.client.force_login(self.recruiter)

        response = self.client.get(
            reverse("applications:download_cv", kwargs={"pk": application.pk})
        )

        self.assertEqual(response.status_code, 404)

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

    def test_other_recruiter_cannot_update_application_status(self):
        application = self.create_application()
        self.client.force_login(self.other_recruiter)

        response = self.client.post(
            reverse(
                "applications:update_status",
                kwargs={"pk": application.pk},
            ),
            {"status": Application.Status.ACCEPTED},
        )

        self.assertEqual(response.status_code, 404)
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.PENDING)

    def test_update_application_status_requires_post(self):
        application = self.create_application()
        self.client.force_login(self.recruiter)

        response = self.client.get(
            reverse(
                "applications:update_status",
                kwargs={"pk": application.pk},
            )
        )

        self.assertEqual(response.status_code, 405)

    def test_company_profile_recruiter_can_update_status(self):
        application = self.create_application()
        self.client.force_login(self.company_recruiter)

        response = self.client.post(
            reverse(
                "applications:update_status",
                kwargs={"pk": application.pk},
            ),
            {"status": Application.Status.REVIEWING},
        )

        self.assertRedirects(
            response,
            reverse(
                "applications:job_applicants",
                kwargs={"job_pk": self.job.pk},
            ),
        )
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.REVIEWING)

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

    def test_candidate_can_toggle_bookmark(self):
        self.client.force_login(self.candidate)
        url = reverse(
            "applications:toggle_bookmark",
            kwargs={"job_pk": self.job.pk},
        )

        create_response = self.client.post(url)

        self.assertRedirects(create_response, reverse("applications:my_bookmarks"))
        self.assertTrue(
            Bookmark.objects.filter(
                candidate=self.candidate,
                job=self.job,
            ).exists()
        )

        delete_response = self.client.post(
            url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(delete_response.json(), {"bookmarked": False})
        self.assertFalse(Bookmark.objects.exists())

    def test_my_bookmarks_only_shows_current_candidate_records(self):
        own_bookmark = Bookmark.objects.create(candidate=self.candidate, job=self.job)
        other_bookmark = Bookmark.objects.create(
            candidate=self.other_candidate,
            job=self.other_job,
        )
        self.client.force_login(self.candidate)

        response = self.client.get(reverse("applications:my_bookmarks"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(own_bookmark, response.context["bookmarks"])
        self.assertNotIn(other_bookmark, response.context["bookmarks"])

    def test_recruiter_cannot_use_candidate_bookmark_views(self):
        self.client.force_login(self.recruiter)

        list_response = self.client.get(reverse("applications:my_bookmarks"))
        toggle_response = self.client.post(
            reverse(
                "applications:toggle_bookmark",
                kwargs={"job_pk": self.job.pk},
            )
        )

        self.assertEqual(list_response.status_code, 403)
        self.assertEqual(toggle_response.status_code, 403)
        self.assertFalse(Bookmark.objects.exists())

    def test_full_application_flow_sends_both_notifications(self):
        self.client.force_login(self.candidate)

        with self.captureOnCommitCallbacks(execute=True):
            apply_response = self.client.post(
                reverse("applications:apply", kwargs={"job_pk": self.job.pk}),
                {"cover_letter": "I would like to apply.", "cv": self.pdf_file()},
            )

        self.assertRedirects(
            apply_response,
            reverse("applications:my_applications"),
        )
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["recruiter@example.com"])
        self.assertIn("Ứng viên mới", mail.outbox[0].subject)

        application = Application.objects.get()
        self.client.force_login(self.recruiter)
        with self.captureOnCommitCallbacks(execute=True):
            review_response = self.client.post(
                reverse(
                    "applications:update_status",
                    kwargs={"pk": application.pk},
                ),
                {"status": Application.Status.REVIEWING},
            )

        self.assertRedirects(
            review_response,
            reverse(
                "applications:job_applicants",
                kwargs={"job_pk": self.job.pk},
            ),
        )
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.REVIEWING)
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(mail.outbox[1].to, ["candidate@example.com"])
        self.assertIn("Reviewing", mail.outbox[1].body)

    def test_unchanged_status_does_not_send_email(self):
        application = self.create_application()
        self.client.force_login(self.recruiter)

        response = self.client.post(
            reverse(
                "applications:update_status",
                kwargs={"pk": application.pk},
            ),
            {"status": Application.Status.PENDING},
        )

        self.assertRedirects(
            response,
            reverse(
                "applications:job_applicants",
                kwargs={"job_pk": self.job.pk},
            ),
        )
        self.assertEqual(len(mail.outbox), 0)

    def test_job_closed_after_validation_cannot_receive_application(self):
        original_clean = ApplicationForm.clean

        def close_after_validation(form):
            result = original_clean(form)
            Job.objects.filter(pk=self.job.pk).update(is_active=False)
            return result

        self.client.force_login(self.candidate)
        with patch.object(ApplicationForm, "clean", close_after_validation):
            response = self.client.post(
                reverse("applications:apply", args=[self.job.pk]),
                {"cv": self.pdf_file()},
            )
        self.assertContains(response, "Công việc này đã đóng ứng tuyển.")
        self.assertFalse(Application.objects.exists())

    def test_generic_model_form_also_rejects_fake_cv(self):
        form_class = modelform_factory(Application, fields=["candidate", "job", "cv"])
        form = form_class(
            data={"candidate": self.candidate.pk, "job": self.job.pk},
            files={"cv": self.pdf_file(content=b"not a pdf")},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("cv", form.errors)

    def test_rollback_discards_status_email(self):
        application = self.create_application()
        self.client.force_login(self.recruiter)
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with transaction.atomic():
                self.client.post(
                    reverse("applications:update_status", args=[application.pk]),
                    {"status": Application.Status.ACCEPTED},
                )
                self.assertEqual(len(mail.outbox), 0)
                transaction.set_rollback(True)
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.PENDING)
        self.assertEqual(callbacks, [])
        self.assertEqual(len(mail.outbox), 0)

    @patch(
        "apps.applications.notifications.send_mail", side_effect=SMTPException("down")
    )
    def test_smtp_failure_is_logged_without_losing_application(self, _):
        self.client.force_login(self.candidate)
        with self.assertLogs("apps.applications.notifications", level="ERROR") as logs:
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse("applications:apply", args=[self.job.pk]),
                    {"cv": self.pdf_file()},
                )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Application.objects.count(), 1)
        self.assertIn("notification_failed", logs.output[0])
        self.assertNotIn(self.candidate.email, logs.output[0])

    def test_repeated_status_update_sends_only_one_email_and_logs_actor(self):
        application = self.create_application()
        self.client.force_login(self.recruiter)
        with self.assertLogs("apps.applications.views", level="INFO") as logs:
            with self.captureOnCommitCallbacks(execute=True):
                for _ in range(2):
                    self.client.post(
                        reverse("applications:update_status", args=[application.pk]),
                        {"status": Application.Status.REVIEWING},
                    )
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(f"actor_id={self.recruiter.pk}", logs.output[0])
        self.assertIn("old_status=pending new_status=reviewing", logs.output[0])

    def test_bookmark_rejects_external_redirect_and_get(self):
        self.client.force_login(self.candidate)
        url = reverse("applications:toggle_bookmark", args=[self.job.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url, {"next": "https://example.org/phishing"})
        self.assertRedirects(response, reverse("applications:my_bookmarks"))

    def test_closed_job_can_only_be_unbookmarked(self):
        self.client.force_login(self.candidate)
        url = reverse("applications:toggle_bookmark", args=[self.closed_job.pk])
        self.assertEqual(self.client.post(url).status_code, 404)
        Bookmark.objects.create(candidate=self.candidate, job=self.closed_job)
        self.assertEqual(self.client.post(url).status_code, 302)
        self.assertFalse(Bookmark.objects.exists())

    def test_state_changing_endpoints_enforce_csrf(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.candidate)
        self.assertEqual(
            client.post(
                reverse("applications:toggle_bookmark", args=[self.job.pk])
            ).status_code,
            403,
        )
        application = self.create_application()
        client.force_login(self.recruiter)
        self.assertEqual(
            client.post(
                reverse("applications:update_status", args=[application.pk]),
                {"status": Application.Status.ACCEPTED},
            ).status_code,
            403,
        )


class SeedDataCommandTests(TestCase):
    @override_settings(ALLOW_DEMO_SEED=False)
    def test_seed_is_blocked_outside_dev(self):
        with self.assertRaises(CommandError):
            call_command("seed_data", stdout=StringIO())
        self.assertFalse(User.objects.exists())

    def test_seed_preserves_changed_passwords_and_jobs(self):
        call_command("seed_data", stdout=StringIO())
        user = User.objects.get(username="demo_admin")
        user.set_password("My-new-private-password!")
        user.save()
        job = Job.objects.first()
        job.is_active = False
        job.description = "Edited by the team"
        job.save()
        call_command("seed_data", stdout=StringIO())
        user.refresh_from_db()
        job.refresh_from_db()
        self.assertTrue(user.check_password("My-new-private-password!"))
        self.assertFalse(job.is_active)
        self.assertEqual(job.description, "Edited by the team")

    def test_seed_does_not_promote_existing_candidate_to_admin(self):
        user = User.objects.create_user(username="demo_admin")
        with self.assertRaises(CommandError):
            call_command("seed_data", stdout=StringIO())
        user.refresh_from_db()
        self.assertFalse(user.is_superuser)
        self.assertEqual(User.objects.count(), 1)

    def test_seed_data_creates_demo_records_and_is_idempotent(self):
        output = StringIO()

        call_command("seed_data", stdout=output)
        call_command("seed_data", stdout=output)

        candidate = User.objects.get(username="demo_candidate")
        recruiter = User.objects.get(username="demo_recruiter")
        self.assertTrue(candidate.check_password("Demo@12345"))
        self.assertEqual(candidate.role, User.Role.CANDIDATE)
        self.assertEqual(recruiter.role, User.Role.RECRUITER)
        self.assertEqual(Company.objects.count(), 1)
        self.assertEqual(Job.objects.count(), 2)
        self.assertEqual(Application.objects.count(), 0)
        self.assertEqual(Bookmark.objects.count(), 1)
        self.assertIn("Đã tạo dữ liệu mẫu", output.getvalue())
