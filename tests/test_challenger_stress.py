#!/usr/bin/env python3
"""
test_challenger_stress.py - Empirical Adversarial Stress Testing Suite
Authored by Challenger 1 (critic / specialist) to stress-test:
1. Patent classification regex (grant "B" specifiers vs false positives like "BUET", "Big", etc.)
2. Chronological sorting boundaries (same-year ordering, ISO dates, fallback handling)
3. Monotonic baseline enforcement in publish_results.py (synthetic regressions, boundaries, --force override)
4. Comprehensive regression run of existing suites.
"""

import sys
import os
import re
import json
import shutil
import tempfile
import unittest
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "assets" / "data"
SCRIPTS_DIR = REPO_ROOT / "scripts"


# ==============================================================================
# 1. Patent Classification Regex Stress Testing
# ==============================================================================

class TestPatentClassificationRegexStress(unittest.TestCase):
    """
    Stress-tests the patent classification logic used in:
    - scripts/generate_publications_html.py (line 177)
    - scripts/scholar_crawler.py (line 177)
    """

    def setUp(self):
        # Extract the exact pattern used in the implementation
        # Pattern in scripts: re.search(r'\bB[1-9]?\b', venue_info)
        self.grant_pattern = re.compile(r'\bB[1-9]?\b')

    def test_positive_grant_specifiers(self):
        """Must correctly classify granted patents with varied B specifiers."""
        positive_cases = [
            ("US 11,234,567 B2", "Standard US granted patent with B2"),
            ("US Patent Grant B1", "Explicit Grant phrase with B1"),
            ("US 10000000 B", "Single B specifier without number"),
            ("EP 1234567 B1", "European Patent with B1"),
            ("US 9,876,543 B3", "Higher digit grant specifier B3"),
            ("US 10,000,000 B9", "Maximum single digit grant specifier B9"),
            ("Patent Publication US 11234567 B2", "Full publication prefix with B2"),
            ("WO 2021/123456 B1", "WIPO grant publication with B1"),
        ]
        for venue_str, desc in positive_cases:
            match = bool(self.grant_pattern.search(venue_str))
            self.assertTrue(
                match,
                f"Failed to classify granted patent for '{desc}': '{venue_str}'",
            )

    def test_negative_pending_applications_and_false_positives(self):
        """Must NOT classify pending applications or common words starting with B as granted."""
        negative_cases = [
            ("BUET Thesis", "Institution name BUET"),
            ("Big Data", "Capitalized word Big"),
            ("Robustness", "Word containing b"),
            ("B2B Platform", "B2B abbreviation"),
            ("US 2023/0274582 A1", "Siamul actual pending patent 1"),
            ("US 2024/0334008 A1", "Siamul actual pending patent 2"),
            ("U.S. Patent Application 18/115,414", "Application number string 1"),
            ("U.S. Patent Application 18/625,685", "Application number string 2"),
            ("SUB-1 algorithm analysis", "Sub-part naming"),
            ("TABLE 12 data results", "Table numbering"),
            ("Section A header note", "Section A"),
            ("Preprint arXiv:2401.00001", "arXiv preprint identifier"),
            ("IEEE Transactions on Biometrics", "Journal title with B"),
        ]
        for venue_str, desc in negative_cases:
            match = bool(self.grant_pattern.search(venue_str))
            self.assertFalse(
                match,
                f"False positive triggered for '{desc}': '{venue_str}' (expected False, got {match})",
            )

    def test_actual_curated_patents_in_repository(self):
        """The two real patent entries in publications.json must classify as Pending Patent."""
        with open(DATA_DIR / "publications.json", "r", encoding="utf-8") as f:
            pubs = json.load(f)

        patents = [p for p in pubs if p.get("type") == "patent"]
        self.assertEqual(len(patents), 2, "Expected exactly 2 patent items in publications.json")

        for p in patents:
            venue_info = f"{p.get('venue', '')} {p.get('venue_short', '')} {p.get('id', '')}"
            is_granted = bool(self.grant_pattern.search(venue_info))
            self.assertFalse(
                is_granted,
                f"Patent {p['id']} was falsely classified as granted: '{venue_info}'",
            )
            self.assertEqual(p.get("category"), "Pending Patent")
            self.assertEqual(p.get("type_display"), "Pending Patent")


