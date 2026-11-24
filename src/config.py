"""Konfigurasi aplikasi yang dimuat dari file .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import date

from dotenv import load_dotenv


@dataclass(frozen=True)
class Config:
    """Konfigurasi runtime yang dimuat dari file .env."""

    meet_url: str
    username: str
    duration_minutes: int
    headless: bool
    keep_audio_on: bool = True
    end_date: date | None = None


def _parse_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_config() -> Config:
    """Memuat dan memvalidasi variabel konfigurasi dari .env."""
    load_dotenv()

    meet_url = os.getenv("MEET_URL", "").strip()
    username = os.getenv("MEET_USERNAME", "").strip()
    duration_raw = os.getenv("DURATION_MINUTES", "100").strip()
    headless_raw = os.getenv("HEADLESS", "false")
    keep_audio_raw = os.getenv("KEEP_AUDIO_ON", "true")
    end_date_raw = os.getenv("END_DATE", "").strip()

    if not meet_url:
        raise ValueError("MEET_URL wajib diisi di file .env")
    if not username:
        raise ValueError("MEET_USERNAME wajib diisi di file .env")

    try:
        duration_minutes = int(duration_raw)
    except ValueError as exc:
        raise ValueError(f"DURATION_MINUTES harus berupa angka bulat: {duration_raw}") from exc

    if duration_minutes <= 0:
        raise ValueError("DURATION_MINUTES harus lebih besar dari 0")

    end_date: date | None = None
    if end_date_raw:
        try:
            end_date = date.fromisoformat(end_date_raw)
        except ValueError as exc:
            raise ValueError(f"END_DATE harus berformat YYYY-MM-DD: {end_date_raw}") from exc

    return Config(
        meet_url=meet_url,
        username=username,
        duration_minutes=duration_minutes,
        headless=_parse_bool(headless_raw),
        keep_audio_on=_parse_bool(keep_audio_raw),
        end_date=end_date,
    )
