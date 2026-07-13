from django.db.models import Q

from apps.users.models import User

from .models import Job


def is_admin(user):
    return bool(
        user.is_authenticated and (user.is_superuser or user.role == User.Role.ADMIN)
    )


def is_recruiter_or_admin(user):
    return bool(
        user.is_authenticated and (is_admin(user) or user.role == User.Role.RECRUITER)
    )


def jobs_managed_by(recruiter):
    """Jobs owned directly, assigned through RecruiterProfile.company, or all jobs for admin."""
    if is_admin(recruiter):
        return Job.objects.all()
    return Job.objects.filter(
        Q(company__recruiter=recruiter) | Q(company__recruiter_profiles__user=recruiter)
    ).distinct()


def companies_managed_by(recruiter):
    from apps.companies.models import Company

    if is_admin(recruiter):
        return Company.objects.all()
    return Company.objects.filter(
        Q(recruiter=recruiter) | Q(recruiter_profiles__user=recruiter)
    ).distinct()
