#!/usr/bin/env python3

"""
Immich Birthday Sync.

See README.md and the command line help for more information.
Copyright (c) 2025 Tom Laermans.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3.

This program is distributed in the hope that it will be useful, but
WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import requests
import configparser
import os
import sys
import argparse
import csv
from datetime import datetime


def load_config():
    """Load Immich configuration from immich.ini or environment variables."""
    config = configparser.ConfigParser()
    ini_path = os.path.join(os.path.dirname(__file__), "immich.ini")

    if not os.path.exists(ini_path):
        raise FileNotFoundError(f"Config file not found: {ini_path}")

    config.read(ini_path)

    IMMICH_URL = config.get("immich", "url", fallback=os.environ.get("IMMICH_URL", "http://localhost:2283"))
    API_KEY = config.get("immich", "api_key", fallback=os.environ.get("IMMICH_API_KEY"))

    if not API_KEY:
        sys.exit("Error: Immich API key not set. Use immich.ini or IMMICH_API_KEY environment variable.")

    return IMMICH_URL, API_KEY


def get_people_without_birthdate(IMMICH_URL, API_KEY):
    headers = {
        "Accept": "application/json",
        "x-api-key": API_KEY,
    }

    page = 1
    size = 1000
    results = []

    while True:
        url = f"{IMMICH_URL}/api/people?withHidden=false&page={page}&size={size}"
        resp = requests.get(url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

        people = data.get("people", [])
        # Keep only those with a name and no birthDate
        for person in people:
            if person.get("name") and not person.get("birthDate"):
                results.append(person)

        # Handle pagination
        if not data.get("hasNextPage", False):
            break
        page += 1

    return results


def validate_birthdate(date_str):
    """Return True if date_str is in YYYY-MM-DD format."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def update_birthdates(IMMICH_URL, API_KEY, rows, silent):
    """Update birthdays on Immich based on the rows passed"""
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": API_KEY,
    }

    for row in rows:
        if not row or len(row) < 3:
            continue  # skip empty or malformed lines

        person_id, name, birthdate = [cell.strip() for cell in row]
        if not birthdate:
            continue

        if not validate_birthdate(birthdate):
            print(f"⚠ Skipping {name} ({person_id}): invalid birthdate '{birthdate}'", file=sys.stderr)
            continue

        url = f"{IMMICH_URL}/api/people/{person_id}"
        payload = {"birthDate": birthdate}

        resp = requests.put(url, headers=headers, json=payload)
        if resp.status_code == 200:
            if not silent:
                print(f"✔ Updated {name} ({person_id}) with birthDate={birthdate}", file=sys.stderr)
        else:
            print(f"✖ Failed to update {name} ({person_id}): {resp.status_code} {resp.text}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Immich people birthdate management")
    parser.add_argument("--fetch", action="store_true", help="Fetch people without birthdates and output CSV")
    parser.add_argument("--update", action="store_true", help="Update people birthdates from CSV")
    parser.add_argument("--silent", action="store_true", help="No non-error output")
    parser.add_argument("--file", type=str, help="CSV file to read from or write to (default: stdin/stdout)")
    args = parser.parse_args()

    if not args.fetch and not args.update:
        sys.exit("Error: must specify either --fetch or --update")

    IMMICH_URL, API_KEY = load_config()

    if args.fetch:
        people_no_birthdate = get_people_without_birthdate(IMMICH_URL, API_KEY)
        output = open(args.file, "w", newline="", encoding="utf-8") if args.file else sys.stdout
        writer = csv.writer(output, delimiter=";")
        writer.writerow(["id", "name", "birthDate"])
        for p in people_no_birthdate:
            writer.writerow([p["id"], p["name"], ""])
        if args.file:
            output.close()

    if args.update:
        input_file = open(args.file, newline="", encoding="utf-8") if args.file else sys.stdin
        reader = csv.reader(input_file, delimiter=";")
        header = next(reader, None)  # skip header
        update_birthdates(IMMICH_URL, API_KEY, reader, args.silent)
        if args.file:
            input_file.close()
