"""Selector dan interaksi UI Microsoft Teams web."""

from __future__ import annotations

import logging
import time

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

logger = logging.getLogger("teams-automation")

# Selector kandidat untuk UI Microsoft Teams web.
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
        (By.CSS_SELECTOR, "input[data-tid='toggle-video']"),
        (By.CSS_SELECTOR, "button[data-tid='toggle-video']"),
        (By.CSS_SELECTOR, "div[data-tid='toggle-video']"),
        (By.CSS_SELECTOR, "button[aria-label*='Camera' i]"),
        (By.CSS_SELECTOR, "input[type='checkbox'][aria-label*='Camera' i]"),
    ],
    "mic_toggle": [
        (By.CSS_SELECTOR, "input[data-tid='toggle-mute']"),
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


def find_first_element(
    driver: webdriver.Chrome,
    locators: list[tuple[str, str]],
    timeout: float = 10.0,
    clickable: bool = False,
    present_only: bool = False,
) -> WebElement | None:
    """Mencari elemen pertama yang cocok dari daftar kandidat selector."""
    if present_only:
        condition = EC.presence_of_element_located
    elif clickable:
        condition = EC.element_to_be_clickable
    else:
        condition = EC.visibility_of_element_located
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
    timeout: float = 5.0,
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
    """Membaca status toggle (ON/OFF) dari title, ARIA, data-cid, atau checkbox."""
    for attr in ("title", "aria-label"):
        text = (element.get_attribute(attr) or "").lower()
        if not text:
            continue
        if "turn off" in text or ("mute" in text and "unmute" not in text):
            return True
        if "turn on" in text or "unmute" in text:
            return False

    data_cid = (element.get_attribute("data-cid") or "").lower()
    if data_cid.endswith("-true"):
        return True
    if data_cid.endswith("-false"):
        return False

    for attr in ("aria-checked", "aria-pressed"):
        val = element.get_attribute(attr)
        if val is not None:
            return val.lower() == "true"

    if element.tag_name.lower() == "input" and (element.get_attribute("type") or "").lower() == "checkbox":
        return element.is_selected()

    return None


def _ensure_toggle_off(
    driver: webdriver.Chrome,
    label: str,
    locators: list[tuple[str, str]],
) -> None:
    """Memastikan toggle media (kamera/mic) dalam posisi mati."""
    toggle = find_first_element(driver, locators, timeout=8.0, present_only=True)
    if not toggle:
        logger.warning("Toggle %s tidak ditemukan (mungkin sudah terblokir oleh browser).", label)
        return

    state = _is_toggle_on(toggle)
    if state is True:
        try:
            toggle.click()
        except WebDriverException:
            driver.execute_script("arguments[0].click();", toggle)
        logger.info("%s dimatikan melalui UI pre-join.", label)
    elif state is False:
        logger.info("%s sudah dalam posisi mati.", label)
    else:
        logger.info("Status %s tidak terbaca jelas; tidak diklik otomatis.", label)


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
