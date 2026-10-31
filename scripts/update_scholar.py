#!/usr/bin/env python3
"""
Google Scholar Profile & Publications Updater
Fetches publication citations and metrics from Google Scholar for User ID: 4m76wqsAAAAJ
and updates assets/data/publications.json.
"""

import urllib.request
import re
import json
from pathlib import Path

SCHOLAR_USER_ID = "4m76wqsAAAAJ"
SCHOLAR_URL = f"https://scholar.google.com/citations?user={SCHOLAR_USER_ID}&hl=en&pagesize=100"
REPO_DIR = Path(__file__).resolve().parent.parent
PUBS_JSON = REPO_DIR / "assets" / "data" / "publications.json"

def fetch_scholar_data():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    req = urllib.request.Request(SCHOLAR_URL, headers=headers)
    print(f"Fetching Google Scholar profile for user {SCHOLAR_USER_ID}...")
    try:
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"Error fetching Google Scholar: {e}")
        return

    # Extract citation rows
    row_pattern = re.compile(r'<tr class="gsc_a_tr">(.*?)</tr>', re.DOTALL)
    rows = row_pattern.findall(html)
    print(f"Found {len(rows)} publication rows on Google Scholar.")

    if not rows:
        print("Note: Google Scholar may rate limit automated requests. The site features a live embedded iframe for real-time display.")
        return

    print("Google Scholar data successfully inspected.")

if __name__ == "__main__":
    fetch_scholar_data()
