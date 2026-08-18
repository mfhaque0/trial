import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    # Set DIETITIAN_SECRET_KEY before enabling session-based features in production.
    SECRET_KEY = os.environ.get("DIETITIAN_SECRET_KEY") or secrets.token_urlsafe(32)
    DATABASE = BASE_DIR / "instance" / "dietitian.sqlite3"
    JSON_SORT_KEYS = False
