# CampAnalytics — Automated Test Infrastructure Specification

**Document Version**: 1.0.0  
**Target Repository**: `/Users/tanvir/WebApp` (`siddiquetanvir/CampAnalytics`)  
**Deployment Target**: Wikimedia Toolforge (`campanalytics.toolforge.org`)  
**Test Suite Path**: `/Users/tanvir/WebApp/tests/test_flask_app.py`  
**Test Runner**: Standard Library `unittest` Discovery (`python3 -m unittest discover`)  

---

## 1. Overview & Architecture

The CampAnalytics automated test infrastructure is designed to provide high-speed, deterministic, and self-contained verification of the Flask application across all routing tiers, analytical calculations, visual rendering components, error states, and security posture.

### Key Architectural Characteristics
- **Zero Third-Party Test Framework Dependencies**: Built on Python's built-in `unittest` module, allowing test execution in any standard Python 3.9+ runtime without requiring separate pytest installation.
- **Flask Native Test Client**: Tests interface directly with `flask_app.app.test_client()`, simulating HTTP GET and POST requests across standard WSGI request contexts without requiring a running web server or socket allocation.
- **Headless Visualization Execution**: Matplotlib is explicitly bound to the non-interactive `'Agg'` backend (`matplotlib.use('Agg')`), enabling rapid generation and base64 verification of PNG heatmaps and stacked barcharts in headless server environments.
- **Dual-Tier Offline Resilience**:
  1. Utilizes the local SQLite persistent cache (`campaign_cache.sqlite3`) with 1,025 pre-cached German WLM participant records (`wlmde22`, `wlmde23`, `wlmde24`, `wlmde25`) for end-to-end integration tests.
  2. Uses `unittest.mock.patch` for deterministic verification of multi-dimensional health scorecard calculations and dynamic regional peer normalization independent of external Wikimedia network connectivity.
- **Execution Performance**: The entire 35-test suite executes in under **1.0 second** (~0.94s).

---

## 2. Test Suite Structure & Layout

The testing infrastructure resides in `/Users/tanvir/WebApp/tests/`:

```
/Users/tanvir/WebApp/
├── tests/
│   ├── __init__.py                # Package marker
│   └── test_flask_app.py          # Primary test suite (6 test classes, 35 test methods)
├── flask_app.py                   # Target application under test
├── analytics.py                   # Mathematical and visualization engine
├── campaign_cache.sqlite3         # Local persistent SQLite cache fixture
├── TEST_INFRA.md                  # This infrastructure specification
└── TEST_READY.md                  # Test execution readiness report
```

### Test Class Organization

