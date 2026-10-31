"""
==============================================================================
Empirical Adversarial Stress-Testing Suite: Challenger 2
==============================================================================
Domain Focus:
1. UI DOM & Client-side Filter / Search Behavior (clicking 'Patent' pill,
   searching 'Pending Patent', 'Deception', 'Liveness', 'PPCA', empty state).
2. Complete Elimination of BUET Undergraduate Thesis from Publications & Controls.
3. SETUP_GUIDE.md Documentation Accuracy, DNS IP Correctness, and Workflow Syntax.

Zero external dependencies - standard library Python 3 only.
==============================================================================
"""

import html
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
import subprocess
import unittest

REPO_ROOT = Path(r"c:\Antigravity\siamul_personal_website")


class HTMLCard(dict):
    """Container for parsed publication card data."""
    pass


class IndexDOMParser(HTMLParser):
    """Extracts publication cards, filter pills, and controls from index.html."""

    def __init__(self):
        super().__init__()
        self.pills = []
        self.cards = []
        self.current_pill = None
        self.current_card = None
        self.current_badge = None
        self.in_card = False
        self.in_pill = False
        self.in_pill_count = False
        self.in_title = False
        self.in_badge = False
        self.in_empty_state = False
        self.empty_state_text = ""
        self.depth = 0

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        classes = attr_dict.get("class", "").split()

        if tag == "button" and "pub-pill" in classes:
            self.in_pill = True
            self.current_pill = {
                "filter": attr_dict.get("data-filter", ""),
                "active": "active" in classes,
                "text": "",
                "count": None,
            }
        elif self.in_pill and tag == "span" and "pub-pill-count" in classes:
            self.in_pill_count = True

        if tag == "article" and "publication-card" in classes:
            self.in_card = True
            self.depth = 1
            self.current_card = HTMLCard({
                "category": attr_dict.get("data-category", ""),
                "title": "",
                "badges": [],
                "text_content": "",
                "actions": [],
            })
        elif self.in_card:
            self.depth += 1
            if tag == "span" and any("badge" in c for c in classes):
                self.in_badge = True
                self.current_badge = {"class": attr_dict.get("class", ""), "text": ""}
            elif tag in ("h3", "h4") and "pub-title" in classes:
                self.in_title = True

        if attr_dict.get("id") == "pub-empty-state":
            self.in_empty_state = True

    def handle_endtag(self, tag):
        if self.in_pill:
            if self.in_pill_count and tag == "span":
                self.in_pill_count = False
            elif tag == "button":
                self.in_pill = False
                self.pills.append(self.current_pill)
                self.current_pill = None

        if self.in_card:
            if self.in_badge and tag == "span":
                self.in_badge = False
                if self.current_badge:
                    self.current_card["badges"].append(self.current_badge)
                    self.current_badge = None
            elif self.in_title and tag in ("h3", "h4"):
                self.in_title = False

            self.depth -= 1
            if self.depth == 0:
                self.in_card = False
                self.cards.append(self.current_card)
                self.current_card = None

        if self.in_empty_state and tag == "div":
            self.in_empty_state = False

    def handle_data(self, data):
        clean = data.strip()
        if self.in_pill:
            self.current_pill["text"] += data
            if self.in_pill_count and clean.isdigit():
                self.current_pill["count"] = int(clean)

        if self.in_card:
            self.current_card["text_content"] += " " + data
            if self.in_title and clean:
                self.current_card["title"] += (" " + clean if self.current_card["title"] else clean)
            if self.in_badge and clean:
                self.current_badge["text"] += (" " + clean if self.current_badge["text"] else clean)

        if self.in_empty_state and clean:
            self.empty_state_text += " " + clean


