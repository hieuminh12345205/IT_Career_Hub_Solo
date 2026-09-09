"""Kiểm tra file tải lên dùng chung cho mọi form có nhận CV."""

from pathlib import Path

from django.core.exceptions import ValidationError

MAX_CV_SIZE = 5 * 1024 * 1024
PDF_MAGIC = b"%PDF-"

SIZE_ERROR = "CV không được lớn hơn 5MB."
TYPE_ERROR = "CV phải là file PDF hợp lệ."


def validate_pdf_upload(uploaded_file, max_size=MAX_CV_SIZE):
    """Chỉ nhận PDF thật, dưới giới hạn dung lượng.

    Kiểm tra dung lượng chạy trước và luôn chạy, kể cả với file đã lưu trong
    storage (không có ``content_type``). MIME do trình duyệt gửi lên có thể bị
    giả mạo nên phần header của file vẫn được đối chiếu với chữ ký PDF.
    """
    if not uploaded_file:
        return uploaded_file

    size = getattr(uploaded_file, "size", None)
    if size is not None and size > max_size:
        raise ValidationError(SIZE_ERROR)

    if Path(uploaded_file.name).suffix.lower() != ".pdf":
        raise ValidationError(TYPE_ERROR)

    # FieldFile đã lưu thì không cần đọc lại. File mới qua Admin cũng phải
    # kiểm header, kể cả ContentFile không có MIME do trình duyệt cung cấp.
    if getattr(uploaded_file, "_committed", False):
        return uploaded_file

    if getattr(uploaded_file, "content_type", "application/pdf") not in (
        "application/pdf",
        "application/octet-stream",
    ):
        raise ValidationError(TYPE_ERROR)

    original_position = uploaded_file.tell()
    try:
        uploaded_file.seek(0)
        header = uploaded_file.read(len(PDF_MAGIC))
    finally:
        uploaded_file.seek(original_position)
    if header != PDF_MAGIC:
        raise ValidationError(TYPE_ERROR)

    return uploaded_file