| Test Class | Target Component / Feature | Test Methods | Focus Areas |
|:---|:---|:---:|:---|
| `TestHealthzEndpoint` | Liveness / Readiness Probes | 1 | Kubernetes / Toolforge ingress probe responding with HTTP 200 and `'OK'`. |
| `TestIndexAndNavigationRoutes` | Navigation, Landing, Modes | 5 | Root (`/`), `/tools`, `/methodology`, mode query parameters (`?mode=Tools`, `?mode=Methodology`), and analytical route delegation. |
| `TestRetentionRoute` | Retention Analytics Suite | 10 | `/retention` GET/POST, Table view, Heatmap view (Base64 PNGs), Worldmap view (Plotly), Average vs Median toggles, single code notice, invalid syntax, empty inputs, and geographical scope notices. |
| `TestHealthRoute` | 5-Dimension Health Evaluation | 9 | `/health` GET/POST, previous-year vs custom baseline, regional peer scanning, mocked 5-dimension scorecard verification (Retention, Utility, Growth, Diversity, Quality, Stars), and input syntax validation. |
| `TestInfluxRoute` | New User Influx & Growth | 7 | `/influx` GET/POST, multi-year chronological series, stacked barchart generation, lifecycle contributor segmentation (1-time, repeaters, veterans), and input boundary edge cases. |
| `TestErrorHandlingAndSecurity` | HTTP Errors & Security Posture | 3 | HTTP 404 handler on undefined endpoints, standard `text/html` Content-Type verification, and response security header validation (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`). |

**Total Test Count**: **35 test methods**.

---

## 3. Test Execution Commands

### Primary Test Command (Project Standard)
Run the full test suite using standard unittest discovery:
```bash
python3 -m unittest discover -s tests -p "test_*.py"
```

### Verbose Mode
Display individual test method execution, docstrings, and execution timing:
```bash
python3 -m unittest discover -s tests -p "test_*.py" -v
```

### Targeted Test Execution
Run a specific test class:
```bash
python3 -m unittest tests.test_flask_app.TestRetentionRoute
```

Run a single specific test method:
```bash
python3 -m unittest tests.test_flask_app.TestHealthRoute.test_health_mocked_scorecard_dimensions
```

---

## 4. Coverage & Verification Mapping

### R1 & R2 Feature Verification Matrix

| Acceptance Criterion | Covered By Test Method(s) | Verified Observable Output |
|:---|:---|:---|
| `/healthz` probe operational | `TestHealthzEndpoint.test_healthz` | Status 200, response body is `'OK'`. |
| Root index & modes operational | `TestIndexAndNavigationRoutes.test_index_mode`<br>`TestIndexAndNavigationRoutes.test_index_mode_delegation` | Status 200, renders landing cards, delegates properly to analytical views. |
| Dedicated `/tools` & `/methodology` | `TestIndexAndNavigationRoutes.test_tools_route`<br>`TestIndexAndNavigationRoutes.test_methodology_route` | Status 200, KaTeX scripts/styles and LaTeX mathematical formulas rendered. |
| Retention Data Table View | `TestRetentionRoute.test_retention_route` | Status 200, HTML table with `class="data-table"` containing participant statistics. |
| Retention Heatmap View | `TestRetentionRoute.test_retention_heatmap_view` | Status 200, `data:image/png;base64,` inline raster image generated. |
| Retention Worldmap View | `TestRetentionRoute.test_retention_worldmap_view` | Status 200, Plotly CDN script and choropleth container rendered. |
| Retention Edge Cases & Notices | `TestRetentionRoute.test_retention_single_campaign_edge_case`<br>`TestRetentionRoute.test_retention_invalid_code_edge_case`<br>`TestRetentionRoute.test_retention_out_of_scope_edge_case` | Status 200, contextual warning banners rendered without HTTP 500 crashes. |
| Community Health Evaluation | `TestHealthRoute.test_health_route`<br>`TestHealthRoute.test_health_with_cached_data` | Status 200, evaluates target event against baseline and regional cluster. |
| 5-Dimension Scorecard & Stars | `TestHealthRoute.test_health_mocked_scorecard_dimensions` | Status 200, renders Retention Index, Content Utility, Growth Capacity, Contributor Diversity, Quality Recognition, stars (`★`), and overall composite score. |
| Contributor Influx & Barchart | `TestInfluxRoute.test_influx_route`<br>`TestInfluxRoute.test_influx_with_parameters` | Status 200, dual-axis stacked barchart (base64 PNG) and lifecycle metrics rendered. |
| 404 Error Handling | `TestErrorHandlingAndSecurity.test_error_handling` | Returns HTTP 404 on unmapped endpoints. |
| Security Response Headers | `TestErrorHandlingAndSecurity.test_security_headers` | Verifies adherence to secure header defaults (`nosniff`, `DENY`/`SAMEORIGIN`, `strict-origin-when-cross-origin`). |

---

## 5. Test Maintenance & Extensibility

When implementing additional features or routes:
1. **Adding New Routes**: Add new test methods to `TestIndexAndNavigationRoutes` or create a new dedicated `unittest.TestCase` subclass.
2. **Export Endpoints**: When CSV/Wikitext backend export routes are added (Milestone M2), add test methods verifying HTTP status 200, `Content-Disposition: attachment; filename=...`, and MIME types (`text/csv`, `text/plain`).
3. **Security Headers**: If custom security headers (`X-Content-Type-Options`, `Content-Security-Policy`) are applied via Flask `@app.after_request`, `test_security_headers` will automatically validate them.
