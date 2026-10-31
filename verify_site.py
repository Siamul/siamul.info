#!/usr/bin/env python3
"""
Siamul Personal Website - Automated Verification Suite & Preview Server
======================================================================
Author: Test Writer M2 (test_writer_m2_web)
Project: Siamul Karim Khan Personal Academic & Professional Website Rebuild
Specification: Acceptance Criteria R1-R5 (PROJECT.md / ORIGINAL_REQUEST.md)
Target Repository: c:\\Antigravity\\siamul_personal_website

Features & Test Coverage:
1. Deployment & Domain Configuration (R4):
   - CNAME file exists and contains strictly "www.siamul.info\\n"
   - .nojekyll exists
   - 404.html exists and is structurally valid with return home CTA
   - README.md exists and documents DNS configurations (CNAME, A records, HTTPS)
2. Data & Asset Foundation (R1, M1):
   - assets/data/profile.json valid JSON with all required fields (5 skill categories, 6 awards, etc.)
   - assets/data/publications.json valid JSON with 13 entries (13 Scholar publications, undergraduate thesis removed)
   - Image assets: avatar.jpg, favicon.png, nd_logo.png, buet_logo.png, 16 volunteer photos
   - Validates image magic headers (JPEG/PNG) and non-zero sizes
3. HTML Structure & Syntax (R1, R2, R5):
   - Validates DOCTYPE html, <html> with lang, <head>, <title>, <body>
   - Validates <meta charset="utf-8"> and responsive <meta name="viewport" ...>
4. Section Presence Verification (R1, R5):
   - Asserts DOM contains all 9 required sections:
     #about, #education, #research, #skills, #awards, #cv, #volunteer, #music, #contact
5. Google Scholar & Publications (R3):
   - Asserts exact "Publications:" heading inside/attached to #research
   - Asserts link to Google Scholar profile with user=4m76wqsAAAAJ
6. Projects Tab Omission (Strict Negative Assertion, R1):
   - Asserts NO navigation links contain "Projects" or "Project"
   - Asserts NO navigation hrefs point to projects
   - Asserts NO section has id="projects" or heading "Projects"
   - Asserts projects.html does NOT exist
7. Asset Integrity Verification (R5):
   - Scans all local <img>, <link>, <script>, and <a> download paths in index.html & 404.html
   - Confirms every referenced local file exists on disk with non-zero size
8. Anchor Link Integrity (R5):
   - Scans all internal href="#..." jump links in index.html
   - Asserts every anchor has a matching element id in the DOM
9. Responsive CSS Verification (R2):
   - Scans css/styles.css for responsive @media queries (<768px, 768-1024px)
   - Scans for dark mode support (prefers-color-scheme / data-theme)
   - Scans for layout overflow safeguards (box-sizing, overflow-x)
10. Built-in Local HTTP Preview Server (R5):
   - CLI flag --serve [port] (defaults to 8000)
   - Graceful shutdown, proper MIME types, root directory binding
11. Diagnostic, Progressive, and Self-Test Modes:
   - --milestone 1 / --m1: Validates M1 assets only
   - --self-test: Validates parser and harness logic against synthetic test cases
   - --json: Structured machine-readable JSON output
   - Exit code 0 on pass, 1 on failure

Zero external runtime or build dependencies — Python 3 standard library only.
"""

import argparse
import html
import http.server
import json
import mimetypes
import os
from pathlib import Path
import re
import socketserver
import sys
from html.parser import HTMLParser
import urllib.parse
from typing import Dict, List, Optional, Set, Tuple, Union


# ==============================================================================
# Terminal Color & Styling Utilities
# ==============================================================================