class SimulatedDOMFilter:
    """
    Simulates the exact JavaScript filtering engine in js/main.js lines 461-511:
    function applyFilters() {
      var visibleCount = 0;
      var queryLower = currentQuery.trim().toLowerCase();
      pubCards.forEach(function (card) {
        var cardCategory = (card.getAttribute("data-category") || "").toLowerCase();
        var cardContent = (card.textContent || "").toLowerCase();
        var matchesCategory = currentCategory === "all" || cardCategory === currentCategory;
        var matchesQuery = !queryLower || cardContent.indexOf(queryLower) !== -1;
        if (matchesCategory && matchesQuery) { ... }
      });
      if (emptyState) {
        emptyState.style.display = visibleCount === 0 ? "block" : "none";
      }
    }
    """

    def __init__(self, cards):
        self.cards = cards
        self.current_category = "all"
        self.current_query = ""

    def select_category(self, cat_filter):
        self.current_category = (cat_filter or "all").lower()

    def set_query(self, query):
        self.current_query = query

    def execute(self):
        visible = []
        hidden = []
        query_lower = self.current_query.strip().lower()

        for card in self.cards:
            card_cat = (card.get("category", "")).lower()
            card_content = (card.get("text_content", "")).lower()

            matches_cat = self.current_category == "all" or card_cat == self.current_category
            matches_query = (not query_lower) or (query_lower in card_content)

            if matches_cat and matches_query:
                visible.append(card)
            else:
                hidden.append(card)

        empty_state_displayed = (len(visible) == 0)
        return {
            "visible": visible,
            "hidden": hidden,
            "visible_count": len(visible),
            "empty_state": "block" if empty_state_displayed else "none",
        }


