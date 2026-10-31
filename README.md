# Siamul Karim Khan — Personal Academic & Professional Website

[![Site Verification](https://img.shields.io/badge/verification-43%2F43%20passing-success.svg)](#local-verification--testing)
[![GitHub Pages](https://img.shields.io/badge/hosted%20on-GitHub%20Pages-blue.svg)](https://pages.github.com/)
[![Custom Domain](https://img.shields.io/badge/domain-www.siamul.info-teal.svg)](http://www.siamul.info)
[![Google Scholar](https://img.shields.io/badge/Google%20Scholar-4m76wqsAAAAJ-4285F4.svg)](https://scholar.google.com/citations?user=4m76wqsAAAAJ)
[![CI/CD Scholar Sync](https://img.shields.io/badge/CI%2FCD%20Sync-Weekly%20Sunday%2002%3A42%20UTC-0d9488.svg)](.github/workflows/update_scholar.yml)

A modern, fast, and responsive academic and professional portfolio website built to replace the previous Google Sites web presence at [www.siamul.info](http://www.siamul.info). The site is statically hosted on **GitHub Pages**, bound to the custom domain `www.siamul.info`, and features rich research publications integrated with **Google Scholar** via a **Decoupled CI/CD Caching Architecture with Monotonic Cache Validation** (GH-ScholarBot / al-folio pattern), structured career timelines, volunteer galleries, and creative media embeds.

Built entirely with **zero external runtime build dependencies** using semantic HTML5, modern CSS3 with custom properties, and vanilla ES6+ JavaScript.

---

## Table of Contents

1. [About Siamul Karim Khan](#about-siamul-karim-khan)
2. [Migrated Content & Architecture](#migrated-content--architecture)
3. [Decoupled Google Scholar CI/CD Architecture](#decoupled-google-scholar-cicd-architecture)
4. [Repository Structure](#repository-structure)
5. [GitHub Pages Deployment Guide](#github-pages-deployment-guide)
6. [Comprehensive DNS Configuration Guide (siamul.info)](#comprehensive-dns-configuration-guide-siamulinfo)
7. [Local Verification & Testing](#local-verification--testing)
8. [Automated Verification Suite](#automated-verification-suite)

---

## About Siamul Karim Khan

- **Current Position:** Software Engineer at **Google** (Sunnyvale, CA, USA).
- **Education:**
  - **Ph.D. in Computer Science and Engineering**, University of Notre Dame (2020 – 2026). Advised by Dr. Adam Czajka at the Computer Vision Research Laboratory (CVRL). GPA: 3.90 / 4.00.
  - **B.Sc. in Computer Science and Engineering**, Bangladesh University of Engineering and Technology (BUET) (2012 – 2017).
- **Core Research:** Computer Vision, Biometrics, Iris Recognition, Presentation Attack Detection (PAD), Generative Adversarial Networks (GANs), Diffusion Models, Synthetic Data Generation, and Deep Learning Security.
- **Academic Profiles:**
  - [Google Scholar Profile (user=4m76wqsAAAAJ)](https://scholar.google.com/citations?user=4m76wqsAAAAJ)
  - [ORCID: 0000-0001-5691-8599](https://orcid.org/0000-0001-5691-8599)
  - [Web of Science: JQJ-5066-2023](https://www.webofscience.com/wos/author/record/JQJ-5066-2023)
  - [LinkedIn](https://www.linkedin.com/in/siamulkarim/)
  - [GitHub](https://github.com/siamulkarim)

---

## Migrated Content & Architecture

All content from the original Google Sites website (`sites.google.com/view/siamul`) was extracted, restructured, and polished:

| Section | ID | Description |
|---|---|---|
| **Home / About** | `#about` | Hero banner, avatar portrait, affiliation badge, research summary, and CTA quick-actions. |
| **Education** | `#education` | Notre Dame Ph.D. and BUET B.Sc. with institutional logos, coursework, thesis topics, and honors. |
| **Research & Publications** | `#research` | Core interests, verified profile links, CI/CD telemetry overview, search/category filter pills, 13 semantic cards, and BibTeX drawer. |
| **Technical Skills** | `#skills` | Grouped skill chips covering languages, deep learning frameworks, databases, and embedded systems. |
| **Awards & Honors** | `#awards` | Chronological list of fellowships, national recognitions, and competitive conference travel awards. |
| **Curriculum Vitae** | `#cv` | Interactive CV overview, experience timelines, and direct link to PDF CV. |
| **Volunteer Experience** | `#volunteer` | Leadership roles in IEEE, student associations, and 16-photo responsive lightbox gallery. |
| **Music & Creative** | `#music` | Passion for acoustic music, live cover switcher, and embedded YouTube player. |
| **Contact Details** | `#contact` | Personal email (`siamulkarim@gmail.com`) with one-click copy, and LinkedIn link. |

---

## Decoupled Google Scholar CI/CD Architecture

Following the recommended architecture from academic web engineering (**GH-ScholarBot / al-folio pattern**), Google Scholar data retrieval is fully decoupled from page serving to bypass Google's strict browser framing (`X-Frame-Options: SAMEORIGIN`) and network-level bot mitigations (HTTP 429 / 403 / CAPTCHAs):

```
+--------------------------------------------------------------------------------+
|                        Weekly GitHub Actions Cron                              |
|                 (.github/workflows/update_scholar.yml)                         |
|                     Sundays at 02:42 UTC / Dispatch                            |
+--------------------------------------------------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
|                   Dual-Path Scholar Crawler (Python)                           |
|                      (scripts/scholar_crawler.py)                              |
|          Queries Google Scholar Profile: user=4m76wqsAAAAJ                     |
+--------------------------------------------------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
|                Monotonic Freshness & Schema Validation Gate                    |
|                      (scripts/publish_results.py)                              |
|          - Verifies all 5 JSON files conform to strict schemas                 |
|          - Enforces monotonic constraint: new >= cached                        |
|          - Blocks corrupted, empty, or rate-limited scrape results             |
+--------------------------------------------------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
|                  Version-Controlled Data Layer (assets/data/)                  |
|  - gs_data.json                    (Full Scholar metadata & 13 publications)   |
|  - gs_data_total_citation.json     (Shields.io live endpoint: Citations)       |
|  - gs_data_h_index.json            (Shields.io live endpoint: h-index)         |
|  - gs_data_i10_index.json          (Shields.io live endpoint: i10-index)       |
|  - gs_data_total_publications.json (Shields.io live endpoint: Publications)    |
+--------------------------------------------------------------------------------+
                                       |
                                       v
+--------------------------------------------------------------------------------+
|               Pre-rendered Semantic DOM Presentation (index.html)              |
|  - 100% SEO indexable for search engines (Googlebot / Google Scholar)          |
|  - 0ms initial page load latency (zero client-side scraping dependencies)      |
|  - Interactive search bar, category pills (All, Journal, Conf, Patent, etc.)   |
|  - Per-paper Google Scholar citation badges linking to citation views          |
|  - Progressive client-side hydration for instant dynamic updates               |
+--------------------------------------------------------------------------------+
```

### Manual Triggering & Local Updating
You can trigger the update workflow on GitHub via **Actions > Update Google Scholar Citations > Run workflow**, or run it locally from your workstation:
```bash
python scripts/scholar_crawler.py
python scripts/publish_results.py
```

---

## Repository Structure

```
siamul_personal_website/
├── .github/
│   └── workflows/
│       └── update_scholar.yml        # Weekly CI/CD Google Scholar update workflow
├── .nojekyll                         # Disables GitHub Pages Jekyll pipeline
├── 404.html                          # Branded custom 404 error page with Return Home CTA
├── CNAME                             # Custom domain binding: "www.siamul.info\n"
├── index.html                        # Single-page responsive portfolio (100% semantic SEO)
├── README.md                         # Deployment, DNS linking, and architecture guide
├── TEST_READY.md                     # Verification milestone checklist
├── verify_site.py                    # Automated test suite (43 checks) & local preview server
├── css/
│   └── styles.css                    # Academic navy design system, responsive breakpoints, dark mode
├── js/
│   └── main.js                       # Theme switcher, floating nav, publication filter, BibTeX modal
├── scripts/
│   ├── scholar_crawler.py            # Dual-path Google Scholar harvester
│   ├── publish_results.py            # Monotonic cache freshness and schema gate
│   ├── generate_publications_html.py # Static semantic HTML generator for publications
│   └── inject_publications.py        # DOM injector for pre-rendered publication cards
└── assets/
    ├── data/
    │   ├── profile.json              # Structured personal and career data
    │   ├── publications.json         # Canonical publication records
    │   ├── gs_data.json              # Decoupled Scholar profile & publication cache
    │   ├── gs_data_total_citation.json
    │   ├── gs_data_h_index.json
    │   ├── gs_data_i10_index.json
    │   └── gs_data_total_publications.json
    └── img/
        ├── avatar.jpg                # Profile portrait
        ├── favicon.png               # Monogram favicon
        ├── nd_logo.png               # University of Notre Dame crest
        ├── buet_logo.png             # BUET institutional crest
        └── volunteer/                # 16 volunteer event photographs
```

---

## GitHub Pages Deployment Guide

This repository is structured for direct deployment via GitHub Pages:

### Step 1: Push Repository to GitHub
```bash
cd siamul_personal_website
git init
git add .
git commit -m "Initial release of personal academic website"
git remote add origin https://github.com/<your-username>/<your-username>.github.io.git
git branch -M main
git push -u origin main
```

### Step 2: Configure GitHub Pages Settings
1. Navigate to your repository on GitHub: `https://github.com/<your-username>/<your-username>.github.io`.
2. Go to **Settings** > **Pages** (in the left sidebar).
3. Under **Build and deployment**:
   - **Source**: Select **Deploy from a branch**.
   - **Branch**: Select `main` / root (`/`). Click **Save**.
4. Under **Custom domain**:
   - Confirm `www.siamul.info` is detected from the `CNAME` file.
   - Check **Enforce HTTPS** (available after DNS propagation).

---

## Comprehensive DNS Configuration Guide (siamul.info)

Configure your DNS provider (e.g., Namecheap, Cloudflare, Google Domains, GoDaddy) as follows:

### 1. Apex Domain A Records (`@` / `siamul.info`)
Add four `A` records pointing to GitHub Pages' anycast IPs:

| Type | Host / Name | Value / Destination | TTL |
|---|---|---|---|
| `A` | `@` | `185.199.108.153` | Automatic / 300s |
| `A` | `@` | `185.199.109.153` | Automatic / 300s |
| `A` | `@` | `185.199.110.153` | Automatic / 300s |
| `A` | `@` | `185.199.111.153` | Automatic / 300s |

### 2. Subdomain CNAME Record (`www` / `www.siamul.info`)
Add a `CNAME` record pointing `www` to your GitHub Pages domain:

| Type | Host / Name | Value / Destination | TTL |
|---|---|---|---|
| `CNAME` | `www` | `<your-username>.github.io.` | Automatic / 300s |

---

## Local Verification & Testing

The repository includes a comprehensive, zero-dependency verification test suite (`verify_site.py`):

```bash
# Run all 43 automated verification checks
python verify_site.py

# Run verification harness self-diagnostics
python verify_site.py --self-test

# Launch local preview HTTP server at http://localhost:8000
python verify_site.py --serve --port 8000
```

---

## Automated Verification Suite

All **43 checks** across 12 test suites pass with 100% compliance:

- **Deployment & Domain Configuration (R4):** CNAME validation, `.nojekyll`, 404 page, and DNS documentation.
- **Structured Data Integrity:** Schema verification of profile and canonical publication data.
- **Image Assets Integrity:** Magic header verification across avatars, logos, and all 16 volunteer photos.
- **HTML Structure & Syntax:** Valid HTML5 DOCTYPE, meta tags, and accessibility attributes.
- **Required Sections Presence:** All 9 core sections confirmed in DOM.
- **Google Scholar & CI/CD Integration:** Decoupled weekly workflow, 5 JSON data artifacts, monotonic cache freshness gate, 13 semantic cards, and Scholar citation badges.
- **Strict Negative Assertions:** Projects tab omitted, Scholar iframe omitted, Notre Dame email omitted, Meta hyperlink omitted.
- **Media Embeds:** YouTube player seeded with single video ID (prevents Error 153).
- **Responsive CSS:** Fluid layouts, tablet/mobile breakpoints, dark mode tokens, and overflow prevention.
