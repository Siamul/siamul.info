# Siamul Karim Khan — Website Deployment & CI/CD Setup Guide

A production-grade, step-by-step operations guide for deploying and maintaining Siamul Karim Khan's academic portfolio website on **GitHub Pages** with custom domain routing (`www.siamul.info` and `siamul.info`) and automated **Google Scholar** metric updates via GitHub Actions.

---

## Table of Contents

1. [Overview & Architecture](#overview--architecture)
2. [Part 1: GitHub Repository Initialization & Pushing Local Code](#part-1-github-repository-initialization--pushing-local-code)
3. [Part 2: GitHub Pages Activation & Custom Domain Configuration](#part-2-github-pages-activation--custom-domain-configuration)
4. [Part 3: Comprehensive DNS Configuration Guide (`siamul.info`)](#part-3-comprehensive-dns-configuration-guide-siamulinfo)
5. [Part 4: Google Scholar CI/CD Workflow (`update_scholar.yml`)](#part-4-google-scholar-cicd-workflow-update_scholaryml)
6. [Part 5: Local Testing, Verification & Maintenance](#part-5-local-testing-verification--maintenance)
7. [Part 6: Troubleshooting & Common Pitfalls](#part-6-troubleshooting--common-pitfalls)

---

## Overview & Architecture

The website architecture follows the decoupled **GH-ScholarBot / al-folio** pattern designed for high-performance static delivery, rock-solid reliability, and zero maintenance overhead:

```
+-------------------------------------------------------------------------------+
|                                GitHub Pages CDN                               |
|                     (Anycast IPs + Let's Encrypt TLS)                         |
|                                                                               |
|   Apex: siamul.info (301 Redirect) ----> Subdomain: www.siamul.info           |
|                                                                               |
|   +-----------------------------------------------------------------------+   |
|   | Static Hosting Layer:                                                 |   |
|   | - index.html (semantic HTML5, pre-rendered publication cards for SEO) |   |
|   | - css/styles.css (responsive layout, dark mode tokens)                |   |
|   | - js/main.js (vanilla ES6+, async metric hydration, filter pills)     |   |
|   | - assets/data/*.json (decoupled JSON data artifacts)                  |   |
|   | - .nojekyll (bypasses Jekyll processing completely)                   |   |
|   | - 404.html (branded fallback page with Return Home CTA)               |   |
|   +-----------------------------------------------------------------------+   |
+---------------------------------------^---------------------------------------+
                                        |
                            git push origin main
                                        |
+---------------------------------------+---------------------------------------+
|                    GitHub Actions Automation Engine                           |
|               Workflow: .github/workflows/update_scholar.yml                  |
|               Schedule: Weekly Sunday at 02:42 UTC (cron: '42 2 * * 0')       |
|                                                                               |
|   1. scholar_crawler.py: Scrapes Google Scholar (ID: 4m76wqsAAAAJ)            |
|   2. publish_results.py: Monotonic freshness gate & schema validation        |
|   3. Conditional Commit: Commits & pushes to assets/data/ [skip ci]           |
+-------------------------------------------------------------------------------+
```

### Key Architectural Strengths

- **Zero Runtime Build Dependencies**: Pure HTML5, modern CSS3, and vanilla ES6+ JavaScript. No Node.js build step, Webpack, Hugo, Jekyll, or Astro compiler required at deployment time.
- **Pre-rendered Publication Cards**: All publication entries are pre-rendered into `index.html` via Python templating (`scripts/generate_publications_html.py`), ensuring 100% search engine indexability and instant First Contentful Paint (FCP).
- **Client-Side Live Hydration**: `js/main.js` asynchronously fetches `assets/data/gs_data.json` to hydrate citation counters in real time without blocking UI rendering.
- **Decoupled Anti-Corruption Pipeline**: Automated weekly crawling is isolated in CI/CD with a strict monotonic gate (`scripts/publish_results.py`). Transient Google CAPTCHAs or HTTP 429 errors can **never** wipe or corrupt clean cached data on the live website.

---

## Part 1: GitHub Repository Initialization & Pushing Local Code

Follow these steps to initialize and push your local codebase to a remote GitHub repository.

### Step 1.1: Verify Local Git State

Open PowerShell or terminal in the repository root directory:

```bash
cd c:\Antigravity\siamul_personal_website
git status
```

Confirm that the local branch is `main`. If git reports `On branch master` or no branch, rename/switch to `main`:

```bash
git branch -M main
```

### Step 1.2: Create Remote Repository on GitHub

1. Log into your GitHub account at [https://github.com](https://github.com).
2. Click the **+** (plus icon) in the top right corner and select **New repository**.
3. Fill in the repository details:
   - **Repository name**: `siamul_personal_website` (or `<your-username>.github.io` if configuring as a personal root site).
   - **Description**: `Personal academic website and research portfolio of Siamul Karim Khan`.
   - **Visibility**: **Public** *(Important: GitHub Pages custom domains on personal free accounts require public repositories; private repositories require a GitHub Pro/Team subscription)*.
4. **CRITICAL**: Under *"Initialize this repository with"*, leave all checkboxes unchecked:
   - ❌ Do **NOT** add a README file.
   - ❌ Do **NOT** add `.gitignore`.
   - ❌ Do **NOT** choose a license.
   *(Leaving these empty prevents branch divergence and merge conflicts on initial push).*
5. Click **Create repository**.

### Step 1.3: Connect Remote and Push Codebase

Back in your local terminal, add the remote origin and push the entire codebase to GitHub:

```bash
# Add all files to staging
git add .

# Create initial commit
git commit -m "Initial release of personal academic portfolio website"

# Associate your local repository with the GitHub remote
# Replace <your-username> with your actual GitHub username (e.g., siamulkarim)
git remote add origin https://github.com/<your-username>/siamul_personal_website.git

# Push main branch and set upstream tracking
git push -u origin main
```

Verify that all files, including `.github/workflows/update_scholar.yml`, `CNAME`, `.nojekyll`, and `assets/data/`, are visible on GitHub.

---

## Part 2: GitHub Pages Activation & Custom Domain Configuration

Once your code is pushed to GitHub, activate GitHub Pages and bind your custom domain `www.siamul.info`.

### Step 2.1: Navigate to Repository Pages Settings

1. Open your repository on GitHub: `https://github.com/<your-username>/siamul_personal_website`.
2. Click the **Settings** tab located in the top repository navigation bar.
3. In the left-hand sidebar under **"Code and automation"**, click **Pages**.

### Step 2.2: Configure Build and Deployment Source

1. Under **"Build and deployment"**:
   - **Source**: Select **"Deploy from a branch"** from the dropdown menu.
   - **Branch**: Select **`main`** from the branch dropdown.
   - **Folder**: Select **`/ (root)`** from the folder dropdown.
2. Click **Save**.
3. *Note on `.nojekyll`*: The repository root already includes a 0-byte `.nojekyll` file. This tells GitHub Pages to bypass Jekyll processing entirely, ensuring directories with underscores and static JSON files in `assets/data/` are served without modification.

### Step 2.3: Custom Domain Detection & Verification

1. Scroll down to the **"Custom domain"** section on the Pages settings page.
2. Notice that **`www.siamul.info`** is automatically populated.
   - *Why?* The repository includes a `CNAME` file at the root containing `www.siamul.info\n`. GitHub Pages automatically reads this file.
   - If the field is blank for any reason, manually enter `www.siamul.info` and click **Save**.
3. GitHub Pages will initiate an automated DNS verification check:
   - A yellow banner will appear: `DNS check in progress`.
   - Once DNS records (configured in Part 3) have propagated, the banner will update to green: `DNS check successful`.

### Step 2.4: TLS Certificate Provisioning & HTTPS Enforcement

1. After DNS verification passes, GitHub Pages automatically requests a free TLS/SSL certificate from **Let's Encrypt** for both `www.siamul.info` and `siamul.info`.
2. This certificate issuance typically completes within 5 to 30 minutes.
3. During certificate provisioning, the checkbox **"Enforce HTTPS"** will remain grayed out with a message: `Unavailable for your site because your domain is not properly configured to support HTTPS` or `Certificate is being issued`.
4. Refresh the page after 15–30 minutes until the checkbox becomes enabled.
5. **Check the "Enforce HTTPS" box**.
6. All traffic arriving on unencrypted HTTP (port 80) will now automatically receive an HTTP 301 Permanent Redirect to secure HTTPS (port 443).

---

## Part 3: Comprehensive DNS Configuration Guide (`siamul.info`)

To direct web traffic to GitHub Pages and enable automatic apex-to-subdomain redirection, configure the following DNS records at your domain registrar or DNS management service (such as Namecheap, Cloudflare, GoDaddy, or Google Domains/Squarespace).

### 3.1: Apex Domain IPv4 Anycast A Records (`@` / `siamul.info`)

Add four `A` records for the apex domain (`@` or `siamul.info`). These point directly to GitHub Pages' globally distributed Anycast server fleet:

| Record Type | Host / Name | Target / IP Address | TTL | Purpose |
|---|---|---|---|---|
| `A` | `@` | `185.199.108.153` | 300s (or Auto) | GitHub Pages Anycast Node 1 |
| `A` | `@` | `185.199.109.153` | 300s (or Auto) | GitHub Pages Anycast Node 2 |
| `A` | `@` | `185.199.110.153` | 300s (or Auto) | GitHub Pages Anycast Node 3 |
| `A` | `@` | `185.199.111.153` | 300s (or Auto) | GitHub Pages Anycast Node 4 |

### 3.2: Subdomain CNAME Record (`www` / `www.siamul.info`)

Add one `CNAME` record for the `www` subdomain pointing to your GitHub Pages host domain:

| Record Type | Host / Name | Target / Value | TTL | Purpose |
|---|---|---|---|---|
| `CNAME` | `www` | `<your-username>.github.io.` | 300s (or Auto) | Routes `www` to GitHub Pages CDN |

*(Example: If your GitHub username is `siamulkarim`, the Target is `siamulkarim.github.io.`). Note: Some DNS providers require a trailing dot (`.`), while others do not.*

### 3.3: Apex Domain IPv6 Anycast AAAA Records (`@` / `siamul.info`)

For complete dual-stack IPv4/IPv6 support, add four `AAAA` records pointing the apex domain to GitHub Pages' IPv6 Anycast addresses:

| Record Type | Host / Name | Target / IPv6 Address | TTL | Purpose |
|---|---|---|---|---|
| `AAAA` | `@` | `2606:50c0:8000::153` | 300s (or Auto) | GitHub Pages IPv6 Node 1 |
| `AAAA` | `@` | `2606:50c0:8001::153` | 300s (or Auto) | GitHub Pages IPv6 Node 2 |
| `AAAA` | `@` | `2606:50c0:8002::153` | 300s (or Auto) | GitHub Pages IPv6 Node 3 |
| `AAAA` | `@` | `2606:50c0:8003::153` | 300s (or Auto) | GitHub Pages IPv6 Node 4 |

### 3.4: DNS Verification Commands

To verify that your DNS records have successfully propagated globally, run the following commands:

#### On Linux / macOS / Git Bash:

```bash
# 1. Verify apex domain A records (must return all 4 GitHub IPs)
dig +noall +answer siamul.info A

# 2. Verify subdomain CNAME record (must return <username>.github.io)
dig +noall +answer www.siamul.info CNAME

# 3. Verify IPv6 AAAA records
dig +noall +answer siamul.info AAAA

# 4. Inspect HTTP to HTTPS redirection
curl -IL http://siamul.info

# 5. Inspect TLS certificate issuance and HTTPS response
curl -Iv https://www.siamul.info
```

#### On Windows PowerShell:

```powershell
# 1. Verify apex domain A records
Resolve-DnsName -Name siamul.info -Type A | Select-Object Name, IPAddress

# 2. Verify subdomain CNAME record
Resolve-DnsName -Name www.siamul.info -Type CNAME | Select-Object Name, NameHost

# 3. Verify HTTPS response
Invoke-WebRequest -Uri "https://www.siamul.info" -Method Head
```

### 3.5: Provider-Specific Configuration Guidelines

- **Cloudflare**:
  - **CRITICAL**: In the Cloudflare dashboard under **SSL/TLS** > **Overview**, set the encryption mode to **"Full"** or **"Full (strict)"**.
  - **DO NOT** use **"Flexible"** — doing so creates an infinite redirect loop (`ERR_TOO_MANY_REDIRECTS`) because Cloudflare connects to GitHub Pages via HTTP while GitHub Pages demands HTTPS.
  - For the initial Let's Encrypt certificate challenge, set the proxy status for `@` and `www` to **DNS Only** (grey cloud). After HTTPS is verified and active on GitHub, you may re-enable proxying (orange cloud) if desired.
- **Namecheap**:
  - In Domain List > Manage > **Advanced DNS**:
  - Remove existing "URL Redirect" or default parking records.
  - Add 4 `A Record` entries with Host `@` and the four GitHub IPs.
  - Add 1 `CNAME Record` with Host `www` and Target `<your-username>.github.io.`.
- **GoDaddy**:
  - In DNS Management:
  - Add 4 `A` records pointing `@` to the four GitHub IPs.
  - Add or edit `CNAME` for `www` pointing to `<your-username>.github.io`.
  - Delete any forwarding rules that conflict with apex DNS records.

---

## Part 4: Google Scholar CI/CD Workflow (`update_scholar.yml`)

The repository includes an automated GitHub Actions workflow at `.github/workflows/update_scholar.yml` that keeps Google Scholar citation counts, publication lists, and Shields.io badge endpoints up to date.

### 4.1: Workflow Mechanics & Automation Schedule

- **Workflow File**: `.github/workflows/update_scholar.yml`
- **Execution Triggers**:
  1. **Weekly Scheduled Cron**: `cron: '42 2 * * 0'` (runs every Sunday at 02:42 UTC).
     - *Why 02:42 UTC?* Running at a non-round minute avoids top-of-the-hour runner queue spikes on GitHub's infrastructure.
  2. **Manual Trigger (`workflow_dispatch`)**: Enables on-demand one-click runs from the GitHub Actions tab whenever you want to update metrics immediately.
  3. **Script Path Push Trigger**: Automatically runs whenever changes are pushed to `scripts/scholar_crawler.py`, `scripts/publish_results.py`, or `.github/workflows/update_scholar.yml`.
- **Pipeline Stages**:
  ```
  [Checkout Repo] -> [Setup Python 3.11] -> [scholar_crawler.py] -> [publish_results.py] -> [git commit & push]
  ```
  - **Step 1**: Check out repository using `actions/checkout@v4` with `fetch-depth: 0`.
  - **Step 2**: Initialize Python environment with `actions/setup-python@v5` (`python-version: '3.11'`).
  - **Step 3**: Execute `python scripts/scholar_crawler.py` to harvest profile `4m76wqsAAAAJ` and output JSON files in `assets/data/`.
  - **Step 4**: Execute `python scripts/publish_results.py` to validate schemas and enforce monotonic non-decreasing metric checks.
  - **Step 5**: If changes exist in `assets/data/`, commit using identity `GitHub Action [ScholarBot]` (`action@github.com`) with message `[ci] update google scholar citations and publications [skip ci]` and push to `origin main`. If no diff, exit cleanly.

### 4.2: CRITICAL: GitHub Actions Repository Permissions

By default, GitHub restricts `GITHUB_TOKEN` permissions for newly created repositories to **Read-only**. If this setting is not adjusted, the workflow will fail at the `git push origin main` step with:

```
fatal: unable to access 'https://github.com/<username>/siamul_personal_website.git/': The requested URL returned error: 403
```

#### How to Enable Read and Write Permissions:

1. Open your repository on GitHub.
2. Click **Settings** in the top navigation bar.
3. In the left sidebar under **"Actions"**, click **General**.
4. Scroll down to the **"Workflow permissions"** section.
5. Select the radio button: **"Read and write permissions"** *(Workflows have read and write permissions in the repository for all scopes)*.
6. Check the box: **"Allow GitHub Actions to create and approve pull requests"**.
7. Click **Save**.

```
+-------------------------------------------------------------------------------+
|  Settings > Actions > General > Workflow permissions                          |
|                                                                               |
|  ( ) Read repository contents and packages permissions                        |
|  (*) Read and write permissions                                 <-- SELECT    |
|      Workflows have read and write permissions in the                         |
|      repository for all scopes.                                               |
|                                                                               |
|  [x] Allow GitHub Actions to create and approve pull requests    <-- CHECK    |
+-------------------------------------------------------------------------------+
```

*Note on workflow YAML declaration*: The workflow file `.github/workflows/update_scholar.yml` already explicitly includes:
```yaml
permissions:
  contents: write
```
However, the repository-level setting in **Settings > Actions > General** acts as an administrative security gate. The workflow-level declaration can only grant permissions up to the limit allowed by the repository policy. Both must allow write access.

### 4.3: Secrets Management

- **Zero Secrets Required**: The workflow does **not** require any API keys, credentials, or custom repository secrets in **Settings > Secrets and variables > Actions**.
  - Google Scholar profile harvesting uses public HTTP GET requests without authentication.
  - Git authentication during `git push origin main` is handled natively by the runner's ephemeral `GITHUB_TOKEN`.
- **Enterprise Policy Alternative**: If an institutional organization policy enforces strict read-only tokens across all repositories, create a Personal Access Token (classic) with `repo` scope, add it as a repository secret named `GH_PAT`, and modify the checkout step in `update_scholar.yml` as follows:
  ```yaml
  - name: Checkout repository
    uses: actions/checkout@v4
    with:
      fetch-depth: 0
      token: ${{ secrets.GH_PAT }}
  ```

### 4.4: Manual Execution & Run Verification

To manually trigger and verify the workflow at any time:

1. Go to your repository on GitHub and click the **Actions** tab.
2. In the left-hand workflow list, click **"Update Google Scholar Publications & Citations"**.
3. Click the **"Run workflow"** button on the right side of the screen.
4. Select branch **`main`** and click the green **"Run workflow"** button.
5. Wait a few seconds for the run to appear, then click into the run to view live execution logs:
   - `Crawl Google Scholar Profile & Citations`: Look for `Live parse success: ... 13 papers`.
   - `Enforce Monotonic Freshness & Schema Gate`: Look for `ALL GATES PASSED: Data files are verified and ready for deployment.`
   - `Commit and push if citations or publications changed`: Either commits changes with `[skip ci]` or outputs `No changes in Google Scholar citation metrics or publications.`

---

## Part 5: Local Testing, Verification & Maintenance

You can run the full suite of crawler, generator, and verification scripts locally on your workstation.

### 5.1: Automated Verification Suite (`verify_site.py`)

The repository includes a comprehensive, zero-external-dependency verification engine (`verify_site.py`):

```bash
# Run all automated verification checks
python verify_site.py

# Run test harness self-diagnostics
python verify_site.py --self-test

# Launch local preview server at http://localhost:8000
python verify_site.py --serve --port 8000
```

### 5.2: Running the Crawler and Monotonic Gate Locally

To refresh Scholar data locally before pushing:

```bash
# 1. Scrape Google Scholar and generate data artifacts in assets/data/
python scripts/scholar_crawler.py

# 2. Validate schemas and test against baseline thresholds
python scripts/publish_results.py
```

### 5.3: Adding New Curated Publications & Updating Pre-Rendered Cards

When you have a new accepted paper, patent, or preprint:

1. **Add Curated Metadata**: Open `assets/data/publications.json` and add a new JSON entry with `title`, `authors`, `venue`, `year`, `date` (`YYYY-MM-DD`), `type` (`journal`, `conference`, `patent`, or `preprint`), `abstract`, `doi`, `pdf`, etc.
2. **Sort Chronologically**: Ensure entries in `publications.json` remain sorted by `date` descending (newest first).
3. **Re-crawl and Merge**:
   ```bash
   python scripts/scholar_crawler.py
   python scripts/publish_results.py
   ```
4. **Re-generate Semantic HTML Cards**:
   ```bash
   python scripts/generate_publications_html.py
   ```
5. **Inject into `index.html`**:
   ```bash
   python scripts/inject_publications.py
   ```
6. **Verify and Commit**:
   ```bash
   python verify_site.py
   git add assets/data/ index.html
   git commit -m "feat(publications): add new publication <title>"
   git push origin main
   ```

---

## Part 6: Troubleshooting & Common Pitfalls

### Pitfall 1: GitHub Action Fails with HTTP 403 Forbidden on Push

- **Symptom**: Step `Commit and push if citations or publications changed` in GitHub Actions fails with:
  `fatal: unable to access 'https://github.com/...': The requested URL returned error: 403`
- **Root Cause**: Repository settings restrict the default `GITHUB_TOKEN` to Read-Only access.
- **Solution**: Follow [Step 4.2](#42-critical-github-actions-repository-permissions). Navigate to **Settings > Actions > General > Workflow permissions**, select **"Read and write permissions"**, check **"Allow GitHub Actions to create and approve pull requests"**, and click **Save**.

---

### Pitfall 2: "Enforce HTTPS" Checkbox is Grayed Out / Disabled

- **Symptom**: In **Settings > Pages**, the **"Enforce HTTPS"** checkbox cannot be checked, showing `Unavailable for your site because your domain is not properly configured to support HTTPS`.
- **Root Cause**: DNS propagation is still underway, or Let's Encrypt has not finished validating the domain challenge.
- **Solution**:
  1. Confirm your DNS records match [Part 3](#part-3-comprehensive-dns-configuration-guide-siamulinfo).
  2. Run `dig +noall +answer www.siamul.info CNAME` and ensure it resolves to `<your-username>.github.io`.
  3. Wait 15–45 minutes for global DNS caches and the Let's Encrypt challenge to complete.
  4. Refresh GitHub Pages settings; the checkbox will unlock once the certificate is installed.

---

### Pitfall 3: Cloudflare Infinite Redirect Loop (`ERR_TOO_MANY_REDIRECTS`) or 525 Error

- **Symptom**: Visiting `https://www.siamul.info` returns browser error `ERR_TOO_MANY_REDIRECTS` or Cloudflare Error 525 (SSL Handshake Failed).
- **Root Cause**: Cloudflare SSL/TLS mode is set to **"Flexible"**. In Flexible mode, Cloudflare connects to GitHub Pages over unencrypted HTTP (port 80). GitHub Pages detects an unencrypted connection and responds with a 301 redirect to HTTPS (port 443). Cloudflare receives this redirect and repeats the loop indefinitely.
- **Solution**:
  1. In the Cloudflare dashboard, navigate to **SSL/TLS** > **Overview**.
  2. Change encryption mode from **Flexible** to **"Full"** or **"Full (strict)"**.
  3. Alternatively, in **DNS > Records**, toggle the Proxy Status for `@` and `www` from Proxied (Orange Cloud) to **DNS Only** (Grey Cloud).

---

### Pitfall 4: Google Scholar Rate Limiting (CAPTCHA or HTTP 429)

- **Symptom**: During automated or local crawling, output displays `Warning: Live fetch failed` or `Google Scholar returned CAPTCHA or blocking response`.
- **Root Cause**: Google Scholar periodically throttles scrapers or requests a CAPTCHA verification.
- **Graceful Behavior & Safeguards**:
  - `scholar_crawler.py` detects CAPTCHA responses and immediately falls back to clean curated baseline metrics in `assets/data/publications.json`.
  - `publish_results.py` acts as a firewall: if metrics are empty or zeroed, the monotonic gate rejects the run and exits with code 1 or 2.
  - In GitHub Actions, a rejected gate stops the workflow **before** any commit occurs, preserving clean existing data on your website. No user action is required; the workflow will retry on the next weekly schedule.

---

### Pitfall 5: Monotonic Metric Decrease Gate Failure (`publish_results.py` Exit Code 2)

- **Symptom**: `publish_results.py` fails with:
  `[gate] REJECT: Scrape rejected by monotonic gate! Metric decrease detected: ...`
- **Root Cause**: Google Scholar occasionally merges/un-merges duplicate citations, recalculating an author's metrics slightly downward.
- **Solution**:
  If you have verified that the decrease on Google Scholar is legitimate and not a transient error:
  ```bash
  # Run publish_results with the --force flag to override the monotonic check
  python scripts/publish_results.py --force
  ```
  Commit and push the updated baseline. Subsequent runs will use the new baseline.

---

### Pitfall 6: Apex Domain (`siamul.info`) Does Not Redirect to Subdomain (`www.siamul.info`)

- **Symptom**: `https://www.siamul.info` works, but typing `http://siamul.info` times out or fails to load.
- **Root Cause**: One or more of the 4 Anycast `A` records on `@` are missing, or conflicting default registrar parking records are still active.
- **Solution**:
  1. Verify all 4 `A` records (`185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`) exist under Host `@`.
  2. Ensure the `CNAME` file in your repository contains exactly `www.siamul.info\n`. GitHub Pages uses the presence of `www.siamul.info` in `CNAME` to configure automated apex-to-subdomain forwarding.

---

### Pitfall 7: `CNAME` File Formatting & Line Ending Warnings

- **Symptom**: `python verify_site.py` warns:
  `CNAME text is 'www.siamul.info' but byte format is ... (expected b'www.siamul.info\n')`
- **Root Cause**: Windows Git checkout converted the Unix line feed (`\n`) to Windows CRLF (`\r\n`), or a text editor introduced trailing spaces.
- **Solution**:
  Keep the file exactly 16 bytes:
  ```bash
  python -c "open('CNAME', 'wb').write(b'www.siamul.info\n')"
  ```

---

### Pitfall 8: Certificate Authority Authorization (CAA) DNS Record Blocks

- **Symptom**: GitHub Pages reports `TLS certificate could not be issued` even though DNS records resolve correctly.
- **Root Cause**: Your domain registrar has CAA records restricting which Certificate Authorities can issue certificates, and Let's Encrypt is not authorized.
- **Solution**:
  In your DNS manager, add a CAA record authorizing Let's Encrypt:
  | Type | Host / Name | Tag | Value | TTL |
  |---|---|---|---|---|
  | `CAA` | `@` | `issue` | `letsencrypt.org` | 300s |

---

*Document Author: Siamul Karim Khan Portfolio Automation Team*  
*Repository: `siamul_personal_website`*  
*Last Verified: 2026-10-31*