# ==============================================================================
# TEST SUITE 1: UI DOM & Client-Side Search/Filter Adversarial Testing
# ==============================================================================
class TestUIDOMAndFilterAdversarial(unittest.TestCase):
    """Empirical tests for UI DOM structure, category pills, and search engine."""

    @classmethod
    def setUpClass(cls):
        index_path = REPO_ROOT / "index.html"
        assert index_path.exists(), "index.html missing"
        with open(index_path, "r", encoding="utf-8") as f:
            cls.html_text = f.read()

        parser = IndexDOMParser()
        parser.feed(cls.html_text)
        cls.pills = parser.pills
        cls.cards = parser.cards
        cls.empty_state_text = parser.empty_state_text.strip()
        cls.sim = SimulatedDOMFilter(cls.cards)

    def test_filter_pill_counts_and_partitioning(self):
        """Pill counts must be exact: All=13, Journal=3, Conf=5, Patent=2, Preprint=3."""
        pill_map = {p["filter"]: p["count"] for p in self.pills}
        self.assertEqual(pill_map.get("all"), 13)
        self.assertEqual(pill_map.get("journal"), 3)
        self.assertEqual(pill_map.get("conference"), 5)
        self.assertEqual(pill_map.get("patent"), 2)
        self.assertEqual(pill_map.get("preprint"), 3)

        # Sum of specific categories must equal 13
        category_sum = (
            pill_map["journal"] + pill_map["conference"] + pill_map["patent"] + pill_map["preprint"]
        )
        self.assertEqual(category_sum, 13)
        self.assertEqual(category_sum, pill_map["all"])

    def test_dom_cards_exact_count(self):
        """Total publication cards in DOM must be exactly 13."""
        self.assertEqual(len(self.cards), 13)

    def test_click_patent_pill_filtering(self):
        """Clicking 'patent' pill must yield exactly 2 visible cards with Pending Patent badges."""
        self.sim.select_category("patent")
        self.sim.set_query("")
        result = self.sim.execute()

        self.assertEqual(result["visible_count"], 2)
        self.assertEqual(len(result["hidden"]), 11)
        self.assertEqual(result["empty_state"], "none")

        # Verify exact patent titles
        titles = [c["title"] for c in result["visible"]]
        self.assertTrue(any("Liveness" in t for t in titles), f"Missing Liveness in {titles}")
        self.assertTrue(any("Deception" in t for t in titles), f"Missing Deception in {titles}")

        # Verify badge on each card is 'Pending Patent' and NOT 'Patent'
        for card in result["visible"]:
            badge_texts = [b["text"].strip() for b in card["badges"]]
            self.assertIn("Pending Patent", badge_texts)
            self.assertNotIn("Patent", badge_texts)

    def test_all_category_pills_individual_behavior(self):
        """Stress-test each filter pill individually."""
        expected = {
            "all": 13,
            "journal": 3,
            "conference": 5,
            "patent": 2,
            "preprint": 3,
        }
        for cat, expected_count in expected.items():
            self.sim.select_category(cat)
            self.sim.set_query("")
            res = self.sim.execute()
            self.assertEqual(
                res["visible_count"],
                expected_count,
                f"Filter pill '{cat}' expected {expected_count} cards, got {res['visible_count']}",
            )
            self.assertEqual(res["empty_state"], "none")

    def test_search_query_deception(self):
        """Searching 'Deception' across 'all' categories returns exactly 2 cards."""
        self.sim.select_category("all")
        self.sim.set_query("Deception")
        res = self.sim.execute()

        # Matches patent "Deception detection" and journal "Deception Detection and Remote..."
        self.assertEqual(res["visible_count"], 2)
        self.assertEqual(res["empty_state"], "none")

        categories = {c["category"] for c in res["visible"]}
        self.assertEqual(categories, {"patent", "journal"})

    def test_search_query_liveness(self):
        """Searching 'Liveness' across 'all' categories returns exactly 2 cards."""
        self.sim.select_category("all")
        self.sim.set_query("Liveness")
        res = self.sim.execute()

        # Matches patent "Liveness detection" and conference "Iris Liveness Detection Competition"
        self.assertEqual(res["visible_count"], 2)
        self.assertEqual(res["empty_state"], "none")

        categories = {c["category"] for c in res["visible"]}
        self.assertEqual(categories, {"patent", "conference"})

    def test_search_query_pending_patent_badge(self):
        """Searching 'Pending Patent' returns exactly the 2 patent cards."""
        self.sim.select_category("all")
        self.sim.set_query("Pending Patent")
        res = self.sim.execute()

        self.assertEqual(res["visible_count"], 2)
        self.assertEqual(res["empty_state"], "none")
        for c in res["visible"]:
            self.assertEqual(c["category"], "patent")

    def test_search_query_ppca_and_empty_state(self):
        """Searching 'PPCA' must return 0 results and activate empty state display."""
        self.sim.select_category("all")
        self.sim.set_query("PPCA")
        res = self.sim.execute()

        self.assertEqual(res["visible_count"], 0)
        self.assertEqual(len(res["hidden"]), 13)
        self.assertEqual(res["empty_state"], "block")

    def test_search_query_pragmatic_thesis_and_empty_state(self):
        """Searching 'Pragmatic' must return 0 results and activate empty state."""
        self.sim.select_category("all")
        self.sim.set_query("Pragmatic")
        res = self.sim.execute()

        self.assertEqual(res["visible_count"], 0)
        self.assertEqual(res["empty_state"], "block")

    def test_category_and_query_interplay_matrix(self):
        """Adversarially evaluate category + query combinations."""
        # Patent + Deception -> 1 result
        self.sim.select_category("patent")
        self.sim.set_query("Deception")
        self.assertEqual(self.sim.execute()["visible_count"], 1)

        # Journal + Deception -> 1 result
        self.sim.select_category("journal")
        self.sim.set_query("Deception")
        self.assertEqual(self.sim.execute()["visible_count"], 1)

        # Conference + Deception -> 0 results (empty state)
        self.sim.select_category("conference")
        self.sim.set_query("Deception")
        res = self.sim.execute()
        self.assertEqual(res["visible_count"], 0)
        self.assertEqual(res["empty_state"], "block")

        # Patent + Liveness -> 1 result
        self.sim.select_category("patent")
        self.sim.set_query("Liveness")
        self.assertEqual(self.sim.execute()["visible_count"], 1)

        # Conference + Liveness -> 1 result
        self.sim.select_category("conference")
        self.sim.set_query("Liveness")
        self.assertEqual(self.sim.execute()["visible_count"], 1)

        # Journal + Liveness -> 0 results (empty state)
        self.sim.select_category("journal")
        self.sim.set_query("Liveness")
        res = self.sim.execute()
        self.assertEqual(res["visible_count"], 0)
        self.assertEqual(res["empty_state"], "block")

    def test_search_case_insensitivity_and_whitespace(self):
        """Search query whitespace trimming and case insensitivity."""
        variations = [
            "deception",
            "DECEPTION",
            "dEcEpTiOn",
            "  deception  ",
            "\tDeception \n",
        ]
        self.sim.select_category("all")
        for v in variations:
            self.sim.set_query(v)
            res = self.sim.execute()
            self.assertEqual(res["visible_count"], 2, f"Failed for query variant: {repr(v)}")

    def test_search_author_siamul_karim_khan(self):
        """Searching 'Siamul Karim Khan' matches all 13 publications."""
        self.sim.select_category("all")
        self.sim.set_query("Siamul Karim Khan")
        res = self.sim.execute()
        self.assertEqual(res["visible_count"], 13)
        self.assertEqual(res["empty_state"], "none")

    def test_search_coauthor_czajka(self):
        """Searching coauthor 'Czajka' matches publications co-authored with Prof. Czajka."""
        self.sim.select_category("all")
        self.sim.set_query("Czajka")
        res = self.sim.execute()
        self.assertGreaterEqual(res["visible_count"], 8)
        self.assertEqual(res["empty_state"], "none")

    def test_search_each_individual_publication_title(self):
        """Searching key title phrases for each of the 13 publications returns exactly 1 card."""
        test_phrases = [
            "IREX",
            "Gender Bias",
            "EyePreserve",
            "Gradient-Guided",
            "LivDet-Iris",
            "Open Source Iris Recognition Repository",
            "18/625,685",  # Patent app number for Liveness detection
            "18/115,414",  # Patent app number for Deception detection
            "DeformIrisNet",
            "Remote Physiological Monitoring",
            "PhotoStylist",
            "CaMR",
            "cricket bowlers",
        ]
        self.sim.select_category("all")
        for phrase in test_phrases:
            self.sim.set_query(phrase)
            res = self.sim.execute()
            self.assertEqual(
                res["visible_count"],
                1,
                f"Query '{phrase}' expected exactly 1 match, got {res['visible_count']}",
            )
            self.assertEqual(res["empty_state"], "none")

    def test_dom_cards_strict_descending_chronological_order(self):
        """DOM cards in index.html must appear in strictly descending chronological order."""
        years = []
        for card in self.cards:
            year_badge = [b["text"].strip() for b in card["badges"] if b["text"].strip().isdigit()]
            if year_badge:
                years.append(int(year_badge[0]))
        # 13 years extracted from 13 cards
        self.assertEqual(len(years), 13)
        self.assertEqual(years, sorted(years, reverse=True))

    def test_empty_state_dom_element_presence(self):
        """#pub-empty-state must exist in index.html with appropriate messaging."""
        self.assertIn('id="pub-empty-state"', self.html_text)
        self.assertIn("No publications match", self.empty_state_text)


