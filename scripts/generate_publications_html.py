#!/usr/bin/env python3
"""
generate_publications_html.py
Generates the pre-rendered, semantic HTML for the Publications section in index.html
from assets/data/gs_data.json following the Decoupled CI/CD Caching architecture.
"""

import json
import html
import re
from pathlib import Path


def generate_bibtex(pub: dict) -> str:
    ptype = pub.get("type", "article")
    entry_type = "article"
    if ptype == "conference":
        entry_type = "inproceedings"
    elif ptype == "patent":
        entry_type = "misc"
    elif ptype == "thesis":
        entry_type = "phdthesis" if "phd" in pub.get("venue", "").lower() else "mastersthesis"
    elif ptype in ("preprint", "repository"):
        entry_type = "misc"

    pub_id = pub.get("id", "pub").replace("-", "_")
    key = f"khan_{pub.get('year', 2024)}_{pub_id[:8]}"

    author_list = []
    for a in pub.get("authors", []):
        parts = a.strip().split()
        if len(parts) > 1:
            author_list.append(f"{parts[-1]}, {' '.join(parts[:-1])}")
        else:
            author_list.append(a)
    authors_bib = " and ".join(author_list)

    title = pub.get("title", "")
    year = pub.get("year", "")
    venue = pub.get("venue", "")

    lines = [f"@{entry_type}{{{key},"]
    lines.append(f"  title = {{{title}}},")
    lines.append(f"  author = {{{authors_bib}}},")
    if entry_type == "inproceedings":
        lines.append(f"  booktitle = {{{venue}}},")
    elif entry_type == "article":
        lines.append(f"  journal = {{{venue}}},")
    elif entry_type in ("phdthesis", "mastersthesis"):
        lines.append(f"  school = {{{venue}}},")
    else:
        lines.append(f"  howpublished = {{{venue}}},")
    lines.append(f"  year = {{{year}}}")
    if pub.get("doi_url"):
        lines.append(f"  doi = {{{pub['doi_url']}}}")
    lines.append("}")
    return "\n".join(lines)


def format_authors(authors: list) -> str:
    formatted = []
    for a in authors:
        a_clean = a.strip()
        if "siamul" in a_clean.lower() and "khan" in a_clean.lower():
            formatted.append(f"<strong>{html.escape(a_clean)}</strong>")
        else:
            formatted.append(html.escape(a_clean))
    return ", ".join(formatted)


def classify_patent_status(venue_or_pub) -> str:
    """Classifies patent as 'Patent' if grant specifier (e.g., B1, B2) is present, or 'Pending Patent' if pending."""
    if isinstance(venue_or_pub, dict):
        text = f"{venue_or_pub.get('venue', '')} {venue_or_pub.get('venue_short', '')} {venue_or_pub.get('id', '')}"
    else:
        text = str(venue_or_pub or "")

    # Match standard patent grant kind codes (B1, B2, B3..B9) or US patent grant number formats (e.g. US 11,234,567 B2)
    # Must NOT match standalone 'B' (e.g. 'BIO-B', 'Section B', 'Table B')
    grant_regex = re.compile(r'\bB[1-9]\b|US\s*\d[\d,]*\s*B[1-9]|Publication\s*No\.?\s*US\s*\d+\s*B[1-9]', re.IGNORECASE)
    return "Patent" if bool(grant_regex.search(text)) else "Pending Patent"


