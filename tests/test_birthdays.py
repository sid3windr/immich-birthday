"""Tests for birthdays.py core functionality."""

import pytest
from datetime import datetime
import sys
import os

# Add parent dir to path for import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from birthdays import validate_birthdate


def test_validate_birthdate_valid():
    assert validate_birthdate("2020-01-15") is True
    assert validate_birthdate("1990-12-31") is True


def test_validate_birthdate_invalid():
    assert validate_birthdate("2020-13-01") is False  # invalid month
    assert validate_birthdate("2020-01-32") is False  # invalid day
    assert validate_birthdate("20-01-15") is False    # wrong format
    assert validate_birthdate("not-a-date") is False
    assert validate_birthdate("") is False
    assert validate_birthdate(None) is False  # None input