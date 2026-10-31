#!/usr/bin/env python3
"""
Comprehensive 4-Tier End-to-End Acceptance Test Suite for Siamul Personal Website
Validating Requirements R1 through R5 from ORIGINAL_REQUEST.md and PROJECT.md:
- R1: Patent Classification and Badge Tagging ("Pending Patent" vs "Patent" grant specifier B)
- R2: Undergraduate Thesis Removal & Total Publication Count Synchronization (13 total)
- R3: Chronological Publication Sorting (strictly descending by date: newest 2026 to oldest 2019)
- R4: Verification Suite & Pipeline Script Synchronization (verify_site.py, publish_results.py)
- R5: GitHub Pages and CI/CD Action Setup Guide (SETUP_GUIDE.md)

Test Tiers:
- Tier 1: Feature Coverage (Core Requirements Acceptance)
- Tier 2: Boundary & Corner Cases
- Tier 3: Cross-Feature Combinations
- Tier 4: Real-World Scenarios (Visitor Browsing, ScholarBot CI/CD, Maintainer Deployment)

Execution:
    python tests/test_e2e_acceptance.py
    python -m unittest tests/test_e2e_acceptance.py
    python -m unittest discover -s tests
"""

import datetime
import html
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

# Root repository path resolution
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.generate_publications_html import classify_patent_status


def get_file_content(relative_path: str) -> str:
    """Reads a text file relative to REPO_ROOT using UTF-8 encoding."""
    target = REPO_ROOT / relative_path
    if not target.exists():
        raise FileNotFoundError(f"Required file not found: {target}")
    return target.read_text(encoding="utf-8")


def load_json_file(relative_path: str):
    """Loads and parses a JSON file relative to REPO_ROOT."""
    content = get_file_content(relative_path)
    return json.loads(content)


class WebsiteDOMParser(HTMLParser):
    """
    Opaque-box HTML structural parser for index.html using Python standard library.
    Extracts publication cards, metric counters, and filter pill elements.
    """

    def __init__(self):
        super().__init__()
        self.metrics = {}
        self.pills = []
        self.cards = []
        self.current_metric_id = None
        self.current_pill = None
        self.current_card = None
        self.in_pill_count = False
        self.in_card_title = False
        self.in_badge = False
        self.current_badge_class = None
        self.in_authors = False
        self.in_venue = False
        self.in_year_badge = False

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        classes = attr_dict.get("class", "").split()
        element_id = attr_dict.get("id", "")

        # Detect citation metric boxes (e.g. #metric-pubs, #metric-citations)
        if element_id.startswith("metric-"):
            self.current_metric_id = element_id

        # Detect publication filter pills
        if tag == "button" and "pub-pill" in classes:
            self.current_pill = {
                "filter": attr_dict.get("data-filter", ""),
                "text": "",
                "count": None,
                "role": attr_dict.get("role", ""),
            }

        if tag == "span" and "pub-pill-count" in classes and self.current_pill is not None:
            self.in_pill_count = True

        # Detect publication cards inside publications list
        if tag == "article" and "publication-card" in classes:
            self.current_card = {
                "category": attr_dict.get("data-category", ""),
                "title": "",
                "title_href": "",
                "year": None,
                "badges": [],
                "badge_patent_text": None,
                "authors": "",
                "venue": "",
            }

        if self.current_card is not None:
            if tag == "span" and "pub-year-badge" in classes:
                self.in_year_badge = True
            elif tag == "span" and "badge" in classes:
                self.in_badge = True
                self.current_badge_class = attr_dict.get("class", "")
            elif tag == "h4" and "pub-title" in classes:
                self.in_card_title = True
            elif tag == "a" and self.in_card_title and "href" in attr_dict:
                self.current_card["title_href"] = attr_dict["href"]
            elif tag == "p" and "pub-authors" in classes:
                self.in_authors = True
            elif tag == "p" and "pub-venue" in classes:
                self.in_venue = True

    def handle_endtag(self, tag):
        if self.current_metric_id and tag == "span":
            self.current_metric_id = None

        if self.current_pill and tag == "button":
            self.pills.append(self.current_pill)
            self.current_pill = None
            self.in_pill_count = False

        if tag == "span" and self.in_pill_count:
            self.in_pill_count = False

        if self.current_card and tag == "article":
            self.cards.append(self.current_card)
            self.current_card = None

        if self.in_card_title and tag == "h4":
            self.in_card_title = False

        if self.in_badge and tag == "span":
            self.in_badge = False
            self.current_badge_class = None

        if self.in_year_badge and tag == "span":
            self.in_year_badge = False

        if self.in_authors and tag == "p":
            self.in_authors = False

        if self.in_venue and tag == "p":
            self.in_venue = False

    def handle_data(self, data):
        text = data.strip()
        if not text:
            return

        if self.current_metric_id:
            self.metrics[self.current_metric_id] = text

        if self.current_pill is not None:
            if self.in_pill_count:
                try:
                    self.current_pill["count"] = int(text)
                except ValueError:
                    self.current_pill["count"] = text
            else:
                if self.current_pill["text"]:
                    self.current_pill["text"] += " " + text
                else:
                    self.current_pill["text"] = text

        if self.current_card is not None:
            if self.in_card_title:
                if self.current_card["title"]:
                    self.current_card["title"] += " " + text
                else:
                    self.current_card["title"] = text
            elif self.in_year_badge:
                try:
                    self.current_card["year"] = int(text)
                except ValueError:
                    self.current_card["year"] = text
            elif self.in_badge:
                self.current_card["badges"].append((self.current_badge_class, text))
                if "badge-patent" in (self.current_badge_class or ""):
                    self.current_card["badge_patent_text"] = text
            elif self.in_authors:
                if self.current_card["authors"]:
                    self.current_card["authors"] += " " + text
                else:
                    self.current_card["authors"] = text
            elif self.in_venue:
                if self.current_card["venue"]:
                    self.current_card["venue"] += " " + text
                else:
                    self.current_card["venue"] = text