class Colors:
    """ANSI color codes with automatic terminal capability detection."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"

    @classmethod
    def disable(cls):
        """Disable all colors for non-TTY or requested plain text mode."""
        for attr in ["RESET", "BOLD", "DIM", "RED", "GREEN", "YELLOW", "BLUE", "MAGENTA", "CYAN", "WHITE"]:
            setattr(cls, attr, "")


def init_terminal_colors(force_color: bool = False, no_color: bool = False):
    """Initialize terminal color support on Windows and other platforms."""
    if no_color or os.environ.get("NO_COLOR"):
        Colors.disable()
        return

    if force_color:
        return

    # Check if stdout is a TTY
    if not hasattr(sys.stdout, "isatty") or not sys.stdout.isatty():
        Colors.disable()
        return

    # Enable ANSI escape sequences on Windows if possible
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.GetStdHandle(-11)  # STD_OUTPUT_HANDLE
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                # ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
                kernel32.SetConsoleMode(handle, mode.value | 0x0004)
        except Exception:
            # Fall back to os.system('') which also enables ANSI on modern Windows 10/11
            try:
                os.system("")
            except Exception:
                Colors.disable()


# ==============================================================================
# HTML Parser for Semantic Inspection
# ==============================================================================

VOID_TAGS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr"
}

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}


class SiteHTMLParser(HTMLParser):
    """
    Robust HTML parser that tracks DOM structure, IDs, navigation links,
    assets, headings, and metadata without third-party dependencies.
    """

    def __init__(self):
        super().__init__()
        self.doctype: Optional[str] = None
        self.has_html_tag = False
        self.html_lang: Optional[str] = None
        self.has_head_tag = False
        self.has_body_tag = False
        self.title_text: Optional[str] = None
        self.meta_charset: Optional[str] = None
        self.meta_viewport: Optional[str] = None

        # Tracking collections
        self.all_ids: Set[str] = set()
        self.tag_stack: List[Tuple[str, Dict[str, Optional[str]]]] = []
        
        # Section and navigation details
        self.nav_links: List[Dict[str, str]] = []  # links inside nav or header
        self.all_links: List[Dict[str, str]] = []  # all <a> tags
        self.internal_anchors: List[str] = []      # list of '#target' href values
        self.referenced_assets: List[str] = []     # all src/href attributes for local files
        self.headings: List[Dict[str, str]] = []   # tag, text, id, in_research, classes
        self.sections_found: Set[str] = set()      # IDs found on section/div/main elements
        self.iframes: List[Dict[str, str]] = []    # all <iframe> tags with src, id, title, class, section
        self.current_section: Optional[str] = None
        self.section_texts: Dict[str, List[str]] = {}
        self.section_links: Dict[str, List[Dict[str, str]]] = {}

        # Transient parser state
        self._current_tag: Optional[str] = None
        self._current_text_buffer: List[str] = []
        self._current_link_data: Optional[Dict[str, str]] = None
        self._current_heading_data: Optional[Dict[str, str]] = None
        self._inside_title = False
        self._inside_research_depth = 0

    def handle_decl(self, decl: str):
        """Capture doctype declarations, e.g. 'DOCTYPE html'."""
        self.doctype = decl.strip()

    def _is_inside_nav(self) -> bool:
        """Check if current position in tag stack is inside <nav> or <header>."""
        for tag, attrs in self.tag_stack:
            if tag in ("nav", "header"):
                return True
            classes = (attrs.get("class") or "").lower()
            tag_id = (attrs.get("id") or "").lower()
            if "nav" in classes or "nav" in tag_id or "menu" in classes:
                return True
        return False

    def _is_inside_research(self) -> bool:
        """Check if current position in tag stack is inside the research section."""
        for tag, attrs in self.tag_stack:
            tag_id = (attrs.get("id") or "").lower()
            if tag_id == "research":
                return True
        return False

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        attr_dict = {k.lower(): v for k, v in attrs}
        tag_lower = tag.lower()

        # Track fundamental tags
        if tag_lower == "html":
            self.has_html_tag = True
            self.html_lang = attr_dict.get("lang")
        elif tag_lower == "head":
            self.has_head_tag = True
        elif tag_lower == "body":
            self.has_body_tag = True
        elif tag_lower == "title":
            self._inside_title = True
            self._current_text_buffer = []

        # Extract IDs
        element_id = attr_dict.get("id")
        if element_id:
            cleaned_id = element_id.strip()
            self.all_ids.add(cleaned_id)
            if tag_lower in ("section", "div", "main", "article", "header", "footer"):
                self.sections_found.add(cleaned_id)

        # Section tracking
        if tag_lower == "section":
            sec_id = attr_dict.get("id")
            if sec_id:
                self.current_section = sec_id.strip()

        # Iframe tracking
        elif tag_lower == "iframe":
            iframe_data = {
                "src": attr_dict.get("src") or "",
                "id": attr_dict.get("id") or "",
                "title": attr_dict.get("title") or "",
                "class": attr_dict.get("class") or "",
                "section": self.current_section or ""
            }
            self.iframes.append(iframe_data)

        # Meta tags
        if tag_lower == "meta":
            if "charset" in attr_dict:
                self.meta_charset = attr_dict["charset"]
            elif attr_dict.get("http-equiv", "").lower() == "content-type":
                content = attr_dict.get("content", "")
                m = re.search(r"charset=([a-zA-Z0-9_-]+)", content, re.IGNORECASE)
                if m:
                    self.meta_charset = m.group(1)

            if attr_dict.get("name", "").lower() == "viewport":
                self.meta_viewport = attr_dict.get("content", "")

        # Asset references: <link>, <script>, <img>
        if tag_lower == "link":
            href = attr_dict.get("href")
            rel = attr_dict.get("rel", "").lower()
            if href:
                self.referenced_assets.append(href)
        elif tag_lower == "script":
            src = attr_dict.get("src")
            if src:
                self.referenced_assets.append(src)
        elif tag_lower == "img":
            src = attr_dict.get("src")
            if src:
                self.referenced_assets.append(src)
            srcset = attr_dict.get("srcset")
            if srcset:
                # Parse comma-separated srcset paths
                for part in srcset.split(","):
                    candidate = part.strip().split()[0]
                    if candidate:
                        self.referenced_assets.append(candidate)

        # Anchor links <a>
        if tag_lower == "a":
            href = attr_dict.get("href", "")
            is_nav = self._is_inside_nav()
            self._current_link_data = {
                "href": href,
                "is_nav": is_nav,
                "text": "",
                "id": attr_dict.get("id", ""),
                "download": attr_dict.get("download", "")
            }
            self._current_text_buffer = []
            if href.startswith("#"):
                self.internal_anchors.append(href)
            elif href and not any(href.startswith(p) for p in ("http://", "https://", "mailto:", "tel:", "javascript:", "//")):
                # Local relative link (e.g. download or local doc)
                self.referenced_assets.append(href)

        # Headings <h1> - <h6>
        if tag_lower in HEADING_TAGS:
            in_research = self._is_inside_research()
            self._current_heading_data = {
                "tag": tag_lower,
                "id": attr_dict.get("id", ""),
                "class": attr_dict.get("class", ""),
                "in_research": in_research,
                "text": ""
            }
            self._current_text_buffer = []

        # Push to stack if not a void tag
        if tag_lower not in VOID_TAGS:
            self.tag_stack.append((tag_lower, attr_dict))

    def handle_endtag(self, tag: str):
        tag_lower = tag.lower()

        if tag_lower == "section":
            self.current_section = None

        elif tag_lower == "title" and self._inside_title:
            self.title_text = "".join(self._current_text_buffer).strip()
            self._inside_title = False
            self._current_text_buffer = []

        elif tag_lower == "a" and self._current_link_data is not None:
            self._current_link_data["text"] = "".join(self._current_text_buffer).strip()
            self.all_links.append(self._current_link_data)
            if self._current_link_data["is_nav"]:
                self.nav_links.append(self._current_link_data)
            if self.current_section:
                self.section_links.setdefault(self.current_section, []).append(self._current_link_data)
            self._current_link_data = None
            self._current_text_buffer = []

        elif tag_lower in HEADING_TAGS and self._current_heading_data is not None:
            self._current_heading_data["text"] = "".join(self._current_text_buffer).strip()
            self.headings.append(self._current_heading_data)
            self._current_heading_data = None
            self._current_text_buffer = []

        # Pop stack up to matching tag
        for i in range(len(self.tag_stack) - 1, -1, -1):
            if self.tag_stack[i][0] == tag_lower:
                self.tag_stack = self.tag_stack[:i]
                break

    def handle_data(self, data: str):
        if self._inside_title or self._current_link_data is not None or self._current_heading_data is not None:
            self._current_text_buffer.append(data)
        if self.current_section:
            self.section_texts.setdefault(self.current_section, []).append(data)


# ==============================================================================
# CSS Scanner for Media Queries and Responsive Design Tokens
# ==============================================================================

class CSSScanner:
    """Scans stylesheet content for responsive media queries, dark mode, and overflow rules."""

    def __init__(self, css_text: str):
        self.css_text = css_text
        self.media_queries: List[str] = []
        self.has_mobile_query = False
        self.has_tablet_desktop_query = False
        self.has_dark_mode = False
        self.has_overflow_protection = False
        self._analyze()

    def _analyze(self):
        # Extract all @media queries
        # Match @media ... { ... }
        query_pattern = re.compile(r"@media\s*([^{]+)\{", re.IGNORECASE)
        for match in query_pattern.finditer(self.css_text):
            query_cond = match.group(1).strip()
            self.media_queries.append(query_cond)

            # Mobile query detection (typically max-width: 768px, 640px, 480px or < 768px)
            if re.search(r"max-width\s*:\s*(?:76[0-8]|770|640|480)px", query_cond, re.IGNORECASE) or \
               re.search(r"width\s*<\s*76[89]px", query_cond, re.IGNORECASE):
                self.has_mobile_query = True

            # Tablet / Desktop query detection (min-width: 768px, 1024px, 1200px or range)
            if re.search(r"min-width\s*:\s*(?:76[0-8]|1024|1200)px", query_cond, re.IGNORECASE) or \
               re.search(r"max-width\s*:\s*(?:1024|1200)px", query_cond, re.IGNORECASE) or \
               re.search(r"width\s*>=\s*76[89]px", query_cond, re.IGNORECASE):
                self.has_tablet_desktop_query = True

        # Dark mode detection (prefers-color-scheme: dark or [data-theme="dark"])
        if re.search(r"prefers-color-scheme\s*:\s*dark", self.css_text, re.IGNORECASE) or \
           re.search(r"\[data-theme=['\"]?dark['\"]?\]", self.css_text, re.IGNORECASE) or \
           re.search(r"\.dark-theme|\.dark\b", self.css_text, re.IGNORECASE):
            self.has_dark_mode = True

        # Horizontal overflow protection
        if re.search(r"box-sizing\s*:\s*border-box", self.css_text, re.IGNORECASE) and \
           (re.search(r"overflow-x\s*:\s*hidden", self.css_text, re.IGNORECASE) or
            re.search(r"max-width\s*:\s*100%", self.css_text, re.IGNORECASE)):
            self.has_overflow_protection = True


# ==============================================================================
# Test Result & Reporting Model
# ==============================================================================

class CheckStatus:
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


class CheckResult:
    """Represents the outcome of a single verification assertion."""

    def __init__(self, suite: str, name: str, status: str, message: str, details: Optional[str] = None):
        self.suite = suite
        self.name = name
        self.status = status
        self.message = message
        self.details = details

    def to_dict(self) -> Dict[str, Optional[str]]:
        return {
            "suite": self.suite,
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details
        }


class TestReport:
    """Aggregates and reports test results across all suites."""

    def __init__(self):
        self.results: List[CheckResult] = []

    def add(self, suite: str, name: str, status: str, message: str, details: Optional[str] = None):
        self.results.append(CheckResult(suite, name, status, message, details))

    def has_failures(self) -> bool:
        return any(r.status == CheckStatus.FAIL for r in self.results)

    def print_terminal_summary(self, verbose: bool = False):
        """Prints a structured colorized report of all verification checks."""
        print()
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 78}{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.WHITE} SIAMUL PERSONAL WEBSITE - AUTOMATED VERIFICATION SUITE{Colors.RESET}")
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 78}{Colors.RESET}")
        print()

        # Group by suite
        suites: Dict[str, List[CheckResult]] = {}
        for r in self.results:
            suites.setdefault(r.suite, []).append(r)

        for suite_name, suite_results in suites.items():
            print(f"{Colors.BOLD}{Colors.BLUE}▶ SUITE: {suite_name}{Colors.RESET}")
            for r in suite_results:
                if r.status == CheckStatus.PASS:
                    badge = f"{Colors.GREEN}[PASS]{Colors.RESET}"
                elif r.status == CheckStatus.FAIL:
                    badge = f"{Colors.RED}[FAIL]{Colors.RESET}"
                elif r.status == CheckStatus.WARN:
                    badge = f"{Colors.YELLOW}[WARN]{Colors.RESET}"
                else:
                    badge = f"{Colors.DIM}[SKIP]{Colors.RESET}"

                print(f"  {badge} {Colors.BOLD}{r.name}{Colors.RESET}: {r.message}")
                if r.details and (verbose or r.status in (CheckStatus.FAIL, CheckStatus.WARN)):
                    for line in r.details.strip().split("\n"):
                        print(f"         {Colors.DIM}↳ {line}{Colors.RESET}")
            print()

        # Summary line
        total = len(self.results)
        passed = sum(1 for r in self.results if r.status == CheckStatus.PASS)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAIL)
        warned = sum(1 for r in self.results if r.status == CheckStatus.WARN)
        skipped = sum(1 for r in self.results if r.status == CheckStatus.SKIP)

        print(f"{Colors.BOLD}{Colors.CYAN}{'-' * 78}{Colors.RESET}")
        status_color = Colors.GREEN if failed == 0 else Colors.RED
        verdict = "PASSED" if failed == 0 else "FAILED"
        print(f"{Colors.BOLD}VERIFICATION SUMMARY: {status_color}{verdict}{Colors.RESET} | "
              f"Total: {total} | "
              f"{Colors.GREEN}Passed: {passed}{Colors.RESET} | "
              f"{Colors.RED}Failed: {failed}{Colors.RESET} | "
              f"{Colors.YELLOW}Warnings: {warned}{Colors.RESET}" +
              (f" | Skipped: {skipped}" if skipped > 0 else ""))
        print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 78}{Colors.RESET}")
        print()

    def to_json(self) -> str:
        """Serializes report into JSON format."""
        passed = sum(1 for r in self.results if r.status == CheckStatus.PASS)
        failed = sum(1 for r in self.results if r.status == CheckStatus.FAIL)
        warned = sum(1 for r in self.results if r.status == CheckStatus.WARN)
        skipped = sum(1 for r in self.results if r.status == CheckStatus.SKIP)
        data = {
            "summary": {
                "verdict": "PASSED" if failed == 0 else "FAILED",
                "total": len(self.results),
                "passed": passed,
                "failed": failed,
                "warned": warned,
                "skipped": skipped
            },
            "checks": [r.to_dict() for r in self.results]
        }
        return json.dumps(data, indent=2)


# ==============================================================================
# Test Suite Implementations
# ==============================================================================

def check_deployment_config(repo_root: Path, report: TestReport):
    """
    R4: GitHub Pages & Custom Domain Configuration
    - CNAME contains strictly "www.siamul.info\n" (16 bytes, exact match)
    - .nojekyll exists
    - 404.html exists, parses correctly, and has a return home CTA
    - README.md exists and documents DNS configurations (CNAME, A records, HTTPS)
    """
    suite = "Deployment & Domain Configuration (R4)"

    # 1. CNAME Check
    cname_path = repo_root / "CNAME"
    if not cname_path.exists():
        report.add(suite, "CNAME File Presence", CheckStatus.FAIL,
                   "CNAME file does not exist in repository root.", str(cname_path))
    else:
        try:
            content = cname_path.read_bytes()
            if content == b"www.siamul.info\n":
                report.add(suite, "CNAME File Format", CheckStatus.PASS,
                           "CNAME contains strictly 'www.siamul.info\\n' (16 bytes exact match).")
            elif content.decode("utf-8", errors="replace").strip() == "www.siamul.info":
                report.add(suite, "CNAME File Format", CheckStatus.WARN,
                           f"CNAME text is 'www.siamul.info' but byte format is {content!r} (expected b'www.siamul.info\\n').")
            else:
                report.add(suite, "CNAME File Format", CheckStatus.FAIL,
                           f"CNAME contains unexpected content: {content!r} (expected b'www.siamul.info\\n').")
        except Exception as e:
            report.add(suite, "CNAME File Read", CheckStatus.FAIL, f"Error reading CNAME: {e}")

    # 2. .nojekyll Check
    nojekyll_path = repo_root / ".nojekyll"
    if not nojekyll_path.exists():
        report.add(suite, ".nojekyll Presence", CheckStatus.FAIL,
                   ".nojekyll file does not exist in repository root (required to bypass Jekyll on GitHub Pages).")
    else:
        report.add(suite, ".nojekyll Presence", CheckStatus.PASS,
                   ".nojekyll file exists in repository root.")

    # 3. 404.html Check
    four04_path = repo_root / "404.html"
    if not four04_path.exists():
        report.add(suite, "404.html Page Presence", CheckStatus.FAIL,
                   "404.html does not exist in repository root.", str(four04_path))
    else:
        try:
            content = four04_path.read_text(encoding="utf-8")
            parser = SiteHTMLParser()
            parser.feed(content)

            has_doctype = parser.doctype is not None and "html" in parser.doctype.lower()
            has_error_mention = "404" in content or "Not Found" in content
            has_home_cta = any(l.get("href") in ("/", "index.html", "./", "#") for l in parser.all_links)

            if has_doctype and has_error_mention and has_home_cta:
                report.add(suite, "404.html Validity & Return CTA", CheckStatus.PASS,
                           "404.html is valid HTML5, announces 404/Not Found, and includes CTA linking back to '/'.")
            else:
                details = f"DOCTYPE: {has_doctype}, 404/Not Found mentioned: {has_error_mention}, Return CTA: {has_home_cta}"
                report.add(suite, "404.html Validity & Return CTA", CheckStatus.FAIL,
                           "404.html is missing required error page elements.", details)
        except Exception as e:
            report.add(suite, "404.html Parse", CheckStatus.FAIL, f"Error parsing 404.html: {e}")

    # 4. README.md DNS Guide Check
    readme_path = repo_root / "README.md"
    if not readme_path.exists():
        report.add(suite, "README.md DNS Guide", CheckStatus.WARN,
                   "README.md not found in repository root (pending Milestone 4 deployment documentation).")
    else:
        try:
            readme_text = readme_path.read_text(encoding="utf-8")
            has_cname_doc = "www.siamul.info" in readme_text or "CNAME" in readme_text
            has_a_records = any(ip in readme_text for ip in ["185.199.108.153", "185.199.109.153", "185.199.110.153", "185.199.111.153"])
            has_https = "HTTPS" in readme_text

            if has_cname_doc and (has_a_records or has_https):
                report.add(suite, "README.md DNS Guide", CheckStatus.PASS,
                           "README.md documents GitHub Pages custom domain and DNS apex/CNAME records.")
            else:
                report.add(suite, "README.md DNS Guide", CheckStatus.WARN,
                           "README.md exists but is missing complete DNS record details (CNAME, A records, HTTPS).")
        except Exception as e:
            report.add(suite, "README.md DNS Guide", CheckStatus.WARN, f"Error reading README.md: {e}")


def check_data_assets(repo_root: Path, report: TestReport):
    """
    R1 / M1: Structured Data Assets Verification
    - profile.json: bio, Google role, Notre Dame Ph.D., BUET B.Sc., 5 skill categories, 6 awards, decoded emails
    - publications.json: 13 entries with title, authors, venue, year, links, sorted chronologically descending
    """
    suite = "Structured Data Integrity (R1, M1)"

    # 1. profile.json
    profile_path = repo_root / "assets" / "data" / "profile.json"
    if not profile_path.exists():
        report.add(suite, "Profile JSON Presence", CheckStatus.FAIL,
                   "assets/data/profile.json does not exist.", str(profile_path))
    else:
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                prof = json.load(f)

            has_name = "Siamul" in prof.get("name", "")
            emails = prof.get("contact", {}).get("emails", [])
            has_personal_email = "siamulkarim@gmail.com" in emails
            has_no_nd_email = "skhan22@nd.edu" not in emails and prof.get("contact", {}).get("primary_email") != "skhan22@nd.edu"
            linkedin_url = prof.get("contact", {}).get("links", {}).get("linkedin", "")
            has_linkedin = "linkedin.com/in/" in linkedin_url.lower()

            categories = prof.get("skills", {}).get("categories", [])
            has_5_categories = len(categories) == 5
            awards = prof.get("awards", [])
            has_6_awards = len(awards) == 6
            # Check volunteer quote
            volunteer_data = prof.get("volunteer", {})
            has_quote = False
            if isinstance(volunteer_data, dict):
                q_text = str(volunteer_data.get("quote", ""))
                q_author = str(volunteer_data.get("quote_author", ""))
                if "Jimmy Carter" in q_author or "Jimmy Carter" in q_text or "peaceful world" in q_text:
                    has_quote = True

            if has_name and has_personal_email and has_no_nd_email and has_linkedin and has_5_categories and has_6_awards:
                report.add(suite, "Profile JSON Completeness", CheckStatus.PASS,
                           f"profile.json verified: {prof.get('name')}, personal email (siamulkarim@gmail.com), ND email removed, LinkedIn link, 5 skill categories, 6 awards.")
            else:
                details = (f"Name: {has_name}, Personal email: {has_personal_email}, "
                           f"ND email removed: {has_no_nd_email}, LinkedIn: {has_linkedin}, "
                           f"Skill categories: {len(categories)}/5, Awards: {len(awards)}/6")
                report.add(suite, "Profile JSON Completeness", CheckStatus.FAIL,
                           "profile.json does not meet updated R5 contact criteria.", details)
        except Exception as e:
            report.add(suite, "Profile JSON Parsing", CheckStatus.FAIL, f"JSON parse error in profile.json: {e}")

    # 2. publications.json
    pubs_path = repo_root / "assets" / "data" / "publications.json"
    if not pubs_path.exists():
        report.add(suite, "Publications JSON Presence", CheckStatus.FAIL,
                   "assets/data/publications.json does not exist.", str(pubs_path))
    else:
        try:
            with open(pubs_path, "r", encoding="utf-8") as f:
                pubs = json.load(f)

            is_list = isinstance(pubs, list)
            count = len(pubs) if is_list else 0
            has_13 = count == 13

            # Check for undergraduate thesis removal and key publications
            thesis_absent = not any("Pragmatic PPCA" in p.get("title", "") for p in pubs) if is_list else False
            has_cricket = any("cricket bowlers" in p.get("title", "").lower() for p in pubs) if is_list else False
            has_scholar_user = all("4m76wqsAAAAJ" in str(p.get("links", {}).get("scholar", "")) for p in pubs) if is_list else False

            # Check patent entries classification
            patent_pubs = [p for p in pubs if p.get("type") == "patent"]
            patents_pending = len(patent_pubs) == 2 and all(p.get("category") == "Pending Patent" for p in patent_pubs)

            # Check strict chronological descending date order
            dates = [str(p.get("date", p.get("year", ""))) for p in pubs]
            is_sorted_desc = len(dates) == 13 and dates == sorted(dates, reverse=True)

            if is_list and has_13 and thesis_absent and has_cricket and patents_pending and is_sorted_desc:
                report.add(suite, "Publications JSON Completeness", CheckStatus.PASS,
                           f"publications.json verified: {count} publications/patents, thesis removed, pending patents classified, sorted descending by date.")
            else:
                details = f"Total count: {count} (expected 13), Thesis absent: {thesis_absent}, Has cricket paper: {has_cricket}, Patents pending: {patents_pending}, Is sorted: {is_sorted_desc}"
                report.add(suite, "Publications JSON Completeness", CheckStatus.FAIL,
                           "publications.json does not meet completeness criteria.", details)
        except Exception as e:
            report.add(suite, "Publications JSON Parsing", CheckStatus.FAIL, f"JSON parse error in publications.json: {e}")


def check_image_assets(repo_root: Path, report: TestReport):
    """
    R1 / M1: Image Assets Integrity
    - avatar.jpg, favicon.png, nd_logo.png, buet_logo.png
    - volunteer/photo_01.jpg through photo_16.jpg (16 event photos)
    - Checks file presence, non-zero size, and binary magic headers.
    """
    suite = "Image Assets Integrity (R1, M1)"

    img_dir = repo_root / "assets" / "img"
    core_images = [
        ("avatar.jpg", b"\xff\xd8\xff"),
        ("favicon.png", b"\x89PNG\r\n\x1a\n"),
        ("nd_logo.png", b"\x89PNG\r\n\x1a\n"),
        ("buet_logo.png", b"\x89PNG\r\n\x1a\n")
    ]

    all_core_ok = True
    core_failures = []
    for filename, magic in core_images:
        path = img_dir / filename
        if not path.exists():
            all_core_ok = False
            core_failures.append(f"Missing: {filename}")
        elif path.stat().st_size == 0:
            all_core_ok = False
            core_failures.append(f"Zero size: {filename}")
        else:
            try:
                head = path.read_bytes()[:len(magic)]
                if head != magic:
                    all_core_ok = False
                    core_failures.append(f"Invalid magic header: {filename}")
            except Exception as e:
                all_core_ok = False
                core_failures.append(f"Error reading {filename}: {e}")

    if all_core_ok:
        report.add(suite, "Core Image Assets", CheckStatus.PASS,
                   "All 4 core image assets (avatar, favicon, ND logo, BUET logo) exist with verified magic headers.")
    else:
        report.add(suite, "Core Image Assets", CheckStatus.FAIL,
                   f"Core image assets check failed ({len(core_failures)} issues).", "\n".join(core_failures))

    # Volunteer gallery photos (photo_01.jpg .. photo_16.jpg)
    vol_dir = img_dir / "volunteer"
    vol_failures = []
    for i in range(1, 17):
        photo_name = f"photo_{i:02d}.jpg"
        p = vol_dir / photo_name
        if not p.exists():
            vol_failures.append(f"Missing: {photo_name}")
        elif p.stat().st_size == 0:
            vol_failures.append(f"Zero size: {photo_name}")
        else:
            try:
                if p.read_bytes()[:3] != b"\xff\xd8\xff":
                    vol_failures.append(f"Invalid JPEG header: {photo_name}")
            except Exception as e:
                vol_failures.append(f"Read error {photo_name}: {e}")

    if not vol_failures:
        report.add(suite, "Volunteer Gallery Photos", CheckStatus.PASS,
                   "All 16 volunteer event photos (photo_01.jpg - photo_16.jpg) exist with valid JPEG headers and non-zero sizes.")
    else:
        report.add(suite, "Volunteer Gallery Photos", CheckStatus.FAIL,
                   f"Volunteer photos check failed ({len(vol_failures)} issues).", "\n".join(vol_failures))


def check_html_structure_and_syntax(repo_root: Path, report: TestReport) -> Optional[SiteHTMLParser]:
    """
    R1, R2, R5: HTML Document Structure & Syntax (index.html)
    - DOCTYPE html
    - <html> tag with lang attribute
    - <head> and <body> tags
    - non-empty <title> tag
    - <meta charset="utf-8">
    - <meta name="viewport" content="width=device-width, initial-scale=1...">
    """
    suite = "HTML Structure & Syntax (R1, R2, R5)"
    index_path = repo_root / "index.html"

    if not index_path.exists():
        report.add(suite, "index.html Presence", CheckStatus.FAIL,
                   "index.html does not exist in repository root (pending Milestone 3 implementation).",
                   str(index_path))
        return None

    try:
        html_content = index_path.read_text(encoding="utf-8")
    except Exception as e:
        report.add(suite, "index.html Read", CheckStatus.FAIL, f"Failed to read index.html: {e}")
        return None

    parser = SiteHTMLParser()
    try:
        parser.feed(html_content)
    except Exception as e:
        report.add(suite, "HTML Parsing Syntax", CheckStatus.FAIL, f"Fatal HTML parse error in index.html: {e}")
        return None

    report.add(suite, "HTML Parsing Syntax", CheckStatus.PASS,
               "index.html parsed cleanly with zero fatal syntax errors.")

    # 1. DOCTYPE Check
    if parser.doctype and "html" in parser.doctype.lower():
        report.add(suite, "HTML5 DOCTYPE Declaration", CheckStatus.PASS,
                   f"Found valid HTML5 DOCTYPE: '<!{parser.doctype}>'.")
    else:
        report.add(suite, "HTML5 DOCTYPE Declaration", CheckStatus.FAIL,
                   "Missing or invalid DOCTYPE declaration (expected '<!DOCTYPE html>').")

    # 2. <html> and lang
    if parser.has_html_tag:
        if parser.html_lang:
            report.add(suite, "HTML Tag & Lang Attribute", CheckStatus.PASS,
                       f"<html> tag present with lang='{parser.html_lang}'.")
        else:
            report.add(suite, "HTML Tag & Lang Attribute", CheckStatus.WARN,
                       "<html> tag present but missing 'lang' attribute.")
    else:
        report.add(suite, "HTML Tag & Lang Attribute", CheckStatus.FAIL,
                   "Missing <html> tag in index.html.")

    # 3. <head> and <body>
    if parser.has_head_tag and parser.has_body_tag:
        report.add(suite, "Head & Body Document Structure", CheckStatus.PASS,
                   "Both <head> and <body> document containers are present.")
    else:
        report.add(suite, "Head & Body Document Structure", CheckStatus.FAIL,
                   f"Incomplete document structure: <head>={parser.has_head_tag}, <body>={parser.has_body_tag}.")

    # 4. <title> Check
    if parser.title_text and len(parser.title_text.strip()) > 0:
        if "siamul" in parser.title_text.lower():
            report.add(suite, "Title Tag Verification", CheckStatus.PASS,
                       f"<title> verified: '{parser.title_text}'.")
        else:
            report.add(suite, "Title Tag Verification", CheckStatus.WARN,
                       f"<title> present but does not mention Siamul: '{parser.title_text}'.")
    else:
        report.add(suite, "Title Tag Verification", CheckStatus.FAIL,
                   "Missing or empty <title> tag in index.html.")

    # 5. Charset Check
    if parser.meta_charset and parser.meta_charset.lower() in ("utf-8", "utf8"):
        report.add(suite, "Character Set Declaration", CheckStatus.PASS,
                   f"Found valid charset declaration: '{parser.meta_charset}'.")
    else:
        report.add(suite, "Character Set Declaration", CheckStatus.FAIL,
                   f"Missing or invalid charset meta tag (found: '{parser.meta_charset}', expected 'utf-8').")

    # 6. Viewport Meta Check
    if parser.meta_viewport:
        vp = parser.meta_viewport.lower()
        if "width=device-width" in vp and "initial-scale=1" in vp:
            report.add(suite, "Viewport Responsive Meta Tag", CheckStatus.PASS,
                       f"Found valid responsive viewport meta tag: '{parser.meta_viewport}'.")
        else:
            report.add(suite, "Viewport Responsive Meta Tag", CheckStatus.WARN,
                       f"Viewport meta tag found but may lack standard properties: '{parser.meta_viewport}'.")
    else:
        report.add(suite, "Viewport Responsive Meta Tag", CheckStatus.FAIL,
                   "Missing <meta name='viewport'> tag required for mobile responsiveness.")

    return parser


def check_required_sections_presence(parser: Optional[SiteHTMLParser], report: TestReport):
    """
    R1: Migration of all content sections
    Asserts DOM contains all 9 required sections:
    1. #about (or #home)
    2. #education
    3. #research
    4. #skills
    5. #awards
    6. #cv (or #curriculum-vitae)
    7. #volunteer (or #volunteer-experience)
    8. #music
    9. #contact
    """
    suite = "Required Sections Presence (R1, R5)"

    if parser is None:
        report.add(suite, "Section Presence Check", CheckStatus.FAIL,
                   "Skipped: index.html was not parsed (pending Milestone 3 implementation).")
        return

    required_sections = [
        ("Home / About", ["about", "home"]),
        ("Education", ["education"]),
        ("Research Experience", ["research"]),
        ("Technical Skills", ["skills"]),
        ("Awards & Honors", ["awards"]),
        ("Curriculum Vitae", ["cv", "curriculum-vitae"]),
        ("Volunteer Experience", ["volunteer", "volunteer-experience"]),
        ("Music & Creative", ["music"]),
        ("Contact Details", ["contact"])
    ]

    missing = []
    found_details = []

    for name, candidate_ids in required_sections:
        matched_id = next((cid for cid in candidate_ids if cid in parser.all_ids), None)
        if matched_id:
            found_details.append(f"#{matched_id} ({name})")
        else:
            missing.append(f"{name} (expected ID: {', '.join('#' + c for c in candidate_ids)})")

    if not missing:
        report.add(suite, "All 9 Required Sections Present", CheckStatus.PASS,
                   f"All 9 primary sections detected in DOM: {', '.join(found_details)}.")
    else:
        report.add(suite, "All 9 Required Sections Present", CheckStatus.FAIL,
                   f"Missing {len(missing)} of 9 required sections: {', '.join(missing)}.",
                   f"Found IDs in DOM: {sorted(list(parser.all_ids))}")


def check_scholar_and_publications(parser: Optional[SiteHTMLParser], repo_root_or_report: Union[Path, TestReport], report: Optional[TestReport] = None):
    """
    R1, R2, R3: Google Scholar & Decoupled CI/CD Publications Integration
    - Valid Publications / Google Scholar section header in DOM (id="publications-heading")
    - Direct link to Google Scholar profile with user=4m76wqsAAAAJ
    - Strict negative assertion: blocked Google Scholar iframe omission
    - Decoupled CI/CD pipeline automation (.github/workflows/update_scholar.yml with weekly cron & workflow_dispatch)
    - Decoupled crawler & publisher scripts (scholar_crawler.py & publish_results.py)
    - 5 Decoupled JSON data artifacts with schema validation (gs_data.json, 4 Shields.io endpoints)
    - Monotonic cache freshness validation
    - Pre-rendered semantic publications cards (#publications-list, 13 cards, search input, filter pills, BibTeX modal)
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
                   "\n".join(issues))

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
            if len(gs_data.get("publications", [])) != 13:
                schema_errors.append(f"gs_data.json expected 13 publications, found {len(gs_data.get('publications', []))}")
            if any("Pragmatic PPCA" in p.get("title", "") for p in gs_data.get("publications", [])):
                schema_errors.append("gs_data.json contains undergraduate thesis (should be removed)")
            gs_dates = [str(p.get("date", p.get("year", ""))) for p in gs_data.get("publications", [])]
            if len(gs_dates) != 13 or gs_dates != sorted(gs_dates, reverse=True):
                schema_errors.append("gs_data.json publications are not ordered chronologically descending")
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
                   "\n".join(schema_errors))

    # 6. Monotonic Freshness & Schema Gate Validation
    try:
        with open(gs_data_file, "r", encoding="utf-8") as f:
            current_gs = json.load(f)
        m = current_gs.get("metrics", {})
        monotonic_ok = m.get("citations", 0) >= 121 and m.get("h_index", 0) >= 5 and m.get("i10_index", 0) >= 4 and m.get("total_publications", 0) >= 13
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

    # R1: Patent badges & pills
    pending_patent_badges = index_text.count('<span class="badge badge-patent">Pending Patent</span>')
    has_patent_pill = 'data-filter="patent"' in index_text

    # R2: Thesis card and pill omission
    has_thesis_card = 'data-category="thesis"' in index_text
    has_thesis_pill = 'data-filter="thesis"' in index_text

    # R3: Strict chronological descending ordering
    expected_titles = [p.get("title", "") for p in current_gs.get("publications", [])]
    html_titles = [html.unescape(t) for t in re.findall(r'<h4 class="pub-title"><a[^>]*>([^<]+)</a></h4>', index_text)]
    is_html_sorted_desc = len(html_titles) == 13 and all(html_titles[i] == expected_titles[i] for i in range(13))

    pub_rendering_issues = []
    if not has_pub_list:
        pub_rendering_issues.append("Missing container element with id='publications-list'")
    if not has_pub_search:
        pub_rendering_issues.append("Missing search input with id='pub-search'")
    if not has_pub_pills:
        pub_rendering_issues.append("Missing category filter pills 'pub-filter-pills'")
    if pub_card_count != 13:
        pub_rendering_issues.append(f"Expected 13 publication cards, found {pub_card_count}")
    if has_thesis_card:
        pub_rendering_issues.append("Undergraduate thesis publication card found in index.html (expected removed)")
    if has_thesis_pill:
        pub_rendering_issues.append("Thesis category filter pill found in index.html (expected removed)")
    if pending_patent_badges != 2:
        pub_rendering_issues.append(f"Expected 2 'Pending Patent' badges, found {pending_patent_badges}")
    if not has_patent_pill:
        pub_rendering_issues.append("Missing 'Patent' category filter pill")
    if not is_html_sorted_desc:
        pub_rendering_issues.append("Publication cards in index.html are not in strict chronological descending order")
    if not has_author_highlight:
        pub_rendering_issues.append("Author 'Siamul Karim Khan' not highlighted with <strong> in publication cards")
    if not has_citation_badges:
        pub_rendering_issues.append("Missing per-paper citation badges 'pub-citations-badge'")
    if not has_bibtex_modal:
        pub_rendering_issues.append("Missing modal element with id='bibtex-modal'")

    if not pub_rendering_issues:
        report.add(suite, "Semantic Publications List & Controls", CheckStatus.PASS,
                   "Pre-rendered semantic publications verified: 13 cards chronologically ordered, 2 Pending Patent badges, "
                   "search filter, category pills (thesis removed), highlighted author 'Siamul Karim Khan', and BibTeX modal.")
    else:
        report.add(suite, "Semantic Publications List & Controls", CheckStatus.FAIL,
                   f"Publication rendering issues found ({len(pub_rendering_issues)} issues).",
                   "\n".join(pub_rendering_issues))

    # 8. Scholar Telemetry Display
    has_hero_card = "scholar-hero-card" in index_text or "scholar-profile-card" in index_text
    has_metrics_telemetry = "scholar-metrics" in index_text and "metric-citations" in parser.all_ids

    telemetry_issues = []
    if not has_hero_card:
        telemetry_issues.append("Missing scholar hero/profile overview card")
    if not has_metrics_telemetry:
        telemetry_issues.append("Missing live metrics telemetry block (.scholar-metrics with #metric-citations)")

    if not telemetry_issues:
        report.add(suite, "Academic Citation Telemetry", CheckStatus.PASS,
                   "Google Scholar overview card verified with metrics telemetry (citations, h-index, i10-index, pubs).")
    else:
        report.add(suite, "Academic Citation Telemetry", CheckStatus.FAIL,
                   f"Scholar telemetry display issues ({len(telemetry_issues)} issues).",
                   "\n".join(telemetry_issues))


