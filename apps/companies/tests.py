from django.test import TestCase
from django.urls import reverse

from apps.users.models import User

from .models import Company


class ManageCompanyViewTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(
            username="company-owner",
            password="test-password",
            role=User.Role.RECRUITER,
        )
        self.member = User.objects.create_user(
            username="company-member",
            password="test-password",
            role=User.Role.RECRUITER,
        )
        self.company = Company.objects.create(
            recruiter=self.owner,
            name="Alpha Tech",
            description="Original description",
            location="Ha Noi",
        )
        self.member.recruiter_profile.company = self.company
        self.member.recruiter_profile.save(update_fields=["company", "updated_at"])
        self.url = reverse("companies:manage_company")

    @staticmethod
    def company_data(name="Updated Alpha Tech"):
        return {
            "name": name,
            "description": "Updated description",
            "website": "https://example.com",
            "location": "Ho Chi Minh City",
        }

    def test_assigned_member_can_edit_company_without_becoming_owner(self):
        self.client.force_login(self.member)

        response = self.client.post(self.url, self.company_data())

        self.assertRedirects(response, self.url)
        self.company.refresh_from_db()
        self.member.recruiter_profile.refresh_from_db()
        self.assertEqual(self.company.name, "Updated Alpha Tech")
        self.assertEqual(self.company.recruiter, self.owner)
        self.assertEqual(self.member.recruiter_profile.company, self.company)

    def test_owned_company_is_preferred_over_an_assigned_company(self):
        member_owned_company = Company.objects.create(
            recruiter=self.member,
            name="Member Owned Co",
            description="Owned description",
            location="Da Nang",
        )
        self.client.force_login(self.member)

        response = self.client.post(self.url, self.company_data("Owner Updated Co"))

        self.assertRedirects(response, self.url)
        member_owned_company.refresh_from_db()
        self.company.refresh_from_db()
        self.member.recruiter_profile.refresh_from_db()
        self.assertEqual(member_owned_company.name, "Owner Updated Co")
        self.assertEqual(member_owned_company.recruiter, self.member)
        self.assertEqual(self.company.name, "Alpha Tech")
        self.assertEqual(self.company.recruiter, self.owner)
        self.assertEqual(self.member.recruiter_profile.company, self.company)

    def test_new_company_is_owned_by_recruiter_and_links_empty_profile(self):
        new_recruiter = User.objects.create_user(
            username="new-recruiter",
            password="test-password",
            role=User.Role.RECRUITER,
        )
        self.client.force_login(new_recruiter)

        response = self.client.post(self.url, self.company_data("New Company"))

        self.assertRedirects(response, self.url)
        company = Company.objects.get(name="New Company")
        new_recruiter.recruiter_profile.refresh_from_db()
        self.assertEqual(company.recruiter, new_recruiter)
        self.assertEqual(new_recruiter.recruiter_profile.company, company)

    def test_candidate_cannot_manage_company(self):
        candidate = User.objects.create_user(
            username="candidate",
            password="test-password",
            role=User.Role.CANDIDATE,
        )
        self.client.force_login(candidate)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 403)
