from .base import *

DEBUG = True

# Development fallback: use local SQLite unless explicitly configured otherwise.
if config("USE_SQLITE", default=True, cast=bool):  # noqa: F405
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",  # noqa: F405
        }
    }