# ==============================================================================
# TEST SUITE 2: Undergraduate Thesis Elimination Verification
# ==============================================================================
class TestThesisEliminationAdversarial(unittest.TestCase):
    """Stress-tests complete elimination of BUET thesis from publication contexts."""

    def test_publications_json_thesis_free(self):
        """Verify publications.json has 0 traces of thesis."""
        p_path = REPO_ROOT / "assets" / "data" / "publications.json"
        with open(p_path, "r", encoding="utf-8") as f:
            pubs = json.load(f)

        self.assertEqual(len(pubs), 13)
        for pub in pubs:
            self.assertNotEqual(pub.get("id"), "pragmatic-ppca-2017")
            self.assertNotEqual(pub.get("type"), "thesis")
            self.assertNotIn("pragmatic", pub.get("title", "").lower())
            self.assertNotIn("ppca", pub.get("title", "").lower())
            self.assertNotIn("pragmatic", pub.get("abstract", "").lower())
            self.assertNotIn("ppca", pub.get("abstract", "").lower())

    def test_gs_data_json_thesis_free(self):
        """Verify gs_data.json has 0 traces of thesis and total_publications == 13."""
        gs_path = REPO_ROOT / "assets" / "data" / "gs_data.json"
        with open(gs_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data.get("metrics", {}).get("total_publications"), 13)
        pubs = data.get("publications", [])
        self.assertEqual(len(pubs), 13)
        for pub in pubs:
            self.assertNotEqual(pub.get("id"), "pragmatic-ppca-2017")
            self.assertNotIn("pragmatic", pub.get("title", "").lower())
            self.assertNotIn("ppca", pub.get("title", "").lower())

    def test_gs_data_total_publications_endpoint(self):
        """Shields.io total publications badge must be exactly 13."""
        endpoint_path = REPO_ROOT / "assets" / "data" / "gs_data_total_publications.json"
        with open(endpoint_path, "r", encoding="utf-8") as f:
            badge = json.load(f)
        self.assertEqual(badge.get("message"), "13")
        self.assertEqual(badge.get("schemaVersion"), 1)

    def test_index_html_publications_list_and_controls_thesis_free(self):
        """index.html publications list and controls must have zero thesis traces."""
        with open(REPO_ROOT / "index.html", "r", encoding="utf-8") as f:
            content = f.read()

        # Extract publications section
        pub_start = content.find('id="publications-heading"')
        pub_end = content.find('id="skills"')
        self.assertGreater(pub_start, 0)
        self.assertGreater(pub_end, pub_start)

        pub_section = content[pub_start:pub_end]

        self.assertNotIn("pragmatic-ppca-2017", pub_section)
        self.assertNotIn("Pragmatic PPCA", pub_section)
        self.assertNotIn('data-category="thesis"', pub_section)
        self.assertNotIn('data-filter="thesis"', pub_section)

    def test_pipeline_monotonic_threshold(self):
        """publish_results.py monotonic threshold must be set to 13."""
        with open(REPO_ROOT / "scripts" / "publish_results.py", "r", encoding="utf-8") as f:
            code = f.read()
        self.assertIn('"total_publications": 13', code)
        self.assertNotIn('"total_publications": 14', code)

    def test_html_generator_cat_counts_thesis_omission(self):
        """scripts/generate_publications_html.py must omit thesis from cat_counts and filter pills."""
        with open(REPO_ROOT / "scripts" / "generate_publications_html.py", "r", encoding="utf-8") as f:
            code = f.read()
        self.assertNotIn('"thesis": 0', code)
        self.assertNotIn('data-filter="thesis"', code)


