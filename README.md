# IT Career Hub

IT Career Hub là nền tảng tuyển dụng IT xây dựng bằng Django, kết nối ứng viên và nhà tuyển dụng.

## Tính năng

- Đăng ký và đăng nhập với hai vai trò Candidate và Recruiter.
- Candidate: tạo hồ sơ, upload CV PDF, tìm kiếm/lọc việc làm, lưu việc yêu thích, ứng tuyển và theo dõi trạng thái.
- Recruiter: quản lý hồ sơ công ty, CRUD tin tuyển dụng, xem ứng viên và cập nhật trạng thái ứng tuyển.
- Email notification dùng console backend trong môi trường development.
- Dashboard thống kê cho Recruiter và Django Admin cho quản trị viên.
- Validation form, phân trang và kiểm soát quyền truy cập.

## Công nghệ

Python 3.11+, Django 5.2, SQLite (development), PostgreSQL (Docker/production), Bootstrap.

## Chạy local

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements/dev.txt
if (!(Test-Path .env)) { Copy-Item .env.example .env }
python manage.py migrate --settings=config.settings.dev
python manage.py seed_data --settings=config.settings.dev
python manage.py runserver --settings=config.settings.dev
```

Linux/macOS/Git Bash có thể dùng `source .venv/bin/activate` và `test -f .env || cp .env.example .env`.

Mở [http://127.0.0.1:8000](http://127.0.0.1:8000). Email development được in trong terminal.

## Tài khoản demo

Sau khi chạy `seed_data`:

| Vai trò | Username | Password |
|---|---|---|
| Candidate | `demo_candidate` | `Demo@12345` |
| Recruiter | `demo_recruiter` | `Demo@12345` |
| Admin | `demo_admin` | `Demo@12345` |

Các tài khoản trên chỉ dành cho demo local, không dùng trong môi trường thật.
`seed_data` chỉ được bật trong cấu hình dev/test. Chạy lại không đổi mật khẩu,
không mở lại tin đã đóng và không ghi đè nội dung đã chỉnh sửa.

## Kiểm thử

```bash
python manage.py check --settings=config.settings.dev
python manage.py test --settings=config.settings.test
python -m flake8 .
python -m black --check .
python -m isort --check-only .
python manage.py makemigrations --check --dry-run --settings=config.settings.test
```

CI chạy cùng bộ test trên SQLite và PostgreSQL. Để kiểm tra khóa dòng và yêu cầu
đồng thời trên máy có PostgreSQL (thông tin DB lấy từ `.env`):

```bash
python manage.py test --settings=config.settings.test_postgres
```

Django tạo database test riêng rồi xóa sau khi chạy. Tài khoản PostgreSQL cần
quyền tạo database; có thể đặt `TEST_DB_NAME` để chọn tên DB test riêng.

## Docker

```bash
docker compose up --build
```

Đây là cấu hình **development**. Ứng dụng chạy tại
[http://localhost:8000](http://localhost:8000). Docker dùng `POSTGRES_DB`,
`POSTGRES_USER`, `POSTGRES_PASSWORD` cho cả database và web; `DB_HOST=db` được
cố định trong container, không lấy `localhost` từ cấu hình chạy local.
Không tự tạo tài khoản demo mỗi lần khởi động. Khi cần dữ liệu mẫu, chạy:

```bash
docker compose exec web python manage.py seed_data --settings=config.settings.dev
```

`.dockerignore` loại `.env`, dữ liệu DB, CV và môi trường ảo khỏi image.

## Xử lý file media

- `media/avatars/` và `media/company_logos/` là ảnh public, được phục vụ qua
  `apps.core.views.public_media` nên hiển thị đúng cả khi `DEBUG=False`.
- `media/cvs/` và `media/application_cvs/` là dữ liệu riêng tư. URL `/media/...`
  tới hai thư mục này luôn trả 404; CV chỉ đọc được qua các view có kiểm quyền
  (`users:candidate_cv`, `applications:download_cv`) và được gửi kèm header
  `Cache-Control: private, no-store`.
- Khi triển khai thật, nên đặt reverse proxy chặn thẳng `/media/cvs/` và
  `/media/application_cvs/` để không phụ thuộc hoàn toàn vào tầng ứng dụng.

## Bảo mật

Không commit `.env`, `db.sqlite3`, thư mục `media/`, `.venv/` hoặc thông tin xác thực thật. Trước khi push, kiểm tra bằng `git status` và `git diff --cached`.

## Triển khai và bảo trì

Xem [hướng dẫn vận hành](docs/operations.md) và [báo cáo rà soát](docs/review-2026-09-05.md).

## License

MIT License. Xem file `LICENSE`.