# ==============================================================================
# TIER 1: Feature Coverage (Core Requirements Acceptance)
# ==============================================================================

class TestTier1FeatureCoverage(unittest.TestCase):
    """
    Tier 1 tests validate explicit acceptance criteria for Requirements R1 through R5.
    Every test derives its expected outcome directly from ORIGINAL_REQUEST.md.
    """

    def setUp(self):
        self.pub_data = load_json_file("assets/data/publications.json")
        self.gs_data = load_json_file("assets/data/gs_data.json")
        self.html_content = get_file_content("index.html")
        self.dom = WebsiteDOMParser()
        self.dom.feed(self.html_content)

    # --------------------------------------------------------------------------
    # R1: Patent Classification & Badges
    # --------------------------------------------------------------------------

    def test_r1_patent_badges_in_publications_json(self):
        """R1: Pending patent entries in publications.json must display 'Pending Patent'."""
        patents = [p for p in self.pub_data if p.get("type") == "patent"]
        self.assertEqual(len(patents), 2, f"Expected exactly 2 patent entries, found {len(patents)}")

        for patent in patents:
            pid = patent.get("id")
            title = patent.get("title")
            category = patent.get("category")
            type_display = patent.get("type_display")

            # Neither application is granted with a B specifier (both are A1 applications)
            self.assertEqual(
                category,
                "Pending Patent",
                f"Patent '{title}' ({pid}) in publications.json has category '{category}', expected 'Pending Patent'",
            )
            self.assertEqual(
                type_display,
                "Pending Patent",
                f"Patent '{title}' ({pid}) in publications.json has type_display '{type_display}', expected 'Pending Patent'",
            )

    def test_r1_patent_badges_in_gs_data_json(self):
        """R1: Pending patent entries in gs_data.json must display 'Pending Patent'."""
        pubs = self.gs_data.get("publications", [])
        patents = [p for p in pubs if p.get("type") == "patent"]
        self.assertEqual(len(patents), 2, f"Expected exactly 2 patent entries in gs_data.json, found {len(patents)}")

        for patent in patents:
            pid = patent.get("id")
            title = patent.get("title")
            self.assertEqual(
                patent.get("category"),
                "Pending Patent",
                f"Patent '{title}' ({pid}) in gs_data.json has category '{patent.get('category')}', expected 'Pending Patent'",
            )
            self.assertEqual(
                patent.get("type_display"),
                "Pending Patent",
                f"Patent '{title}' ({pid}) in gs_data.json has type_display '{patent.get('type_display')}', expected 'Pending Patent'",
            )

    def test_r1_patent_badges_rendered_in_index_html(self):
        """R1: Rendered patent cards in index.html must display badge 'Pending Patent' and NOT 'Patent'."""
        patent_cards = [c for c in self.dom.cards if c["category"] == "patent"]
        self.assertEqual(len(patent_cards), 2, f"Expected 2 patent cards in index.html, found {len(patent_cards)}")

        for card in patent_cards:
            title = card["title"]
            badge_text = card["badge_patent_text"]
            self.assertIsNotNone(badge_text, f"Patent card '{title}' is missing a badge-patent element")
            self.assertEqual(
                badge_text,
                "Pending Patent",
                f"Patent card '{title}' has badge text '{badge_text}', expected 'Pending Patent'",
            )

    def test_r1_patent_filter_pill_in_index_html(self):
        """R1: Single filter pill 'Patent' filters both pending and granted patents; count must be 2."""
        patent_pills = [p for p in self.dom.pills if p["filter"] == "patent"]
        self.assertEqual(len(patent_pills), 1, f"Expected exactly 1 patent filter pill, found {len(patent_pills)}")

        pill = patent_pills[0]
        self.assertTrue(
            pill["text"].startswith("Patent"),
            f"Patent pill label should start with 'Patent', found '{pill['text']}'",
        )
        self.assertEqual(pill["count"], 2, f"Patent pill count should be 2, found {pill['count']}")

        # Ensure no separate 'pending-patent' pill exists
        pending_pills = [p for p in self.dom.pills if "pending" in p["filter"].lower()]
        self.assertEqual(len(pending_pills), 0, f"Found prohibited pending filter pills: {pending_pills}")

    def test_r1_grant_specifier_b_classification_logic(self):
        """R1: Logic assigns 'Patent' if grant specifier 'B' is present, 'Pending Patent' if not."""
        test_cases = [
            ("U.S. Patent Application 18/115,414 (Publication No. US 2023/0274582 A1)", "Pending Patent"),
            ("U.S. Patent Application 18/625,685 (Publication No. US 2024/0334008 A1)", "Pending Patent"),
            ("U.S. Patent 11,234,567 B2", "Patent"),
            ("U.S. Patent Grant US 10500123 B1", "Patent"),
            ("Publication No. US 2022/0123456 A2", "Pending Patent"),
            ("US Patent 9,876,543 B2", "Patent"),
        ]

        for venue, expected in test_cases:
            assigned = classify_patent_status(venue)
            self.assertEqual(
                assigned,
                expected,
                f"Classification failed for venue '{venue}': assigned '{assigned}', expected '{expected}'",
            )

    # --------------------------------------------------------------------------
    # R2: Undergraduate Thesis Removal & Total Publication Count
    # --------------------------------------------------------------------------

    def test_r2_thesis_removed_from_publications_json(self):
        """R2: 'Pragmatic PPCA' thesis must be absent from publications.json."""
        for pub in self.pub_data:
            self.assertNotEqual(
                pub.get("id"),
                "pragmatic-ppca-2017",
                "Found prohibited undergraduate thesis ID 'pragmatic-ppca-2017' in publications.json",
            )
            self.assertNotIn(
                "Pragmatic PPCA",
                pub.get("title", ""),
                f"Found prohibited thesis title in publications.json: {pub.get('title')}",
            )

    def test_r2_thesis_removed_from_gs_data_json(self):
        """R2: 'Pragmatic PPCA' thesis must be absent from gs_data.json."""
        pubs = self.gs_data.get("publications", [])
        for pub in pubs:
            self.assertNotEqual(
                pub.get("id"),
                "pragmatic-ppca-2017",
                "Found prohibited undergraduate thesis ID 'pragmatic-ppca-2017' in gs_data.json",
            )
            self.assertNotIn(
                "Pragmatic PPCA",
                pub.get("title", ""),
                f"Found prohibited thesis title in gs_data.json: {pub.get('title')}",
            )

    def test_r2_thesis_removed_from_index_html_publications_list(self):
        """R2: 'Pragmatic PPCA' publication card and thesis category must be absent from publications list."""
        for card in self.dom.cards:
            self.assertNotEqual(
                card["category"],
                "thesis",
                f"Found publication card with prohibited category 'thesis': {card['title']}",
            )
            self.assertNotIn(
                "Pragmatic PPCA",
                card["title"],
                f"Found prohibited thesis title in publication card: {card['title']}",
            )

    def test_r2_thesis_filter_pill_removed_from_index_html(self):
        """R2: 'Thesis' filter pill button must be completely removed from index.html."""
        thesis_pills = [p for p in self.dom.pills if p["filter"] == "thesis" or "thesis" in p["text"].lower()]
        self.assertEqual(len(thesis_pills), 0, f"Prohibited thesis filter pill found: {thesis_pills}")

    def test_r2_total_publication_count_exactly_13(self):
        """R2: Total publication count must be exactly 13 across all data artifacts, UI metrics, and scripts."""
        # 1. publications.json list length
        self.assertEqual(len(self.pub_data), 13, f"publications.json expected 13 entries, found {len(self.pub_data)}")

        # 2. gs_data.json publications array
        gs_pubs = self.gs_data.get("publications", [])
        self.assertEqual(len(gs_pubs), 13, f"gs_data.json expected 13 entries, found {len(gs_pubs)}")

        # 3. gs_data.json metrics object
        metrics = self.gs_data.get("metrics", {})
        self.assertEqual(
            metrics.get("total_publications"),
            13,
            f"gs_data.json metrics.total_publications expected 13, found {metrics.get('total_publications')}",
        )

        # 4. Shields.io badge endpoint (gs_data_total_publications.json)
        shields_data = load_json_file("assets/data/gs_data_total_publications.json")
        self.assertEqual(
            shields_data.get("message"),
            "13",
            f"gs_data_total_publications.json message expected '13', found '{shields_data.get('message')}'",
        )

        # 5. UI Metric Counter #metric-pubs
        metric_pubs = self.dom.metrics.get("metric-pubs")
        self.assertEqual(metric_pubs, "13", f"index.html #metric-pubs expected '13', found '{metric_pubs}'")

        # 6. 'All' Filter Pill count
        all_pills = [p for p in self.dom.pills if p["filter"] == "all"]
        self.assertTrue(len(all_pills) == 1, "Expected exactly 1 'All' filter pill")
        self.assertEqual(all_pills[0]["count"], 13, f"'All' filter pill count expected 13, found {all_pills[0]['count']}")

        # 7. Total rendered publication cards
        self.assertEqual(len(self.dom.cards), 13, f"index.html expected 13 publication cards, found {len(self.dom.cards)}")

        # 8. publish_results.py monotonic baseline
        publish_script = get_file_content("scripts/publish_results.py")
        self.assertRegex(
            publish_script,
            r'["\']total_publications["\']\s*:\s*13\b',
            "scripts/publish_results.py MIN_BASELINES['total_publications'] must be set to 13",
        )

    # --------------------------------------------------------------------------
    # R3: Chronological Sorting
    # --------------------------------------------------------------------------

    def test_r3_publications_json_chronologically_sorted(self):
        """R3: publications.json must be strictly ordered by date descending (newest first)."""
        dates = [p.get("date") for p in self.pub_data]
        self.assertTrue(all(dates), "All entries in publications.json must have non-empty date")

        sorted_dates = sorted(dates, reverse=True)
        self.assertEqual(
            dates,
            sorted_dates,
            f"publications.json is not chronologically sorted descending.\nFound order: {dates}\nExpected order: {sorted_dates}",
        )
        self.assertEqual(dates[0], "2026-05-01", f"First publication date should be '2026-05-01', found '{dates[0]}'")
        self.assertEqual(dates[-1], "2019-11-28", f"Last publication date should be '2019-11-28', found '{dates[-1]}'")

    def test_r3_gs_data_json_chronologically_sorted(self):
        """R3: gs_data.json must be strictly ordered by date descending (newest first)."""
        pubs = self.gs_data.get("publications", [])
        dates = [p.get("date") for p in pubs]
        sorted_dates = sorted(dates, reverse=True)
        self.assertEqual(
            dates,
            sorted_dates,
            f"gs_data.json is not chronologically sorted descending.\nFound: {dates}\nExpected: {sorted_dates}",
        )

    def test_r3_index_html_cards_chronologically_sorted(self):
        """R3: Pre-rendered publication cards in index.html must be strictly ordered chronologically descending."""
        # Create a mapping of publication titles to dates from publications.json
        title_to_date = {}
        for p in self.pub_data:
            # Normalize title for matching
            norm_title = re.sub(r"\s+", " ", p.get("title", "")).strip().lower()
            title_to_date[norm_title] = p.get("date")

        card_dates = []
        for card in self.dom.cards:
            norm_card_title = re.sub(r"\s+", " ", card["title"]).strip().lower()
            # Match by normalized substring if exact match not found
            matched_date = None
            if norm_card_title in title_to_date:
                matched_date = title_to_date[norm_card_title]
            else:
                for t, d in title_to_date.items():
                    if t in norm_card_title or norm_card_title in t:
                        matched_date = d
                        break

            self.assertIsNotNone(
                matched_date,
                f"Could not map card title '{card['title']}' to a known publication date in publications.json",
            )
            card_dates.append(matched_date)

        sorted_card_dates = sorted(card_dates, reverse=True)
        self.assertEqual(
            card_dates,
            sorted_card_dates,
            f"Publication cards in index.html are not in chronological descending order.\nFound: {card_dates}\nExpected: {sorted_card_dates}",
        )

    # --------------------------------------------------------------------------
    # R4: Verification Suite & Pipeline Consistency
    # --------------------------------------------------------------------------

    def test_r4_verify_site_script_passes(self):
        """R4: python verify_site.py must pass with 0 errors (100% pass rate)."""
        proc = subprocess.run(
            [sys.executable, "verify_site.py"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"verify_site.py failed with exit code {proc.returncode}.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )
        self.assertIn("Failed: 0", proc.stdout)
        self.assertIn("VERIFICATION SUMMARY: PASSED", proc.stdout)

    def test_r4_verify_site_self_test_passes(self):
        """R4: python verify_site.py --self-test must pass with 0 errors (100% pass rate)."""
        proc = subprocess.run(
            [sys.executable, "verify_site.py", "--self-test"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"verify_site.py --self-test failed with exit code {proc.returncode}.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )
        self.assertIn("Failed: 0", proc.stdout)
        self.assertIn("VERIFICATION SUMMARY: PASSED", proc.stdout)

    def test_r4_pipeline_publish_results_runs_cleanly(self):
        """R4: python scripts/publish_results.py must pass schema & monotonic gates without error."""
        proc = subprocess.run(
            [sys.executable, "scripts/publish_results.py"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"publish_results.py failed with exit code {proc.returncode}.\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}",
        )
        self.assertIn("ALL GATES PASSED", proc.stdout)

    # --------------------------------------------------------------------------
    # R5: Deployment & CI/CD Documentation
    # --------------------------------------------------------------------------

    def test_r5_setup_guide_exists_and_covers_github_pages(self):
        """R5: SETUP_GUIDE.md must exist and cover GitHub Pages custom domain www.siamul.info."""
        guide = get_file_content("SETUP_GUIDE.md")
        self.assertGreater(len(guide), 1000, "SETUP_GUIDE.md is too short or empty")
        self.assertIn("www.siamul.info", guide, "SETUP_GUIDE.md must document custom domain 'www.siamul.info'")
        self.assertIn("GitHub Pages", guide, "SETUP_GUIDE.md must document GitHub Pages deployment")

    def test_r5_setup_guide_covers_dns_records(self):
        """R5: SETUP_GUIDE.md must specify all 4 Anycast A records and CNAME for www."""
        guide = get_file_content("SETUP_GUIDE.md")
        expected_ips = [
            "185.199.108.153",
            "185.199.109.153",
            "185.199.110.153",
            "185.199.111.153",
        ]
        for ip in expected_ips:
            self.assertIn(ip, guide, f"SETUP_GUIDE.md must document Anycast IP {ip}")

        self.assertIn("CNAME", guide, "SETUP_GUIDE.md must document CNAME record")
        self.assertRegex(guide, r"github\.io", "SETUP_GUIDE.md must document CNAME target pointing to github.io")

    def test_r5_setup_guide_covers_https_enforcement(self):
        """R5: SETUP_GUIDE.md must document HTTPS enforcement."""
        guide = get_file_content("SETUP_GUIDE.md")
        self.assertIn("Enforce HTTPS", guide, "SETUP_GUIDE.md must document 'Enforce HTTPS'")

    def test_r5_setup_guide_covers_github_actions_write_permissions(self):
        """R5: SETUP_GUIDE.md must document GitHub Actions write permissions and GITHUB_TOKEN."""
        guide = get_file_content("SETUP_GUIDE.md")
        has_write_perm = (
            "Read and write permissions" in guide
            or "contents: write" in guide
            or "write permissions" in guide.lower()
        )
        self.assertTrue(has_write_perm, "SETUP_GUIDE.md must document repository workflow write permissions")
        self.assertIn("GITHUB_TOKEN", guide, "SETUP_GUIDE.md must mention GITHUB_TOKEN write access")


# ==============================================================================
# TIER 2: Boundary & Corner Cases
# ==============================================================================

class TestTier2BoundaryAndCorner(unittest.TestCase):
    """
    Tier 2 tests evaluate edge conditions, regex boundary fidelity, date boundaries,
    special characters, and zero/empty states.
    """

    def setUp(self):
        self.pub_data = load_json_file("assets/data/publications.json")
        self.html_content = get_file_content("index.html")
        self.dom = WebsiteDOMParser()
        self.dom.feed(self.html_content)

    def test_t2_patent_grant_specifier_regex_variations(self):
        """T2: Patent classifier must handle varied formats and reject false positives."""
        # Granted variations
        granted_samples = [
            "US 11,234,567 B2",
            "US 10987654 B1",
            "US Patent 9,123,456 B2",
            "European Patent EP 1234567 B1",
            "Grant specifier B2",
        ]
        for sample in granted_samples:
            self.assertEqual(
                classify_patent_status(sample),
                "Patent",
                f"Classifier failed to identify granted patent pattern in: '{sample}'",
            )

        # Pending variations & False Positive traps
        pending_and_traps = [
            "US 2023/0274582 A1",
            "Application 18/115,414",
            "US 2024/0334008 A1",
            "Application 18/625,685",
            "SUB-1 algorithm analysis",
            "TABLE 12 data results",
            "BIO-B protein database",
            "Section B header note",
        ]
        for sample in pending_and_traps:
            self.assertEqual(
                classify_patent_status(sample),
                "Pending Patent",
                f"Classifier falsely identified granted patent pattern in pending or false-positive trap: '{sample}'",
            )

    def test_t2_iso8601_date_formats_and_strict_descending_boundaries(self):
        """T2: Dates must strictly conform to ISO 8601 (YYYY-MM-DD) and resolve same-year boundaries."""
        date_pattern = re.compile(r"^\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])$")

        dates = []
        for pub in self.pub_data:
            d = pub.get("date")
            self.assertIsNotNone(d, f"Missing date in pub: {pub.get('title')}")
            self.assertRegex(d, date_pattern, f"Date '{d}' does not match strict ISO 8601 YYYY-MM-DD")

            # Validate year matches first 4 characters
            self.assertEqual(int(d[:4]), pub.get("year"), f"Year field does not match date prefix in {pub.get('id')}")
            dates.append(d)

        # Boundary test: within 2026, verify month-level ordering (May > March > February)
        dates_2026 = [d for d in dates if d.startswith("2026")]
        self.assertEqual(dates_2026, ["2026-05-01", "2026-03-01", "2026-02-01"])

        # Boundary test: within 2025, verify month-level ordering (Nov > Sept > Jan)
        dates_2025 = [d for d in dates if d.startswith("2025")]
        self.assertEqual(dates_2025, ["2025-11-15", "2025-09-15", "2025-01-01"])

        # Boundary test: within 2023, verify month-level ordering (Aug > Jan)
        dates_2023 = [d for d in dates if d.startswith("2023")]
        self.assertEqual(dates_2023, ["2023-08-31", "2023-01-05"])

    def test_t2_filter_pill_counts_exact_partitioning(self):
        """T2: The sum of category filter pills must equal the total count (13)."""
        category_counts = {}
        for pill in self.dom.pills:
            category_counts[pill["filter"]] = pill["count"]

        # Expected category breakdown:
        # journal: 3, conference: 5, patent: 2, preprint: 3 -> sum = 13
        subtotal = (
            category_counts.get("journal", 0)
            + category_counts.get("conference", 0)
            + category_counts.get("patent", 0)
            + category_counts.get("preprint", 0)
        )
        self.assertEqual(subtotal, 13, f"Sum of category pill counts ({subtotal}) does not equal 13")
        self.assertEqual(category_counts.get("all"), 13, f"'All' pill count ({category_counts.get('all')}) != 13")
        self.assertNotIn("thesis", category_counts, "Thesis category count must not exist in filter pills")

    def test_t2_unicode_entity_encoding_integrity(self):
        """T2: Titles and abstracts must maintain clean UTF-8 encoding with no double-escaped entities."""
        raw_html = self.html_content

        # Double-escaped entity checks
        self.assertNotIn("&amp;amp;", raw_html, "Found double-escaped &amp;amp; in index.html")
        self.assertNotIn("&amp;quot;", raw_html, "Found double-escaped &amp;quot; in index.html")
        self.assertNotIn("&amp;lt;", raw_html, "Found double-escaped &amp;lt; in index.html")

        # Mojibake checks
        mojibake_signatures = ["Ã¢", "Ã©", "Ã", "â\x80\x93", "â\x80\x94"]
        for sig in mojibake_signatures:
            self.assertNotIn(sig, raw_html, f"Found possible UTF-8 mojibake pattern '{sig}' in index.html")

    def test_t2_deployment_artifact_boundaries(self):
        """T2: Deployment artifacts CNAME, .nojekyll, and 404.html must satisfy boundary constraints."""
        cname_path = REPO_ROOT / "CNAME"
        self.assertTrue(cname_path.exists(), "CNAME file must exist")
        cname_bytes = cname_path.read_bytes()
        self.assertEqual(
            cname_bytes,
            b"www.siamul.info\n",
            f"CNAME must be byte-exact b'www.siamul.info\\n' (16 bytes), found {cname_bytes!r}",
        )

        nojekyll_path = REPO_ROOT / ".nojekyll"
        self.assertTrue(nojekyll_path.exists(), ".nojekyll file must exist")
        self.assertEqual(nojekyll_path.stat().st_size, 0, ".nojekyll must be an empty file (0 bytes)")

        error404_path = REPO_ROOT / "404.html"
        self.assertTrue(error404_path.exists(), "404.html must exist")
        content_404 = error404_path.read_text(encoding="utf-8")
        self.assertIn("<!DOCTYPE html>", content_404, "404.html must have HTML5 DOCTYPE")
        self.assertRegex(content_404, r'href=["\'](?:/|index\.html)["\']', "404.html must provide return link to root")


# ==============================================================================
# TIER 3: Cross-Feature Combinations
# ==============================================================================

class TestTier3CrossFeatureCombinations(unittest.TestCase):
    """
    Tier 3 tests evaluate inter-module consistency, pipeline reproducibility,
    and cross-artifact data alignment between JSON stores, generator scripts, and DOM.
    """

    def setUp(self):
        self.pub_data = load_json_file("assets/data/publications.json")
        self.gs_data = load_json_file("assets/data/gs_data.json")
        self.html_content = get_file_content("index.html")
        self.dom = WebsiteDOMParser()
        self.dom.feed(self.html_content)

    def test_t3_all_cards_map_to_valid_filter_pills(self):
        """T3: Every publication card must map to an active filter pill and match pill counts."""
        pill_filters = {p["filter"]: p["count"] for p in self.dom.pills}

        cards_by_cat = {}
        for card in self.dom.cards:
            cat = card["category"]
            self.assertIn(
                cat,
                pill_filters,
                f"Card '{card['title']}' has category '{cat}' which does not match any filter pill",
            )
            cards_by_cat[cat] = cards_by_cat.get(cat, 0) + 1

        for cat, count in cards_by_cat.items():
            pill_count = pill_filters.get(cat)
            self.assertEqual(
                count,
                pill_count,
                f"Category '{cat}' has {count} cards in DOM, but pill count displays {pill_count}",
            )

    def test_t3_cross_artifact_publication_count_and_id_alignment(self):
        """T3: Exact publication IDs and sequence must agree across publications.json and gs_data.json."""
        pubs_ids = [p["id"] for p in self.pub_data]
        gs_ids = [p["id"] for p in self.gs_data.get("publications", [])]

        self.assertEqual(len(pubs_ids), 13, f"Expected 13 IDs in publications.json, found {len(pubs_ids)}")
        self.assertEqual(len(gs_ids), 13, f"Expected 13 IDs in gs_data.json, found {len(gs_ids)}")
        self.assertEqual(
            pubs_ids,
            gs_ids,
            "ID sequence mismatch between publications.json and gs_data.json",
        )

    def test_t3_html_generator_reproducibility(self):
        """T3: Executing scripts/generate_publications_html.py must generate 13 cards with Pending Patent badges."""
        proc = subprocess.run(
            [sys.executable, "scripts/generate_publications_html.py"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15,
        )
        self.assertEqual(
            proc.returncode,
            0,
            f"generate_publications_html.py failed: {proc.stderr}",
        )
        self.assertIn("Generated", proc.stdout)

        # Direct invocation to inspect generated HTML content
        if str(REPO_ROOT) not in sys.path:
            sys.path.insert(0, str(REPO_ROOT))
        from scripts.generate_publications_html import build_publications_html
        generated_html = build_publications_html(REPO_ROOT)

        self.assertIn("Pending Patent", generated_html, "Generated HTML must include 'Pending Patent' badge")
        self.assertNotIn('data-category="thesis"', generated_html, "Generated HTML must not include thesis category")

        card_matches = re.findall(r'<article class="publication-card"', generated_html)
        self.assertEqual(
            len(card_matches),
            13,
            f"generate_publications_html.py generated {len(card_matches)} cards, expected 13",
        )

    def test_t3_shields_io_monotonic_compatibility(self):
        """T3: Shields.io endpoint file schema and metric value must pass monotonic check."""
        shields_data = load_json_file("assets/data/gs_data_total_publications.json")
        self.assertEqual(shields_data.get("schemaVersion"), 1)
        self.assertEqual(shields_data.get("label", "").lower(), "publications")
        self.assertEqual(shields_data.get("message"), "13")


# ==============================================================================
# TIER 4: Real-World Scenarios
# ==============================================================================

class TestTier4RealWorldScenarios(unittest.TestCase):
    """
    Tier 4 tests simulate end-to-end user journeys:
    1. Recruiter / academic visitor exploring Siamul's portfolio.
    2. Weekly Google ScholarBot GitHub Action run.
    3. Maintainer deploying the repository to GitHub Pages according to SETUP_GUIDE.md.
    """

    def setUp(self):
        self.html_content = get_file_content("index.html")
        self.dom = WebsiteDOMParser()
        self.dom.feed(self.html_content)

    def test_t4_visitor_browsing_simulation(self):
        """T4: Simulate an academic visitor checking metrics, patents, and recent publications."""
        # Step 1: Visitor reads the publication metrics banner
        total_pubs = self.dom.metrics.get("metric-pubs")
        self.assertEqual(total_pubs, "13", "Visitor should observe 13 total publications")

        # Step 2: Visitor inspects patent applications to ensure they are properly labeled as pending
        patent_cards = [c for c in self.dom.cards if c["category"] == "patent"]
        self.assertEqual(len(patent_cards), 2, "Visitor should find 2 patent entries")
        for card in patent_cards:
            self.assertEqual(
                card["badge_patent_text"],
                "Pending Patent",
                f"Visitor expects patent '{card['title']}' to be labeled 'Pending Patent', not 'Patent'",
            )

        # Step 3: Visitor views the topmost publication; should see latest 2026 work
        first_card = self.dom.cards[0]
        self.assertEqual(first_card["year"], 2026, f"Top publication should be from 2026, found {first_card['year']}")

        # Step 4: Visitor searches for undergraduate thesis; should find zero results
        thesis_matches = [c for c in self.dom.cards if "ppca" in c["title"].lower()]
        self.assertEqual(len(thesis_matches), 0, "Visitor searching for thesis should find 0 results in publications")

    def test_t4_cicd_scholarbot_workflow_simulation(self):
        """T4: Simulate ScholarBot automated weekly workflow validation."""
        workflow_content = get_file_content(".github/workflows/update_scholar.yml")

        # Workflow permissions check
        self.assertRegex(
            workflow_content,
            r"permissions:\s*\n\s*contents:\s*write",
            "CI/CD workflow must declare 'permissions: contents: write'",
        )

        # Cron schedule check
        self.assertIn("cron: '42 2 * * 0'", workflow_content, "CI/CD cron schedule must be '42 2 * * 0'")

        # Commit loop prevention check
        self.assertIn("[skip ci]", workflow_content, "CI/CD commit message must contain [skip ci]")

    def test_t4_maintainer_deployment_readiness(self):
        """T4: Simulate a maintainer executing the setup guide step-by-step."""
        guide = get_file_content("SETUP_GUIDE.md")

        # Step 1: Git initialization commands present
        self.assertIn("git branch -M main", guide)
        self.assertIn("git push -u origin main", guide)

        # Step 2: GitHub Pages configuration present
        self.assertIn("Deploy from a branch", guide)
        self.assertIn("/ (root)", guide)

        # Step 3: DNS verification commands present
        self.assertIn("185.199.108.153", guide)
        self.assertIn("www.siamul.info", guide)

        # Step 4: GitHub Actions repository setting present
        self.assertIn("Workflow permissions", guide)


# ==============================================================================
# Runner Execution
# ==============================================================================

if __name__ == "__main__":
    unittest.main(verbosity=2)
