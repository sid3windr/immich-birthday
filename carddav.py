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

import csv
import requests
import vobject
from xml.etree import ElementTree as ET
import argparse
from urllib.parse import urljoin
import time
from datetime import datetime
import configparser
import os
import sys
import re

NAMESPACES = {'D': 'DAV:', 'C': 'urn:ietf:params:xml:ns:carddav'}


def load_config():
    """Load Immich configuration from immich.ini or environment variables."""
    config = configparser.ConfigParser()
    ini_path = os.path.join(os.path.dirname(__file__), "immich.ini")

    if not os.path.exists(ini_path):
        raise FileNotFoundError(f"Config file not found: {ini_path}")

    config.read(ini_path)

    CARDDAV_URL = config.get("carddav", "url", fallback=os.environ.get("CARDDAV_URL"))
    CARDDAV_USER = config.get("carddav", "username", fallback=os.environ.get("CARDDAV_USER"))
    CARDDAV_PASS = config.get("carddav", "password", fallback=os.environ.get("CARDDAV_PASS"))
    CARDDAV_SLEEP = config.getfloat("carddav", "sleep", fallback=os.environ.get("CARDDAV_SLEEP"))

    return CARDDAV_URL, CARDDAV_USER, CARDDAV_PASS, CARDDAV_SLEEP


def normalize_bday(bday: str) -> str | None:
    """Normalize birthday string to YYYY-MM-DD if in supported formats.
    Supported formats are: YYYY-MM-DD, YYYYMMDD.
    Returns None if unsupported format.
    """
    bday = bday.strip()
    for fmt in ("%Y%m%d", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(bday, fmt)
            if dt.year < 1900:  # Likely "X-APPLE-OMIT-YEAR" 1604 - stored date without year, cannot use
                return None

            return datetime.strptime(bday, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None  # unsupported format


def fetch_birthdates_from_carddav(rows, url, username, password, sleep):
    # CardDAV addressbook URL
    addressbook_url = f"{url}/addressbooks/{username}/contacts/"

    # PROPFIND to list all vCard URLs - get minimal data (just the etag)
    headers = {'Depth': '1', 'Content-Type': 'application/xml'}
    propfind_body = '''<?xml version="1.0" encoding="UTF-8"?>
<D:propfind xmlns:D="DAV:" xmlns:C="urn:ietf:params:xml:ns:carddav">
  <D:prop><D:getetag/></D:prop>
</D:propfind>'''
    resp = requests.request('PROPFIND', addressbook_url, data=propfind_body, auth=(username, password), headers=headers)
    resp.raise_for_status()
    tree = ET.fromstring(resp.text)

    # Extract vCard URLs
    card_urls = []
    for resp_elem in tree.findall('D:response', NAMESPACES):
        href_elem = resp_elem.find('D:href', NAMESPACES)
        if href_elem is not None:
            card_urls.append(href_elem.text)

    # Fetch every vCard and check for matches with our input
    updated_rows = []
    for card_url in card_urls:
        full_card_url = urljoin(url, card_url)  # DAV returns relative URLs (/dav/...)
        card_resp = requests.get(full_card_url, auth=(username, password))
        card_resp.raise_for_status()
        try:
            vcard = vobject.readOne(card_resp.text)
        except Exception:
            continue

        vcard_name = getattr(vcard, 'fn', None)
        vcard_bday = getattr(vcard, 'bday', None)
        found_birthdate = None
        for person_id, name, birthdate in rows:
            name = name.strip()

            vcard_clean_name = vcard_name.value.strip().lower()
            # Clean up nicknames ("William Turner (Bill)" -> "William Turner")
            vcard_clean_name = re.sub(r"\s*\([^)]*\)", "", vcard_clean_name)

            if vcard_name and vcard_clean_name == name.lower() and vcard_bday:
                found_birthdate = normalize_bday(str(vcard_bday.value))
                break

        if found_birthdate:
            updated_rows.append([person_id, name, found_birthdate])

        if sleep > 0:
            time.sleep(sleep)

    return updated_rows


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fill birthdates from CardDAV server")
    parser.add_argument("--input", required=False, help="Input CSV file (defaults to stdin)")
    parser.add_argument("--output", required=False, help="Output CSV file (defaults to stdout)")
    parser.add_argument("--url", required=False, help="CardDAV server URL")
    parser.add_argument("--username", required=False, help="CardDAV username")
    parser.add_argument("--password", required=False, help="CardDAV password")
    parser.add_argument("--sleep", type=float, default=0, help="Seconds to sleep between requests to avoid rate-limiting")
    args = parser.parse_args()

    # Load configuration from INI, with environment variable fallback
    CARDDAV_URL, CARDDAV_USER, CARDDAV_PASS, CARDDAV_SLEEP = load_config()

    # Commandline parameters overrule INI/environment variable configuration
    if args.url:
        CARDDAV_URL = args.url

    if args.username:
        CARDDAV_USER = args.username

    if args.password:
        CARDDAV_PASS = args.password

    if args.sleep:
        CARDDAV_SLEEP = args.sleep

    # Error out if we don't have the critical configuration fields
    if not CARDDAV_USER or not CARDDAV_PASS or not CARDDAV_URL:
        sys.exit("Error: CardDAV URL, username or password not set. Use immich.ini or CARDDAV_URL, CARDDAV_USER and CARDDAV_URL environment variables.")

    # Read input CSV, from specified file name or stdin
    input_file = open(args.input, newline="", encoding="utf-8") if args.input else sys.stdin
    reader = csv.reader(input_file, delimiter=";")
    header = next(reader, None)  # skip header
    rows = [row for row in reader if row and len(row) >= 3]

    # Go CardDAV!
    updated_rows = fetch_birthdates_from_carddav(rows, CARDDAV_URL, CARDDAV_USER, CARDDAV_PASS, CARDDAV_SLEEP)

    # Write output CSV, to specified file name or stdout
    output = open(args.output, "w", newline="", encoding="utf-8") if args.output else sys.stdout
    writer = csv.writer(output, delimiter=";")
    writer.writerow(["id", "name", "birthDate"])
    for row in updated_rows:
        writer.writerow(row)
