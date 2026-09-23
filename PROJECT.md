# Project: CampAnalytics Evaluation and Enhancement

## Architecture
CampAnalytics is a Flask-based analytical dashboard (`flask_app.py`, `analytics.py`, `campaign_cache.py`, `templates/`) deployed on Wikimedia Toolforge. It ingests campaign participant data from Wikimedia Commons via `ptools.toolforge.org` and the Commons Action API with exponential backoff and dual-tier caching (Toolforge MariaDB replica / local SQLite3 `campaign_cache.sqlite3`).
The frontend uses Apple/GLAMtools caliber typography (Inter font), glassmorphism components, KaTeX mathematical typesetting, responsive data tables, and visualization charts.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | 20-Metric Baseline Scorecard | Comprehensive audit across 4 pillars (20 metrics, 5 pts each) establishing 70.0/100.0 baseline | Survey / Baseline | R1 / Survey |
| 2 | Wikimedia Peer Comparative Benchmark | 25-capability matrix benchmark vs GLAMtools, Pageviews Analysis, PetScan, Quarry | Survey / Benchmark | R2 / Survey |
| 3 | Automated Flask Test Client Suite | Unit and integration test suite testing `/`, `/retention`, `/health`, `/influx`, `/methodology`, `/healthz`, `/tools` | M3 (Testing) | Acceptance Criteria |
| 4 | Universal Multi-Format Export Engine | CSV with provenance metadata header comments + MediaWiki Wikitext + JSON across Retention, Health, and Influx | M2 (Backend) & M1 (Frontend) | R1, R2 / Spec Miner |
| 5 | Interactive Data Table Suite | Client-side column sorting, live search filtering, pagination, and sticky mobile first column | M1 (Frontend) | R1, R2 / Spec Miner |
| 6 | KaTeX Display Math & Inline Cards | Fix unescaped HTML characters (`j < t` -> `j &lt; t`), add formula cards and composite equation to Health | M1 (Frontend) | R1, R2 / Evaluator |
| 7 | Dynamic URL State & Compact Sharing | Two-way `history.replaceState` sync and compact query string representation for large multi-campaign queries | M1 (Frontend) | R1, R2 / Spec Miner |
| 8 | Analytical Logic & Normalization Fixes | Heatmap diagonal 100% fix, zero-peer benchmark distortion protection, newcomer baseline year badge | M2 (Backend) | R1, R2 / Evaluator |
| 9 | Connection Pooling & Cache Bounding | urllib3 pool size matching concurrency (20 pool / 16 threads), bounded LRU in-memory caching | M2 (Backend) | R1, R2 / Evaluator |
| 10 | Security Headers & Error Handling | Flask custom 404/500 templates, security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`) | M2 (Backend) | R1 / Evaluator |
| 11 | Toolhub 2.0.0 Manifest & Attribution | Standard `toolhub.yaml` manifest and enhanced methodology citations | M2 (Backend) | R1 / Evaluator |
| 12 | Final 20-Metric Re-Evaluation | Rigorous audit confirming composite score >= 94/100 with itemized point gains | M4 (Verification) | Acceptance Criteria |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Survey, Baseline Scorecard & Peer Benchmark | Baseline audit (70.0/100) and peer tool benchmark matrix | none | DONE |
| M1 | Frontend UX, Tables & Visual Polish | Interactive tables, universal export UI, KaTeX math cards, responsive sticky layout | M0 | PLANNED |
| M2 | Backend Query, Analytics & Export Logic | CSV/Wikitext backend logic, normalization & diagonal fixes, connection pool, security headers, toolhub.yaml | M0 | PLANNED |
| M3 | E2E Automated Verification Test Suite | Pytest/unittest suite for all 5 core routes + exports + error handling, publish TEST_READY.md | M0 | PLANNED |
| M4 | Integration, Gate & Re-Evaluation (>= 94/100) | Run test suite, Reviewers, Challengers, Forensic Auditor, and re-score platform | M1, M2, M3 | PLANNED |

## Interface Contracts
### Export Engine Contract
- Endpoint / JS Function: `exportTableToFormat(tableId, format, filename, metadata)`
  - Formats supported: `'csv'` (with `# Tool: CampAnalytics`, `# Timestamp: ...`, `# Params: ...`), `'wikitext'` (`{| class="wikitable sortable" ... |}`), `'json'`
  - Available on all three modules: Retention (`retention-data-table`), Health (`health-data-table`), Influx (`influx-data-table`).

### Table Interactivity Contract
- Container: `.table-interactive-wrapper` with controls bar `.table-toolbar` containing `.table-search-input`, `.table-page-size`, and export buttons `.btn-export-group`.
- Attributes: `table.data-table` has `data-sortable="true"`. Clicking `th` toggles ascending/descending numeric/lexicographical sorting.

### Automated Test Contract (`tests/test_flask_app.py`)
- Python `unittest` suite using `flask_app.app.test_client()`.
- Verifies:
  1. `test_healthz`: `/healthz` returns 200 OK.
  2. `test_index_mode`: `/`, `/?mode=Tools`, `/?mode=Methodology` return 200.
  3. `test_retention_route`: `/retention` with default and target campaigns returns 200 and renders retention tables.
  4. `test_health_route`: `/health` with target event and region returns 200 and renders health dimensions.
  5. `test_influx_route`: `/influx` returns 200 and renders influx tables.
  6. `test_methodology_route`: `/methodology` returns 200 and renders LaTeX/KaTeX components.
  7. `test_error_handling`: 404 route returns styled 404 response.
  8. `test_security_headers`: Responses contain required security headers.

## Code Layout
- `flask_app.py`: Flask routing, view controllers, security headers, error handlers, export endpoints.
- `analytics.py`: Retention matrix calculation, health indexing, influx categorization, connection pooling, bounded caching.
- `templates/index.html`: Main dashboard template with interactive table toolbar, export buttons, KaTeX formula cards.
- `templates/base.html`: Base layout, navigation, typography, CSS/JS links.
- `styles.css`: Visual styling, responsive breakpoints, focus rings, table styling, sticky columns.
- `toolhub.yaml`: Modern Wikimedia Toolhub 2.0.0 manifest.
- `tests/test_flask_app.py`: Automated verification test suite.
