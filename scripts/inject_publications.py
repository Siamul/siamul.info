#!/usr/bin/env python3
"""
inject_publications.py
Injects the generated publications HTML and BibTeX modal into index.html.
"""

import sys
from pathlib import Path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root / 'scripts'))
from generate_publications_html import build_publications_html, get_bibtex_modal_html

def main():
    index_file = repo_root / 'index.html'
    html = index_file.read_text(encoding='utf-8')

    # 1. Generate the publications HTML block
    pubs_html = build_publications_html(repo_root)

    header_tag = '<h3 id="publications-heading" class="section-subheading">Publications:</h3>'
    start_idx = html.find(header_tag)
    if start_idx == -1:
        print('Error: publications-heading tag not found!')
        sys.exit(1)

    # Find the closing tag of section container before </section>
    end_search = '      </div>\n    </section>'
    if end_search not in html:
        end_search = '</div>\n    </section>'
    if end_search not in html:
        # Check CRLF
        end_search = '      </div>\r\n    </section>'

    end_idx = html.find(end_search, start_idx)
    if end_idx == -1:
        print('Error: end of research section not found!')
        sys.exit(1)

    new_research_content = header_tag + '\n\n' + pubs_html + '\n'
    html = html[:start_idx] + new_research_content + html[end_idx:]

    # 2. Add bibtex-modal if not already present
    if 'id="bibtex-modal"' not in html:
        modal_html = get_bibtex_modal_html()
        insert_before = '<!-- Volunteer Photo Lightbox Modal -->'
        if insert_before in html:
            html = html.replace(insert_before, modal_html + '\n\n  ' + insert_before)
        else:
            html = html.replace('</body>', modal_html + '\n</body>')

    index_file.write_text(html, encoding='utf-8')
    print('Successfully updated index.html with publications and BibTeX modal!')

if __name__ == '__main__':
    main()