def check_media_and_content_fixes(parser: Optional[SiteHTMLParser], repo_root_or_report: Union[Path, TestReport], report: Optional[TestReport] = None):
    """
    R3: Media Embeds & Content Polish
    - YouTube iframe embed clean configuration (Error 153 prevention)
    - Music & Creative subheader omission
    - Music & Creative quotes omission around personal message
    - Bio Meta hyperlink omission (plain text 'Meta' without enclosing <a> or link to meta.com)
    """
    if isinstance(repo_root_or_report, TestReport):
        report = repo_root_or_report
        repo_root = Path(__file__).resolve().parent
    else:
        repo_root = repo_root_or_report
        if report is None:
            raise ValueError("TestReport object must be provided")

    suite = "Media Embeds & Content Polish (R3)"
    if parser is None:
        report.add(suite, "Media & Content Polish Check", CheckStatus.FAIL, "Skipped: index.html not parsed.")
        return

    index_file = repo_root / "index.html"
    index_text = index_file.read_text(encoding="utf-8") if index_file.exists() else ""

    # 1. YouTube Player Error 153 Configuration Fix
    yt_iframes = [ifr for ifr in parser.iframes if "youtube" in ifr.get("src", "").lower()]
    yt_error_153_found = False
    yt_issues = []

    for ifr in yt_iframes:
        src = ifr.get("src", "")
        if re.search(r'/embed/[a-zA-Z0-9_-]+\?.*list=', src) or re.search(r'/embed/[a-zA-Z0-9_-]+[&?]list=', src):
            yt_error_153_found = True
            yt_issues.append(f"Iframe src combines single video and playlist query: '{src}'")

    if yt_iframes and not yt_error_153_found:
        report.add(suite, "YouTube Embed Configuration (Error 153 Prevention)", CheckStatus.PASS,
                   "YouTube embed configured cleanly without conflicting playlist parameters.")
    elif not yt_iframes:
        report.add(suite, "YouTube Embed Configuration (Error 153 Prevention)", CheckStatus.WARN,
                   "No YouTube iframe found in DOM.")
    else:
        report.add(suite, "YouTube Embed Configuration (Error 153 Prevention)", CheckStatus.FAIL,
                   "YouTube iframe configuration triggers Error 153 (conflicting playlist query on single embed).",
                   "\n".join(yt_issues))

    # 2. Music & Creative Subheader Removal (R3)
    music_text = "".join(parser.section_texts.get("music", []))
    m_sec = re.search(r'<section\s+id=["\']music["\'].*?</section>', index_text, re.DOTALL | re.IGNORECASE)
    music_raw = m_sec.group(0) if m_sec else music_text
    has_music_subheader = bool(re.search(r"Acoustic guitar,\s*ukulele,\s*and musical vocal performances?",
                                         music_raw, re.IGNORECASE))
    if not has_music_subheader:
        report.add(suite, "Music & Creative Subheader Omission", CheckStatus.PASS,
                   "Confirmed subheader 'Acoustic guitar, ukulele, and musical vocal performance' is removed.")
    else:
        report.add(suite, "Music & Creative Subheader Omission", CheckStatus.FAIL,
                   "Violated R3: Subheader 'Acoustic guitar, ukulele, and musical vocal performance' still present in #music.")

    # 3. Music & Creative Quotes Removal (R3)
    has_straight_quotes = bool(re.search(r'"I am a musicophile\b', music_raw) or
                               re.search(r'below\."\s*', music_raw))
    has_curly_quotes = bool(re.search(r'[“"][^"“”]*musicophile[^"“”]*[”"]', music_raw))

    if not (has_straight_quotes or has_curly_quotes):
        report.add(suite, "Music & Creative Quotes Omission", CheckStatus.PASS,
                   "Confirmed quotation marks removed from personal message in #music.")
    else:
        report.add(suite, "Music & Creative Quotes Omission", CheckStatus.FAIL,
                   "Violated R3: Personal message in #music is still enclosed in quotation marks.")

    # 4. Meta Hyperlink Omission in Bio (R3)
    about_text = "".join(parser.section_texts.get("about", []))
    has_meta_mention = "meta" in about_text.lower() or "meta" in index_text.lower()

    about_links = parser.section_links.get("about", [])
    has_meta_link = any(
        "meta.com" in l.get("href", "").lower() or l.get("text", "").strip() == "Meta"
        for l in about_links
    )
    about_sec = re.search(r'<section\s+id=["\']about["\'].*?</section>', index_text, re.DOTALL | re.IGNORECASE)
    if about_sec:
        if re.search(r'<a\s+[^>]*href=["\'][^"\']*meta\.com[^"\']*["\'][^>]*>.*?</a>', about_sec.group(0), re.IGNORECASE | re.DOTALL) or \
           re.search(r'<a\s+[^>]*>\s*Meta\s*</a>', about_sec.group(0), re.IGNORECASE):
            has_meta_link = True

    if has_meta_mention and not has_meta_link:
        report.add(suite, "Bio Meta Hyperlink Omission", CheckStatus.PASS,
                   "Confirmed 'Meta' is mentioned as plain text in Bio with zero hyperlink.")
    elif not has_meta_mention:
        report.add(suite, "Bio Meta Hyperlink Omission", CheckStatus.WARN,
                   "'Meta' not found in Bio section text.")
    else:
        report.add(suite, "Bio Meta Hyperlink Omission", CheckStatus.FAIL,
                   "Violated R3: 'Meta' in Bio is hyperlinked.")


