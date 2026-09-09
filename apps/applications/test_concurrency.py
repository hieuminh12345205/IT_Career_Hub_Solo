import tempfile
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connections
from django.test import (
    Client,
    TransactionTestCase,
    override_settings,
    skipUnlessDBFeature,
)
from django.urls import reverse

from apps.companies.models import Company
from apps.jobs.models import Job
from apps.users.models import User

from .models import Application, Bookmark


@skipUnlessDBFeature("has_select_for_update")
class ConcurrentRecruitmentTests(TransactionTestCase):
    """Dùng kết nối DB riêng để kiểm tra khóa thật, không mock ORM."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        media_settings = override_settings(MEDIA_ROOT=directory.name)
        media_settings.enable()
        self.addCleanup(media_settings.disable)
        self.candidate = User.objects.create_user(
            username="concurrent-candidate", email="candidate@example.com"
        )
        self.recruiter = User.objects.create_user(
            username="concurrent-recruiter",
            email="recruiter@example.com",
            role=User.Role.RECRUITER,
        )
        company = Company.objects.create(recruiter=self.recruiter, name="Concurrent Co")
        self.job = Job.objects.create(
            company=company,
            title="Backend Developer",
            job_type=Job.JobType.FULL_TIME,
            experience_level=Job.ExperienceLevel.JUNIOR,
        )

    def post_twice(self, user, url, data_factory):
        clients = [Client(), Client()]
        for client in clients:
            client.force_login(user)
        barrier = Barrier(2, timeout=10)

        def post(client):
            try:
                barrier.wait()
                return client.post(url, data_factory()).status_code
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as executor:
            results = [executor.submit(post, client) for client in clients]
            return sorted(result.result(timeout=20) for result in results)

    def test_concurrent_apply_creates_one_application_and_email(self):
        statuses = self.post_twice(
            self.candidate,
            reverse("applications:apply", args=[self.job.pk]),
            lambda: {
                "cv": SimpleUploadedFile("cv.pdf", b"%PDF-1.4", "application/pdf")
            },
        )
        self.assertEqual(statuses, [200, 302])
        self.assertEqual(Application.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)

    def test_concurrent_bookmark_toggles_cancel_each_other(self):
        statuses = self.post_twice(
            self.candidate,
            reverse("applications:toggle_bookmark", args=[self.job.pk]),
            dict,
        )
        self.assertEqual(statuses, [302, 302])
        self.assertFalse(Bookmark.objects.exists())

    def test_concurrent_same_status_sends_one_notification(self):
        application = Application.objects.create(
            candidate=self.candidate, job=self.job, cv="application_cvs/test.pdf"
        )
        statuses = self.post_twice(
            self.recruiter,
            reverse("applications:update_status", args=[application.pk]),
            lambda: {"status": Application.Status.REVIEWING},
        )
        self.assertEqual(statuses, [302, 302])
        application.refresh_from_db()
        self.assertEqual(application.status, Application.Status.REVIEWING)
        self.assertEqual(len(mail.outbox), 1)
