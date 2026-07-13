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
Copy-Item .env.example .env
python manage.py migrate --settings=config.settings.dev
python manage.py seed_data --settings=config.settings.dev
python manage.py runserver --settings=config.settings.dev
```

Linux/macOS/Git Bash có thể dùng `source .venv/bin/activate` và `cp .env.example .env`.

Mở [http://127.0.0.1:8000](http://127.0.0.1:8000). Email development được in trong terminal.

## Tài khoản demo

Sau khi chạy `seed_data`:

| Vai trò | Username | Password |
|---|---|---|
| Candidate | `demo_candidate` | `Demo@12345` |
| Recruiter | `demo_recruiter` | `Demo@12345` |
| Admin | `demo_admin` | `Demo@12345` |

Các tài khoản trên chỉ dành cho demo local, không dùng trong môi trường thật.

## Kiểm thử

```bash
python manage.py check --settings=config.settings.dev
python manage.py test --settings=config.settings.test
```

## Docker

```bash
docker compose up --build
```

Ứng dụng chạy tại [http://localhost:8000](http://localhost:8000). Có thể thay các biến `POSTGRES_*`, `DB_*` và `SECRET_KEY` bằng file `.env` local; không commit file này.

## Bảo mật

Không commit `.env`, `db.sqlite3`, thư mục `media/`, `.venv/` hoặc thông tin xác thực thật. Trước khi push, kiểm tra bằng `git status` và `git diff --cached`.

## License

MIT License. Xem file `LICENSE`.