# ==============================================================================
# 2. Chronological Sorting Boundaries Stress Testing
# ==============================================================================

class TestChronologicalSortingBoundariesStress(unittest.TestCase):
    """
    Stress-tests chronological ordering, boundary resolution, and fallback keys.
    """

    def setUp(self):
        with open(DATA_DIR / "publications.json", "r", encoding="utf-8") as f:
            self.pubs = json.load(f)
        with open(DATA_DIR / "gs_data.json", "r", encoding="utf-8") as f:
            self.gs_pubs = json.load(f).get("publications", [])

    def test_all_13_publications_strictly_descending(self):
        """All 13 publications must strictly descend by date."""
        self.assertEqual(len(self.pubs), 13)
        self.assertEqual(len(self.gs_pubs), 13)

        pub_dates = [p["date"] for p in self.pubs]
        gs_dates = [p["date"] for p in self.gs_pubs]

        self.assertEqual(pub_dates, sorted(pub_dates, reverse=True))
        self.assertEqual(gs_dates, sorted(gs_dates, reverse=True))
        self.assertEqual(pub_dates, gs_dates)

    def test_same_year_boundary_resolution(self):
        """Publications in 2026, 2025, and 2023 must correctly order by month and day."""
        # 2026 cluster: 3 publications
        pubs_2026 = [p for p in self.pubs if p.get("year") == 2026]
        self.assertEqual(len(pubs_2026), 3)
        dates_2026 = [p["date"] for p in pubs_2026]
        self.assertEqual(dates_2026, ["2026-05-01", "2026-03-01", "2026-02-01"])

        # 2025 cluster: 3 publications
        pubs_2025 = [p for p in self.pubs if p.get("year") == 2025]
        self.assertEqual(len(pubs_2025), 3)
        dates_2025 = [p["date"] for p in pubs_2025]
        self.assertEqual(dates_2025, ["2025-11-15", "2025-09-15", "2025-01-01"])

        # 2023 cluster: 2 publications (patent in August vs conference in January)
        pubs_2023 = [p for p in self.pubs if p.get("year") == 2023]
        self.assertEqual(len(pubs_2023), 2)
        dates_2023 = [p["date"] for p in pubs_2023]
        self.assertEqual(dates_2023, ["2023-08-31", "2023-01-05"])

    def test_sorting_key_stability_and_fallback(self):
        """Simulate sorting on mixed dates: full ISO date vs year-only."""
        sort_key = lambda p: str(p.get("date", p.get("year", "")))

        synthetic_data = [
            {"id": "p_2025_year", "year": 2025},
            {"id": "p_2026_may", "year": 2026, "date": "2026-05-01"},
            {"id": "p_2025_dec", "year": 2025, "date": "2025-12-31"},
            {"id": "p_2026_feb", "year": 2026, "date": "2026-02-01"},
            {"id": "p_2024_oct", "year": 2024, "date": "2024-10-03"},
        ]

        sorted_pubs = sorted(synthetic_data, key=sort_key, reverse=True)
        sorted_ids = [p["id"] for p in sorted_pubs]

        # In reverse sort:
        # "2026-05-01" > "2026-02-01" > "2025-12-31" > "2025" > "2024-10-03"
        expected_ids = ["p_2026_may", "p_2026_feb", "p_2025_dec", "p_2025_year", "p_2024_oct"]
        self.assertEqual(sorted_ids, expected_ids)


# ==============================================================================
# 3. Monotonic Freshness Gate Robustness in publish_results.py
# ==============================================================================

