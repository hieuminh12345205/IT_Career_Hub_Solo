"""Cùng bộ test với SQLite, nhưng kiểm tra DB và khóa dòng trên PostgreSQL."""

from .base import DATABASES as POSTGRES_DATABASES
from .test import *  # noqa: F403

DATABASES = POSTGRES_DATABASES
DATABASES["default"]["TEST"] = {
    "NAME": config("TEST_DB_NAME", default=None)
}  # noqa: F405
