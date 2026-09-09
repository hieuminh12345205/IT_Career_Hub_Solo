# Vận hành IT Career Hub

## Cập nhật một bản phát hành

1. Review PR và chờ cả hai nhóm CI (SQLite/PostgreSQL) thành công.
2. Sao lưu PostgreSQL và toàn bộ media bằng công cụ của hạ tầng; thử khôi phục
   vào môi trường riêng định kỳ. CV phải nằm trong bản sao lưu có kiểm soát quyền.
3. Cài requirements tương ứng; chạy migration trước khi khởi động bản mới.
4. Kiểm tra đăng nhập, tạo tin, ứng tuyển, tải CV có quyền và thay đổi trạng thái.

Không sửa/xóa migration đã được team áp dụng. Nếu hai nhánh tạo migration trùng
số, cần review dependencies và tạo migration merge phù hợp trước khi triển khai.
Không dùng `migrate --fake` để bỏ qua lỗi thiếu cột.

## Chạy production

Dockerfile và docker-compose.yml hiện tại dành cho development. Production dùng
Linux với PostgreSQL, Gunicorn và reverse proxy HTTPS; đặt biến môi trường
`DJANGO_SETTINGS_MODULE=config.settings.prod`. Cấu hình cần có:

- `SECRET_KEY`: chuỗi ngẫu nhiên riêng, tối thiểu 50 ký tự; không dùng khóa demo.
- `ALLOWED_HOSTS`: domain thật, phân cách bằng dấu phẩy, không dùng `*`.
- Các biến `DB_*`: thông tin database production.
- `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` và thông tin SMTP.
- `EMAIL_TIMEOUT=10`: giới hạn chờ SMTP, tính bằng giây.

Ví dụ các lệnh sau khi cấu hình môi trường:

```bash
python -m pip install -r requirements/prod.txt
python manage.py check --deploy --settings=config.settings.prod
python manage.py migrate --settings=config.settings.prod
python manage.py collectstatic --noinput --settings=config.settings.prod
python manage.py createsuperuser --settings=config.settings.prod
gunicorn config.wsgi:application --bind 127.0.0.1:8000 --workers 2 --timeout 60
```

Chỉ bật `TRUST_X_FORWARDED_PROTO=True` nếu proxy tin cậy luôn ghi đè header này.
Giữ HTTPS và secure cookies bật. Mount media trên ổ đĩa bền vững và hạn chế quyền
đọc cho tài khoản chạy app. Không phục vụ cả MEDIA_ROOT qua Nginx/CDN: chỉ cho
phép `avatars/` và `company_logos/`; CV phải đi qua view có kiểm quyền. Đặt giới
hạn request body ở proxy phù hợp (ví dụ 12 MB để cập nhật đồng thời avatar/CV).

## Email và log

Email ứng tuyển và đổi trạng thái được gửi sau khi transaction commit. Lỗi SMTP
không hủy đơn ứng tuyển/trạng thái đã lưu; log `notification_failed` hoặc
`notification_not_sent` chỉ chứa ID và loại lỗi, không chứa CV hoặc mật khẩu.
Kiểm tra SMTP và đối chiếu application ID khi có lỗi.

Log `application_created` và `application_status_changed` ghi người thao tác,
application ID và trạng thái trước/sau ở luồng tuyển dụng. Django Admin có lịch
sử thay đổi riêng. Hạ tầng cần thu gom, lưu trữ và xoay vòng log; log console
không phải lịch sử bất biến trong database. Đổi trạng thái trực tiếp trong Admin
hiện không gửi thông báo: dùng trang ứng viên của tin để chạy đầy đủ luồng email.

Hiện email gửi đồng bộ, **chưa có retry tự động** và chưa bảo đảm giao thư tới
hộp thư thật. Khi cần cam kết giao thông báo, bổ sung outbox bền vững và worker
retry; timeout SMTP không thay thế cơ chế này.

## Công việc bảo trì định kỳ

- Review PR cập nhật dependency do Dependabot tạo, chạy CI trước khi merge.
- Kiểm tra dung lượng media, bản sao lưu và việc khôi phục dữ liệu.
- Xác định thời hạn giữ CV, quy trình xóa dữ liệu và quyền của recruiter.
- Trước khi mở dịch vụ công khai, cấu hình giới hạn đăng nhập/request ở proxy
  hoặc bổ sung cơ chế chống brute force, rồi thử trên staging.

Kiểm tra chữ ký `%PDF-` và giới hạn 5 MB là kiểm tra loại file cơ bản, không phải
quét mã độc hoặc xác minh toàn bộ cấu trúc PDF. Khi nhận CV từ nguồn công khai
quy mô lớn, cân nhắc antivirus/quarantine và lưu file ở miền riêng.
