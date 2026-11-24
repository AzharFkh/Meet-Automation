"""Entrypoint automasi join Microsoft Teams via web menggunakan Selenium."""

from __future__ import annotations

import logging
import sys
import time
from datetime import date

from selenium import webdriver
from selenium.common.exceptions import WebDriverException

from src.config import load_config
from src.driver import create_driver
from src.teams import (
    click_join_button,
    click_optional_prompt,
    ensure_media_off,
    fill_username,
    leave_meeting,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("teams-automation")


def wait_in_meeting(driver: webdriver.Chrome, duration_minutes: int) -> None:
    """Menunggu di dalam meeting sesuai durasi target dengan log hitung mundur."""
    total_seconds = duration_minutes * 60
    end_time = time.monotonic() + total_seconds
    logger.info("Timer absen dimulai: %d menit.", duration_minutes)

    last_logged_minute = duration_minutes + 1
    while True:
        remaining = end_time - time.monotonic()
        if remaining <= 0:
            logger.info("Durasi %d menit telah tercapai.", duration_minutes)
            break

        try:
            if not driver.window_handles:
                logger.warning("Jendela browser ditutup secara manual. Menghentikan timer.")
                break
        except WebDriverException:
            logger.warning("Sesi browser sudah terputus. Menghentikan timer.")
            break

        remaining_minutes = int((remaining + 59) // 60)
        if remaining_minutes < last_logged_minute:
            logger.info("Sisa waktu meeting: ~%d menit.", remaining_minutes)
            last_logged_minute = remaining_minutes

        time.sleep(min(15.0, remaining))


def main() -> int:
    try:
        config = load_config()
    except ValueError as exc:
        logger.error("Konfigurasi tidak valid: %s", exc)
        return 1

    if config.end_date and date.today() > config.end_date:
        logger.info("Periode kegiatan sudah berakhir (%s). Melewati eksekusi.", config.end_date)
        return 0

    logger.info(
        "Menyiapkan Chrome WebDriver (headless=%s, keep_audio_on=%s)...",
        config.headless,
        config.keep_audio_on,
    )
    driver = create_driver(config.headless, config.keep_audio_on)

    try:
        logger.info("Membuka link meeting...")
        driver.get(config.meet_url)

        click_optional_prompt(
            driver,
            "continue_in_browser",
            "Memilih lanjut melalui browser web.",
            "Prompt launcher browser tidak ditemukan, lanjut ke tahap berikutnya.",
        )
        click_optional_prompt(
            driver,
            "continue_without_av",
            "Menutup popup izin dengan klik 'Continue without audio or video'.",
            "Popup izin audio/video tidak muncul, lanjut ke pre-join.",
            timeout=10.0,
        )
        fill_username(driver, config.username)
        ensure_media_off(driver)
        click_join_button(driver)

        wait_in_meeting(driver, config.duration_minutes)
    except KeyboardInterrupt:
        logger.info("Dihentikan oleh pengguna (Ctrl+C).")
    finally:
        leave_meeting(driver)

    return 0


if __name__ == "__main__":
    sys.exit(main())
