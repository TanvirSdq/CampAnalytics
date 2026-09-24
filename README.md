# CampAnalytics — Event Evaluation

> **A high-performance analytics suite for Wikimedia Commons campaigns, longitudinal contributor retention analysis, cross-campaign ecosystem influx, and regional health benchmarking.**

[![Hosted on Wikimedia Toolforge](https://img.shields.io/badge/Hosted%20on-Wikimedia%20Toolforge-006699?style=flat-square&logo=wikipedia)](https://campanalytics.toolforge.org/)
[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://campanalytics.streamlit.app/)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg?style=flat-square)](https://www.python.org/downloads/)
[![License: GPL-2.0+](https://img.shields.io/badge/License-GPL--2.0%2B-blue.svg?style=flat-square)](https://www.gnu.org/licenses/gpl-2.0.html)
[![Affiliation: Project Korikath](https://img.shields.io/badge/Affiliation-Project%20Korikath-183f54?style=flat-square)](https://meta.wikimedia.org/wiki/Project_Korikath)

---

<div align="center">

### [📖 Overview](README.md) &nbsp;&nbsp;|&nbsp;&nbsp; [📐 Scientific Methodology](METHODOLOGY.md) &nbsp;&nbsp;|&nbsp;&nbsp; [⚖️ License](LICENSE) &nbsp;&nbsp;|&nbsp;&nbsp; [🌐 Live Toolforge Deployment](https://campanalytics.toolforge.org/)

</div>

---

## Live Deployments

CampAnalytics is accessible online through two official live web deployments:

| Platform | Live URL | Description |
|:---|:---|:---|
| **Wikimedia Toolforge** | [campanalytics.toolforge.org](https://campanalytics.toolforge.org/) | Production Flask web application integrated with the Wikimedia ecosystem |
| **Streamlit Community Cloud** | [campanalytics.streamlit.app](https://campanalytics.streamlit.app/) | Interactive reactive dashboard with sidebar controls and exploratory charts |

Both interfaces run on the identical core analytics engine ([`analytics.py`](analytics.py)).

## Overview

**CampAnalytics** is an open-source analytical platform for campaign organizers, program evaluators, and Wikimedia community leaders. It provides data-driven intelligence across the major recurring international Wiki Loves photography campaigns by querying live metadata directly from Wikimedia Commons and Toolforge replica databases.

| Code | Campaign | Focus | Commons Category Pattern |
|:---|:---|:---|:---|
| `wlm` | Wiki Loves Monuments | Built & architectural cultural heritage | `Images_from_Wiki_Loves_Monuments_YYYY_in_Country` |
| `wle` | Wiki Loves Earth | Natural heritage & protected areas | `Images_from_Wiki_Loves_Earth_YYYY_in_Country` |
| `wlf` | Wiki Loves Folklore | Intangible culture, traditions, festivals | `Images_from_Wiki_Loves_Folklore_YYYY_in_Country` |
| `wla` | Wiki Loves Africa | African cultural heritage & daily life | `Images_from_Wiki_Loves_Africa_YYYY_in_Country` |
| `wlb` | Wiki Loves Bangla | Regional cultural & biodiversity heritage | `Images_from_Wiki_Loves_Bangla_YYYY` |
| `all` | All Campaigns | Ecosystem combination per country | Scoped aggregate across all active campaigns for the target country |

CampAnalytics answers five core programmatic questions:

1. **Ecosystem Vitality** — How healthy is a specific campaign edition compared to top-performing regional peers?
2. **Contributor Continuity** — How effectively do campaigns retain participant cohorts across consecutive editions?
3. **True Newcomer Influx** — Across all campaigns in a year and country, how many genuinely new people entered the Wikimedia movement?
4. **Encyclopedic Utility** — How effectively are uploaded media files integrated into Wikipedia and sister project articles?
5. **Quality Recognition** — What proportion of submissions attain formal artistic and curatorial recognition (Quality Images, Featured Pictures, Valued Images)?

---

## Five Analytical Tools

### 1. Health Evaluation (`/health`)

Scores a campaign edition on a standardized 0–100 scale across five defensible dimensions structured into paired analytical pillars summing to 100%, each benchmarked against empirical regional reference thresholds:

| Dimension | Weight | Pillar | What it Measures |
|:---|:---:|:---|:---|
| **Retention Index** ($S_{\text{ret}}$) | **25%** | Community Vitality (50%) | Returning contributors from the prior edition — primary community sustainability signal |
| **Growth Capacity** ($S_{\text{grow}}$) | **25%** | Community Vitality (50%) | First-time newcomer acquisition share across the campaign lifecycle |
| **Content Utility** ($S_{\text{util}}$) | **20%** | Content Impact (35%) | Files actively deployed across Wikimedia wikis (`prop=globalusage`) |
| **Quality Recognition** ($S_{\text{qual}}$) | **15%** | Content Impact (35%) | Proportion of submissions receiving formal Commons quality designations (QI / FP / VI) |
| **Contributor Diversity** ($S_{\text{div}}$) | **15%** | Participation Equity (15%) | Upload distribution equity (inverse top-10% uploader concentration) |

#### How the System Evaluates:
- **Composite Index Formulation**:
  $$\text{Evaluation Index} = 0.25 S_{\text{ret}} + 0.25 S_{\text{grow}} + 0.20 S_{\text{util}} + 0.15 S_{\text{qual}} + 0.15 S_{\text{div}}$$
- **Continuous Utility Functions**: Rather than linear scoring ($x/B$), scores map through a continuous concave utility curve:
  $$S(x, B) = \begin{cases} 0.0 & \text{if } x \le 0 \\ 70.0 \times \left(\frac{x}{B}\right)^{0.75} & \text{if } 0 < x \le B \\ 70.0 + 30.0 \times \left(1 - \exp\left(-1.2 \times \frac{x - B}{B}\right)\right) & \text{if } x > B \end{cases}$$
  *Key properties*: Strict zero-floor integrity ($S(0) = 0$), exact regional alignment ($S(B) = 70.0$), sub-linear encouragement below benchmark, and asymptotic damping above benchmark (capped at 100).
- **Inverse Diversity Scoring**: High concentration in the top 10% indicates fragile reliance on a few power uploaders; broad distribution achieves up to 100 points.
- **Empirical Bayesian Regularization**:
  $$B_{\text{effective}} = \frac{N}{N + M} \cdot \bar{B}_{\text{regional}} + \frac{M}{N + M} \cdot B_{\text{global}}$$
  with shrinkage pseudo-count $M = 3.0$. In regions with few peer editions ($N \le 3$), benchmarks blend toward global movement baselines to eliminate small-sample volatility or division-by-zero artifacts.
- **Qualitative Star Tiers**:
  - ★★★★★ **Outstanding** (85.0–100.0) · Exceeds regional and global standards
  - ★★★★☆ **Strong** (70.0–84.9) · Meets or slightly surpasses regional benchmarks
  - ★★★☆☆ **Moderate** (50.0–69.9) · Solid fundamentals with identifiable growth opportunities
  - ★★☆☆☆ **Emerging** (30.0–49.9) · Early-stage progress requiring strategic development
  - ★☆☆☆☆ **Critical** (0.0–29.9) · Severe structural concentration or minimal continuity

### 2. Retention Analytics (`/retention`)

- **Selection Builder**: Flexible multi-event, multi-nation, and multi-year comparative matrices (`[event][country][YY]`, e.g. `wlmde22`, `wlmbd24`).
- **Directional Retention Matrix**: Exact longitudinal account persistence from baseline edition $A$ to target edition $B$:
  $$\text{Retention}(A \to B) = \left( \frac{|U_A \cap U_B|}{|U_A|} \right) \times 100\%$$
- **Three Visualization Projections**: Interactive sortable Data Table · Pairwise Seaborn Heatmap Matrix · Global Choropleth World Map with regional peer filtering.

### 3. Contributor Influx & Growth (`/influx`)

- **Temporal Span**: Consecutive annual sequence analysis from 2010 to 2040.
- **Single-Campaign vs. Ecosystem Aggregation**:
  - *Single Campaign*: Tracks consecutive editions of a specific contest (e.g. `wlmde20` $\to$ `wlmde24`).
  - *All Campaigns* (`all[cc][YY]`): De-duplicates contributors across all active photo competitions within a nation to isolate true movement-level recruitment from inter-campaign migration.
- **Scope Enforcement**: Governed by `EVENT_COUNTRY_SCOPE` in `config.json` to prevent phantom queries for geographically inapplicable contests.
- **Lifecycle Cohort Segmentation**:
  - **1-Time Entrants**: Single-edition participants.
  - **Repeaters**: Active across 2–3 campaign editions.
  - **Core Veterans**: Long-term stalwarts participating in 4+ editions.
- **Visual Trajectory**: Dual-axis stacked bar chart illustrating annual newcomer influx ($I_t$), returning veterans ($R_t$), and the cumulative contributor footprint.

### 4. Content Utility (`/utility`)

- **Encyclopedic Reuse Analysis**: Connects to the Wikimedia Commons Action API (`prop=globalusage`) to track the exact propagation of campaign media across live Wikipedia language editions, Wikidata, Wikivoyage, and Wikimedia Commons galleries.
- **Metrics Computed**:
  - **Overall Utility Rate**: Proportion of uploaded files embedded in at least one article.
  - **Total Article Inclusions**: Cumulative cross-wiki deployment count.
  - **Wiki Project Footprint**: Breakdown of usage by project (e.g. English Wikipedia, German Wikipedia, Wikidata, Wikimedia Commons).
  - **Photographer Leaderboard**: Ranks contributors whose files have achieved the widest readership and highest reuse.

### 5. Quality Recognition (`/quality`)

- **Curatorial Honors Engine**: Analyzes submissions that have passed peer-reviewed quality processes on Wikimedia Commons:
  - **Quality Images (QI)**: Assessed by the Commons Quality committee for technical photographic standards.
  - **Featured Pictures (FP)**: The finest images on Wikimedia Commons, representing community-wide consensus.
  - **Valued Images (VI)**: Canonical subject-matter reference illustrations.
- **Showcase Gallery & Metadata**: Interactive showcase with lazy-loaded thumbnails, direct Wikimedia Commons file links, photographer attributions, and exportable data tables (CSV, Wikitext, JSON).
- **Photographer Hall of Fame**: Recognizes top-performing contributors with formal honors badges.

### 6. Scientific Methodology & Documentation (`/documentation`)

CampAnalytics is grounded in published literature on peer production, open collaboration, and composite indicator design.

👉 **[Read the Full Methodology Paper (METHODOLOGY.md)](METHODOLOGY.md)**

<details>
<summary><b>📐 Click to Expand Methodology Overview & Mathematical Formulas</b></summary>

#### A. Longitudinal Account Retention Matrix
$$\text{Retention}(A \to B) = \left( \frac{|U_A \cap U_B|}{|U_A|} \right) \times 100\%$$

#### B. Empirical Bayesian Benchmark Regularization
$$B_{\text{effective}} = \frac{N}{N + M} \cdot \bar{B}_{\text{regional}} + \frac{M}{N + M} \cdot B_{\text{global}}$$
Where $M = 3.0$ prevents denominator collapse in regions with few peer editions.

#### C. Continuous Relative Utility Scoring Function
$$S(x, B) = \begin{cases} 0.0 & \text{if } x \le 0 \\ 70.0 \times \left(\frac{x}{B}\right)^{0.75} & \text{if } 0 < x < B \\ 70.0 + 30.0 \times \left(1 - \exp\left(-1.2 \times \frac{x - B}{B}\right)\right) & \text{if } x \ge B \end{cases}$$

Key mathematical properties:
- **Strict zero-floor integrity**: $S(0) = 0.0$ (no passing score for zero output).
- **Exact benchmark alignment**: $S(B) = 70.0$ ("Meets Benchmark").
- **Concave progress**: Encourages initial gains below benchmark.
- **Diminishing returns**: Bounded at 100.0 without runaway scores.

For full mathematical proofs, refer to [`METHODOLOGY.md`](METHODOLOGY.md).
</details>

---

## System Architecture

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

---

## Mathematical Formulations

### 1. Directional Contributor Retention
$$\text{Retention}(A \to B) = \left( \frac{|U_A \cap U_B|}{|U_A|} \right) \times 100\%$$

where $U_A$, $U_B$ are verified unique uploader accounts. Note: $\text{Retention}(A \to B) \neq \text{Retention}(B \to A)$ when cohort sizes differ.

### 2. Contributor Growth Capacity
$$\text{Growth}(A \to B) = \left( \frac{|U_B \setminus U_A|}{|U_B|} \right) \times 100\%$$

### 3. Single-Campaign Longitudinal Influx
For editions $(C_1, C_2, \dots, C_T)$ with cohorts $(U_1, U_2, \dots, U_T)$:

- **New Influx** ($I_t$): $I_t = \left| U_t \setminus \bigcup_{j < t} U_j \right|$
- **Returning** ($R_t$): $R_t = \left| U_t \cap \bigcup_{j < t} U_j \right|$
- **Cumulative Pool** ($P_t$): $P_t = \left| \bigcup_{j \le t} U_j \right|$

### 4. Multi-Campaign Ecosystem Influx
For the `all` pseudo-event, only campaigns in scope for the target country $cc$ are included:

$$U_t = \bigcup_{e \in E_{cc}} U_{e,t}$$

$$I_t = U_t \setminus \bigcup_{j < t} U_j \qquad R_t = U_t \cap \bigcup_{j < t} U_j \qquad P_t = \bigcup_{j \le t} U_j$$

where $E_{cc}$ is the subset of campaigns with documented editions in country $cc$, as declared in `EVENT_COUNTRY_SCOPE` in `config.json`. Contributors active in multiple campaigns during the same year are de-duplicated, giving an accurate count of distinct individuals.

---

## Campaign Code Format

Standard query codes follow the pattern: `[event][country][YY]`

```
wlm de 24   →  Wiki Loves Monuments · Germany · 2024
wle in 23   →  Wiki Loves Earth · India · 2023
wlf bd 22   →  Wiki Loves Folklore · Bangladesh · 2022
wla ng 23   →  Wiki Loves Africa · Nigeria · 2023
wlb bd 24   →  Wiki Loves Bangla · Bangladesh · 2024
all de 24   →  All Campaigns · Germany · 2024
```

Supported country codes: `bd` `in` `de` `it` `fr` `us` `ca` `uk` `nl` `pl` `br` `mx` `es` `pt` `pk` `np` `ng` `ke` `id` `rs` `ph` `my` `tr` `eg` `ua` `ru` `ch` `se` `no` `fi` `be` `at` `ar` `co` `lk` `au` `nz` `th` `gr` `tn` `ma` `dz` `za` `gh` `tz` `pe` `cl` `ve` `cz` `ro` `hu`

---

## Deployment Architecture & Operations

CampAnalytics is deployed as a cloud-native webservice on **Wikimedia Toolforge** (Kubernetes backend) using the Toolforge Buildpacks Service (Tekton CI/CD pipeline).

### 1. Toolforge Deployment Workflow

The production service is built and deployed directly from GitHub:

```bash
# 1. SSH into the Toolforge bastion
ssh <username>@login.toolforge.org

# 2. Switch to the tool account
become campanalytics

# 3. Trigger a container build from GitHub (Heroku/CNB Python buildpack)
toolforge build start https://github.com/TanvirSdq/CampAnalytics.git

# 4. Perform a zero-downtime rolling restart of the Kubernetes webservice
webservice --backend=kubernetes buildservice restart
```

### 2. Runtime & Process Configuration

- **Process Model (`Procfile`)**:
  ```procfile
  web: gunicorn --workers=2 --threads=4 --timeout=240 --bind=0.0.0.0:8000 --limit-request-line=8190 --forwarded-allow-ips=* flask_app:app
  ```
  - `gthread` worker engine with 2 worker processes and 4 threads per worker, allowing concurrent servicing of API requests.
  - Generous 240-second timeout to accommodate multi-category deep harvests on Commons without gateway drops.
  - `--forwarded-allow-ips=*` properly preserves client protocol and IP information across the Wikimedia ingress proxy.

- **Dynamic Payload Compression**:
  Integrated with `Flask-Compress` (supporting Gzip and Brotli compression). Compresses analytical HTML payloads from ~280 KB down to ~27 KB (an 85%+ reduction), preventing ingress proxy throttling and eliminating browser loading hangs.

- **Persistent Volume Caching**:
  Because buildpack containers run on an ephemeral container filesystem that resets on every deployment or replica restart, the cache is explicitly routed to the tool's persistent NFS storage:
  - Cache Path: `/data/project/campanalytics/campaign_cache.sqlite3`
  - Ensures multi-year participant sets, global usage metrics, and Commons quality badges are preserved across releases and pod restarts.
  - Automatically falls back to local SQLite in development or replica MariaDB (`replica.my.cnf`) when configured.

- **Offline Prefetch & Warmup**:
  Run `python3 refresh_cache.py` to pre-populate multi-year metrics offline, ensuring immediate sub-second dashboard rendering for organizers.

---

## Installation & Local Usage

### Prerequisites
- Python 3.9+

### Clone & Install
```bash
git clone https://github.com/TanvirSdq/CampAnalytics.git
cd CampAnalytics
pip install -r requirements.txt
```

### Run Flask App Locally
```bash
python3 app.py
```
Visit: `http://localhost:5001`

The `Procfile` runs the same Flask application through Gunicorn on port `8000` for Toolforge-style deployments.

### Run Streamlit App
```bash
streamlit run streamlit_app.py
```
Visit: `http://localhost:8501`

### Running the Test Suite
```bash
python3 -m unittest discover tests
```
The automated test suite contains 58 unit tests validating all five tool routes, edge-case resilience, scoping, and data aggregations.

---

## Repository Layout

```
CampAnalytics/
├── app.py                   # Local launcher & WSGI fallback
├── flask_app.py             # Production Flask application & 5-tool routing engine
├── streamlit_app.py         # Streamlit interactive exploratory dashboard
├── analytics.py             # Core analytical engine (Commons API, replica DB, math, plotting)
├── app_config.py            # Global styles, palette, typography & layout parameters
├── campaign_cache.py        # Dual-backend persistent cache (Toolforge NFS SQLite & MariaDB)
├── refresh_cache.py         # Offline batch prefetcher and cache warmer
├── config.json              # 5 campaigns · 51 countries · 9 regional clusters & scopes
├── METHODOLOGY.md           # Formal mathematical framework, formulas & peer benchmark specs
├── README.md                # Project documentation, deployment architecture & quickstart
├── styles.css               # Modern responsive design system, mobile drawer & print styles
├── streamlit_styles.css     # Streamlit theme and responsive stylesheet
├── toolhub.yaml             # Wikimedia Toolhub 2.0.0 metadata specification
├── toolinfo.json            # Wikimedia Toolinfo registry definition
├── Procfile                 # Toolforge Buildpacks process definition for Gunicorn
├── requirements.txt         # Production Python dependencies (Flask, Compress, PyMySQL, etc.)
├── templates/
│   ├── base.html            # Foundation template, responsive navbar, mobile off-canvas drawer
│   └── index.html           # Unified template: 5 tools (Evaluation, Retention, Influx, Utility, Quality) & Documentation
└── tests/
    ├── __init__.py          # Test suite package marker
    └── test_flask_app.py    # Automated test suite (58 unit tests covering all routes and edge cases)
```

---

## License & Attribution

- **License**: [GNU General Public License v2.0 or later (GPL-2.0+)](https://www.gnu.org/licenses/gpl-2.0.html)
- **Affiliation**: Built in support of [Project Korikath](https://meta.wikimedia.org/wiki/Project_Korikath)
- **Data**: Live metadata from [Wikimedia Commons](https://commons.wikimedia.org) under open licenses
