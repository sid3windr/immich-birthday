"""Tests for birthdays.py core functionality."""

import pytest
from datetime import datetime
import sys
import os

# Add parent dir to path for import
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from birthdays import validate_birthdate, update_birthdates


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


def test_update_birthdates_skips_malformed_and_empty_rows():
    """CSV/row edge cases: short rows, empty birthdates, and invalid dates are skipped gracefully."""
    import requests_mock

    rows = [
        ["id1", "Alice", ""],           # empty birthdate -> skip
        ["id2", "Bob", "not-a-date"],  # invalid -> skip with warning
        ["id3"],                           # too short -> skip
        ["id4", "Charlie", "2023-05-01"],  # valid, should call API
    ]

    with requests_mock.Mocker() as m:
        m.put("http://example.com/api/people/id4", json={}, status_code=200)
        # Should not raise, and only make one real API call
        update_birthdates("http://example.com", "dummykey", rows, silent=True)

    # Only one PUT was made
    assert len(m.request_history) == 1
    assert m.request_history[0].url.endswith("/id4")