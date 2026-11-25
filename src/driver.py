"""Inisialisasi Chrome WebDriver untuk automasi browser."""

from __future__ import annotations

import os

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service


def create_driver(headless: bool, keep_audio_on: bool = True) -> webdriver.Chrome:
    """Inisialisasi Chrome WebDriver dengan kontrol izin media dan notifikasi."""
    options = Options()
    media_setting = 1 if keep_audio_on else 2
    prefs = {
        "profile.default_content_setting_values.media_stream_mic": media_setting,
        "profile.default_content_setting_values.media_stream_camera": media_setting,
        "profile.default_content_setting_values.notifications": 2,
    }
    options.add_experimental_option("prefs", prefs)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument("--disable-notifications")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--autoplay-policy=no-user-gesture-required")

    if keep_audio_on:
        # Otomatis izinkan prompt browser & pakai virtual device senyap agar
        # audio meeting tetap aktif (termasuk di headless/Docker) tanpa bocor suara mic.
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--use-fake-device-for-media-stream")

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
