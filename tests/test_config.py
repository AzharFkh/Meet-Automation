"""Unit test untuk konfigurasi aplikasi."""

from __future__ import annotations

import os
import unittest
from datetime import date
from unittest.mock import patch

from src.config import load_config


class TestConfig(unittest.TestCase):
    def test_load_config_valid(self) -> None:
        env = {
            "MEET_URL": "https://teams.microsoft.com/meet/123?p=abc",
            "MEET_USERNAME": "Tester",
            "DURATION_MINUTES": "100",
            "HEADLESS": "true",
            "KEEP_AUDIO_ON": "true",
            "END_DATE": "2026-12-30",
        }
        with patch("src.config.load_dotenv"), patch.dict(os.environ, env, clear=True):
            cfg = load_config()

        self.assertEqual(cfg.meet_url, env["MEET_URL"])
        self.assertEqual(cfg.username, "Tester")
        self.assertEqual(cfg.duration_minutes, 100)
        self.assertTrue(cfg.headless)
        self.assertTrue(cfg.keep_audio_on)
        self.assertEqual(cfg.end_date, date(2026, 12, 30))

    def test_missing_meet_url_raises(self) -> None:
        env = {"MEET_USERNAME": "Tester"}
        with patch("src.config.load_dotenv"), patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError):
                load_config()

    def test_invalid_end_date_raises(self) -> None:
        env = {
            "MEET_URL": "https://teams.microsoft.com/meet/123",
            "MEET_USERNAME": "Tester",
            "END_DATE": "30-12-2026",
        }
        with patch("src.config.load_dotenv"), patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError):
                load_config()


if __name__ == "__main__":
    unittest.main()
