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

CampAnalytics answers three core programmatic questions:

1. **Contributor Continuity** — How effectively do campaigns retain participant cohorts across consecutive editions?
2. **Ecosystem Vitality** — How healthy is a specific campaign edition compared to top-performing regional peers?
3. **True Newcomer Influx** — Across all campaigns in a year and country, how many genuinely new people entered the Wikimedia movement?

---

## Four Analytical Modules

### 1. Retention Analytics

- **Selection Builder**: Choose any combination of campaigns, countries, and year ranges. Codes follow the pattern `[event][country][YY]` (e.g. `wlmde22` = Wiki Loves Monuments, Germany, 2022).
- **Directional Retention Matrix**: Exact account persistence from baseline edition $A$ to subsequent edition $B$:
  $$\text{Retention}(A \to B) = \left( \frac{|U_A \cap U_B|}{|U_A|} \right) \times 100\%$$
- **Three Visualization Models**: Data Table · Heatmap Matrix (Seaborn) · Choropleth World Map (Plotly)

### 2. Health Evaluation (5-Dimension Scorecard)

Scores a campaign edition on a 0–100 scale across five defensible dimensions structured into paired analytical pillars summing to 100%, each benchmarked against empirical regional reference thresholds:

| Dimension | Weight | Pillar | What it Measures |
|:---|:---:|:---|:---|
| Retention Index | **25%** | Community Vitality (50%) | Returning contributors from the prior edition — primary sustainability signal |
| Growth Capacity | **25%** | Community Vitality (50%) | First-time newcomer acquisition share across campaign lifecycle |
| Content Utility | **20%** | Content Impact (35%) | Files actively used across Wikimedia wikis (`prop=globalusage`) |
| Quality Recognition | **15%** | Content Impact (35%) | Commons QI/FP recognition rate of uploaded media |
| Contributor Diversity | **15%** | Participation Equity (15%) | Upload distribution equity (top-10% uploader concentration) |

Regional benchmarks are regularized using Empirical Bayesian shrinkage ($B_{\text{effective}} = \frac{N}{N + 3} B_{\text{regional}} + \frac{3}{N + 3} B_{\text{global}}$), preventing small-sample distortion in sparse regions.

### 3. New User Influx & Growth

- **Year span**: 2010–2040
- **Single-campaign mode**: Follows consecutive editions (e.g. `wlmde20 wlmde21 wlmde22`)
- **All Campaigns mode** (`all[cc][YY]`): Aggregates all campaigns valid for that country and year, de-duplicates cross-participation, and isolates true movement-wide newcomers from returning veterans
- **Scope intelligence**: Each campaign has a declared country scope in `config.json`. The `all` aggregator only queries campaign × country pairs that are documented on Commons — preventing phantom category lookups (e.g. WL Bangla will not be queried for Germany; WL Africa will not be queried for Europe)
- **Longevity segmentation**: 1-Time Entrants · Repeaters (2–3 editions) · Core Veterans (4+ editions)
- **Campaign breakdown**: Per-year breakdown of which campaigns contributed to the composite cohort

### 4. Scientific Methodology & Formal Specifications

CampAnalytics is backed by a formal mathematical methodology with zero-floor utility scoring, concave progress curves, and academic citations.

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

## Repository Layout

```
CampAnalytics/
├── app.py                   # Production Toolforge WSGI entrypoint
├── flask_app.py             # Flask route controllers & UI
├── streamlit_app.py         # Streamlit interactive dashboard
├── analytics.py             # Core engine: caching, Commons API, math, charts
├── app_config.py            # Global palette and settings
├── campaign_cache.py        # Persistent SQLite participant cache
├── config.json              # 5 campaigns · 51 countries · 9 regional clusters
├── METHODOLOGY.md           # Scientific methodology paper & mathematical specifications
├── styles.css               # Flask stylesheet & mobile ergonomics
├── streamlit_styles.css     # Streamlit theme and sidebar stylesheet
├── toolhub.yaml             # Wikimedia Toolhub 2.0.0 manifest
├── toolinfo.json            # Wikimedia Toolinfo registry metadata
├── Procfile                 # Web process definition
├── requirements.txt         # Python dependencies
├── templates/
│   ├── base.html            # Layout shell, top navbar, Project Korikath brand
│   └── index.html           # 4-mode suite: Evaluation · Retention · Influx · Methodology
└── tests/
    └── test_flask_app.py    # Automated test suite (43 unit tests)
```

---

## License & Attribution

- **License**: [GNU General Public License v2.0 or later (GPL-2.0+)](https://www.gnu.org/licenses/gpl-2.0.html)
- **Affiliation**: Built in support of [Project Korikath](https://meta.wikimedia.org/wiki/Project_Korikath)
- **Data**: Live metadata from [Wikimedia Commons](https://commons.wikimedia.org) under open licenses