# ==============================================================================
# TEST SUITE 3: SETUP_GUIDE.md Documentation Accuracy & DNS IP Verification
# ==============================================================================
class TestSetupGuideAndWorkflowAdversarial(unittest.TestCase):
    """Stress-tests SETUP_GUIDE.md documentation, DNS IPs, and GitHub Actions workflow."""

    @classmethod
    def setUpClass(cls):
        guide_path = REPO_ROOT / "SETUP_GUIDE.md"
        assert guide_path.exists(), "SETUP_GUIDE.md missing"
        with open(guide_path, "r", encoding="utf-8") as f:
            cls.guide_text = f.read()

        wf_path = REPO_ROOT / ".github" / "workflows" / "update_scholar.yml"
        assert wf_path.exists(), "update_scholar.yml missing"
        with open(wf_path, "r", encoding="utf-8") as f:
            cls.workflow_text = f.read()

    def test_github_pages_official_ipv4_anycast_ips(self):
        """Verify SETUP_GUIDE.md contains all 4 official GitHub Pages Anycast IPv4 IPs."""
        expected_ips = [
            "185.199.108.153",
            "185.199.109.153",
            "185.199.110.153",
            "185.199.111.153",
        ]
        for ip in expected_ips:
            self.assertIn(ip, self.guide_text, f"Missing required IPv4 Anycast IP: {ip}")

        # Negative check: no typos like .154 or .112
        self.assertNotIn("185.199.108.154", self.guide_text)
        self.assertNotIn("185.199.112.153", self.guide_text)
        self.assertNotIn("192.30.252.", self.guide_text)  # Obsolete legacy GitHub IP

    def test_github_pages_official_ipv6_anycast_ips(self):
        """Verify SETUP_GUIDE.md contains official GitHub Pages Anycast IPv6 IPs."""
        expected_ipv6 = [
            "2606:50c0:8000::153",
            "2606:50c0:8001::153",
            "2606:50c0:8002::153",
            "2606:50c0:8003::153",
        ]
        for ip6 in expected_ipv6:
            self.assertIn(ip6, self.guide_text, f"Missing required IPv6 Anycast IP: {ip6}")

    def test_cname_domain_instructions(self):
        """Verify SETUP_GUIDE.md covers www.siamul.info and apex redirection."""
        self.assertIn("www.siamul.info", self.guide_text)
        self.assertIn("siamul.info", self.guide_text)
        self.assertIn("CNAME", self.guide_text)
        self.assertIn(".nojekyll", self.guide_text)

    def test_https_enforcement_and_cloudflare_safeguards(self):
        """Verify HTTPS enforcement and Cloudflare Full/Full (strict) guidance."""
        self.assertIn("Enforce HTTPS", self.guide_text)
        self.assertIn("Full (strict)", self.guide_text)
        self.assertIn("ERR_TOO_MANY_REDIRECTS", self.guide_text)
        self.assertIn("Flexible", self.guide_text)

    def test_github_actions_write_permissions_instruction(self):
        """Verify documentation of GitHub Actions workflow write permissions."""
        self.assertIn("Read and write permissions", self.guide_text)
        self.assertIn("GITHUB_TOKEN", self.guide_text)
        self.assertIn("403", self.guide_text)
        self.assertIn("Allow GitHub Actions to create and approve pull requests", self.guide_text)

    def test_workflow_cron_schedule_and_syntax(self):
        """Verify .github/workflows/update_scholar.yml cron format and configuration."""
        # Cron expression '42 2 * * 0' (standard 5-part cron)
        cron_match = re.search(r"cron:\s*'([^']+)'", self.workflow_text)
        self.assertIsNotNone(cron_match, "cron schedule not found in workflow")
        cron_expr = cron_match.group(1)
        fields = cron_expr.split()
        self.assertEqual(len(fields), 5, f"Cron must have 5 fields, got {len(fields)}: '{cron_expr}'")
        self.assertEqual(fields[0], "42")  # minute
        self.assertEqual(fields[1], "2")   # hour (02:00)
        self.assertEqual(fields[2], "*")   # day of month
        self.assertEqual(fields[3], "*")   # month
        self.assertEqual(fields[4], "0")   # day of week (0=Sunday)

        # Check workflow_dispatch
        self.assertIn("workflow_dispatch:", self.workflow_text)

        # Check permissions
        self.assertIn("contents: write", self.workflow_text)

        # Check skip ci to avoid recursion
        self.assertIn("[skip ci]", self.workflow_text)

    def test_setup_guide_code_fence_balance(self):
        """All code fences in SETUP_GUIDE.md must be balanced (closed properly)."""
        lines = self.guide_text.splitlines()
        fences = [i for i, line in enumerate(lines, 1) if line.lstrip().startswith("```")]
        self.assertEqual(
            len(fences) % 2,
            0,
            f"Unbalanced code fences found in SETUP_GUIDE.md! Total fence markers: {len(fences)}",
        )

    def test_patent_classification_regex_adversarial_matrix(self):
        """Stress-test regex r'\bB[1-9]?\b' for grant specifier detection."""
        grant_cases = [
            "US 11,234,567 B2",
            "US 10,987,654 B1",
            "US 9,876,543 B",
            "EP 3 456 789 B1",
            "Patent Grant No. 12345 B2",
            "US 11223344 B9",
        ]
        pending_cases = [
            "U.S. Patent Application 18/115,414 (Publication No. US 2023/0274582 A1)",
            "U.S. Patent Application 18/625,685 (Publication No. US 2024/0334008 A1)",
            "PCT/US2023/012345 A1",
            "US 2022/0123456",
            "SUB-1234 Application",
        ]

        pattern = r'\bB[1-9]?\b'
        for text in grant_cases:
            self.assertTrue(bool(re.search(pattern, text)), f"Failed to detect grant in: {text}")

        for text in pending_cases:
            self.assertFalse(bool(re.search(pattern, text)), f"False positive grant detected in: {text}")

    def test_referenced_repo_files_in_setup_guide_exist(self):
        """Ensure all local files mentioned in SETUP_GUIDE.md commands actually exist."""
        referenced_files = [
            "CNAME",
            ".nojekyll",
            "index.html",
            "404.html",
            "verify_site.py",
            "scripts/scholar_crawler.py",
            "scripts/publish_results.py",
            "scripts/generate_publications_html.py",
            "scripts/inject_publications.py",
            ".github/workflows/update_scholar.yml",
            "assets/data/publications.json",
            "assets/data/gs_data.json",
        ]
        for rel_file in referenced_files:
            file_path = REPO_ROOT / rel_file
            self.assertTrue(file_path.exists(), f"File referenced in SETUP_GUIDE.md does not exist: {rel_file}")


if __name__ == "__main__":
    unittest.main()
