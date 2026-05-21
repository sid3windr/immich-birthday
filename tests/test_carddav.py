"""Tests for carddav.py core functionality."""

import pytest
import sys
import os

# Add parent dir to path for import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from carddav import normalize_bday


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