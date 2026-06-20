from unittest.mock import patch

from django.db.models.signals import post_save
from django.test import SimpleTestCase

from .models import CandidateProfile, RecruiterProfile, User
from .signals import create_role_profile


class CandidateProfileModelDefinitionTests(SimpleTestCase):
    def test_candidate_profile_has_one_user(self):
        user_field = CandidateProfile._meta.get_field("user")

        self.assertTrue(user_field.one_to_one)
        self.assertEqual(user_field.remote_field.related_name, "candidate_profile")

    def test_candidate_profile_has_optional_skills_and_cv(self):
        skills_field = CandidateProfile._meta.get_field("skills")
        cv_field = CandidateProfile._meta.get_field("cv_file")

        self.assertTrue(skills_field.many_to_many)
        self.assertTrue(skills_field.blank)
        self.assertEqual(cv_field.upload_to, "cvs/")
        self.assertTrue(cv_field.blank)
        self.assertTrue(cv_field.null)
        self.assertEqual(cv_field.validators[0].allowed_extensions, ["pdf"])

    def test_candidate_profile_str_prefers_full_name(self):
        user = User(username="alice")
        profile = CandidateProfile(user=user, full_name="Alice Nguyen")

        self.assertEqual(str(profile), "Alice Nguyen")


class RecruiterProfileModelDefinitionTests(SimpleTestCase):
    def test_recruiter_profile_has_one_user(self):
        user_field = RecruiterProfile._meta.get_field("user")

        self.assertTrue(user_field.one_to_one)
        self.assertEqual(user_field.remote_field.related_name, "recruiter_profile")

    def test_recruiter_profile_has_optional_company_fk(self):
        company_field = RecruiterProfile._meta.get_field("company")

        self.assertTrue(company_field.many_to_one)
        self.assertEqual(company_field.remote_field.related_name, "recruiter_profiles")
        self.assertTrue(company_field.blank)
        self.assertTrue(company_field.null)

    def test_recruiter_profile_str_handles_missing_company(self):
        user = User(username="recruiter")
        profile = RecruiterProfile(user=user)

        self.assertEqual(str(profile), "recruiter - No company")


class UserProfileSignalTests(SimpleTestCase):
    def test_post_save_signal_is_registered_for_user(self):
        self.assertTrue(post_save.has_listeners(User))

    @patch("apps.users.signals.RecruiterProfile.objects.get_or_create")
    @patch("apps.users.signals.CandidateProfile.objects.get_or_create")
    def test_signal_creates_candidate_profile_for_new_candidate(
        self,
        candidate_get_or_create,
        recruiter_get_or_create,
    ):
        user = User(username="candidate", role=User.Role.CANDIDATE)

        create_role_profile(User, user, created=True)

        candidate_get_or_create.assert_called_once_with(user=user)
        recruiter_get_or_create.assert_not_called()

    @patch("apps.users.signals.RecruiterProfile.objects.get_or_create")
    @patch("apps.users.signals.CandidateProfile.objects.get_or_create")
    def test_signal_creates_recruiter_profile_for_new_recruiter(
        self,
        candidate_get_or_create,
        recruiter_get_or_create,
    ):
        user = User(username="recruiter", role=User.Role.RECRUITER)

        create_role_profile(User, user, created=True)

        recruiter_get_or_create.assert_called_once_with(user=user)
        candidate_get_or_create.assert_not_called()

    @patch("apps.users.signals.RecruiterProfile.objects.get_or_create")
    @patch("apps.users.signals.CandidateProfile.objects.get_or_create")
    def test_signal_skips_existing_users(
        self,
        candidate_get_or_create,
        recruiter_get_or_create,
    ):
        user = User(username="candidate", role=User.Role.CANDIDATE)

        create_role_profile(User, user, created=False)

        candidate_get_or_create.assert_not_called()
        recruiter_get_or_create.assert_not_called()