def build_publications_html(repo_root: Path) -> str:
    gs_data_file = repo_root / "assets" / "data" / "gs_data.json"
    if not gs_data_file.exists():
        raise FileNotFoundError(f"Missing {gs_data_file}")

    with open(gs_data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    metrics = data.get("metrics", {"citations": 121, "h_index": 5, "i10_index": 4, "total_publications": 13})
    publications = data.get("publications", [])

    # Sort publications strictly chronologically descending
    publications = sorted(publications, key=lambda p: str(p.get("date", p.get("year", ""))), reverse=True)

    # Map publication type to filter category
    # categories: all, journal, conference, patent, preprint
    cat_counts = {"all": len(publications), "journal": 0, "conference": 0, "patent": 0, "preprint": 0}
    for p in publications:
        ptype = p.get("type", "other")
        if ptype == "repository":
            ptype = "preprint"
        if ptype in cat_counts:
            cat_counts[ptype] += 1

    out = []

    # 1. Telemetry / Scholar Hero Card
    out.append('        <!-- Google Scholar Telemetry Card (Decoupled CI/CD Caching Architecture) -->')
    out.append('        <div class="scholar-hero-card">')
    out.append('          <div class="scholar-hero-info">')
    out.append('            <div class="scholar-icon-bubble">')
    out.append('              <svg width="32" height="32" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">')
    out.append('                <path d="M12 24a7 7 0 1 1 0-14 7 7 0 0 1 0 14zm0-24L0 9.5l4.838 3.94A8 8 0 0 1 12 9a8 8 0 0 1 7.162 4.44L24 9.5z"/>')
    out.append('              </svg>')
    out.append('            </div>')
    out.append('            <div>')
    out.append('              <div style="display: flex; align-items: center; gap: 0.75rem; flex-wrap: wrap;">')
    out.append('                <h4 class="scholar-hero-title" style="margin: 0;">Google Scholar Profile</h4>')
    out.append('                <span class="scholar-user-badge">User ID: <strong>4m76wqsAAAAJ</strong></span>')
    out.append('              </div>')
    out.append('              <p style="color: var(--text-secondary); font-size: 0.95rem; margin: 0.35rem 0 0.5rem 0;">')
    out.append('                Synchronized weekly via automated decoupled CI/CD crawler with monotonic validation.')
    out.append('              </p>')
    out.append('              <div class="scholar-sync-badge">')
    out.append('                <span class="scholar-sync-dot"></span>')
    out.append('                <span>Decoupled CI/CD • Monotonic Cache Verified</span>')
    out.append('              </div>')
    out.append('            </div>')
    out.append('          </div>')
    out.append('')
    out.append('          <div class="scholar-metrics">')
    out.append('            <div class="metric-box">')
    out.append(f'              <span class="metric-value" id="metric-citations">{metrics["citations"]}</span>')
    out.append('              <span class="metric-label">Citations</span>')
    out.append('            </div>')
    out.append('            <div class="metric-box">')
    out.append(f'              <span class="metric-value" id="metric-hindex">{metrics["h_index"]}</span>')
    out.append('              <span class="metric-label">h-index</span>')
    out.append('            </div>')
    out.append('            <div class="metric-box">')
    out.append(f'              <span class="metric-value" id="metric-i10index">{metrics["i10_index"]}</span>')
    out.append('              <span class="metric-label">i10-index</span>')
    out.append('            </div>')
    out.append('            <div class="metric-box">')
    out.append(f'              <span class="metric-value" id="metric-pubs">{metrics["total_publications"]}</span>')
    out.append('              <span class="metric-label">Publications</span>')
    out.append('            </div>')
    out.append('          </div>')
    out.append('')
    out.append('          <div class="scholar-profile-action">')
    out.append('            <a href="https://scholar.google.com/citations?user=4m76wqsAAAAJ" target="_blank" rel="noopener noreferrer" class="btn btn-primary scholar-link-btn">')
    out.append('              <span>View Google Scholar Profile</span>')
    out.append('              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>')
    out.append('            </a>')
    out.append('          </div>')
    out.append('        </div>')
    out.append('')

    # 2. Controls: Search + Filter Pills
    out.append('        <!-- Publication Search & Filter Controls -->')
    out.append('        <div class="pub-controls">')
    out.append('          <div class="pub-search-wrapper">')
    out.append('            <svg class="pub-search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>')
    out.append('            <input type="text" id="pub-search" class="pub-search-input" placeholder="Search publications by title, author, venue, keyword, or year..." aria-label="Search publications">')
    out.append('          </div>')
    out.append('')
    out.append('          <div class="pub-filter-pills" role="tablist" aria-label="Publication category filters">')
    out.append(f'            <button class="pub-pill active" data-filter="all" role="tab" aria-selected="true">All <span class="pub-pill-count">{cat_counts["all"]}</span></button>')
    out.append(f'            <button class="pub-pill" data-filter="journal" role="tab" aria-selected="false">Journal <span class="pub-pill-count">{cat_counts["journal"]}</span></button>')
    out.append(f'            <button class="pub-pill" data-filter="conference" role="tab" aria-selected="false">Conference <span class="pub-pill-count">{cat_counts["conference"]}</span></button>')
    out.append(f'            <button class="pub-pill" data-filter="patent" role="tab" aria-selected="false">Patent <span class="pub-pill-count">{cat_counts["patent"]}</span></button>')
    out.append(f'            <button class="pub-pill" data-filter="preprint" role="tab" aria-selected="false">Preprint / Software <span class="pub-pill-count">{cat_counts["preprint"]}</span></button>')
    out.append('          </div>')
    out.append('        </div>')
    out.append('')

    # 3. Publications List Container
    out.append('        <!-- Semantic Publications List (Pre-rendered for 100% SEO Indexing) -->')
    out.append('        <div id="publications-list" class="publications-list">')

    for pub in publications:
        ptype = pub.get("type", "other")
        filter_cat = "preprint" if ptype == "repository" else ptype
        badge_class = f"badge-{filter_cat}"
        if ptype == "patent":
            cat_display = classify_patent_status(pub)
        else:
            cat_display = pub.get("category", ptype.title())
        citations = pub.get("citations", 0)
        scholar_url = pub.get("scholar_url")
        doi_url = pub.get("doi_url")
        pdf_url = pub.get("pdf_url")
        primary_link = doi_url or pdf_url or scholar_url or "#"
        bibtex_code = generate_bibtex(pub)
        escaped_bibtex = html.escape(bibtex_code, quote=True)

        out.append(f'          <article class="publication-card" data-category="{filter_cat}">')
        out.append('            <div class="pub-card-top">')
        out.append('              <div class="pub-badges-row">')
        out.append(f'                <span class="pub-year-badge">{pub.get("year", "")}</span>')
        out.append(f'                <span class="badge {badge_class}">{html.escape(cat_display)}</span>')
        out.append('              </div>')

        # Per-paper Google Scholar Citation Badge
        if scholar_url:
            out.append(f'              <a href="{scholar_url}" target="_blank" rel="noopener noreferrer" class="pub-citations-badge" title="View {citations} citations on Google Scholar">')
            out.append('                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d="M12 24a7 7 0 1 1 0-14 7 7 0 0 1 0 14zm0-24L0 9.5l4.838 3.94A8 8 0 0 1 12 9a8 8 0 0 1 7.162 4.44L24 9.5z"/></svg>')
            out.append(f'                <span>{citations} Citations</span>')
            out.append('              </a>')
        else:
            out.append('              <span class="pub-citations-badge" style="color: var(--text-muted); background-color: var(--bg-surface); border: 1px solid var(--border-color);">')
            out.append('                <span>BUET Archive</span>')
            out.append('              </span>')

        out.append('            </div>')
        out.append('')
        out.append(f'            <h4 class="pub-title"><a href="{primary_link}" target="_blank" rel="noopener noreferrer">{html.escape(pub.get("title", ""))}</a></h4>')
        out.append(f'            <p class="pub-authors">{format_authors(pub.get("authors", []))}</p>')
        out.append(f'            <p class="pub-venue">{html.escape(pub.get("venue", ""))}</p>')

        if pub.get("abstract"):
            out.append('            <details class="pub-abstract-details">')
            out.append('              <summary class="pub-abstract-summary">Abstract</summary>')
            out.append(f'              <p class="pub-abstract">{html.escape(pub.get("abstract"))}</p>')
            out.append('            </details>')

        out.append('            <div class="pub-actions">')
        if scholar_url:
            out.append(f'              <a href="{scholar_url}" target="_blank" rel="noopener noreferrer" class="pub-action-btn" title="View citation on Google Scholar">')
            out.append('                <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 24a7 7 0 1 1 0-14 7 7 0 0 1 0 14zm0-24L0 9.5l4.838 3.94A8 8 0 0 1 12 9a8 8 0 0 1 7.162 4.44L24 9.5z"/></svg>')
            out.append('                <span>Google Scholar</span>')
            out.append('              </a>')

        if pdf_url:
            out.append(f'              <a href="{pdf_url}" target="_blank" rel="noopener noreferrer" class="pub-action-btn" title="Download Open-Access PDF">')
            out.append('                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>')
            out.append('                <span>PDF</span>')
            out.append('              </a>')

        if doi_url:
            out.append(f'              <a href="{doi_url}" target="_blank" rel="noopener noreferrer" class="pub-action-btn" title="Publisher DOI link">')
            out.append('                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>')
            out.append('                <span>DOI / Publisher</span>')
            out.append('              </a>')

        out.append(f'              <button type="button" class="pub-action-btn btn-bibtex" data-bibtex="{escaped_bibtex}" title="View and copy BibTeX citation">')
        out.append('                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2"></path><rect x="8" y="2" width="8" height="4" rx="1" ry="1"></rect></svg>')
        out.append('                <span>BibTeX</span>')
        out.append('              </button>')
        out.append('            </div>')
        out.append('          </article>')

    out.append('        </div>')
    out.append('')
    out.append('        <div id="pub-empty-state" class="pub-empty-state" style="display: none;">')
    out.append('          <p>No publications match your search query or filter selection.</p>')
    out.append('        </div>')

    return "\n".join(out)


def get_bibtex_modal_html() -> str:
    return '''  <!-- BibTeX Citation Modal -->
  <div id="bibtex-modal" class="modal" aria-hidden="true" role="dialog" aria-labelledby="bibtex-modal-title">
    <div class="modal-content">
      <div class="modal-header">
        <h3 id="bibtex-modal-title" class="modal-title">BibTeX Citation</h3>
        <button id="bibtex-modal-close" class="modal-close-btn" aria-label="Close modal">&times;</button>
      </div>
      <pre id="bibtex-code" class="bibtex-code"></pre>
      <div class="modal-footer" style="display: flex; justify-content: flex-end; gap: 0.75rem;">
        <button id="bibtex-copy-btn" class="btn btn-primary" style="display: inline-flex; align-items: center; gap: 0.5rem;">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
          <span>Copy BibTeX</span>
        </button>
      </div>
    </div>
  </div>'''


if __name__ == "__main__":
    root = Path(__file__).resolve().parent.parent
    html_content = build_publications_html(root)
    print(f"Generated {len(html_content)} characters of Publications HTML.")