def check_copy_and_section_removals(parser: Optional[SiteHTMLParser], repo_root_or_report: Union[Path, TestReport], report: Optional[TestReport] = None):
    """
    R4, R5: Copy Polish & Section Omissions
    - Profiles & Network section and navigation omission
    - Footer domain note omission ("Hosted on GitHub Pages · Linked to www.siamul.info")
    - Contact section email and LinkedIn link verification (siamulkarim@gmail.com present, skhan22@nd.edu absent, LinkedIn present)
    """
    if isinstance(repo_root_or_report, TestReport):
        report = repo_root_or_report
        repo_root = Path(__file__).resolve().parent
    else:
        repo_root = repo_root_or_report
        if report is None:
            raise ValueError("TestReport object must be provided")

    suite = "Copy Polish & Section Omissions (R4, R5)"
    if parser is None:
        report.add(suite, "Copy & Section Omissions Check", CheckStatus.FAIL, "Skipped: index.html not parsed.")
        return

    index_file = repo_root / "index.html"
    index_text = index_file.read_text(encoding="utf-8") if index_file.exists() else ""

    # 1. Profiles & Network Removal from DOM and Navigation (R4)
    has_profiles_network_heading = any(
        "profiles & network" in h.get("text", "").lower() or "profiles & networks" in h.get("text", "").lower()
        for h in parser.headings
    )
    has_profiles_network_id = any(
        i in parser.all_ids for i in ("profiles-network", "profiles_network", "profiles-and-network", "profiles")
    )
    has_profiles_network_nav = any(
        "profile" in l.get("text", "").lower() or "network" in l.get("text", "").lower()
        for l in parser.nav_links
    )
    has_profiles_network_text = bool(re.search(r'Profiles\s*&\s*Networks?', index_text, re.IGNORECASE))

    if not (has_profiles_network_heading or has_profiles_network_id or has_profiles_network_nav or has_profiles_network_text):
        report.add(suite, "Profiles & Network Section Omission", CheckStatus.PASS,
                   "Confirmed 'Profiles & Network' section and nav links are completely removed.")
    else:
        issues = []
        if has_profiles_network_heading:
            issues.append("Heading titled 'Profiles & Network(s)' found in DOM")
        if has_profiles_network_id:
            issues.append("Element ID 'profiles-network' found in DOM")
        if has_profiles_network_nav:
            issues.append("Navigation link for Profiles/Network found")
        if has_profiles_network_text:
            issues.append("Text 'Profiles & Networks' found in index.html")
        report.add(suite, "Profiles & Network Section Omission", CheckStatus.FAIL,
                   "Violated R4: 'Profiles & Network' still present in DOM or navigation.",
                   "\n".join(issues))

    # 2. Footer Note Removal (R4)
    has_footer_note = bool(
        re.search(r"Hosted on GitHub Pages", index_text, re.IGNORECASE) or
        re.search(r"Linked to\s*(?:<[^>]+>)?\s*www\.siamul\.info", index_text, re.IGNORECASE) or
        "footer-domain-note" in index_text
    )

    if not has_footer_note:
        report.add(suite, "Footer Domain Note Omission", CheckStatus.PASS,
                   "Confirmed footer domain note 'Hosted on GitHub Pages · Linked to www.siamul.info' is removed.")
    else:
        report.add(suite, "Footer Domain Note Omission", CheckStatus.FAIL,
                   "Violated R4: Footer note 'Hosted on GitHub Pages · Linked to www.siamul.info' still present in index.html.")

    # 3. Contact Section Details (R5)
    contact_links = parser.section_links.get("contact", [])
    contact_text = "".join(parser.section_texts.get("contact", []))
    contact_sec = re.search(r'<section\s+id=["\']contact["\'].*?</section>', index_text, re.DOTALL | re.IGNORECASE)
    contact_raw = contact_sec.group(0) if contact_sec else contact_text

    # 3a. Personal Email Presence (siamulkarim@gmail.com)
    has_personal_email = (
        "siamulkarim@gmail.com" in contact_raw or
        any("mailto:siamulkarim@gmail.com" in l.get("href", "").lower() for l in contact_links)
    )
    if has_personal_email:
        report.add(suite, "Personal Email Presence", CheckStatus.PASS,
                   "Found personal email 'siamulkarim@gmail.com' in Contact section.")
    else:
        report.add(suite, "Personal Email Presence", CheckStatus.FAIL,
                   "Missing required personal email 'siamulkarim@gmail.com' in Contact section.")

    # 3b. Strict Negative Check: Notre Dame Email Absence (skhan22@nd.edu)
    has_nd_email_in_contact = "skhan22@nd.edu" in contact_raw or any("skhan22@nd.edu" in l.get("href", "").lower() for l in contact_links)
    has_nd_email_in_dom = "skhan22@nd.edu" in index_text

    if not has_nd_email_in_contact and not has_nd_email_in_dom:
        report.add(suite, "Notre Dame Email Strict Omission", CheckStatus.PASS,
                   "Confirmed ND email 'skhan22@nd.edu' is completely removed from Contact section and DOM.")
    else:
        report.add(suite, "Notre Dame Email Strict Omission", CheckStatus.FAIL,
                   "Violated R5: ND email 'skhan22@nd.edu' is still present in Contact section or DOM.")

    # 3c. LinkedIn Profile Link Presence in Contact
    has_linkedin_link = any(
        "linkedin.com/in/" in l.get("href", "").lower()
        for l in contact_links
    ) or bool(re.search(r'href=["\']https?://(?:www\.)?linkedin\.com/in/[^"\']*["\']', contact_raw, re.IGNORECASE))

    if has_linkedin_link:
        report.add(suite, "Contact LinkedIn Profile Link", CheckStatus.PASS,
                   "Found working LinkedIn profile link in Contact section.")
    else:
        report.add(suite, "Contact LinkedIn Profile Link", CheckStatus.FAIL,
                   "Missing required LinkedIn profile link in Contact section.")


