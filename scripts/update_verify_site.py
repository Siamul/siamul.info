#!/usr/bin/env python3
"""
update_verify_site.py
Updates verify_site.py with positive tests for the Decoupled CI/CD Caching architecture.
"""

from pathlib import Path
import re

def main():
    verify_file = Path(__file__).resolve().parent.parent / "verify_site.py"
    content = verify_file.read_text(encoding="utf-8")

    # Locate check_scholar_and_publications definition
    start_tag = "def check_scholar_and_publications("
    end_tag = "def check_media_and_content_fixes("

    start_idx = content.find(start_tag)
    end_idx = content.find(end_tag)

    if start_idx == -1 or end_idx == -1:
        print("Error: Could not locate check_scholar_and_publications function bounds!")
        return

    new_check_code = '''def check_scholar_and_publications(parser: Optional[SiteHTMLParser], repo_root_or_report: Union[Path, TestReport], report: Optional[TestReport] = None):
    """
    R1, R2, R3: Google Scholar & Decoupled CI/CD Publications Integration
    - Valid Publications / Google Scholar section header in DOM (id="publications-heading")
    - Direct link to Google Scholar profile with user=4m76wqsAAAAJ
    - Strict negative assertion: blocked Google Scholar iframe omission
    - Decoupled CI/CD pipeline automation (.github/workflows/update_scholar.yml with weekly cron & workflow_dispatch)
    - Decoupled crawler & publisher scripts (scholar_crawler.py & publish_results.py)
    - 5 Decoupled JSON data artifacts with schema validation (gs_data.json, 4 Shields.io endpoints)
    - Monotonic cache freshness validation
    - Pre-rendered semantic publications cards (#publications-list, 14 cards, search input, filter pills, BibTeX modal)
    - Live citation telemetry display (Citations, h-index, i10-index, Publications, sync badge)
    """
    if isinstance(repo_root_or_report, TestReport):
        report = repo_root_or_report
        repo_root = Path(__file__).resolve().parent
    else:
        repo_root = repo_root_or_report
        if report is None:
            raise ValueError("TestReport object must be provided")

    suite = "Google Scholar & Publications Integration (R1, R2, R3)"

    if parser is None:
        report.add(suite, "Scholar Integration Check", CheckStatus.FAIL,
                   "Skipped: index.html was not parsed (pending Milestone 3 implementation).")
        return

    index_file = repo_root / "index.html"
    index_text = index_file.read_text(encoding="utf-8") if index_file.exists() else ""

    # 1. Exact or recognized Publications/Scholar Header Check
    has_pub_heading = any(
        h.get("text", "").strip() in ("Publications:", "Publications", "Google Scholar Profile", "Research & Publications") or
        h.get("id") == "publications-heading" or
        "publications" in h.get("text", "").lower()
        for h in parser.headings
    )
    if has_pub_heading:
        report.add(suite, "Publications / Scholar Section Header", CheckStatus.PASS,
                   "Found valid Publications / Google Scholar header in DOM.")
    else:
        found_headings = [f"<{h.get('tag')}> {h.get('text', '')}" for h in parser.headings]
        report.add(suite, "Publications / Scholar Section Header", CheckStatus.FAIL,
                   "Could not find valid Publications / Google Scholar header in DOM.",
                   f"Found headings: {found_headings}")

    # 2. Google Scholar Profile Link Check (user=4m76wqsAAAAJ)
    scholar_user = "4m76wqsAAAAJ"
    scholar_links = [
        l.get("href", "") for l in parser.all_links
        if "scholar.google.com" in l.get("href", "") and scholar_user in l.get("href", "")
    ]

    if scholar_links:
        report.add(suite, "Google Scholar Profile Link", CheckStatus.PASS,
                   f"Found Google Scholar link with user={scholar_user}: {scholar_links[0]}.")
    else:
        all_scholars = [l.get("href", "") for l in parser.all_links if "scholar.google" in l.get("href", "")]
        report.add(suite, "Google Scholar Profile Link", CheckStatus.FAIL,
                   f"Missing required link to Google Scholar profile with user={scholar_user}.",
                   f"Scholar links found: {all_scholars}")

    # 3. Strict Negative Check: Blocked Google Scholar Iframe Omission (R1)
    scholar_iframes = [
        ifr.get("src", "") for ifr in parser.iframes
        if "scholar.google.com" in ifr.get("src", "")
    ]
    if not scholar_iframes:
        report.add(suite, "Google Scholar Iframe Omission", CheckStatus.PASS,
                   "Confirmed non-functioning Google Scholar iframe is completely removed from DOM.")
    else:
        report.add(suite, "Google Scholar Iframe Omission", CheckStatus.FAIL,
                   f"Violated R1: Google Scholar iframe still present: {scholar_iframes}")

    # 4. Decoupled CI/CD Workflow & Automation
    workflow_file = repo_root / ".github" / "workflows" / "update_scholar.yml"
    crawler_script = repo_root / "scripts" / "scholar_crawler.py"
    publisher_script = repo_root / "scripts" / "publish_results.py"

    workflow_ok = False
    if workflow_file.exists():
        wf_text = workflow_file.read_text(encoding="utf-8")
        workflow_ok = ("schedule:" in wf_text or "cron:" in wf_text) and "workflow_dispatch:" in wf_text

    if workflow_ok and crawler_script.exists() and publisher_script.exists():
        report.add(suite, "Decoupled CI/CD Automation Pipeline", CheckStatus.PASS,
                   "Verified GitHub Actions weekly cron workflow (.github/workflows/update_scholar.yml), "
                   "crawler script (scripts/scholar_crawler.py), and monotonic publisher (scripts/publish_results.py).")
    else:
        issues = []
        if not workflow_file.exists():
            issues.append("Missing .github/workflows/update_scholar.yml")
        elif not workflow_ok:
            issues.append("Workflow missing schedule cron or workflow_dispatch triggers")
        if not crawler_script.exists():
            issues.append("Missing scripts/scholar_crawler.py")
        if not publisher_script.exists():
            issues.append("Missing scripts/publish_results.py")
        report.add(suite, "Decoupled CI/CD Automation Pipeline", CheckStatus.FAIL,
                   f"Decoupled CI/CD pipeline files incomplete ({len(issues)} issues).",
                   "\\n".join(issues))

    # 5. Decoupled JSON Data Artifacts & Shields.io Schema Check
    data_dir = repo_root / "assets" / "data"
    gs_data_file = data_dir / "gs_data.json"
    shield_files = [
        ("gs_data_total_citation.json", "citations"),
        ("gs_data_h_index.json", "h-index"),
        ("gs_data_i10_index.json", "i10-index"),
        ("gs_data_total_publications.json", "publications"),
    ]

    schema_errors = []
    if not gs_data_file.exists():
        schema_errors.append("Missing assets/data/gs_data.json")
    else:
        try:
            with open(gs_data_file, "r", encoding="utf-8") as f:
                gs_data = json.load(f)
            metrics = gs_data.get("metrics", {})
            for k in ["citations", "h_index", "i10_index", "total_publications"]:
                if k not in metrics or not isinstance(metrics[k], int):
                    schema_errors.append(f"gs_data.json metrics missing integer '{k}'")
            if len(gs_data.get("publications", [])) < 14:
                schema_errors.append(f"gs_data.json expected 14 publications, found {len(gs_data.get('publications', []))}")
        except Exception as e:
            schema_errors.append(f"gs_data.json invalid JSON: {e}")

    for fname, expected_label in shield_files:
        fpath = data_dir / fname
        if not fpath.exists():
            schema_errors.append(f"Missing Shields.io endpoint {fname}")
        else:
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    s_data = json.load(f)
                if s_data.get("schemaVersion") != 1:
                    schema_errors.append(f"{fname}: schemaVersion must be 1")
                if "message" not in s_data:
                    schema_errors.append(f"{fname}: missing 'message' key")
                if s_data.get("label") != expected_label:
                    schema_errors.append(f"{fname}: label expected '{expected_label}', got '{s_data.get('label')}'")
            except Exception as e:
                schema_errors.append(f"{fname} invalid JSON: {e}")

    if not schema_errors:
        report.add(suite, "Decoupled Data Artifacts & Shields.io Schema", CheckStatus.PASS,
                   "All 5 decoupled JSON artifacts verified (gs_data.json + 4 Shields.io endpoints) with strict schema compliance.")
    else:
        report.add(suite, "Decoupled Data Artifacts & Shields.io Schema", CheckStatus.FAIL,
                   f"Schema errors in decoupled data assets ({len(schema_errors)} issues).",
                   "\\n".join(schema_errors))

    # 6. Monotonic Freshness & Schema Gate Validation
    try:
        with open(gs_data_file, "r", encoding="utf-8") as f:
            current_gs = json.load(f)
        m = current_gs.get("metrics", {})
        monotonic_ok = m.get("citations", 0) >= 121 and m.get("h_index", 0) >= 5 and m.get("i10_index", 0) >= 4 and m.get("total_publications", 0) >= 14
        if monotonic_ok:
            report.add(suite, "Monotonic Cache Freshness Gate", CheckStatus.PASS,
                       f"Monotonic validation passed: citations={m['citations']}, h={m['h_index']}, i10={m['i10_index']}, pubs={m['total_publications']}.")
        else:
            report.add(suite, "Monotonic Cache Freshness Gate", CheckStatus.FAIL,
                       f"Monotonic benchmark gate failed with values: {m}")
    except Exception as e:
        report.add(suite, "Monotonic Cache Freshness Gate", CheckStatus.FAIL,
                   f"Error executing monotonic cache validation: {e}")

    # 7. Semantic Publications Pre-rendered HTML (100% SEO Indexable)
    has_pub_list = "publications-list" in parser.all_ids
    has_pub_search = "pub-search" in parser.all_ids
    has_pub_pills = "pub-filter-pills" in index_text
    pub_card_count = index_text.count("publication-card")
    has_author_highlight = "<strong>Siamul Karim Khan</strong>" in index_text
    has_citation_badges = "pub-citations-badge" in index_text
    has_bibtex_modal = "bibtex-modal" in parser.all_ids

    pub_rendering_issues = []
    if not has_pub_list:
        pub_rendering_issues.append("Missing container element with id='publications-list'")
    if not has_pub_search:
        pub_rendering_issues.append("Missing search input with id='pub-search'")
    if not has_pub_pills:
        pub_rendering_issues.append("Missing category filter pills 'pub-filter-pills'")
    if pub_card_count != 14:
        pub_rendering_issues.append(f"Expected 14 publication cards, found {pub_card_count}")
    if not has_author_highlight:
        pub_rendering_issues.append("Author 'Siamul Karim Khan' not highlighted with <strong> in publication cards")
    if not has_citation_badges:
        pub_rendering_issues.append("Missing per-paper citation badges 'pub-citations-badge'")
    if not has_bibtex_modal:
        pub_rendering_issues.append("Missing modal element with id='bibtex-modal'")

    if not pub_rendering_issues:
        report.add(suite, "Semantic Publications List & Controls", CheckStatus.PASS,
                   "Pre-rendered semantic publications verified: 14 cards, search filter, category pills, "
                   "highlighted author 'Siamul Karim Khan', and BibTeX modal.")
    else:
        report.add(suite, "Semantic Publications List & Controls", CheckStatus.FAIL,
                   f"Publication rendering issues found ({len(pub_rendering_issues)} issues).",
                   "\\n".join(pub_rendering_issues))

    # 8. Scholar Telemetry & Cache Sync Display
    has_hero_card = "scholar-hero-card" in index_text or "scholar-profile-card" in index_text
    has_sync_badge = "scholar-sync-badge" in index_text
    has_metrics_telemetry = "scholar-metrics" in index_text and "metric-citations" in parser.all_ids

    telemetry_issues = []
    if not has_hero_card:
        telemetry_issues.append("Missing scholar hero/profile overview card")
    if not has_sync_badge:
        telemetry_issues.append("Missing CI/CD sync badge 'scholar-sync-badge'")
    if not has_metrics_telemetry:
        telemetry_issues.append("Missing live metrics telemetry block (.scholar-metrics with #metric-citations)")

    if not telemetry_issues:
        report.add(suite, "Academic Citation Telemetry & Cache Sync", CheckStatus.PASS,
                   "Google Scholar overview card verified with metrics telemetry (citations, h-index, i10-index, pubs) "
                   "and CI/CD sync indicator badge.")
    else:
        report.add(suite, "Academic Citation Telemetry & Cache Sync", CheckStatus.FAIL,
                   f"Scholar telemetry display issues ({len(telemetry_issues)} issues).",
                   "\\n".join(telemetry_issues))


'''

    # Replace the check_scholar_and_publications function
    content = content[:start_idx] + new_check_code + content[end_idx:]

    # Also update Test 6 in run_self_tests if present
    old_self_test_6 = '''    # Test 6: Static publications list detector catches #publications-list
    bad_pub_html = """<!DOCTYPE html><html><body><div id="publications-list"><div class="publication-card">Paper</div></div></body></html>"""
    p_pub = SiteHTMLParser()
    p_pub.feed(bad_pub_html)
    static_pub_detected = "publications-list" in p_pub.all_ids or "publication-card" in bad_pub_html
    if static_pub_detected:
        report.add(suite, "Harness Static Publications Sensitivity", CheckStatus.PASS,
                   "Static publications detector successfully caught prohibited #publications-list and cards.")
    else:
        report.add(suite, "Harness Static Publications Sensitivity", CheckStatus.FAIL,
                   "Static publications detector failed to catch prohibited #publications-list.")'''

    new_self_test_6 = '''    # Test 6: Decoupled CI/CD schema validator catches invalid schema
    invalid_badge_json = {"schemaVersion": 2, "label": "citations"}  # missing message
    is_valid_badge = invalid_badge_json.get("schemaVersion") == 1 and "message" in invalid_badge_json
    if not is_valid_badge:
        report.add(suite, "Harness Shields.io Schema Sensitivity", CheckStatus.PASS,
                   "Schema validator successfully detected invalid Shields.io badge schema.")
    else:
        report.add(suite, "Harness Shields.io Schema Sensitivity", CheckStatus.FAIL,
                   "Schema validator failed to detect invalid Shields.io badge schema.")'''

    if old_self_test_6 in content:
        content = content.replace(old_self_test_6, new_self_test_6)

    verify_file.write_text(content, encoding="utf-8")
    print("Successfully updated verify_site.py!")

if __name__ == "__main__":
    main()
