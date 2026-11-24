"""Automasi join Microsoft Teams via web menggunakan Selenium dengan timer."""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass
from datetime import date

from dotenv import load_dotenv
from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("teams-automation")

# Selector kandidat untuk UI Microsoft Teams web.
# Mudah disesuaikan nanti saat uji coba alur klik langsung.
TEAMS_SELECTORS: dict[str, list[tuple[str, str]]] = {
    "continue_in_browser": [
        (By.CSS_SELECTOR, "button[data-tid='joinOnWeb']"),
        (By.XPATH, "//button[contains(., 'Continue on this browser')]"),
        (By.XPATH, "//button[contains(., 'Join on the web instead')]"),
        (By.XPATH, "//a[contains(., 'Continue on this browser')]"),
    ],
    "continue_without_av": [
        (By.CSS_SELECTOR, "button[data-focus-target='gum-continue']"),
        (By.XPATH, "//button[contains(., 'Continue without audio or video')]"),
        (By.CSS_SELECTOR, "button[data-tid='prejoin-continue-without-av']"),
        (By.XPATH, "//button[contains(., 'Lanjutkan tanpa audio atau video')]"),
    ],
    "username_input": [
        (By.CSS_SELECTOR, "input[data-tid='prejoin-display-name-input']"),
        (By.CSS_SELECTOR, "input[placeholder*='name' i]"),
        (By.CSS_SELECTOR, "input[aria-label*='name' i]"),
    ],
    "camera_toggle": [
        (By.CSS_SELECTOR, "button[data-tid='toggle-video']"),
        (By.CSS_SELECTOR, "div[data-tid='toggle-video']"),
        (By.CSS_SELECTOR, "button[aria-label*='Camera' i]"),
        (By.CSS_SELECTOR, "input[type='checkbox'][aria-label*='Camera' i]"),
    ],
    "mic_toggle": [
        (By.CSS_SELECTOR, "button[data-tid='toggle-mute']"),
        (By.CSS_SELECTOR, "div[data-tid='toggle-mute']"),
        (By.CSS_SELECTOR, "button[aria-label*='Mic' i]"),
        (By.CSS_SELECTOR, "input[type='checkbox'][aria-label*='Mic' i]"),
    ],
    "join_button": [
        (By.CSS_SELECTOR, "button[data-tid='prejoin-join-button']"),
        (By.XPATH, "//button[contains(., 'Join now')]"),
    ],
    "leave_button": [
        (By.CSS_SELECTOR, "button[data-tid='hangup-main-btn']"),
        (By.CSS_SELECTOR, "button[aria-label*='Leave' i]"),
        (By.XPATH, "//button[contains(., 'Leave')]"),
    ],
}


@dataclass(frozen=True)
class Config:
    """Konfigurasi runtime yang dimuat dari file .env."""

    meet_url: str
    username: str
    duration_minutes: int
    headless: bool
    end_date: date | None = None


def load_config() -> Config:
    """Memuat dan memvalidasi variabel konfigurasi dari .env."""
    load_dotenv()

    meet_url = os.getenv("MEET_URL", "").strip()
    username = os.getenv("MEET_USERNAME", "").strip()
    duration_raw = os.getenv("DURATION_MINUTES", "100").strip()
    headless_raw = os.getenv("HEADLESS", "false").strip().lower()
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

    headless = headless_raw in {"1", "true", "yes", "on"}
    return Config(
        meet_url=meet_url,
        username=username,
        duration_minutes=duration_minutes,
        headless=headless,
        end_date=end_date,
    )