class TestMonotonicGateRobustnessStress(unittest.TestCase):
    """
    Stress-tests scripts/publish_results.py under synthetic regressions,
    schema mutations, and --force override.
    """

    def setUp(self):
        # Create an isolated temporary sandbox with copies of assets/data
        self.temp_dir = tempfile.TemporaryDirectory()
        self.sandbox_path = Path(self.temp_dir.name)
        self.sandbox_assets = self.sandbox_path / "assets" / "data"
        self.sandbox_scripts = self.sandbox_path / "scripts"

        shutil.copytree(DATA_DIR, self.sandbox_assets)
        shutil.copytree(SCRIPTS_DIR, self.sandbox_scripts)

    def tearDown(self):
        self.temp_dir.cleanup()

    def _run_publisher(self, extra_args=None):
        cmd = [sys.executable, str(self.sandbox_scripts / "publish_results.py")]
        if extra_args:
            cmd.extend(extra_args)
        return subprocess.run(
            cmd,
            cwd=str(self.sandbox_path),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10,
        )

    def test_clean_state_passes(self):
        """In clean baseline state (13 pubs, 121 cites, h=5, i10=4), publisher must exit 0."""
        res = self._run_publisher()
        self.assertEqual(res.returncode, 0, f"Expected clean pass, got {res.returncode}:\n{res.stdout}\n{res.stderr}")
        self.assertIn("ALL GATES PASSED", res.stdout)

    def test_synthetic_regression_pubs_under_13_rejected(self):
        """If publications drop to 12 (below baseline 13), gate must reject with exit code 2."""
        gs_file = self.sandbox_assets / "gs_data.json"
        with open(gs_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["metrics"]["total_publications"] = 12
        data["publications"] = data["publications"][:12]
        with open(gs_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        res = self._run_publisher()
        self.assertEqual(
            res.returncode,
            2,
            f"Expected rejection with exit code 2 when pubs=12, got {res.returncode}:\n{res.stdout}",
        )
        self.assertIn("REJECT: Scrape rejected by monotonic gate", res.stdout)
        self.assertIn("total_publications (12 < 13)", res.stdout)

    def test_synthetic_regression_citations_rejected(self):
        """If citations drop below 121, gate must reject with exit code 2."""
        gs_file = self.sandbox_assets / "gs_data.json"
        with open(gs_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["metrics"]["citations"] = 100
        with open(gs_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        res = self._run_publisher()
        self.assertEqual(res.returncode, 2)
        self.assertIn("citations (100 < 121)", res.stdout)

    def test_force_flag_bypasses_monotonic_rejection(self):
        """When --force is specified, a regressed crawl must pass."""
        gs_file = self.sandbox_assets / "gs_data.json"
        with open(gs_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["metrics"]["total_publications"] = 12
        data["metrics"]["citations"] = 50
        with open(gs_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        res = self._run_publisher(extra_args=["--force"])
        self.assertEqual(res.returncode, 0, f"Expected --force override to exit 0:\n{res.stdout}")
        self.assertIn("--force flag enabled: Bypassing monotonic decrease check", res.stdout)
        self.assertIn("ALL GATES PASSED", res.stdout)

    def test_monotonic_growth_accepted(self):
        """Metrics higher than baseline (e.g. 14 pubs, 130 cites) must pass cleanly."""
        gs_file = self.sandbox_assets / "gs_data.json"
        with open(gs_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["metrics"]["total_publications"] = 14
        data["metrics"]["citations"] = 130
        data["metrics"]["h_index"] = 6
        data["metrics"]["i10_index"] = 5
        with open(gs_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        res = self._run_publisher()
        self.assertEqual(res.returncode, 0, f"Expected metric growth to pass:\n{res.stdout}")
        self.assertIn("ALL GATES PASSED", res.stdout)

    def test_schema_corruption_fails_gate(self):
        """Missing required file or invalid JSON must exit with code 1."""
        missing_file = self.sandbox_assets / "gs_data_total_publications.json"
        missing_file.unlink()

        res = self._run_publisher()
        self.assertEqual(
            res.returncode,
            1,
            f"Expected schema failure with exit code 1 when file missing, got {res.returncode}:\n{res.stdout}",
        )
        self.assertIn("Missing required file", res.stdout)


# ==============================================================================
# 4. Website Presentation & DOM Rendering Integrity
# ==============================================================================

class TestWebsiteDOMIntegrity(unittest.TestCase):
    """
    Stress-tests the pre-rendered HTML in index.html for exact count,
    badge rendering, pill partitioning, and chronological ordering.
    """

    def setUp(self):
        with open(REPO_ROOT / "index.html", "r", encoding="utf-8") as f:
            self.html = f.read()
        with open(DATA_DIR / "publications.json", "r", encoding="utf-8") as f:
            self.pubs = json.load(f)

    def test_publication_count_telemetry(self):
        """Metric counter #metric-pubs must display 13."""
        m = re.search(r'id="metric-pubs">(\d+)</span>', self.html)
        self.assertIsNotNone(m, "Missing #metric-pubs counter in index.html")
        self.assertEqual(int(m.group(1)), 13)

    def test_filter_pills_partitioning_and_thesis_omission(self):
        """Filter pills must partition 13 items and omit thesis."""
        self.assertNotIn('data-filter="thesis"', self.html)
        self.assertNotIn('data-category="thesis"', self.html)

        pill_matches = re.findall(r'data-filter="([^"]+)".*?<span class="pub-pill-count">(\d+)</span>', self.html, re.DOTALL)
        pills = {k: int(v) for k, v in pill_matches}

        self.assertEqual(pills.get("all"), 13)
        self.assertEqual(pills.get("journal"), 3)
        self.assertEqual(pills.get("conference"), 5)
        self.assertEqual(pills.get("patent"), 2)
        self.assertEqual(pills.get("preprint"), 3)
        self.assertEqual(pills["journal"] + pills["conference"] + pills["patent"] + pills["preprint"], 13)

    def test_patent_badges_rendered(self):
        """Both patent cards must display Pending Patent badge."""
        patent_badges = re.findall(r'<span class="badge badge-patent">(.*?)</span>', self.html)
        self.assertEqual(len(patent_badges), 2)
        self.assertEqual(patent_badges, ["Pending Patent", "Pending Patent"])

    def test_dom_publication_cards_chronological_order(self):
        """All 13 publication cards must appear in strictly descending chronological order."""
        card_matches = re.findall(r'<article class="publication-card"[^>]*>.*?<h4 class="pub-title"><a[^>]*>(.*?)</a></h4>', self.html, re.DOTALL)
        self.assertEqual(len(card_matches), 13)

        title_to_date = {p["title"].strip(): p["date"] for p in self.pubs}
        card_dates = []
        for raw_title in card_matches:
            import html as pyhtml
            clean_title = pyhtml.unescape(raw_title).strip()
            # find matching pub
            matched_date = None
            for p_title, d in title_to_date.items():
                if p_title == clean_title or p_title in clean_title or clean_title in p_title:
                    matched_date = d
                    break
            self.assertIsNotNone(matched_date, f"Could not match card title: {clean_title}")
            card_dates.append(matched_date)

        self.assertEqual(card_dates, sorted(card_dates, reverse=True))

    def test_shields_io_total_publications_endpoint(self):
        """assets/data/gs_data_total_publications.json must match Shields schema with message 13."""
        with open(DATA_DIR / "gs_data_total_publications.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data.get("schemaVersion"), 1)
        self.assertEqual(data.get("label", "").lower(), "publications")
        self.assertEqual(data.get("message"), "13")
        self.assertTrue(bool(data.get("color")), "Missing badge color")


# ==============================================================================
# 5. Existing Suites Regression Verification
# ==============================================================================

class TestExistingSuitesRegression(unittest.TestCase):
    """
    Confirms all production test suites pass 100% without error or regression.
    """

    def test_verify_site_script(self):
        res = subprocess.run(
            [sys.executable, "verify_site.py"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(res.returncode, 0, f"verify_site.py failed:\n{res.stdout}")
        self.assertIn("Passed: 43 | Failed: 0", res.stdout)

    def test_verify_site_self_test(self):
        res = subprocess.run(
            [sys.executable, "verify_site.py", "--self-test"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(res.returncode, 0, f"verify_site.py --self-test failed:\n{res.stdout}")
        self.assertIn("Passed: 9 | Failed: 0", res.stdout)

    def test_e2e_acceptance_suite(self):
        res = subprocess.run(
            [sys.executable, "tests/test_e2e_acceptance.py"],
            cwd=str(REPO_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        self.assertEqual(res.returncode, 0, f"test_e2e_acceptance.py failed:\n{res.stdout}\n{res.stderr}")
        self.assertIn("OK", res.stderr)


if __name__ == "__main__":
    unittest.main()
