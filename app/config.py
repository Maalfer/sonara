"""Configuración — Sonara (FastAPI, standalone)."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

VERSION = (BASE_DIR / "VERSION").read_text(encoding="utf-8").strip() if (BASE_DIR / "VERSION").exists() else "0.0.0"

SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-key-change-me")
DEBUG = os.environ.get("DEBUG", "0") == "1"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h.strip()]

DB_PATH = Path(os.environ.get("DB_PATH", str(BASE_DIR / "data" / "db.sqlite3")))
MUSIC_UPLOADS_ROOT = Path(os.environ.get("MUSIC_UPLOADS_ROOT", BASE_DIR / "data" / "uploads"))

SESSION_COOKIE_SECURE = not DEBUG