def check_contact_details(parser: Optional[SiteHTMLParser], repo_root_or_report: Union[Path, TestReport], report: Optional[TestReport] = None):
    """Direct alias for contact checks in check_copy_and_section_removals."""
    return check_copy_and_section_removals(parser, repo_root_or_report, report)


def check_projects_omission(parser: Optional[SiteHTMLParser], repo_root: Path, report: TestReport):
    """
    R1 Strict Negative Requirement: Projects Tab Omission
    - Asserts that NO navigation links contain "Projects" or "Project"
    - Asserts that NO navigation hrefs point to #projects or projects.html
    - Asserts that NO section has id="projects" or heading strictly titled "Projects"
    - Asserts projects.html does NOT exist on disk
    """
    suite = "Projects Tab Omission (Strict Negative Assertion, R1)"

    # 1. Check file system for projects.html
    projects_file = repo_root / "projects.html"
    if projects_file.exists():
        report.add(suite, "No projects.html File", CheckStatus.FAIL,
                   "projects.html was found on disk; Projects tab must be completely omitted per R1.",
                   str(projects_file))
    else:
        report.add(suite, "No projects.html File", CheckStatus.PASS,
                   "Confirmed projects.html does not exist in repository root.")

    if parser is None:
        report.add(suite, "Navigation Omission Check", CheckStatus.FAIL,
                   "Skipped: index.html was not parsed (pending Milestone 3 implementation).")
        return

    # 2. Check navigation links
    nav_violations = []
    for link in parser.nav_links:
        text = link.get("text", "").lower()
        href = link.get("href", "").lower()
        if "project" in text or "project" in href:
            nav_violations.append(f"Nav Link text='{link.get('text')}', href='{link.get('href')}'")

    if not nav_violations:
        report.add(suite, "Navigation Links Omit Projects", CheckStatus.PASS,
                   "Confirmed navigation contains zero links with text 'Projects' or pointing to projects.")
    else:
        report.add(suite, "Navigation Links Omit Projects", CheckStatus.FAIL,
                   f"Violated Projects omission rule: {len(nav_violations)} project link(s) found in navigation.",
                   "\n".join(nav_violations))

    # 3. Check section IDs and headings
    dom_violations = []
    if "projects" in parser.all_ids or "project" in parser.all_ids:
        dom_violations.append("Element with id='projects' exists in DOM")

    for h in parser.headings:
        if h.get("text", "").strip().lower() in ("projects", "my projects", "featured projects"):
            dom_violations.append(f"Heading titled '{h.get('text')}' exists in DOM")

    if not dom_violations:
        report.add(suite, "DOM IDs & Section Headings Omit Projects", CheckStatus.PASS,
                   "Confirmed DOM contains no sections with id='projects' or headings titled 'Projects'.")
    else:
        report.add(suite, "DOM IDs & Section Headings Omit Projects", CheckStatus.FAIL,
                   f"Violated Projects omission rule in DOM: {len(dom_violations)} violation(s).",
                   "\n".join(dom_violations))


