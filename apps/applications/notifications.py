from django.conf import settings
from django.core.mail import send_mail

from apps.users.models import User


def _recruiter_emails(company):
    """Lấy email của chủ công ty và các recruiter được gán vào công ty."""
    emails = {company.recruiter.email}
    emails.update(
        User.objects.filter(
            role=User.Role.RECRUITER,
            recruiter_profile__company=company,
        ).values_list("email", flat=True)
    )
    return sorted(email for email in emails if email)


def notify_recruiters_new_application(application):
    recipients = _recruiter_emails(application.job.company)
    if not recipients:
        return 0

    return send_mail(
        subject=f"Ứng viên mới cho vị trí {application.job.title}",
        message=(
            f"Ứng viên {application.candidate.get_full_name() or application.candidate.username} "
            f"vừa ứng tuyển vị trí {application.job.title}."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        fail_silently=True,
    )


def notify_candidate_status_changed(application):
    if not application.candidate.email:
        return 0

    return send_mail(
        subject=f"Cập nhật đơn ứng tuyển: {application.job.title}",
        message=(
            f"Đơn ứng tuyển vị trí {application.job.title} của bạn đã chuyển sang "
            f"trạng thái {application.get_status_display()}."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.candidate.email],
        fail_silently=True,
    )
