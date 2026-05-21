"""Tests for carddav.py core functionality."""

import pytest
import sys
import os

# Add parent dir to path for import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from carddav import normalize_bday, load_config


def test_normalize_bday_valid_formats():
    assert normalize_bday("2023-05-15") == "2023-05-15"
    assert normalize_bday("19901231") == "1990-12-31"
    assert normalize_bday("  2020-01-01  ") == "2020-01-01"


def test_normalize_bday_unsupported_or_invalid():
    assert normalize_bday("2023/05/15") is None  # wrong separator
    assert normalize_bday("15-05-2023") is None  # wrong order
    assert normalize_bday("not-a-date") is None
    assert normalize_bday("") is None


def test_normalize_bday_old_year_omitted():
    # X-APPLE-OMIT-YEAR style (year < 1900)
    assert normalize_bday("1604-05-15") is None
    assert normalize_bday("18001231") is None


def test_load_config_carddav_with_ini(tmp_path, monkeypatch):
    """carddav load_config reads from immich.ini when present."""
    ini = tmp_path / "immich.ini"
    ini.write_text("[carddav]\nurl=https://carddav.test\nusername=testuser\npassword=secret\nsleep=0.5\n")

    monkeypatch.setattr("carddav.__file__", str(tmp_path / "carddav.py"))

    url, user, pw, slp = load_config()
    assert url == "https://carddav.test"
    assert user == "testuser"
    assert pw == "secret"
    assert slp == 0.5


def test_load_config_carddav_fallback_to_env(tmp_path, monkeypatch):
    """carddav load_config falls back to env vars."""
    ini = tmp_path / "immich.ini"
    ini.write_text("[carddav]\n")

    monkeypatch.setattr("carddav.__file__", str(tmp_path / "carddav.py"))
    monkeypatch.setenv("CARDDAV_URL", "https://env-carddav.test")
    monkeypatch.setenv("CARDDAV_USER", "envuser")
    monkeypatch.setenv("CARDDAV_PASS", "envpass")
    monkeypatch.setenv("CARDDAV_SLEEP", "1.0")

    url, user, pw, slp = load_config()
    assert url == "https://env-carddav.test"
    assert user == "envuser"
    assert pw == "envpass"
    assert slp == 1.0


def test_name_cleaning_emoji_and_nickname():
    """Nickname cleanup and trailing emoji/symbol stripping using the real implementation."""
    from carddav import clean_name

    assert clean_name("William Turner (Bill)") == "William Turner"
    assert clean_name("Alice ⚰") == "Alice"
    assert clean_name("Bob 🇩🇪") == "Bob"
    assert clean_name("  Charlie (Chuck) 🎉  ") == "Charlie"