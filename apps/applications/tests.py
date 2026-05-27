from django.test import SimpleTestCase

from .models import Application, CandidateProfile, RecruiterProfile


class ApplicationModelDefinitionTests(SimpleTestCase):
    def test_candidate_profile_has_one_user(self):
        user_field = CandidateProfile._meta.get_field("user")

        self.assertTrue(user_field.one_to_one)
        self.assertEqual(user_field.remote_field.related_name, "candidate_profile")

    def test_recruiter_profile_has_one_user_and_company_relationship(self):
        user_field = RecruiterProfile._meta.get_field("user")
        company_field = RecruiterProfile._meta.get_field("company")

        self.assertTrue(user_field.one_to_one)
        self.assertTrue(company_field.many_to_one)

    def test_candidate_can_apply_to_a_job_only_once(self):
        self.assertIn(
            ("candidate", "job"),
            Application._meta.unique_together,
        )

    def test_new_application_defaults_to_pending(self):
        status_field = Application._meta.get_field("status")

        self.assertEqual(status_field.default, Application.Status.PENDING)