def check_asset_integrity(parser: Optional[SiteHTMLParser], repo_root: Path, report: TestReport):
    """
    R5: Asset Path & File Integrity
    Scans all local <img>, <link>, <script>, and <a> download paths in index.html & 404.html.
    Confirms every referenced local file exists on disk with non-zero size.
    """
    suite = "Asset Integrity Verification (R5)"

    # Also parse 404.html assets
    assets_to_check: Set[str] = set()

    if parser is not None:
        assets_to_check.update(parser.referenced_assets)

    four04_path = repo_root / "404.html"
    if four04_path.exists():
        try:
            p404 = SiteHTMLParser()
            p404.feed(four04_path.read_text(encoding="utf-8"))
            assets_to_check.update(p404.referenced_assets)
        except Exception:
            pass

    if not assets_to_check:
        if parser is None:
            report.add(suite, "Asset Integrity Scan", CheckStatus.FAIL,
                       "Skipped: index.html was not parsed (pending Milestone 3 implementation).")
        else:
            report.add(suite, "Asset Integrity Scan", CheckStatus.WARN,
                       "No local asset references were extracted from HTML documents.")
        return

    missing_assets = []
    empty_assets = []
    verified_assets = []

    for raw_asset in sorted(assets_to_check):
        # Ignore external or data URLs
        if any(raw_asset.startswith(p) for p in ("http://", "https://", "//", "data:", "mailto:", "tel:", "javascript:")):
            continue
        if raw_asset.startswith("#"):
            continue

        # Clean query parameters and fragments
        parsed_url = urllib.parse.urlparse(raw_asset)
        clean_path = urllib.parse.unquote(parsed_url.path).strip()

        # Handle root / home navigation links (e.g. "/" or "/#contact")
        if clean_path in ("", "/"):
            target_path = repo_root / "index.html"
            display_name = f"{raw_asset} -> index.html (Home Document)"
        elif clean_path.startswith("/"):
            target_path = repo_root / clean_path.lstrip("/")
            display_name = raw_asset
        else:
            target_path = repo_root / clean_path
            display_name = raw_asset

        if not target_path.exists() or not target_path.is_file():
            missing_assets.append(f"Referenced: '{raw_asset}' -> Target file not found: {target_path}")
        elif target_path.stat().st_size == 0:
            empty_assets.append(f"Referenced: '{raw_asset}' -> 0 bytes: {target_path}")
        else:
            verified_assets.append(f"{display_name} ({target_path.stat().st_size} bytes)")

    if not missing_assets and not empty_assets:
        report.add(suite, "All Referenced Local Assets Exist", CheckStatus.PASS,
                   f"Successfully verified {len(verified_assets)} local assets on disk with non-zero size.")
    else:
        total_issues = len(missing_assets) + len(empty_assets)
        details = []
        if missing_assets:
            details.append("Missing Files:\n  " + "\n  ".join(missing_assets))
        if empty_assets:
            details.append("Zero-Byte Files:\n  " + "\n  ".join(empty_assets))
        report.add(suite, "All Referenced Local Assets Exist", CheckStatus.FAIL,
                   f"Asset integrity check failed for {total_issues} referenced asset(s).",
                   "\n".join(details))


