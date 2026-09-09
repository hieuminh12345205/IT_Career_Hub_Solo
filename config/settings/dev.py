from .base import *  # noqa: F403

DEBUG = True
ALLOW_DEMO_SEED = True

# Development fallback: use local SQLite unless explicitly configured otherwise.
if config("USE_SQLITE", default=True, cast=bool):  # noqa: F405
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }

# django-debug-toolbar chỉ bật ở dev và chỉ khi cài được, để `pip install -r
# requirements/base.txt` (môi trường prod) vẫn chạy dev settings không lỗi.
try:
    import debug_toolbar  # noqa: F401
except ImportError:
    pass
else:
    INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
    MIDDLEWARE.insert(  # noqa: F405
        0, "debug_toolbar.middleware.DebugToolbarMiddleware"
    )
    INTERNAL_IPS = ["127.0.0.1", "localhost"]
