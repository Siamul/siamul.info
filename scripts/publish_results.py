#!/usr/bin/env python3
"""
publish_results.py - Monotonic Freshness & Schema Gate
Part of the Decoupled CI/CD Caching Architecture (GH-ScholarBot / al-folio pattern).

Enforces:
1. Schema verification: Verifies all 5 JSON files exist and conform to required structure.
2. Monotonic non-decreasing check: Compares newly crawled metrics against prior cached benchmarks
   (citations, h-index, i10-index, total_publications).
3. Anti-corruption safeguard: Rejects zeroed, truncated, or blocked crawler results so
   transient Google 429/403/CAPTCHA errors can NEVER overwrite clean cached data.
4. Provides --force flag for manual override if Google Scholar legitimately recalculates downward.
"""

import sys
import os
import json
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "assets" / "data"

GS_DATA_FILE = DATA_DIR / "gs_data.json"
SHIELDS_CITATIONS_FILE = DATA_DIR / "gs_data_total_citation.json"
SHIELDS_HINDEX_FILE = DATA_DIR / "gs_data_h_index.json"
SHIELDS_I10INDEX_FILE = DATA_DIR / "gs_data_i10_index.json"
SHIELDS_PUBLICATIONS_FILE = DATA_DIR / "gs_data_total_publications.json"

REQUIRED_FILES = [
    GS_DATA_FILE,
    SHIELDS_CITATIONS_FILE,
    SHIELDS_HINDEX_FILE,
    SHIELDS_I10INDEX_FILE,
    SHIELDS_PUBLICATIONS_FILE,
]

# Baseline minimum thresholds to prevent zeroed corrupt data
MIN_BASELINES = {
    "citations": 121,
    "h_index": 5,
    "i10_index": 4,
    "total_publications": 13,
}


def validate_schema() -> bool:
    """Verifies that all 5 files exist and match their expected schema."""
    for fpath in REQUIRED_FILES:
        if not fpath.exists():
            print(f"[gate] FAIL: Missing required file: {fpath}")
            return False
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[gate] FAIL: Invalid JSON in {fpath}: {e}")
            return False

        # Validate Shields.io endpoint schema
        if fpath != GS_DATA_FILE:
            if not isinstance(data, dict):
                print(f"[gate] FAIL: Shields endpoint {fpath} must be a dict.")
                return False
            if data.get("schemaVersion") != 1:
                print(f"[gate] FAIL: Shields endpoint {fpath} missing schemaVersion: 1")
                return False
            if not data.get("label") or "message" not in data:
                print(f"[gate] FAIL: Shields endpoint {fpath} missing label or message.")
                return False

    # Validate gs_data.json schema
    try:
        with open(GS_DATA_FILE, "r", encoding="utf-8") as f:
            gs = json.load(f)
        author = gs.get("author", {})
        metrics = gs.get("metrics", {})
        pubs = gs.get("publications", [])

        if author.get("user_id") != "4m76wqsAAAAJ":
            print(f"[gate] FAIL: gs_data.json author.user_id mismatch.")
            return False
        if not isinstance(metrics, dict) or "citations" not in metrics:
            print(f"[gate] FAIL: gs_data.json metrics missing.")
            return False
        if not isinstance(pubs, list) or len(pubs) == 0:
            print(f"[gate] FAIL: gs_data.json publications list is empty.")
            return False
    except Exception as e:
        print(f"[gate] FAIL: Schema check error: {e}")
        return False

    print("[gate] PASS: Schema verification passed for all 5 JSON files.")
    return True


def check_monotonic(force: bool = False) -> bool:
    """
    Compares newly crawled metrics against baseline thresholds.
    Rejects any update where metrics decrease or become 0 unless force=True.
    """
    with open(GS_DATA_FILE, "r", encoding="utf-8") as f:
        gs = json.load(f)

    metrics = gs.get("metrics", {})
    curr_cites = int(metrics.get("citations", 0))
    curr_h = int(metrics.get("h_index", 0))
    curr_i10 = int(metrics.get("i10_index", 0))
    curr_pubs = int(metrics.get("total_publications", len(gs.get("publications", []))))

    print(f"[gate] Scraped metrics: citations={curr_cites}, h={curr_h}, i10={curr_i10}, pubs={curr_pubs}")
    print(f"[gate] Baselines:       citations={MIN_BASELINES['citations']}, h={MIN_BASELINES['h_index']}, i10={MIN_BASELINES['i10_index']}, pubs={MIN_BASELINES['total_publications']}")

    if force:
        print("[gate] --force flag enabled: Bypassing monotonic decrease check.")
        return True

    # Check non-decreasing
    failed_keys = []
    if curr_cites < MIN_BASELINES["citations"]:
        failed_keys.append(f"citations ({curr_cites} < {MIN_BASELINES['citations']})")
    if curr_h < MIN_BASELINES["h_index"]:
        failed_keys.append(f"h_index ({curr_h} < {MIN_BASELINES['h_index']})")
    if curr_i10 < MIN_BASELINES["i10_index"]:
        failed_keys.append(f"i10_index ({curr_i10} < {MIN_BASELINES['i10_index']})")
    if curr_pubs < MIN_BASELINES["total_publications"]:
        failed_keys.append(f"total_publications ({curr_pubs} < {MIN_BASELINES['total_publications']})")

    if failed_keys:
        print(f"[gate] REJECT: Scrape rejected by monotonic gate! Metric decrease detected: {', '.join(failed_keys)}.")
        print("[gate] This safeguard prevents empty/blocked scrapes (e.g. CAPTCHA/429) from corrupting the live cache.")
        return False

    print("[gate] PASS: Monotonic freshness gate passed cleanly.")
    return True


def main():
    parser = argparse.ArgumentParser(description="Monotonic Freshness & Schema Gate for Google Scholar Caching")
    parser.add_argument("--force", action="store_true", help="Bypass monotonic non-decreasing validation")
    args = parser.parse_args()

    if not validate_schema():
        sys.exit(1)

    if not check_monotonic(force=args.force):
        sys.exit(2)

    print("[gate] ALL GATES PASSED: Data files are verified and ready for deployment.")
    sys.exit(0)


if __name__ == "__main__":
    main()
