#!/usr/bin/env python3
"""
scholar_crawler.py - Decoupled Google Scholar Profile & Publications Crawler
Part of the Decoupled CI/CD Caching Architecture (GH-ScholarBot / al-folio pattern).

Features:
- Scrapes author profile for Google Scholar ID: 4m76wqsAAAAJ
- Extracts author telemetry: total citations, h-index, i10-index, total publications
- Extracts per-paper citation counts from Google Scholar table
- Merges with curated metadata (abstracts, DOIs, PDFs, BibTeX) in publications.json
- Generates 5 decoupled output files in assets/data/:
  1. gs_data.json (Complete Scholar JSON payload)
  2. gs_data_total_citation.json (Shields.io endpoint)
  3. gs_data_h_index.json (Shields.io endpoint)
  4. gs_data_i10_index.json (Shields.io endpoint)
  5. gs_data_total_publications.json (Shields.io endpoint)
"""

import sys
import os
import re
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

SCHOLAR_USER_ID = "4m76wqsAAAAJ"
SCHOLAR_URL = f"https://scholar.google.com/citations?user={SCHOLAR_USER_ID}&hl=en&pagesize=100"

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_publications_html import classify_patent_status

DATA_DIR = REPO_ROOT / "assets" / "data"
PUBLICATIONS_FILE = DATA_DIR / "publications.json"

GS_DATA_FILE = DATA_DIR / "gs_data.json"
SHIELDS_CITATIONS_FILE = DATA_DIR / "gs_data_total_citation.json"
SHIELDS_HINDEX_FILE = DATA_DIR / "gs_data_h_index.json"
SHIELDS_I10INDEX_FILE = DATA_DIR / "gs_data_i10_index.json"
SHIELDS_PUBLICATIONS_FILE = DATA_DIR / "gs_data_total_publications.json"


