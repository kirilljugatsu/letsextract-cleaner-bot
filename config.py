"""Configuration for LetsExtract Cleaner Bot."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


# Load environment variables from .env if present.
load_dotenv()

# General bot configuration constants.
TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS: list[str] = [".xlsx", ".xls"]

# Data cleaning configuration constants.
RUSSIAN_ZONES: list[str] = [".ru", ".рф", ".su"]
SEARCH_ENGINE_DOMAINS: list[str] = [
    "search.yahoo",
    "search.brave",
    "google.com",
    "google.ru",
    "yandex.ru/search",
    "bing.com",
    "duckduckgo.com",
]
REQUIRED_COLUMNS: list[str] = [
    "Значение",
    "Домен",
    "Заголовок",
    "META Description",
]

# Paths.
BASE_DIR = Path(__file__).resolve().parent
TEMP_DIR = BASE_DIR / "temp_files"
TEMP_DIR.mkdir(exist_ok=True)