def create_driver(headless: bool) -> webdriver.Chrome:
    """Inisialisasi Chrome WebDriver dengan blokir kamera, mic, dan notifikasi."""
    options = Options()
    # Blokir izin kamera, mikrofon, dan notifikasi di level browser (2 = Block).
    prefs = {
        "profile.default_content_setting_values.media_stream_mic": 2,
        "profile.default_content_setting_values.media_stream_camera": 2,
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")

    chrome_binary = os.getenv("CHROME_BINARY", "").strip()
    if chrome_binary:
        options.binary_location = chrome_binary

    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
    else:
        options.add_argument("--start-maximized")

    chromedriver_path = os.getenv("CHROMEDRIVER_PATH", "").strip()
    if chromedriver_path:
        return webdriver.Chrome(service=Service(executable_path=chromedriver_path), options=options)

    return webdriver.Chrome(options=options)


def find_first_element(
    driver: webdriver.Chrome,
    locators: list[tuple[str, str]],
    timeout: float = 10.0,
    clickable: bool = False,
) -> WebElement | None:
    """Mencari elemen pertama yang cocok dari daftar kandidat selector."""
    condition = EC.element_to_be_clickable if clickable else EC.visibility_of_element_located
    per_locator_timeout = max(1.5, timeout / max(len(locators), 1))

    for by, value in locators:
        try:
            return WebDriverWait(driver, per_locator_timeout).until(condition((by, value)))
        except TimeoutException:
            continue
    return None


def click_optional_prompt(
    driver: webdriver.Chrome,
    selector_key: str,
    found_message: str,
    missing_message: str,
    timeout: float = 8.0,
) -> None:
    """Klik tombol prompt opsional jika muncul di halaman."""
    btn = find_first_element(
        driver,
        TEAMS_SELECTORS[selector_key],
        timeout=timeout,
        clickable=True,
    )
    if btn:
        btn.click()
        logger.info(found_message)
    else:
        logger.info(missing_message)


def fill_username(driver: webdriver.Chrome, username: str) -> bool:
    """Mengisi nama peserta pada layar pre-join Teams."""
    name_input = find_first_element(
        driver,
        TEAMS_SELECTORS["username_input"],
        timeout=20.0,
        clickable=True,
    )
    if not name_input:
        logger.warning("Kolom input nama belum ditemukan.")
        return False

    name_input.clear()
    name_input.send_keys(username)
    logger.info("Nama peserta diisi: %s", username)
    return True


def _is_toggle_on(element: WebElement) -> bool | None:
    """Membaca status toggle (ON/OFF) dari atribut ARIA umum."""
    for attr in ("aria-checked", "aria-pressed"):
        val = element.get_attribute(attr)
        if val is not None:
            return val.lower() == "true"

    label = (element.get_attribute("aria-label") or "").lower()
    if "turn off" in label or "mute" in label and "unmute" not in label:
        return True
    if "turn on" in label or "unmute" in label:
        return False
    return None


def _ensure_toggle_off(
    driver: webdriver.Chrome,
    label: str,
    locators: list[tuple[str, str]],
) -> None:
    """Memastikan toggle media (kamera/mic) dalam posisi mati."""
    toggle = find_first_element(driver, locators, timeout=8.0, clickable=True)
    if not toggle:
        logger.warning("Toggle %s tidak ditemukan (mungkin sudah terblokir oleh browser).", label)
        return

    state = _is_toggle_on(toggle)
    if state is True:
        toggle.click()
        logger.info("%s dimatikan melalui UI pre-join.", label)
    elif state is False:
        logger.info("%s sudah dalam posisi mati.", label)
    else:
        logger.info("Status %s tidak terbaca jelas dari atribut ARIA; tidak diklik otomatis.", label)


def ensure_media_off(driver: webdriver.Chrome) -> None:
    """Memastikan kamera dan mikrofon dalam keadaan mati sebelum join."""
    _ensure_toggle_off(driver, "Kamera", TEAMS_SELECTORS["camera_toggle"])
    _ensure_toggle_off(driver, "Mikrofon", TEAMS_SELECTORS["mic_toggle"])


def click_join_button(driver: webdriver.Chrome) -> bool:
    """Menekan tombol Join now pada layar pre-join."""
    join_btn = find_first_element(
        driver,
        TEAMS_SELECTORS["join_button"],
        timeout=15.0,
        clickable=True,
    )
    if not join_btn:
        logger.warning("Tombol 'Join now' tidak ditemukan.")
        return False

    join_btn.click()
    logger.info("Tombol Join diklik.")
    return True


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


def leave_meeting(driver: webdriver.Chrome) -> None:
    """Mencoba klik tombol Leave lalu menutup browser dengan bersih."""
    try:
        if driver.window_handles:
            leave_btn = find_first_element(
                driver,
                TEAMS_SELECTORS["leave_button"],
                timeout=5.0,
                clickable=True,
            )
            if leave_btn:
                leave_btn.click()
                logger.info("Berhasil klik tombol Leave.")
                time.sleep(2)
    except WebDriverException:
        pass
    finally:
        driver.quit()
        logger.info("Browser ditutup.")


def main() -> int:
    try:
        config = load_config()
    except ValueError as exc:
        logger.error("Konfigurasi tidak valid: %s", exc)
        return 1

    if config.end_date and date.today() > config.end_date:
        logger.info("Periode kegiatan sudah berakhir (%s). Melewati eksekusi.", config.end_date)
        return 0

    logger.info("Menyiapkan Chrome WebDriver (headless=%s)...", config.headless)
    driver = create_driver(config.headless)

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