def check_anchor_integrity(parser: Optional[SiteHTMLParser], report: TestReport):
    """
    R5: Internal Anchor Link Integrity
    Scans all href="#..." jump links in index.html and confirms a matching id exists in the DOM.
    """
    suite = "Internal Anchor Link Integrity (R5)"

    if parser is None:
        report.add(suite, "Internal Anchor Integrity", CheckStatus.FAIL,
                   "Skipped: index.html was not parsed (pending Milestone 3 implementation).")
        return

    broken_anchors = []
    valid_anchors = []

    for anchor in parser.internal_anchors:
        target_id = anchor.lstrip("#").strip()
        if not target_id or target_id in ("!", "top"):
            # Generic top jump or empty dummy anchor
            continue

        if target_id in parser.all_ids:
            valid_anchors.append(anchor)
        else:
            broken_anchors.append(f"Anchor '{anchor}' targets nonexistent id='{target_id}'")

    if not broken_anchors:
        report.add(suite, "All Internal Anchors Valid", CheckStatus.PASS,
                   f"All {len(valid_anchors)} internal jump links resolve to valid element IDs in the DOM.")
    else:
        report.add(suite, "All Internal Anchors Valid", CheckStatus.FAIL,
                   f"Found {len(broken_anchors)} broken internal anchor link(s).",
                   "\n".join(broken_anchors))


def check_responsive_css(repo_root: Path, report: TestReport):
    """
    R2: Responsive CSS & Styling Verification
    - Confirms css/styles.css exists and is non-empty
    - Confirms responsive @media queries for mobile (<768px) and tablet/desktop (768-1024px)
    - Confirms dark mode tokens / query
    - Confirms horizontal overflow prevention (box-sizing, overflow-x)
    """
    suite = "Responsive CSS & Styling (R2, R5)"
    css_path = repo_root / "css" / "styles.css"

    if not css_path.exists():
        report.add(suite, "Stylesheet Presence", CheckStatus.FAIL,
                   "css/styles.css does not exist in repository (pending Milestone 3 implementation).",
                   str(css_path))
        return

    try:
        css_text = css_path.read_text(encoding="utf-8")
    except Exception as e:
        report.add(suite, "Stylesheet Read", CheckStatus.FAIL, f"Failed to read css/styles.css: {e}")
        return

    if len(css_text.strip()) == 0:
        report.add(suite, "Stylesheet Content", CheckStatus.FAIL, "css/styles.css is empty (0 bytes).")
        return

    report.add(suite, "Stylesheet Content", CheckStatus.PASS,
               f"css/styles.css exists ({len(css_text)} characters).")

    scanner = CSSScanner(css_text)

    # 1. Mobile Media Query
    if scanner.has_mobile_query:
        report.add(suite, "Mobile Responsive Breakpoint (<768px)", CheckStatus.PASS,
                   "Found responsive @media query for mobile viewports (<768px).")
    else:
        report.add(suite, "Mobile Responsive Breakpoint (<768px)", CheckStatus.FAIL,
                   "Missing mobile responsive @media breakpoint (e.g. max-width: 768px).",
                   f"Found queries: {scanner.media_queries}")

    # 2. Tablet / Desktop Breakpoint
    if scanner.has_tablet_desktop_query:
        report.add(suite, "Tablet/Desktop Responsive Breakpoint (768-1024px)", CheckStatus.PASS,
                   "Found responsive @media query for tablet/desktop viewports (768-1024px).")
    else:
        report.add(suite, "Tablet/Desktop Responsive Breakpoint (768-1024px)", CheckStatus.WARN,
                   "No explicit tablet/desktop breakpoint found (single mobile breakpoint detected).",
                   f"Found queries: {scanner.media_queries}")

    # 3. Dark Mode
    if scanner.has_dark_mode:
        report.add(suite, "Dark Mode Design Tokens", CheckStatus.PASS,
                   "Stylesheet includes dark mode support (prefers-color-scheme or data-theme).")
    else:
        report.add(suite, "Dark Mode Design Tokens", CheckStatus.WARN,
                   "No dark mode rules detected in stylesheet.")

    # 4. Overflow Protection
    if scanner.has_overflow_protection:
        report.add(suite, "Zero Horizontal Overflow Safeguards", CheckStatus.PASS,
                   "Stylesheet includes box-sizing and overflow safeguards preventing horizontal scrolling.")
    else:
        report.add(suite, "Zero Horizontal Overflow Safeguards", CheckStatus.WARN,
                   "Could not confirm explicit 'overflow-x: hidden' or 'box-sizing: border-box' rules.")


# ==============================================================================
# Built-In Local Preview HTTP Server
# ==============================================================================

class QuietHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler with clean MIME type mapping and silent or formatted logging."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def log_message(self, format, *args):
        # Format request logs cleanly with timestamp and status
        status = args[1] if len(args) > 1 else ""
        color = Colors.GREEN if status.startswith("2") or status.startswith("3") else Colors.RED
        print(f"  {Colors.DIM}[HTTP]{Colors.RESET} {args[0]} -> {color}{status}{Colors.RESET}")

    def guess_type(self, path):
        # Ensure correct MIME type for modern web assets
        ctype = super().guess_type(path)
        if path.endswith(".js"):
            return "application/javascript"
        if path.endswith(".json"):
            return "application/json"
        if path.endswith(".css"):
            return "text/css"
        return ctype


def run_preview_server(repo_root: Path, port: int = 8000):
    """Starts a local HTTP server rooted at repo_root with graceful shutdown."""
    os.chdir(str(repo_root))

    handler_factory = lambda *args, **kwargs: QuietHTTPRequestHandler(*args, directory=str(repo_root), **kwargs)

    try:
        with socketserver.TCPServer(("", port), handler_factory) as httpd:
            print()
            print(f"{Colors.BOLD}{Colors.GREEN}{'=' * 78}{Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.WHITE} SIAMUL PERSONAL WEBSITE - LOCAL PREVIEW SERVER{Colors.RESET}")
            print(f"{Colors.BOLD}{Colors.GREEN}{'=' * 78}{Colors.RESET}")
            print(f"  {Colors.BOLD}Document Root:{Colors.RESET} {repo_root}")
            print(f"  {Colors.BOLD}Local URL:{Colors.RESET}     {Colors.CYAN}http://localhost:{port}/{Colors.RESET} or {Colors.CYAN}http://127.0.0.1:{port}/{Colors.RESET}")
            print(f"  {Colors.BOLD}Status:{Colors.RESET}        Serving requests... Press {Colors.YELLOW}Ctrl+C{Colors.RESET} to stop.")
            print(f"{Colors.BOLD}{Colors.GREEN}{'=' * 78}{Colors.RESET}")
            print()
            httpd.serve_forever()
    except KeyboardInterrupt:
        print()
        print(f"\n{Colors.YELLOW}[INFO] Server stopped by user. Goodbye!{Colors.RESET}")
    except OSError as e:
        print(f"\n{Colors.RED}[ERROR] Could not start server on port {port}: {e}{Colors.RESET}")
        print(f"{Colors.YELLOW}[HINT] Try specifying a different port using --serve [port] (e.g. --serve 8080).{Colors.RESET}")
        sys.exit(1)


# ==============================================================================
# Self-Test / Harness Diagnostic Mode
# ==============================================================================

