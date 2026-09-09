"""Đưa vai trò người dùng vào template thay vì so sánh chuỗi thủ công."""

from apps.jobs.services import is_admin, is_recruiter_or_admin
from apps.users.models import User


def user_roles(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {
            "is_admin": False,
            "is_recruiter": False,
            "is_recruiter_or_admin": False,
            "is_candidate": False,
        }
    return {
        "is_admin": is_admin(user),
        "is_recruiter": user.role == User.Role.RECRUITER,
        "is_recruiter_or_admin": is_recruiter_or_admin(user),
        "is_candidate": user.role == User.Role.CANDIDATE,
    }
