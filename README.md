# CampAnalytics — Event Evaluation

> **A high-performance analytics suite for Wikimedia Commons campaigns, longitudinal contributor retention analysis, cross-campaign ecosystem influx, and regional health benchmarking.**

[![Hosted on Wikimedia Toolforge](https://img.shields.io/badge/Hosted%20on-Wikimedia%20Toolforge-006699?style=flat-square&logo=wikipedia)](https://toolforge.org)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg?style=flat-square)](https://www.python.org/downloads/)
[![License: GPL-2.0+](https://img.shields.io/badge/License-GPL--2.0%2B-blue.svg?style=flat-square)](https://www.gnu.org/licenses/gpl-2.0.html)
[![Affiliation: Project Korikath](https://img.shields.io/badge/Affiliation-Project%20Korikath-183f54?style=flat-square)](https://meta.wikimedia.org/wiki/Project_Korikath)
[![Test Suite: 33 Passing](https://img.shields.io/badge/tests-33%20passed-success.svg?style=flat-square)](tests/test_app.py)

---

## 🌟 Overview

**CampAnalytics** is an open-source analytical platform designed for organizers, program evaluators, and Wikimedia community leaders. It provides data-driven intelligence across the entire spectrum of major international Wiki Loves campaigns and regional photographic initiatives:

- **Wiki Loves Monuments (WLM)** — Built & architectural cultural heritage
- **Wiki Loves Earth (WLE)** — Natural heritage & protected biodiversity areas
- **Wiki Loves Folklore (WLF)** — Intangible cultural heritage, festivals & rituals
- **Wiki Loves Africa (WLA)** — Continental African culture, history & traditions
- **Wiki Loves Bangla (WLB)** — Bengali regional cultural & biodiversity documentation
- **Wiki Loves Pride (WLP)** — LGBTQ+ community visibility and heritage
- **Wiki Loves Food (WLFood)** — Global culinary heritage and food cultures
- **Wiki Loves Public Art (WLPA)** — Public sculpture, outdoor monuments & street art
- **Wiki Loves Living Heritage (WLLH)** — Craft traditions and oral heritage
- **Wiki Loves Sport (WLS)** — Physical culture, athletic games & competitions
- **Wiki Loves Butterfly (WLBF)** — Lepidoptera and wildlife documentation
- **Wiki Loves Birds (WLBirds)** — Avian biodiversity documentation
- **All Campaigns Combined (Ecosystem Overview)** — Cross-campaign aggregation measuring the net influx of contributors into the Wikimedia movement

By querying live metadata from Wikimedia Commons alongside Toolforge replica databases, CampAnalytics answers critical programmatic questions:
1. **Contributor Continuity**: How effectively do campaigns retain participant cohorts across consecutive editions and across different event types?
2. **Ecosystem Vitality**: How healthy is a specific campaign edition compared to top-performing regional peers operating under similar geographic and resource conditions?
3. **True Newcomer Influx**: When looking at all campaigns together across a year or country, how many genuinely new people are brought into the Wikimedia movement, and what percentage are recurring veterans?

---

## 🚀 Two Modern Interfaces

CampAnalytics is architected with a single shared analytical core powering two deployment models:

| Interface | Runtime | Primary Target | Design System & Highlights |
| :--- | :--- | :--- | :--- |
| **Flask Web App** | WSGI / Gunicorn | **Wikimedia Toolforge** | Fast, lightweight, GLAMtools visual coherence, Marine Petrol (`#183f54`) and Cyan Accent (`#72ded6`) palette, Project Korikath identity, zero client-side bloat. |
| **Streamlit App** | Streamlit Runtime | **Streamlit Cloud / Local** | Interactive prototyping dashboard, flat dark slate aesthetic (`#0f172a`), interactive Plotly charts, reactive series builder. |

Both interfaces consume identical data pipelines and mathematical models via [`analytics.py`](analytics.py) and [`config.json`](config.json).

---

## 🛠️ Four Core Analytical Modules

### 1. Retention Analytics
- **Selection Builder**: Select any combination of events (WLM, WLE, WLF, WLA, WLB, WLP, etc.), target countries (with a 1-click **Select All Global** option), and multi-year spans.
- **Directional Retention Matrix**: Measures exact account persistence between baseline edition $A$ and subsequent edition $B$:
  $$\text{Retention}(A \to B) = \left( \frac{|U_A \cap U_B|}{|U_A|} \right) \times 100\%$$
- **Three Visualization Models**:
  - **Data Table**: Tabular matrix with CSV download.
  - **Heatmap Matrix**: High-contrast Seaborn visualization on clean white canvas.
  - **Choropleth World Map**: Interactive Plotly projection of country-level average and median retention.

### 2. Health Evaluation (5-Dimension Scorecard)
- **Scorecard (0–100 Scale)**:
  - **Retention Index (35%)**: Share of returning participants from the baseline edition.
  - **Growth Capacity (20%)**: Share of first-time participant acquisition.
  - **Content Utility (20%)**: Share of uploaded files illustrated across Wikimedia projects (`prop=globalusage`).
  - **Quality Recognition (15%)**: Recognition rate under Commons quality categories (`Category:Quality images`, `Category:Featured pictures`).
  - **Contributor Diversity (10%)**: Community upload distribution parity (top 10% uploader concentration proxy).
- **Dynamic Regional Peer Benchmarking**: Replaces arbitrary global thresholds with upper-quartile envelopes computed dynamically from peer campaigns across 9 geographic clusters.
- **Diagnostic Insights**: Automatically generated qualitative recommendations and strengths tailored to regional performance.

### 3. New User Influx & Growth
- **Single-Campaign & Multi-Campaign Modes**:
  - **Single Campaign**: Follows consecutive editions of a specific program (e.g. `wlmde20` $\to$ `wlmde24`).
  - **All Campaigns Combined (`all`)**: Gathers participant sets across *all* active photography campaigns in that country/year, de-duplicates cross-participation, and isolates true movement-wide new contributor influx ($I_t$) versus returning movement veterans ($R_t$).
- **Per-Campaign Contribution Breakdown**: Identifies which specific campaigns (e.g. WLM vs WLE vs WLF) mobilized contributors within the composite annual cohort.
- **Longevity Segmentation**:
  - **1-Time Entrants**: One-off contributors active in only 1 edition.
  - **Repeaters**: Contributors participating in 2–3 editions.
  - **Core Veterans**: Sustained contributors returning for 4+ editions.
- **Dual-Axis Visualization**: Stacked newcomer/veteran volume bars accompanied by cumulative community pool progression line ($P_t$).

### 4. Methodology & Usage Guide
- Transparent mathematical formulations, regional normalization criteria, Commons Action API / Toolforge database failover specs, and usage guidelines for programmatic organizers.

---

## 🏗️ System Architecture

```
========================================================================================
                          CAMPANALYTICS — SYSTEM ARCHITECTURE
========================================================================================

      [ Wikimedia Community Analyst / Organiser Browser ]
                             │
                ┌────────────┴────────────┐
                ▼ (Port 5001)             ▼ (Port 8501)
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
      │  • All-Campaign Ecosystem Aggregator (Pseudo-Event 'all')  │
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
     │   Action API / DB      │       │   (12 Events ↔ 50 Nations  │
     │   (Live Meta-data)     │       │    ↔ 9 Regional Clusters)  │
     └────────────────────────┘       └────────────────────────────┘

========================================================================================
```

---

## 📐 Mathematical Formulations

### 1. Directional Contributor Retention
$$\text{Retention}(A \to B) = \left( \frac{|U_A \cap U_B|}{|U_A|} \right) \times 100\%$$

where $U_A$ and $U_B$ denote verified unique uploader accounts. Note that $\text{Retention}(A \to B) \neq \text{Retention}(B \to A)$ when cohort sizes differ.

### 2. Contributor Growth Capacity
$$\text{Growth}(A \to B) = \left( \frac{|U_B \setminus U_A|}{|U_B|} \right) \times 100\%$$

### 3. Single-Campaign Longitudinal Influx
For campaign editions $(C_1, C_2, \dots, C_T)$ with cohorts $(U_1, U_2, \dots, U_T)$:
- **New Influx ($I_t$)**: $I_t = \left| U_t \setminus \bigcup_{j < t} U_j \right|$
- **Returning ($R_t$)**: $R_t = \left| U_t \cap \bigcup_{j < t} U_j \right|$
- **Cumulative Pool ($P_t$)**: $P_t = \left| \bigcup_{j \le t} U_j \right|$
- **Newcomer Share %**: $\left( \frac{I_t}{|U_t|} \right) \times 100\%$

### 4. Multi-Campaign Ecosystem Influx & De-duplication
When assessing all campaigns combined (`all[country][year]`):
$$U_t = \bigcup_{e \in E} U_{e, t}$$
$$I_t = U_t \setminus \bigcup_{j < t} U_j, \quad R_t = U_t \cap \bigcup_{j < t} U_j, \quad P_t = \bigcup_{j \le t} U_j$$

where $E = \{\text{WLM}, \text{WLE}, \text{WLF}, \text{WLA}, \text{WLB}, \text{WLP}, \text{WLFood}, \text{WLPA}, \text{WLLH}, \text{WLS}, \dots\}$. Contributors active in multiple contests during the same year are de-duplicated, providing an accurate total count of distinct individuals brought into the Wikimedia movement annually.

---

## 💻 Installation & Local Usage

### Prerequisites
- Python 3.9+
- Git

### Clone Repository
```bash
git clone https://github.com/siddiquetanvir/CampAnalytics.git
cd CampAnalytics
```

### Install Dependencies
```bash
pip install -r requirements.txt
```

### Run Flask App (Toolforge Interface)
```bash
python3 app.py
```
*Visit:* `http://localhost:5001`

### Run Streamlit App
```bash
streamlit run streamlit_app.py
```
*Visit:* `http://localhost:8501`

---

## 🧪 Automated Test Suite

CampAnalytics includes a comprehensive 33-test regression suite covering routes, input normalization, GLAMtools CSS compliance, regional calibration, ecosystem aggregation, and charting:

```bash
PYTHONPATH=. python3 tests/test_app.py
```

```
.................................
----------------------------------------------------------------------
Ran 33 tests in 0.459s

OK
```

---

## 🌐 Toolforge Deployment

CampAnalytics is pre-configured for automated Toolforge deployment via Buildpacks:

1. **Log into Toolforge Bastion**:
   ```bash
   ssh <username>@login.toolforge.org
   become <toolname>
   ```
2. **Clone & Pull**:
   ```bash
   git clone https://github.com/siddiquetanvir/CampAnalytics.git src
   cd src
   ```
3. **Start Web Service**:
   ```bash
   toolforge webservice buildpack start
   ```

---

## 📁 Repository Layout

```
CampAnalytics/
├── app.py                   # Production Toolforge WSGI entrypoint
├── flask_app.py             # Flask application & GLAMtools route controllers
├── streamlit_app.py         # Streamlit interactive dashboard application
├── analytics.py             # Core analytics engine, cache, math & Commons API
├── app_config.py            # Global application settings, palette, and style loaders
├── config.json              # 12 Campaign events, 50 countries, 9 regional clusters
├── styles.css               # Toolforge Flask GLAMtools stylesheet (770+ lines)
├── streamlit_styles.css     # Dedicated Streamlit dark-mode stylesheet
├── Procfile                 # Toolforge / Heroku web process definition
├── requirements.txt         # Python package dependencies
├── templates/               # Jinja2 templates for Flask UI
│   ├── base.html            # Layout shell, top navbar, footer & Korikath brand
│   └── index.html           # 4-Mode Suite: Retention, Health, Influx, Methodology
└── tests/                   # Complete automated test suite
    └── test_app.py          # 33 passing regression, influx, and unit test cases
```

---

## 📜 License & Community Attribution

- **License**: Released under the **[GNU General Public License v2.0 or later (GPL-2.0+)](https://www.gnu.org/licenses/gpl-2.0.html)**.
- **Affiliation**: Built in support of **[Project Korikath](https://meta.wikimedia.org/wiki/Project_Korikath)**, an open community knowledge initiative on Meta-Wiki.
- **Data Source**: Live metadata queried directly from **[Wikimedia Commons](https://commons.wikimedia.org)** under open licenses.
