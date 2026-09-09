import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import send_mail

from apps.users.models import User

logger = logging.getLogger(__name__)


def _send_notification(application_id, **kwargs):
    """Lỗi SMTP không hủy thao tác đã lưu, nhưng phải có log để xử lý."""
    try:
        sent = send_mail(fail_silently=False, **kwargs)
    except (SMTPException, OSError, ValueError) as exc:
        # Không ghi email, nội dung CV hay thông tin xác thực vào log.
        logger.error(
            "notification_failed application_id=%s error_type=%s",
            application_id,
            type(exc).__name__,
        )
        return 0
    if not sent:
        logger.warning("notification_not_sent application_id=%s", application_id)
    return sent


def _candidate_name(candidate):
    return candidate.get_full_name() or candidate.username


def _recruiter_emails(company):
    """Lấy email của chủ công ty và các recruiter được gán vào công ty."""
    # recruiter có thể là None sau khi tài khoản chủ công ty bị xóa.
    owner = company.recruiter
    emails = {owner.email if owner and owner.is_active else ""}
    emails.update(
        User.objects.filter(
            role=User.Role.RECRUITER,
            is_active=True,
            recruiter_profile__company=company,
        ).values_list("email", flat=True)
    )
    return sorted(email for email in emails if email)


def notify_recruiters_new_application(application):
    recipients = _recruiter_emails(application.job.company)
    if not recipients:
        return 0

    return _send_notification(
        application.pk,
        subject=f"Ứng viên mới cho vị trí {application.job.title}",
        message=(
            f"Ứng viên {_candidate_name(application.candidate)} "
            f"vừa ứng tuyển vị trí {application.job.title}."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
    )


def notify_candidate_status_changed(application):
    if not application.candidate.email or not application.candidate.is_active:
        return 0

    return _send_notification(
        application.pk,
        subject=f"Cập nhật đơn ứng tuyển: {application.job.title}",
        message=(
            f"Đơn ứng tuyển vị trí {application.job.title} của bạn đã chuyển sang "
            f"trạng thái {application.get_status_display()}."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[application.candidate.email],
    )
