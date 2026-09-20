# CampAnalytics — Event Evaluation

> **A high-performance analytics suite for Wikimedia Commons campaigns, longitudinal contributor retention analysis, cross-campaign ecosystem influx, and regional health benchmarking.**

[![Hosted on Wikimedia Toolforge](https://img.shields.io/badge/Hosted%20on-Wikimedia%20Toolforge-006699?style=flat-square&logo=wikipedia)](https://toolforge.org)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg?style=flat-square)](https://www.python.org/downloads/)
[![License: GPL-2.0+](https://img.shields.io/badge/License-GPL--2.0%2B-blue.svg?style=flat-square)](https://www.gnu.org/licenses/gpl-2.0.html)
[![Affiliation: Project Korikath](https://img.shields.io/badge/Affiliation-Project%20Korikath-183f54?style=flat-square)](https://meta.wikimedia.org/wiki/Project_Korikath)
[![Test Suite: 33 Passing](https://img.shields.io/badge/tests-33%20passed-success.svg?style=flat-square)](tests/test_app.py)

---

## Overview

**CampAnalytics** is an open-source analytical platform for campaign organizers, program evaluators, and Wikimedia community leaders. It provides data-driven intelligence across 12 major international Wiki Loves campaigns by querying live metadata directly from Wikimedia Commons and Toolforge replica databases.

| Code | Campaign | Commons Category Pattern |
|:---|:---|:---|
| `wlm` | Wiki Loves Monuments | `Images_from_Wiki_Loves_Monuments_YYYY_in_Country` |
| `wle` | Wiki Loves Earth | `Images_from_Wiki_Loves_Earth_YYYY_in_Country` |
| `wlf` | Wiki Loves Folklore | `Images_from_Wiki_Loves_Folklore_YYYY_in_Country` |
| `wla` | Wiki Loves Africa | `Images_from_Wiki_Loves_Africa_YYYY_in_Country` |
| `wlb` | Wiki Loves Bangla | `Images_from_Wiki_Loves_Bangla_YYYY` *(no country suffix)* |
| `wlp` | Wiki Loves Pride | `Images_from_Wiki_Loves_Pride_YYYY` *(global year-only)* |
| `wlfood` | Wiki Loves Food | `Images_from_Wiki_Loves_Food_YYYY` *(global year-only)* |
| `wlpa` | Wiki Loves Public Art | `Images_from_Wiki_Loves_Public_Art_and_Cemeteries_YYYY_in_Country` |
| `wllh` | Wiki Loves Living Heritage | `Images_from_Wiki_Loves_Living_Heritage_YYYY_in_Country` |
| `wls` | Wiki Loves Sport | `Images_from_Wiki_Loves_Sport_YYYY` *(global year-only)* |
| `wlbf` | Wiki Loves Butterfly | `Images_from_Wiki_Loves_Butterfly_YYYY` *(global year-only)* |
| `wlbirds` | Wiki Loves Birds | `Images_from_Wiki_Loves_Birds_YYYY` *(global year-only)* |
| `all` | All Campaigns | Scoped aggregate across all valid campaigns for the country |

CampAnalytics answers three core programmatic questions:

1. **Contributor Continuity** — How effectively do campaigns retain participant cohorts across consecutive editions?
2. **Ecosystem Vitality** — How healthy is a specific campaign edition compared to top-performing regional peers?
3. **True Newcomer Influx** — Across all campaigns in a year and country, how many genuinely new people entered the Wikimedia movement?

---

## Two Interfaces

CampAnalytics is built on a single shared analytical core powering two deployment models:

| Interface | Runtime | Target | Notes |
|:---|:---|:---|:---|
| **Flask Web App** | WSGI / Gunicorn | Wikimedia Toolforge | GLAMtools visual coherence, Marine Petrol `#183f54` + Cyan `#72ded6` palette, zero client-side bloat |
| **Streamlit App** | Streamlit Runtime | Streamlit Cloud / Local | Interactive Plotly charts, reactive series builder, dark slate aesthetic, sidebar-driven controls |

Both consume identical data pipelines via [`analytics.py`](analytics.py) and [`config.json`](config.json).

---

## Four Analytical Modules

### 1. Retention Analytics

- **Selection Builder**: Choose any combination of campaigns, countries, and year ranges. Codes follow the pattern `[event][country][YY]` (e.g. `wlmde22` = Wiki Loves Monuments, Germany, 2022).
- **Directional Retention Matrix**: Exact account persistence from baseline edition $A$ to subsequent edition $B$:
  $$\text{Retention}(A \to B) = \left( \frac{|U_A \cap U_B|}{|U_A|} \right) \times 100\%$$
- **Three Visualization Models**: Data Table · Heatmap Matrix (Seaborn) · Choropleth World Map (Plotly)

### 2. Health Evaluation (5-Dimension Scorecard)

Scores a campaign edition on a 0–100 scale across five weighted dimensions:

| Dimension | Weight | Metric |
|:---|:---|:---|
| Retention Index | 35% | Returning participants from prior edition |
| Growth Capacity | 20% | First-time participant share |
| Content Utility | 20% | Files illustrated across Wikimedia projects |
| Quality Recognition | 15% | Commons quality/featured image rate |
| Contributor Diversity | 10% | Upload distribution equity (top-10% uploader share) |

Regional benchmarks are computed dynamically from upper-quartile peer campaigns across 9 geographic clusters — not arbitrary global thresholds.

### 3. New User Influx & Growth

- **Year span**: 2010–2040
- **Single-campaign mode**: Follows consecutive editions (e.g. `wlmde20 wlmde21 wlmde22`)
- **All Campaigns mode** (`all[cc][YY]`): Aggregates all campaigns valid for that country and year, de-duplicates cross-participation, and isolates true movement-wide newcomers from returning veterans
- **Scope intelligence**: Each campaign has a declared country scope in `config.json`. The `all` aggregator only queries campaign × country pairs that are documented on Commons — preventing phantom category lookups (e.g. WL Bangla will not be queried for Germany; WL Africa will not be queried for Europe)
- **Longevity segmentation**: 1-Time Entrants · Repeaters (2–3 editions) · Core Veterans (4+ editions)
- **Campaign breakdown**: Per-year breakdown of which campaigns contributed to the composite cohort

### 4. Methodology & Usage Guide

Transparent mathematical formulations, regional normalization criteria, Commons API / Toolforge failover specifications, and usage guidelines for programmatic organizers — built into the app as a dedicated tab.

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
      │  • GLAMtools Theme   │  │   • Dark Slate Reactive UI       │
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
     │   Action API / DB      │       │  12 Campaigns · 51 Nations │
     │   (Live Metadata)      │       │  9 Regional Clusters       │
     └────────────────────────┘       │  Country Scope Map         │
                                      │  Category Name Overrides   │
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

Input codes use one of two patterns: `[event][country][YY]` for country editions, or `[event][YY]` for campaigns whose Commons categories are year-only.

```
wlm de 24   →  Wiki Loves Monuments · Germany · 2024
wlf bd 22   →  Wiki Loves Folklore · Bangladesh · 2022
all ng 23   →  All Campaigns · Nigeria · 2023
wlb 24      →  Wiki Loves Bangla · 2024  (no country suffix — year-only category)
wlp 25      →  Wiki Loves Pride · 2025   (no country suffix — year-only category)
wlfood 25  →  Wiki Loves Food · 2025    (no country suffix — year-only category)
```

Supported country codes: `bd` `in` `de` `it` `fr` `us` `ca` `uk` `nl` `pl` `br` `mx` `es` `pt` `pk` `np` `ng` `ke` `id` `rs` `ph` `my` `tr` `eg` `ua` `ru` `ch` `se` `no` `fi` `be` `at` `ar` `co` `lk` `au` `nz` `th` `gr` `tn` `ma` `dz` `za` `gh` `tz` `pe` `cl` `ve` `cz` `ro` `hu`

---

## Installation & Local Usage

### Prerequisites
- Python 3.9+

### Clone & Install
```bash
git clone https://github.com/siddiquetanvir/CampAnalytics.git
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

---

## Automated Test Suite

```bash
PYTHONPATH=. python3 tests/test_app.py
```

```
.................................
----------------------------------------------------------------------
Ran 33 tests in ~0.5s

OK
```

The suite covers route correctness, input normalization, GLAMtools CSS compliance, regional calibration, scope filtering, Commons category name resolution, ecosystem aggregation, and chart generation.

---

## Toolforge Deployment

```bash
ssh <username>@login.toolforge.org
become <toolname>
git clone https://github.com/siddiquetanvir/CampAnalytics.git src
cd src
toolforge webservice buildpack start
```

---

## Repository Layout

```
CampAnalytics/
├── app.py                   # Production Toolforge WSGI entrypoint
├── flask_app.py             # Flask route controllers & GLAMtools UI
├── streamlit_app.py         # Streamlit interactive dashboard
├── analytics.py             # Core engine: caching, Commons API, math, charts
├── app_config.py            # Global palette and settings
├── config.json              # 12 campaigns · 51 countries · 9 regional clusters
│                            #   EVENT_MAP · EVENT_DISPLAY_MAP
│                            #   EVENT_COUNTRY_SCOPE · CATEGORY_NAME_OVERRIDE
│                            #   COUNTRY_MAP · REGION_COUNTRY_MAPPING
├── styles.css               # Flask GLAMtools stylesheet
├── streamlit_styles.css     # Streamlit theme and sidebar stylesheet
├── Procfile                 # Web process definition
├── requirements.txt         # Python dependencies
├── templates/
│   ├── base.html            # Layout shell, top navbar, Project Korikath brand
│   └── index.html           # 4-mode suite: Retention · Health · Influx · Methodology
└── tests/
    └── test_app.py          # 33 regression, influx, and unit test cases
```

---

## License & Attribution

- **License**: [GNU General Public License v2.0 or later (GPL-2.0+)](https://www.gnu.org/licenses/gpl-2.0.html)
- **Affiliation**: Built in support of [Project Korikath](https://meta.wikimedia.org/wiki/Project_Korikath)
- **Data**: Live metadata from [Wikimedia Commons](https://commons.wikimedia.org) under open licenses