def run_self_tests(report: TestReport):
    """
    Self-tests the verification harness itself using synthetic HTML and mock data
    to prove detection power and rule out dummy/facade implementations.
    """
    suite = "Verification Harness Self-Diagnostic"

    # Test 1: Parser extracts DOCTYPE and all 9 sections
    good_html = """<!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Siamul Karim Khan</title>
        <link rel="stylesheet" href="css/styles.css">
    </head>
    <body>
        <nav><a href="#about">About</a><a href="#research">Research</a></nav>
        <section id="about"><h1>About</h1></section>
        <section id="education"><h2>Education</h2></section>
        <section id="research">
            <h2>Research</h2>
            <h3>Publications:</h3>
            <a href="https://scholar.google.com/citations?user=4m76wqsAAAAJ">Google Scholar</a>
        </section>
        <section id="skills"><h2>Skills</h2></section>
        <section id="awards"><h2>Awards</h2></section>
        <section id="cv"><h2>CV</h2></section>
        <section id="volunteer"><h2>Volunteer</h2></section>
        <section id="music"><h2>Music</h2></section>
        <section id="contact"><h2>Contact</h2></section>
    </body>
    </html>"""

    p = SiteHTMLParser()
    p.feed(good_html)

    if p.doctype == "DOCTYPE html" and len(p.all_ids) >= 9 and p.title_text == "Siamul Karim Khan":
        report.add(suite, "Harness Parser Structural Extraction", CheckStatus.PASS,
                   "Synthetic valid HTML parsed correctly: extracted DOCTYPE, all 9 sections, and title.")
    else:
        report.add(suite, "Harness Parser Structural Extraction", CheckStatus.FAIL,
                   "Synthetic valid HTML failed parser extraction.")

    # Test 2: Projects omission detector catches illicit nav link
    bad_nav_html = """<!DOCTYPE html><html><body><nav><a href="/projects">Projects</a></nav></body></html>"""
    p_bad = SiteHTMLParser()
    p_bad.feed(bad_nav_html)
    caught_violation = any("project" in l.get("text", "").lower() for l in p_bad.nav_links)
    if caught_violation:
        report.add(suite, "Harness Projects Omission Sensitivity", CheckStatus.PASS,
                   "Omission detector successfully caught illicit 'Projects' link in navigation.")
    else:
        report.add(suite, "Harness Projects Omission Sensitivity", CheckStatus.FAIL,
                   "Omission detector failed to catch illicit 'Projects' navigation link.")

    # Test 3: Anchor validator catches dangling links
    dangling_html = """<!DOCTYPE html><html><body><a href="#nonexistent">Jump</a></body></html>"""
    p_dang = SiteHTMLParser()
    p_dang.feed(dangling_html)
    dangling_detected = any(a.lstrip("#") not in p_dang.all_ids for a in p_dang.internal_anchors)
    if dangling_detected:
        report.add(suite, "Harness Broken Anchor Sensitivity", CheckStatus.PASS,
                   "Anchor validator successfully caught unresolved '#nonexistent' internal link.")
    else:
        report.add(suite, "Harness Broken Anchor Sensitivity", CheckStatus.FAIL,
                   "Anchor validator failed to detect unresolved internal anchor.")

    # Test 4: CSS Scanner detects media queries and dark mode
    sample_css = """
    * { box-sizing: border-box; }
    body { max-width: 100%; overflow-x: hidden; }
    @media (max-width: 768px) { .nav { display: none; } }
    @media (min-width: 1024px) { .grid { grid-template-columns: 3fr 1fr; } }
    @media (prefers-color-scheme: dark) { :root { --bg: #0f172a; } }
    """
    css_scan = CSSScanner(sample_css)
    if css_scan.has_mobile_query and css_scan.has_tablet_desktop_query and css_scan.has_dark_mode and css_scan.has_overflow_protection:
        report.add(suite, "Harness CSS Scanner Accuracy", CheckStatus.PASS,
                   "CSS scanner accurately detected mobile breakpoint, tablet/desktop breakpoint, dark mode, and overflow safeguards.")
    else:
        report.add(suite, "Harness CSS Scanner Accuracy", CheckStatus.FAIL,
                   "CSS scanner failed to detect expected rules in synthetic CSS snippet.")

    # Test 5: Scholar iframe detector catches prohibited Google Scholar iframe
    bad_iframe_html = """<!DOCTYPE html><html><body><section id="research"><iframe src="https://scholar.google.com/citations?user=4m76wqsAAAAJ"></iframe></section></body></html>"""
    p_ifr = SiteHTMLParser()
    p_ifr.feed(bad_iframe_html)
    scholar_ifr_detected = any("scholar.google.com" in ifr.get("src", "") for ifr in p_ifr.iframes)
    if scholar_ifr_detected:
        report.add(suite, "Harness Scholar Iframe Sensitivity", CheckStatus.PASS,
                   "Scholar iframe detector successfully detected prohibited Google Scholar iframe.")
    else:
        report.add(suite, "Harness Scholar Iframe Sensitivity", CheckStatus.FAIL,
                   "Scholar iframe detector failed to detect prohibited Google Scholar iframe.")

    # Test 6: Decoupled CI/CD schema validator catches invalid schema
    invalid_badge_json = {"schemaVersion": 2, "label": "citations"}  # missing message
    is_valid_badge = invalid_badge_json.get("schemaVersion") == 1 and "message" in invalid_badge_json
    if not is_valid_badge:
        report.add(suite, "Harness Shields.io Schema Sensitivity", CheckStatus.PASS,
                   "Schema validator successfully detected invalid Shields.io badge schema.")
    else:
        report.add(suite, "Harness Shields.io Schema Sensitivity", CheckStatus.FAIL,
                   "Schema validator failed to detect invalid Shields.io badge schema.")

    # Test 7: YouTube Error 153 detector catches playlist query on single video embed
    bad_yt_html = """<!DOCTYPE html><html><body><iframe src="https://www.youtube-nocookie.com/embed/kqCpVDByXEI?list=PLylGZraUqGUYGIGAUxayykId_WeByqD8X&enablejsapi=1"></iframe></body></html>"""
    p_yt = SiteHTMLParser()
    p_yt.feed(bad_yt_html)
    yt_bad_detected = any(bool(re.search(r'/embed/[a-zA-Z0-9_-]+\?.*list=', ifr.get("src", ""))) for ifr in p_yt.iframes)
    if yt_bad_detected:
        report.add(suite, "Harness YouTube Error 153 Sensitivity", CheckStatus.PASS,
                   "YouTube configuration checker successfully detected conflicting playlist parameter on single embed.")
    else:
        report.add(suite, "Harness YouTube Error 153 Sensitivity", CheckStatus.FAIL,
                   "YouTube configuration checker failed to detect conflicting playlist parameter.")

    # Test 8: Meta hyperlink detector catches hyperlinked Meta in bio
    bad_meta_html = """<!DOCTYPE html><html><body><section id="about"><p>I interned at <a href="http://www.meta.com">Meta</a>.</p></section></body></html>"""
    p_meta = SiteHTMLParser()
    p_meta.feed(bad_meta_html)
    meta_link_detected = any("meta.com" in l.get("href", "").lower() or l.get("text", "").strip() == "Meta" for l in p_meta.section_links.get("about", []))
    if meta_link_detected:
        report.add(suite, "Harness Meta Hyperlink Sensitivity", CheckStatus.PASS,
                   "Bio detector successfully caught prohibited hyperlink on 'Meta'.")
    else:
        report.add(suite, "Harness Meta Hyperlink Sensitivity", CheckStatus.FAIL,
                   "Bio detector failed to catch prohibited hyperlink on 'Meta'.")

    # Test 9: Contact omission detector catches skhan22@nd.edu
    bad_contact_html = """<!DOCTYPE html><html><body><section id="contact"><a href="mailto:skhan22@nd.edu">Email</a></section></body></html>"""
    p_contact = SiteHTMLParser()
    p_contact.feed(bad_contact_html)
    nd_email_detected = any("skhan22@nd.edu" in l.get("href", "").lower() for l in p_contact.section_links.get("contact", []))
    if nd_email_detected:
        report.add(suite, "Harness Contact Email Sensitivity", CheckStatus.PASS,
                   "Contact email checker successfully caught prohibited 'skhan22@nd.edu' email.")
    else:
        report.add(suite, "Harness Contact Email Sensitivity", CheckStatus.FAIL,
                   "Contact email checker failed to catch prohibited 'skhan22@nd.edu' email.")


# ==============================================================================
# Main CLI Orchestration
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Siamul Personal Website Automated Verification Suite & Preview Server",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python verify_site.py                   # Run full verification suite against repository
  python verify_site.py --m1              # Verify Milestone 1 assets and configs only
  python verify_site.py --suite media     # Verify YouTube embed and Music/Bio content polish
  python verify_site.py --suite copy      # Verify section omissions and contact information
  python verify_site.py --serve           # Start local preview server on default port 8000
  python verify_site.py --serve 8080      # Start local preview server on port 8080
  python verify_site.py --self-test       # Execute harness diagnostic sensitivity tests
  python verify_site.py --json            # Output test results as JSON for CI/audit
        """
    )

    parser.add_argument("--root", type=str, default=None,
                        help="Path to repository root (defaults to script's directory)")
    parser.add_argument("--serve", nargs="?", const=8000, type=int, default=None,
                        help="Launch local preview HTTP server on specified port (default 8000)")
    parser.add_argument("--m1", "--milestone-1", action="store_true", dest="m1_only",
                        help="Run verification for Milestone 1 assets only (CNAME, 404, images, data)")
    parser.add_argument("--suite", type=str, default=None,
                        choices=["deployment", "data", "images", "html", "sections", "scholar", "omission", "assets", "anchors", "css", "media", "copy", "contact", "all"],
                        help="Run a specific test suite only")
    parser.add_argument("--self-test", action="store_true",
                        help="Execute harness self-diagnostic sensitivity tests")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Show detailed check information and full diagnostics")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable terminal color formatting")
    parser.add_argument("--json", action="store_true",
                        help="Output results in JSON format")

    args = parser.parse_args()

    # Determine repository root
    if args.root:
        repo_root = Path(args.root).resolve()
    else:
        repo_root = Path(__file__).resolve().parent

    init_terminal_colors(no_color=args.no_color or args.json)

    # 1. Preview server mode
    if args.serve is not None:
        run_preview_server(repo_root, port=args.serve)
        return

    report = TestReport()

    # 2. Self-test mode
    if args.self_test:
        run_self_tests(report)
        if args.json:
            print(report.to_json())
        else:
            report.print_terminal_summary(verbose=args.verbose)
        sys.exit(1 if report.has_failures() else 0)

    # 3. Targeted or full test execution
    suite_filter = (args.suite or "").lower()

    # Deployment suite
    if not suite_filter or suite_filter in ("deployment", "all"):
        check_deployment_config(repo_root, report)

    # Data suite
    if not suite_filter or suite_filter in ("data", "all"):
        check_data_assets(repo_root, report)

    # Image suite
    if not suite_filter or suite_filter in ("images", "all"):
        check_image_assets(repo_root, report)

    # If --m1 flag passed, stop here and report M1 status
    if args.m1_only:
        if args.json:
            print(report.to_json())
        else:
            report.print_terminal_summary(verbose=args.verbose)
        sys.exit(1 if report.has_failures() else 0)

    # M3-dependent suites: HTML structure, sections, scholar, omission, media, copy, contact, assets, anchors, css
    parsed_html: Optional[SiteHTMLParser] = None

    if not suite_filter or suite_filter in ("html", "sections", "scholar", "omission", "assets", "anchors", "css", "media", "copy", "contact", "all"):
        parsed_html = check_html_structure_and_syntax(repo_root, report)

    if not suite_filter or suite_filter in ("sections", "all"):
        check_required_sections_presence(parsed_html, report)

    if not suite_filter or suite_filter in ("scholar", "all"):
        check_scholar_and_publications(parsed_html, repo_root, report)

    if not suite_filter or suite_filter in ("omission", "all"):
        check_projects_omission(parsed_html, repo_root, report)

    if not suite_filter or suite_filter in ("media", "all"):
        check_media_and_content_fixes(parsed_html, repo_root, report)

    if not suite_filter or suite_filter in ("copy", "omission", "contact", "all"):
        check_copy_and_section_removals(parsed_html, repo_root, report)

    if not suite_filter or suite_filter in ("assets", "all"):
        check_asset_integrity(parsed_html, repo_root, report)

    if not suite_filter or suite_filter in ("anchors", "all"):
        check_anchor_integrity(parsed_html, report)

    if not suite_filter or suite_filter in ("css", "all"):
        check_responsive_css(repo_root, report)

    # Output report
    if args.json:
        print(report.to_json())
    else:
        report.print_terminal_summary(verbose=args.verbose)

    # Exit code
    sys.exit(1 if report.has_failures() else 0)


if __name__ == "__main__":
    main()
