# CampAnalytics

An analytics platform for Wikimedia Commons photography campaigns, providing longitudinal contributor retention metrics, cross-campaign ecosystem influx, and regional health benchmarking.

[![Hosted on Wikimedia Toolforge](https://img.shields.io/badge/Hosted%20on-Wikimedia%20Toolforge-006699?style=flat-square&logo=wikipedia)](https://campanalytics.toolforge.org/)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://campanalytics.streamlit.app/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg?style=flat-square)](https://www.python.org/downloads/)
[![License: GPL-2.0+](https://img.shields.io/badge/License-GPL--2.0%2B-blue.svg?style=flat-square)](https://www.gnu.org/licenses/gpl-2.0.html)
[![Affiliation: Project Korikath](https://img.shields.io/badge/Affiliation-Project%20Korikath-183f54?style=flat-square)](https://meta.wikimedia.org/wiki/Project_Korikath)

---

## Live Deployments

CampAnalytics is accessible through two web deployments:

| Platform | URL | Description |
|:---|:---|:---|
| **Wikimedia Toolforge** | [campanalytics.toolforge.org](https://campanalytics.toolforge.org/) | Production Flask application running in the Wikimedia ecosystem |
| **Streamlit Community Cloud** | [campanalytics.streamlit.app](https://campanalytics.streamlit.app/) | Interactive dashboard with reactive filters and exploratory charts |

Both interfaces use the shared core analytics engine ([`analytics.py`](analytics.py)).

---

## Overview

**CampAnalytics** is an open-source analytics platform for campaign organizers, program evaluators, and Wikimedia community leaders. It analyzes international Wiki Loves photography campaigns by querying live metadata directly from Wikimedia Commons and Toolforge replica databases.

### Supported Campaigns

| Code | Campaign | Focus | Commons Category Pattern |
|:---|:---|:---|:---|
| `wlm` | Wiki Loves Monuments | Built and architectural cultural heritage | `Images_from_Wiki_Loves_Monuments_YYYY_in_Country` |
| `wle` | Wiki Loves Earth | Natural heritage and protected areas | `Images_from_Wiki_Loves_Earth_YYYY_in_Country` |
| `wlf` | Wiki Loves Folklore | Intangible culture, traditions, and festivals | `Images_from_Wiki_Loves_Folklore_YYYY_in_Country` |
| `wla` | Wiki Loves Africa | African cultural heritage and daily life | `Images_from_Wiki_Loves_Africa_YYYY_in_Country` |
| `wlb` | Wiki Loves Bangla | Regional cultural and biodiversity heritage | `Images_from_Wiki_Loves_Bangla_YYYY` |
| `all` | All Campaigns | Ecosystem combination per country | Scoped aggregate across active campaigns for the target country |

### Core Evaluation Questions

1. **Ecosystem Vitality**: How healthy is a campaign edition relative to regional peers?
2. **Contributor Continuity**: How effectively do campaigns retain participant cohorts across consecutive editions?
3. **True Newcomer Influx**: How many new contributors entered the movement across all national campaigns in a given year?
4. **Encyclopedic Utility**: How frequently are uploaded media files integrated into Wikipedia articles and sister projects?
5. **Quality Recognition**: What proportion of submissions achieve formal curatorial recognition (Quality Images, Featured Pictures, Valued Images)?

---

## Features

### 1. Health Evaluation (`/health`)

Scores campaign editions on a 0–100 scale across five dimensions grouped into three pillars, benchmarked against regional reference thresholds:

| Dimension | Weight | Pillar | Measurement Focus |
|:---|:---:|:---|:---|
| **Retention Index** ($S_{\text{ret}}$) | **25%** | Community Vitality (50%) | Percentage of prior-edition participants who returned |
| **Growth Capacity** ($S_{\text{grow}}$) | **25%** | Community Vitality (50%) | Proportion of participants joining for the first time |
| **Content Utility** ($S_{\text{util}}$) | **20%** | Content Impact (35%) | Files embedded in Wikimedia projects (`prop=globalusage`) |
| **Quality Recognition** ($S_{\text{qual}}$) | **15%** | Content Impact (35%) | Share of uploads designated as QI, FP, or VI on Commons |
| **Contributor Diversity** ($S_{\text{div}}$) | **15%** | Participation Equity (15%) | Upload distribution equity (inverse top-10% uploader concentration) |

**Rating Tiers**:
- ★★★★★ **Outstanding** (85.0–100.0) — Exceeds regional and global benchmarks
- ★★★★☆ **Strong** (70.0–84.9) — Meets or exceeds regional expectations
- ★★★☆☆ **Moderate** (50.0–69.9) — Stable fundamentals with room for growth
- ★★☆☆☆ **Emerging** (30.0–49.9) — Early-stage baseline requiring strategic focus
- ★☆☆☆☆ **Critical** (0.0–29.9) — Low retention or high contributor concentration

### 2. Retention Analytics (`/retention`)

- **Cohort Selection**: Build comparative matrices across events, countries, and years (e.g., `wlmde22`, `wlmbd24`).
- **Directional Persistence**: Calculates exact retention between baseline and target editions ($A \to B$).
- **Visualizations**: Interactive sortable data tables, pairwise Seaborn heatmaps, and global choropleth maps with regional filtering.

### 3. Contributor Influx & Growth (`/influx`)

- **Longitudinal Tracking**: Analyzes annual participation sequences from 2010 to 2040.
- **Single-Campaign vs. Ecosystem Deduplication**:
  - *Single Campaign*: Tracks consecutive editions of a single contest (e.g., `wlmde20` $\to$ `wlmde24`).
  - *All Campaigns (`all[cc][YY]`)*: Deduplicates participants across all contests in a country to isolate true newcomer acquisition from inter-campaign movement.
- **Cohort Categorization**: Segments contributors into 1-time entrants, repeaters (2–3 editions), and core veterans (4+ editions).
- **Trajectory Visuals**: Dual-axis stacked charts showing annual newcomers ($I_t$), returning contributors ($R_t$), and cumulative participant pool ($P_t$).

### 4. Content Utility (`/utility`)

- **Cross-Wiki Deployment**: Queries the Commons Action API (`prop=globalusage`) to measure file usage across Wikipedia language editions, Wikidata, Wikivoyage, and Commons galleries.
- **Output Metrics**: Global reuse rate, total article inclusions, project-level distribution, and contributor-level utilization rankings.

### 5. Quality Recognition (`/quality`)

- **Peer-Reviewed Status**: Audits uploads for community quality badges:
  - **Quality Images (QI)**: Technical image quality validated by Commons reviewers.
  - **Featured Pictures (FP)**: High-caliber images selected by community consensus.
  - **Valued Images (VI)**: Canonical subject-matter reference images.
- **Galleries & Exports**: Thumbnail gallery with photographer attribution, direct Commons links, and exportable data (CSV, Wikitext, JSON).

---

## Methodology & Mathematical Models

Detailed mathematical formulations and proofs are available in [METHODOLOGY.md](METHODOLOGY.md). Key formulations include:

### 1. Directional Contributor Retention
$$\text{Retention}(A \to B) = \left( \frac{|U_A \cap U_B|}{|U_A|} \right) \times 100\%$$
*Note: $\text{Retention}(A \to B) \neq \text{Retention}(B \to A)$ when cohort sizes differ.*

### 2. Contributor Growth Capacity
$$\text{Growth}(A \to B) = \left( \frac{|U_B \setminus U_A|}{|U_B|} \right) \times 100\%$$

### 3. Longitudinal & Ecosystem Influx
For consecutive cohorts $(U_1, U_2, \dots, U_T)$ (or country-scoped ecosystem sets $U_t = \bigcup_{e \in E_{cc}} U_{e,t}$):
- **New Influx**: $I_t = \left| U_t \setminus \bigcup_{j < t} U_j \right|$
- **Returning**: $R_t = \left| U_t \cap \bigcup_{j < t} U_j \right|$
- **Cumulative Pool**: $P_t = \left| \bigcup_{j \le t} U_j \right|$

### 4. Continuous Relative Utility Curve
Dimension metrics ($x$) map against regional benchmark ($B$) via a concave utility curve:
$$S(x, B) = \begin{cases} 0.0 & \text{if } x \le 0 \\ 70.0 \times \left(\frac{x}{B}\right)^{0.75} & \text{if } 0 < x \le B \\ 70.0 + 30.0 \times \left(1 - \exp\left(-1.2 \times \frac{x - B}{B}\right)\right) & \text{if } x > B \end{cases}$$
- **Zero-floor integrity**: $S(0) = 0$
- **Benchmark alignment**: Meeting the regional benchmark yields $S(B) = 70.0$
- **Concavity**: Sub-linear gains below benchmark; asymptotic damping capped at 100 above benchmark.

### 5. Empirical Bayesian Benchmark Regularization
To prevent small-sample volatility in sparse regions ($N \le 3$), benchmarks blend toward global baselines using shrinkage pseudo-count $M = 3.0$:
$$B_{\text{effective}} = \frac{N}{N + M} \cdot \bar{B}_{\text{regional}} + \frac{M}{N + M} \cdot B_{\text{global}}$$

---

## Architecture & Tech Stack

```
========================================================================================
                          CAMPANALYTICS — SYSTEM ARCHITECTURE
========================================================================================

      [ Wikimedia Community Analyst / Organiser Browser ]
                             │
                ┌────────────┴────────────┐
                ▼ (Port 5001 locally / 8000 Toolforge)   ▼ (Port 8501)
      ┌──────────────────────┐  ┌──────────────────────────────────┐
      │      FLASK APP       │  │          STREAMLIT APP           │
      │    (flask_app.py)    │  │       (streamlit_app.py)         │
      │  • User Friendly UX  │  │   • Dark Slate Reactive UI       │
      │  • Toolforge Ready   │  │   • Prototyping Explorer         │
      └──────────┬───────────┘  └─────────────────┬────────────────┘
                 │                                │
                 └───────────────┬────────────────┘
                                 ▼
      ┌────────────────────────────────────────────────────────────┐
      │                  SHARED ANALYTICS ENGINE                   │
      │                      (analytics.py)                        │
      ├────────────────────────────────────────────────────────────┤
      │  • Dual Commons Ingestion: Toolforge DB + Action API       │
      │  • Scoped All-Campaign Aggregator (Pseudo-Event 'all')     │
      │  • Directional Contributor Retention Mathematics           │
      │  • 5-Dimension Health Index & Regional Benchmark Engine    │
      │  • Dual-Axis Influx & Longevity Profile Engine             │
      │  • Visualizations (Agg Matplotlib, Seaborn, Plotly)        │
      │  • In-Memory Thread-Safe TTL Caching Layer                 │
      └──────────────────────────┬─────────────────────────────────┘
                                 │
                ┌────────────────┴────────────────┐
                ▼                                 ▼
     ┌────────────────────────┐       ┌────────────────────────────┐
     │   Wikimedia Commons    │       │        config.json         │
     │   Action API / DB      │       │  5 Campaigns · 51 Nations  │
     │   (Live Metadata)      │       │  9 Regional Clusters       │
     └────────────────────────┘       │  Country Scope Map         │
                                      └────────────────────────────┘

========================================================================================
```

### Technology Stack
- **Backend**: Python 3.9+, Flask, Gunicorn
- **Dashboard**: Streamlit, Plotly, Seaborn, Matplotlib
- **Data & Ingestion**: Wikimedia Commons Action API, Toolforge MariaDB replica databases (`PyMySQL`)
- **Persistence & Caching**: SQLite (NFS mount), in-memory TTL caching, `Flask-Compress`

---

## Campaign Query Codes

Campaigns are referenced using code format: `[event][country][YY]`

| Code | Campaign | Country | Year |
|:---|:---|:---|:---|
| `wlmde24` | Wiki Loves Monuments | Germany (`de`) | 2024 |
| `wlein23` | Wiki Loves Earth | India (`in`) | 2023 |
| `wlfbd22` | Wiki Loves Folklore | Bangladesh (`bd`) | 2022 |
| `wlang23` | Wiki Loves Africa | Nigeria (`ng`) | 2023 |
| `wlbbd24` | Wiki Loves Bangla | Bangladesh (`bd`) | 2024 |
| `allde24` | All Campaigns (Combined) | Germany (`de`) | 2024 |

**Supported country codes (51 nations)**:  
`ar`, `at`, `au`, `bd`, `be`, `br`, `ca`, `ch`, `cl`, `co`, `cz`, `de`, `dz`, `eg`, `es`, `fi`, `fr`, `gh`, `gr`, `hu`, `id`, `in`, `it`, `ke`, `lk`, `ma`, `mx`, `my`, `ng`, `nl`, `no`, `np`, `nz`, `pe`, `ph`, `pk`, `pl`, `pt`, `ro`, `rs`, `ru`, `se`, `th`, `tn`, `tr`, `tz`, `ua`, `uk`, `us`, `ve`, `za`.

---

## Installation & Local Usage

### Prerequisites
- Python 3.9 or higher
- Git

### Setup
```bash
git clone https://github.com/TanvirSdq/CampAnalytics.git
cd CampAnalytics
pip install -r requirements.txt
```

### Run Flask Application
```bash
python3 app.py
```
Open [http://localhost:5001](http://localhost:5001) in your browser.

### Run Streamlit Application
```bash
streamlit run streamlit_app.py
```
Open [http://localhost:8501](http://localhost:8501) in your browser.

### Run Test Suite
```bash
python3 -m unittest discover tests
```
The automated test suite runs 58 unit tests covering routing, edge cases, scope restrictions, and data aggregation logic.

---

## Deployment & Operations

CampAnalytics is deployed as a Kubernetes webservice on **Wikimedia Toolforge** using the Toolforge Buildpacks service (Tekton CI/CD).

### Deployment Workflow
```bash
# 1. SSH into the Toolforge bastion
ssh <username>@login.toolforge.org

# 2. Switch to the project tool account
become campanalytics

# 3. Trigger a container build from GitHub
toolforge build start https://github.com/TanvirSdq/CampAnalytics.git

# 4. Restart the webservice
webservice --backend=kubernetes buildservice restart
```

### Production Runtime Configuration
- **Process Model (`Procfile`)**:
  ```procfile
  web: gunicorn --workers=2 --threads=4 --timeout=240 --bind=0.0.0.0:8000 --limit-request-line=8190 --forwarded-allow-ips=* flask_app:app
  ```
  - `gthread` worker model with 2 processes and 4 threads per worker.
  - 240-second request timeout to allow deep multi-category Commons metadata queries.
  - `--forwarded-allow-ips=*` preserves client headers across Wikimedia ingress proxies.
- **Response Compression**: `Flask-Compress` compresses analytical HTML responses from ~280 KB to ~27 KB (>85% reduction).
- **Persistent Cache**: Container filesystems on Toolforge are ephemeral. The cache database is located on Toolforge NFS storage at `/data/project/campanalytics/campaign_cache.sqlite3` to persist multi-year metadata and global usage stats across restarts.
- **Cache Pre-warming**: Run `python3 refresh_cache.py` to pre-fetch multi-year datasets offline.

---

## Repository Layout

```
CampAnalytics/
├── app.py                   # Local entry point & WSGI fallback
├── flask_app.py             # Production Flask application & tool routing
├── streamlit_app.py         # Streamlit interactive dashboard
├── analytics.py             # Core analytics engine (Commons API, DB, scoring, plots)
├── app_config.py            # Global UI styling, color palettes, and layout parameters
├── campaign_cache.py        # Persistent cache interface (SQLite on NFS & MariaDB)
├── refresh_cache.py         # Offline batch prefetcher and cache warmer
├── config.json              # Campaign definitions, regional clusters, and country scopes
├── METHODOLOGY.md           # Mathematical foundations, derivations, and benchmark definitions
├── README.md                # Project documentation and setup guide
├── styles.css               # Web interface styling and responsive design
├── streamlit_styles.css     # Streamlit theme adjustments
├── toolhub.yaml             # Wikimedia Toolhub 2.0.0 metadata specification
├── toolinfo.json            # Wikimedia Toolinfo registry record
├── Procfile                 # Toolforge Buildpacks process definition for Gunicorn
├── requirements.txt         # Python package dependencies
├── templates/
│   ├── base.html            # Base template with navigation and layout structure
│   └── index.html           # Main template for analytics tools and documentation
└── tests/
    ├── __init__.py          # Test suite package file
    └── test_flask_app.py    # Automated test suite (58 unit tests)
```

---

## License & Attribution

- **License**: [GNU General Public License v2.0 or later (GPL-2.0+)](https://www.gnu.org/licenses/gpl-2.0.html)
- **Affiliation**: Developed in support of [Project Korikath](https://meta.wikimedia.org/wiki/Project_Korikath)
- **Data Attribution**: Metadata queried from [Wikimedia Commons](https://commons.wikimedia.org) under open licenses