def fetch_scholar_html() -> str:
    """Fetches raw HTML from Google Scholar using browser-like request headers."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
    }
    req = urllib.request.Request(SCHOLAR_URL, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[crawler] Warning: Live fetch failed: {e}")
        return ""


def parse_scholar_html(html: str):
    """Parses author metrics and publication rows from Scholar HTML."""
    if not html:
        return None

    # Check for CAPTCHA or blocking
    if "Please show you're not a robot" in html or "recaptcha" in html.lower():
        print("[crawler] Warning: Google Scholar returned CAPTCHA challenge.")
        return None

    # Metrics table: [citations_all, citations_since, h_all, h_since, i10_all, i10_since]
    metrics = re.findall(r'<td class="gsc_rsb_std">(\d+)</td>', html)
    if len(metrics) < 3:
        print("[crawler] Warning: Metrics table not found in HTML.")
        return None

    total_citations = int(metrics[0])
    h_index = int(metrics[2])
    i10_index = int(metrics[4]) if len(metrics) > 4 else 0

    # Parse publication rows
    rows = re.findall(r'<tr class="gsc_a_tr">(.*?)</tr>', html, re.DOTALL)
    scraped_papers = []

    for r in rows:
        title_m = re.search(r'class="gsc_a_at"[^>]*>([^<]+)</a>', r)
        url_m = re.search(r'class="gsc_a_at"\s+href="([^"]+)"', r)
        cites_m = re.search(r'class="gsc_a_ac[^"]*"[^>]*>([^<]*)</a>', r)
        year_m = re.search(r'class="gsc_a_h gsc_a_hc[^"]*"[^>]*>([^<]*)</span>', r)
        gray_divs = re.findall(r'<div class="gs_gray">([^<]*)</div>', r)

        if not title_m:
            continue

        title = title_m.group(1).strip()
        link = "https://scholar.google.com" + url_m.group(1) if url_m else ""
        cites_str = cites_m.group(1).strip() if (cites_m and cites_m.group(1).strip()) else "0"
        try:
            cites = int(cites_str)
        except ValueError:
            cites = 0
        year = year_m.group(1).strip() if (year_m and year_m.group(1).strip()) else ""

        authors = gray_divs[0].strip() if len(gray_divs) > 0 else ""
        venue = gray_divs[1].strip() if len(gray_divs) > 1 else ""

        # Extract citation ID from URL if present
        cid_match = re.search(r'citation_for_view=([^&]+)', link)
        cid = cid_match.group(1) if cid_match else ""

        scraped_papers.append({
            "title": title,
            "citations": cites,
            "year": int(year) if year.isdigit() else None,
            "authors": authors,
            "venue": venue,
            "scholar_url": link,
            "citation_id": cid,
        })

    return {
        "user_id": SCHOLAR_USER_ID,
        "name": "Siamul Karim Khan",
        "total_citations": total_citations,
        "h_index": h_index,
        "i10_index": i10_index,
        "scraped_papers": scraped_papers,
    }


def merge_with_canonical_publications(parsed_data):
    """
    Merges scraped citations into curated publications.json.
    If scraping failed or returned partial results, preserves curated records safely.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    canonical = []
    if PUBLICATIONS_FILE.exists():
        try:
            with open(PUBLICATIONS_FILE, "r", encoding="utf-8") as f:
                canonical = json.load(f)
        except Exception as e:
            print(f"[crawler] Warning: Error reading {PUBLICATIONS_FILE}: {e}")

    # Fallback default values if scrape was blocked
    total_citations = 121
    h_index = 5
    i10_index = 4

    if parsed_data:
        total_citations = max(total_citations, parsed_data.get("total_citations", 0))
        h_index = max(h_index, parsed_data.get("h_index", 0))
        i10_index = max(i10_index, parsed_data.get("i10_index", 0))

        # Update per-paper citations in canonical by matching titles
        scraped_map = {p["title"].lower().strip(): p for p in parsed_data.get("scraped_papers", [])}
        for item in canonical:
            t = item.get("title", "").lower().strip()
            # Match directly or by prefix
            match = None
            if t in scraped_map:
                match = scraped_map[t]
            else:
                for st, sp in scraped_map.items():
                    if t[:30] in st or st[:30] in t:
                        match = sp
                        break
            if match:
                item["citations"] = max(item.get("citations", 0), match["citations"])
                if not item.get("scholar_url") and match.get("scholar_url"):
                    item["scholar_url"] = match["scholar_url"]

    # Classify patents and sort chronologically descending
    for item in canonical:
        if item.get("type") == "patent":
            tag = classify_patent_status(item)
            item["category"] = tag
            item["type_display"] = tag

    canonical.sort(key=lambda p: str(p.get("date", p.get("year", ""))), reverse=True)
    total_publications = len(canonical)

    # Build gs_data.json payload
    timestamp_utc = datetime.now(timezone.utc).isoformat()
    gs_data = {
        "author": {
            "name": "Siamul Karim Khan",
            "user_id": SCHOLAR_USER_ID,
            "affiliation": "Software Engineer at Google | Ph.D. University of Notre Dame",
            "scholar_url": f"https://scholar.google.com/citations?user={SCHOLAR_USER_ID}",
            "updated_at": timestamp_utc,
        },
        "metrics": {
            "citations": total_citations,
            "h_index": h_index,
            "i10_index": i10_index,
            "total_publications": total_publications,
        },
        "publications": canonical,
    }

    # Build Shields.io endpoint payloads
    # Schema: https://shields.io/badges/endpoint-badge
    shields_citations = {
        "schemaVersion": 1,
        "label": "citations",
        "message": str(total_citations),
        "color": "0a4da5",
    }
    shields_hindex = {
        "schemaVersion": 1,
        "label": "h-index",
        "message": str(h_index),
        "color": "1c4f8f",
    }
    shields_i10index = {
        "schemaVersion": 1,
        "label": "i10-index",
        "message": str(i10_index),
        "color": "2e7fca",
    }
    shields_pubs = {
        "schemaVersion": 1,
        "label": "publications",
        "message": str(total_publications),
        "color": "0d9488",
    }

    return gs_data, shields_citations, shields_hindex, shields_i10index, shields_pubs


def save_json_files(gs_data, shields_citations, shields_hindex, shields_i10index, shields_pubs):
    """Writes the 5 standardized decoupled JSON files."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with open(GS_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(gs_data, f, indent=2, ensure_ascii=False)
    print(f"[crawler] Wrote {GS_DATA_FILE}")

    with open(SHIELDS_CITATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(shields_citations, f, indent=2)
    print(f"[crawler] Wrote {SHIELDS_CITATIONS_FILE}")

    with open(SHIELDS_HINDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(shields_hindex, f, indent=2)
    print(f"[crawler] Wrote {SHIELDS_HINDEX_FILE}")

    with open(SHIELDS_I10INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(shields_i10index, f, indent=2)
    print(f"[crawler] Wrote {SHIELDS_I10INDEX_FILE}")

    with open(SHIELDS_PUBLICATIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(shields_pubs, f, indent=2)
    print(f"[crawler] Wrote {SHIELDS_PUBLICATIONS_FILE}")


def main():
    print(f"[crawler] Starting Google Scholar decoupled crawl for {SCHOLAR_USER_ID}...")
    html = fetch_scholar_html()
    parsed = parse_scholar_html(html)
    if parsed:
        print(f"[crawler] Live parse success: {parsed['total_citations']} citations, h={parsed['h_index']}, i10={parsed['i10_index']}, {len(parsed['scraped_papers'])} papers.")
    else:
        print("[crawler] Live parse was not available; using monotonic fallback from curated records.")

    gs_data, s_cite, s_h, s_i10, s_pubs = merge_with_canonical_publications(parsed)
    save_json_files(gs_data, s_cite, s_h, s_i10, s_pubs)
    print("[crawler] Crawl completed successfully.")


if __name__ == "__main__":
    main()
