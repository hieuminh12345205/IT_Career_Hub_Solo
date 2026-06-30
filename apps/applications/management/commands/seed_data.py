from django.core.management.base import BaseCommand

from apps.applications.models import Application, Bookmark
from apps.companies.models import Company
from apps.jobs.models import Job, Skill
from apps.users.models import CandidateProfile, RecruiterProfile, User


class Command(BaseCommand):
    help = "Tạo dữ liệu mẫu để chạy thử luồng tuyển dụng"

    def handle(self, *args, **options):
        recruiter = self._upsert_user(
            username="demo_recruiter",
            email="recruiter@example.com",
            role=User.Role.RECRUITER,
            first_name="Demo",
            last_name="Recruiter",
        )
        candidate = self._upsert_user(
            username="demo_candidate",
            email="candidate@example.com",
            role=User.Role.CANDIDATE,
            first_name="Demo",
            last_name="Candidate",
        )

        company, _ = Company.objects.update_or_create(
            recruiter=recruiter,
            defaults={
                "name": "Demo Tech",
                "description": "Công ty công nghệ dùng cho dữ liệu mẫu.",
                "website": "https://example.com",
                "location": "Hà Nội",
            },
        )
        RecruiterProfile.objects.update_or_create(
            user=recruiter,
            defaults={"company": company, "position": "HR Manager"},
        )
        CandidateProfile.objects.update_or_create(
            user=candidate,
            defaults={
                "full_name": "Demo Candidate",
                "bio": "Ứng viên mẫu cho dự án IT Career Hub.",
                "experience_years": 1,
                "location": "Hà Nội",
            },
        )

        python_skill, _ = Skill.objects.get_or_create(name="Python")
        django_skill, _ = Skill.objects.get_or_create(name="Django")

        backend_job = self._upsert_job(
            company=company,
            title="Python Backend Developer",
            experience_level=Job.ExperienceLevel.JUNIOR,
        )
        backend_job.skills.set([python_skill, django_skill])

        intern_job = self._upsert_job(
            company=company,
            title="Django Intern",
            experience_level=Job.ExperienceLevel.INTERN,
            job_type=Job.JobType.INTERN,
        )
        intern_job.skills.set([python_skill, django_skill])

        Application.objects.get_or_create(
            candidate=candidate,
            job=backend_job,
            defaults={
                "cv": "application_cvs/demo-cv.pdf",
                "cover_letter": "Tôi muốn ứng tuyển vị trí Python Backend Developer.",
            },
        )
        Bookmark.objects.get_or_create(candidate=candidate, job=intern_job)

        self.stdout.write(
            self.style.SUCCESS(
                "Đã tạo dữ liệu mẫu. Đăng nhập bằng demo_candidate hoặc "
                "demo_recruiter với mật khẩu Demo@12345."
            )
        )

    @staticmethod
    def _upsert_user(username, email, role, first_name, last_name):
        user, _ = User.objects.get_or_create(
            username=username,
            defaults={"email": email, "role": role},
        )
        user.email = email
        user.role = role
        user.first_name = first_name
        user.last_name = last_name
        user.set_password("Demo@12345")
        user.save()
        return user

    @staticmethod
    def _upsert_job(
        company,
        title,
        experience_level,
        job_type=Job.JobType.FULL_TIME,
    ):
        job, _ = Job.objects.update_or_create(
            company=company,
            title=title,
            defaults={
                "description": f"Mô tả công việc mẫu cho {title}.",
                "requirement": "Có kiến thức Python và tinh thần học hỏi.",
                "salary_min": 8_000_000,
                "salary_max": 15_000_000,
                "location": "Hà Nội",
                "job_type": job_type,
                "experience_level": experience_level,
                "is_active": True,
            },
        )
        return job
