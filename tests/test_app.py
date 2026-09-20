import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/matplotlib')

import unittest
from unittest.mock import patch
import json
import re
import pandas as pd
import numpy as np

# Ensure headless Agg backend
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from flask_app import app
import analytics
import app_config

class CampaignSuiteTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    # =========================================================================
    # 1. ROUTE STATUS CODES & TOLERANCE
    # =========================================================================
    def test_routes_status_get_index(self):
        """GET / should return 200 OK and default to Methodology mode."""
        res = self.client.get('/')
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('Methodology &amp; Usage Guide', html)

    def test_routes_status_get_modes(self):
        """GET / with ?mode= query parameter should return 200 OK for all modes."""
        for mode in ['Methodology', 'Retention Analytics', 'Health Evaluation', 'New User Influx']:
            res = self.client.get(f'/?mode={mode}')
            self.assertEqual(res.status_code, 200)

    def test_routes_status_retention_get_and_post(self):
        """/retention must accept both GET and POST requests with 200 OK."""
        # GET request (direct visit / bookmark)
        res_get = self.client.get('/retention')
        self.assertEqual(res_get.status_code, 200)
        html_get = res_get.data.decode('utf-8')
        self.assertIn('Retention Analytics', html_get)
        self.assertIn('What to look up · Selection Builder', html_get)

        # POST request (form submission)
        with patch.object(analytics, 'fetch_all_concurrently') as mock_fetch:
            mock_fetch.return_value = {
                'wlmde21': {'user1', 'user2', 'user3'},
                'wlmde22': {'user2', 'user3', 'user4'}
            }
            res_post = self.client.post('/retention', data={
                'target_campaigns': 'wlmde21 wlmde22',
                'view_mode': 'Table'
            })
            self.assertEqual(res_post.status_code, 200)
            html_post = res_post.data.decode('utf-8')
            self.assertIn('Analysis Output: Table Model', html_post)
            self.assertIn('Germany', html_post)

    def test_routes_status_health_get_and_post(self):
        """/health must accept both GET and POST requests with 200 OK."""
        # GET request
        res_get = self.client.get('/health')
        self.assertEqual(res_get.status_code, 200)
        html_get = res_get.data.decode('utf-8')
        self.assertIn('Health Evaluation', html_get)
        self.assertIn('Target Campaign Registry Code', html_get)

        # POST request
        with patch.object(analytics, 'fetch_all_concurrently') as mock_fetch, \
             patch.object(analytics, 'fetch_structural_metrics_concurrently') as mock_struct:
            mock_fetch.return_value = {
                'wlmbd24': {'user1', 'user2', 'user3', 'user4'},
                'wlmbd23': {'user2', 'user3', 'user5'},
                'wlmin24': {'user10', 'user11'},
                'wlmin23': {'user10', 'user12'}
            }
            mock_struct.return_value = {
                'wlmbd24': {'quality_image_share': 5.0, 'top10_uploader_share': 45.0, 'usage_share': 12.0, 'total_uploads': 150}
            }
            res_post = self.client.post('/health', data={
                'target_event': 'wlmbd24',
                'comp_mode': 'Previous Year Baseline',
                'region': 'South Asia'
            })
            self.assertEqual(res_post.status_code, 200)
            html_post = res_post.data.decode('utf-8')
            self.assertIn('Health Evaluation Scorecard', html_post)
            self.assertIn('WLMBD24', html_post)

    def test_routes_status_influx_get_and_post(self):
        """/influx must accept both GET and POST requests with 200 OK."""
        # GET request
        res_get = self.client.get('/influx')
        self.assertEqual(res_get.status_code, 200)
        html_get = res_get.data.decode('utf-8')
        self.assertIn('Year-over-Year New User Influx', html_get)
        self.assertIn('What to look up · Campaign Influx Builder', html_get)

        # POST request with mock data
        with patch.object(analytics, 'fetch_all_concurrently') as mock_fetch:
            mock_fetch.return_value = {
                'wlmbd22': {'u1', 'u2', 'u3'},
                'wlmbd23': {'u2', 'u3', 'u4', 'u5'},
                'wlmbd24': {'u3', 'u5', 'u6'}
            }
            res_post = self.client.post('/influx', data={
                'influx_codes': 'wlmbd22 wlmbd23 wlmbd24'
            })
            self.assertEqual(res_post.status_code, 200)
            html_post = res_post.data.decode('utf-8')
            self.assertIn('Year-over-Year Influx Breakdown Data Table', html_post)
            self.assertIn('Cumulative Community Footprint', html_post)
            self.assertIn('data:image/png;base64,', html_post)

    def test_routes_status_methodology(self):
        """GET /methodology route should return 200 OK."""
        res = self.client.get('/methodology')
        self.assertEqual(res.status_code, 200)
        self.assertIn('Methodology &amp; Usage Guide', res.data.decode('utf-8'))

    # =========================================================================
    # 2. TOP NAVBAR & BRANDING
    # =========================================================================
    def test_top_navbar_branding_and_logo(self):
        """Verify GLAMtools top navbar: dark teal bar, two-tone branding, and active tab."""
        res = self.client.get('/')
        html = res.data.decode('utf-8')
        
        # Dark teal top navbar container
        self.assertIn('class="top-navbar"', html)
        
        # Two-tone brand logo: "Camp" bold white and "Analytics" accent
        self.assertIn('class="brand-bold">Camp</span>', html)
        self.assertIn('class="brand-accent">Analytics</span>', html)
        
        # Navigation tabs
        self.assertIn('Retention Analytics', html)
        self.assertIn('Health Evaluation', html)
        self.assertIn('Methodology', html)

        # Working GitHub link icon to repository
        self.assertIn('https://github.com/siddiquetanvir/CampAnalytics', html)
        self.assertIn('GitHub', html)

        # Project Korikath Logo with intact source replacing Docs
        self.assertIn('Project_Korikath_Logo-dark.svg', html)
        self.assertIn('Project Korikath', html)

    def test_navbar_active_tab_state(self):
        """Verify active underline indicator applies to the corresponding route."""
        # Retention
        res_ret = self.client.get('/retention')
        html_ret = res_ret.data.decode('utf-8')
        self.assertIn('href="/retention" class="nav-tab-link active">Retention Analytics</a>', html_ret)

        # Health
        res_health = self.client.get('/health')
        html_health = res_health.data.decode('utf-8')
        self.assertIn('href="/health" class="nav-tab-link active">Health Evaluation</a>', html_health)

        # Methodology
        res_meth = self.client.get('/?mode=Methodology')
        html_meth = res_meth.data.decode('utf-8')
        self.assertIn('href="/?mode=Methodology" class="nav-tab-link active">Methodology</a>', html_meth)

    # =========================================================================
    # 3. GLAMTOOLS VISUAL THEME & DARK MODE PURGE
    # =========================================================================
    def test_dark_mode_purged_from_stylesheet(self):
        """Ensure all dark mode tokens and legacy Streamlit rules are purged from styles.css."""
        css_path = os.path.join(os.path.dirname(__file__), '..', 'styles.css')
        with open(css_path, 'r', encoding='utf-8') as f:
            css_content = f.read()

        dark_tokens = ['#0a1526', '#13284a', '#0f172a', '#1e293b', '#101f2f', '.stApp', 'stSidebar']
        for token in dark_tokens:
            self.assertNotIn(token, css_content, f"Gloomy dark token '{token}' found in styles.css!")

    def test_glamtools_tokens_in_app_config(self):
        """Verify color variables defined in app_config.py."""
        self.assertEqual(app_config.NAV_TEAL, "#183f54")
        self.assertIn(app_config.NAV_ACCENT, ["#72ded6", "#7ce0d3", "#98f5e1"])
        self.assertEqual(app_config.BG_CANVAS, "#ffffff")
        self.assertEqual(app_config.TEXT_INK, "#202122")
        self.assertEqual(app_config.TEXT_MUTED, "#54595d")
        self.assertEqual(app_config.BORDER_COLOR, "#e0e0e0")
        self.assertEqual(app_config.WIKI_BLUE, "#3366cc")
        self.assertEqual(app_config.WIKI_BLUE_HOVER, "#14428e")

    def test_glamtools_panels_in_rendered_html(self):
        """Verify structured GLAMtools panels ('glam-panel') in rendered output."""
        res = self.client.get('/retention')
        html = res.data.decode('utf-8')
        self.assertIn('class="glam-panel"', html)
        self.assertIn('class="glam-panel-header"', html)
        self.assertIn('class="glam-panel-body"', html)

    # =========================================================================
    # 4. TOOLFORGE FOOTER & GPL-2.0+ LICENSING
    # =========================================================================
    def test_toolforge_footer(self):
        """Verify Toolforge footer with attribution, GPL-2.0+ license, and links."""
        res = self.client.get('/')
        html = res.data.decode('utf-8')
        self.assertIn('toolforge-footer', html)
        self.assertIn('Wikimedia Toolforge', html)
        self.assertIn('GNU General Public License v2.0 or later (GPL-2.0+)', html)
        self.assertIn('https://github.com/siddiquetanvir/CampAnalytics', html)

    # =========================================================================
    # 5. BUILDER-FIRST RETENTION WORKFLOW & PRESETS
    # =========================================================================
    def test_retention_builder_elements(self):
        """Verify builder controls: event pills, country dropdown, year range, auto-synced input, and presets."""
        res = self.client.get('/retention')
        html = res.data.decode('utf-8')

        # Builder panel header
        self.assertIn('What to look up · Selection Builder', html)

        # Event pills
        for event_key in ['wlm', 'wle', 'wlf', 'wlb']:
            self.assertIn(f'id="evt-{event_key}"', html)

        # Country dropdown & year inputs
        self.assertIn('id="builder_country"', html)
        self.assertIn('id="builder_yr_start"', html)
        self.assertIn('id="builder_yr_end"', html)

        # Auto-synced target code input
        self.assertIn('id="target_campaigns"', html)

        # Quick preset examples
        self.assertIn('wlmde21 wlmde22', html)
        self.assertIn('wlmbd22 wlmbd23', html)
        self.assertIn('wlein21 wlein22', html)
        self.assertIn('loadRetentionPreset', html)

        # Visualization Model radios
        self.assertIn('value="Table"', html)
        self.assertIn('value="Heatmap"', html)
        self.assertIn('value="Worldmap"', html)

    # =========================================================================
    # 6. RETENTION DATA VISUALIZATIONS & COMPUTATIONS
    # =========================================================================
    def test_compute_retention_percentages(self):
        """Test directional retention percentage math: (|A ∩ B| / |A|) * 100."""
        events = {
            'wlmde21': {'alice', 'bob', 'carol', 'dave'},
            'wlmde22': {'bob', 'carol', 'eve'}
        }
        # 2 overlapping / 4 source = 50.0%
        # 2 overlapping / 3 source = 66.666...%
        percentages = analytics.compute_retention_percentages(events)
        self.assertEqual(len(percentages), 2)
        self.assertAlmostEqual(percentages[0], 50.0, places=1)
        self.assertAlmostEqual(percentages[1], 66.67, places=1)

    def test_build_global_table(self):
        """Test Pandas global table generation."""
        valid_countries = {
            'de': {
                'wlmde21': {'u1', 'u2', 'u3', 'u4'},
                'wlmde22': {'u2', 'u3', 'u5'}
            }
        }
        df = analytics.build_global_table(valid_countries)
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertIn('Country', df.columns)
        self.assertIn('Avg Retention (%)', df.columns)
        self.assertEqual(df.iloc[0]['Country'], 'Germany')

    def test_build_world_data(self):
        """Test world data construction."""
        valid_countries = {
            'bd': {
                'wlmbd22': {'u1', 'u2'},
                'wlmbd23': {'u2', 'u3'}
            }
        }
        df_avg = analytics.build_world_data(valid_countries, 'Average')
        self.assertFalse(df_avg.empty)
        self.assertEqual(df_avg.iloc[0]['Country'], 'Bangladesh')
        self.assertEqual(df_avg.iloc[0]['Retention (%)'], 50.0)

    def test_create_heatmap_figure(self):
        """Test Seaborn heatmap generation on clean bright canvas."""
        events = {
            'wlmde21': {'u1', 'u2', 'u3'},
            'wlmde22': {'u2', 'u3', 'u4'}
        }
        fig = analytics.create_heatmap(events, 'Germany')
        self.assertIsInstance(fig, plt.Figure)
        # Background must be bright #ffffff
        self.assertEqual(matplotlib.colors.to_hex(fig.get_facecolor()), '#ffffff')
        plt.close(fig)

    def test_create_worldmap_plotly(self):
        """Test Plotly choropleth map themed to bright natural earth aesthetic."""
        df = pd.DataFrame([
            {'Country': 'Germany', 'Retention (%)': 45.2, 'Occurrences Compared': 2},
            {'Country': 'Bangladesh', 'Retention (%)': 52.0, 'Occurrences Compared': 2}
        ])
        fig = analytics.create_worldmap(df, 'Average')
        layout = fig.layout
        self.assertEqual(layout.paper_bgcolor, '#ffffff')
        self.assertEqual(layout.plot_bgcolor, '#ffffff')
        self.assertEqual(layout.geo.landcolor, '#e8ecef')
        self.assertEqual(layout.geo.lakecolor, '#ffffff')
        self.assertEqual(layout.font.color, analytics.TEXT_INK)

    # =========================================================================
    # 7. HEALTH EVALUATION CONFIGURATION & PRESETS
    # =========================================================================
    def test_health_evaluation_configuration_panel(self):
        """Verify Health 'What to look up' panel with parameters and presets."""
        res = self.client.get('/health')
        html = res.data.decode('utf-8')

        self.assertIn('Target Campaign Registry Code', html)
        self.assertIn('Benchmark Baseline', html)
        self.assertIn('Previous Year Baseline (Automatic)', html)
        self.assertIn('Custom Baseline Campaign', html)
        self.assertIn('Geographic Standardization Framework', html)
        self.assertIn('South Asia', html)
        self.assertIn('Northern &amp; Western Europe', html)

        # Preset benchmarks
        self.assertIn('wlmbd24', html)
        self.assertIn('wlmde22', html)
        self.assertIn('loadHealthPreset', html)

    # =========================================================================
    # 8. HEALTH SCORECARD, STAR RATINGS & COHORT FOOTPRINTS
    # =========================================================================
    def test_calculate_stars(self):
        """Test 5-star rating conversion logic."""
        stars_high, count_high = analytics.calculate_stars(95)
        self.assertEqual(stars_high, "★★★★★")
        self.assertEqual(count_high, 5)

        stars_mid, count_mid = analytics.calculate_stars(60)
        self.assertEqual(stars_mid, "★★★☆☆")
        self.assertEqual(count_mid, 3)

        stars_low, count_low = analytics.calculate_stars(15)
        self.assertEqual(stars_low, "★☆☆☆☆")
        self.assertEqual(count_low, 1)

    def test_generate_health_metrics_engine(self):
        """Test 5-dimension scorecard computation: Retention 35%, Growth 20%, Usage 20%, Quality 15%, Diversity 10%."""
        target_users = {'u1', 'u2', 'u3', 'u4', 'u5'}
        base_users = {'u2', 'u3', 'u6', 'u7'}
        target_structural = {
            'quality_image_share': 4.0,
            'top10_uploader_share': 50.0,
            'usage_share': 10.0,
            'total_uploads': 200
        }
        benchmarks = {
            'retention': 40.0,
            'growth': 50.0,
            'quality': 3.0,
            'diversity': 60.0,
            'usage': 8.0
        }
        metrics = analytics.generate_health_metrics(target_users, base_users, target_structural, benchmarks)
        
        # Verify all 5 dimensions exist plus Overall
        self.assertIn('Retention', metrics)
        self.assertIn('Growth', metrics)
        self.assertIn('Usage', metrics)
        self.assertIn('Quality', metrics)
        self.assertIn('Diversity', metrics)
        self.assertIn('Overall', metrics)

        # Verify Overall is between 0 and 100
        self.assertTrue(0 <= metrics['Overall'] <= 100)

    def test_health_scorecard_and_footprints_rendered(self):
        """Verify scorecard cards, star displays, and cohort footprints rendered in HTML."""
        with patch.object(analytics, 'fetch_all_concurrently') as mock_fetch, \
             patch.object(analytics, 'fetch_structural_metrics_concurrently') as mock_struct:
            mock_fetch.return_value = {
                'wlmbd24': {'u1', 'u2', 'u3'},
                'wlmbd23': {'u2', 'u3', 'u4'}
            }
            mock_struct.return_value = {
                'wlmbd24': {'quality_image_share': 2.5, 'top10_uploader_share': 55.0, 'usage_share': 8.0, 'total_uploads': 80}
            }
            res = self.client.post('/health', data={
                'target_event': 'wlmbd24',
                'comp_mode': 'Previous Year Baseline',
                'region': 'South Asia'
            })
            html = res.data.decode('utf-8')

            # Scorecard header and 5 dimensions
            self.assertIn('Health Evaluation Scorecard', html)
            self.assertIn('Retention Index', html)
            self.assertIn('Growth Capacity', html)
            self.assertIn('Content Utility', html)
            self.assertIn('Quality Images', html)
            self.assertIn('Diversity Index', html)

            # Footprint stats
            self.assertIn('Target Cohort Participants', html)
            self.assertIn('Baseline Reference Participants', html)
            self.assertIn('Retained Contributors (Overlap)', html)

    # =========================================================================
    # 9. DIAGNOSTIC INSIGHTS PRESENTATION
    # =========================================================================
    def test_generate_insights_callouts(self):
        """Test generation and styling of peer-relative diagnostic insights."""
        metrics = {
            'Retention': {'score': 85.0, 'raw': '55.0%'},
            'Growth': {'score': 45.0, 'raw': '30.0%'},
            'Usage': {'score': 70.0, 'raw': 15.0},
            'Quality': {'score': 40.0, 'raw': 1.0},
            'Diversity': {'score': 80.0, 'raw': 40.0}
        }
        benchmarks = {'retention': 35.0, 'growth': 50.0, 'usage': 10.0, 'quality': 3.0, 'diversity': 60.0}
        insights = analytics.generate_insights(metrics, 'South Asia', benchmarks)
        self.assertIsInstance(insights, list)
        self.assertTrue(len(insights) > 0)
        self.assertTrue(any('South Asia' in ins for ins in insights))

    # =========================================================================
    # 10. METHODOLOGY DOCUMENTATION FRESHNESS
    # =========================================================================
    def test_methodology_guide_and_quick_cards(self):
        """Verify GLAMtools-style quick start cards, no stale sidebar references, and clear formulas."""
        res = self.client.get('/?mode=Methodology')
        html = res.data.decode('utf-8')

        # Quick-start cards
        self.assertIn('methodology-cards-grid', html)
        self.assertIn('Retention Analytics', html)
        self.assertIn('Health Evaluation', html)
        self.assertIn('Commons Data Pipeline', html)
        self.assertIn('Launch Retention Builder →', html)
        self.assertIn('Launch Health Evaluator →', html)

        # No stale references to sidebar
        self.assertNotIn('sidebar', html.lower(), "Found outdated reference to 'sidebar' in Methodology!")

        # Mathematical formulas documented
        self.assertIn('Retention(A → B) = (|U_A ∩ U_B| / |U_A|) × 100%', html)
        self.assertIn('Growth(A → B) = (|U_B \\setminus U_A| / |U_B|) × 100%', html)
        self.assertIn('Influx(C_t)', html)
        self.assertIn('Retention Index (35%)', html)
        self.assertIn('Growth Capacity (20%)', html)
        self.assertIn('Content Utility (20%)', html)
        self.assertIn('Quality Images (15%)', html)
        self.assertIn('Contributor Diversity (10%)', html)

    # =========================================================================
    # 11. ERROR HANDLING & STATE RECOVERY
    # =========================================================================
    def test_error_handling_invalid_retention_parameters(self):
        """Verify friendly notice banner on missing/invalid retention parameters."""
        res = self.client.post('/retention', data={'target_campaigns': 'invalidcode123'})
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('notice-banner', html)
        self.assertIn('Please provide valid campaign codes', html)

    def test_error_handling_invalid_health_parameters(self):
        """Verify friendly notice banner on syntax anomaly in health target code."""
        res = self.client.post('/health', data={'target_event': 'invalid!!!'})
        self.assertEqual(res.status_code, 200)
        html = res.data.decode('utf-8')
        self.assertIn('notice-banner', html)
        self.assertIn('Anomaly detected in target campaign code syntax', html)

    # =========================================================================
    # 12. TOOLFORGE PRODUCTION READINESS & STREAMLIT DECOUPLING
    # =========================================================================
    def test_streamlit_completely_decoupled(self):
        """Verify analytics.py does not import streamlit and uses headless Matplotlib Agg."""
        analytics_path = os.path.join(os.path.dirname(__file__), '..', 'analytics.py')
        with open(analytics_path, 'r', encoding='utf-8') as f:
            analytics_code = f.read()

        # Must not contain import streamlit
        self.assertNotIn('import streamlit', analytics_code)
        self.assertNotIn('st.progress', analytics_code)
        self.assertNotIn('@st.cache', analytics_code)

        # Matplotlib headless Agg configured
        self.assertIn("matplotlib.use('Agg')", analytics_code)

    def test_in_memory_timed_cache(self):
        """Verify in-memory timed_cache decorator works properly."""
        call_count = 0

        @analytics.timed_cache(ttl=60)
        def sample_func(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        # First call calculates
        res1 = sample_func(5)
        self.assertEqual(res1, 10)
        self.assertEqual(call_count, 1)

        # Second call returns from cache
        res2 = sample_func(5)
        self.assertEqual(res2, 10)
        self.assertEqual(call_count, 1)

    # =========================================================================
    # 13. YEAR-OVER-YEAR INFLUX ANALYTICS
    # =========================================================================
    def test_compute_yoy_influx(self):
        """Test compute_yoy_influx algorithm with multi-year mock data."""
        with patch.object(analytics, 'fetch_all_concurrently') as mock_fetch:
            mock_fetch.return_value = {
                'wlmbd22': {'alice', 'bob', 'charlie'},
                'wlmbd23': {'bob', 'charlie', 'david', 'eve'},
                'wlmbd24': {'charlie', 'eve', 'frank'}
            }
            res = analytics.compute_yoy_influx(['wlmbd22', 'wlmbd23', 'wlmbd24'])
            
            self.assertEqual(len(res['records']), 3)
            # Year 22: 3 total, all 3 new, 0 returning
            r0 = res['records'][0]
            self.assertEqual(r0['year'], 2022)
            self.assertEqual(r0['total_active'], 3)
            self.assertEqual(r0['new_contributors'], 3)
            self.assertEqual(r0['returning_contributors'], 0)
            self.assertEqual(r0['newcomer_share_pct'], 100.0)
            self.assertEqual(r0['cumulative_pool'], 3)

            # Year 23: 4 total, 2 returning (bob, charlie), 2 new (david, eve)
            r1 = res['records'][1]
            self.assertEqual(r1['year'], 2023)
            self.assertEqual(r1['total_active'], 4)
            self.assertEqual(r1['new_contributors'], 2)
            self.assertEqual(r1['returning_contributors'], 2)
            self.assertEqual(r1['newcomer_share_pct'], 50.0)
            self.assertEqual(r1['retention_from_prev_pct'], 66.7) # 2/3
            self.assertEqual(r1['cumulative_pool'], 5) # alice, bob, charlie, david, eve

            # Year 24: 3 total, 2 returning (charlie, eve), 1 new (frank)
            r2 = res['records'][2]
            self.assertEqual(r2['year'], 2024)
            self.assertEqual(r2['total_active'], 3)
            self.assertEqual(r2['new_contributors'], 1)
            self.assertEqual(r2['returning_contributors'], 2)
            self.assertEqual(r2['cumulative_pool'], 6)

            # Lifecycle profile
            # alice: 1 time
            # bob: 2 times (22, 23)
            # charlie: 3 times (22, 23, 24)
            # david: 1 time
            # eve: 2 times (23, 24)
            # frank: 1 time
            # 1-time: 3 (alice, david, frank)
            # repeat 2-3: 3 (bob, charlie, eve)
            # core 4+: 0
            lifecycle = res['lifecycle']
            self.assertEqual(lifecycle['one_time'], 3)
            self.assertEqual(lifecycle['repeat_2_3'], 3)
            self.assertEqual(lifecycle['core_4_plus'], 0)

            # Summary metrics
            summary = res['summary']
            self.assertEqual(summary['total_unique_community'], 6)
            self.assertEqual(summary['latest_total'], 3)

    def test_influx_charts_generation(self):
        """Test Matplotlib base64 and Plotly chart generation for Influx."""
        records = [
            {
                'year': 2022, 'code': 'wlmbd22', 'total_active': 10,
                'new_contributors': 10, 'returning_contributors': 0,
                'newcomer_share_pct': 100.0, 'retention_from_prev_pct': 0.0,
                'yoy_growth_pct': 0.0, 'new_to_veteran_ratio': 'N/A',
                'cumulative_pool': 10
            },
            {
                'year': 2023, 'code': 'wlmbd23', 'total_active': 15,
                'new_contributors': 8, 'returning_contributors': 7,
                'newcomer_share_pct': 53.3, 'retention_from_prev_pct': 70.0,
                'yoy_growth_pct': 50.0, 'new_to_veteran_ratio': '1.14',
                'cumulative_pool': 18
            }
        ]
        # Matplotlib PNG Base64
        import flask_app
        fig = analytics.create_influx_barchart(records, title="Test Influx Chart")
        self.assertIsNotNone(fig)
        chart_b64 = f"data:image/png;base64,{flask_app.fig_to_base64(fig)}"
        self.assertTrue(chart_b64.startswith("data:image/png;base64,"))

        # Plotly Figure
        fig = analytics.create_influx_plotly_chart(records, title="Test Plotly Influx")
        self.assertIsNotNone(fig)
        self.assertEqual(len(fig.data), 3) # New, Returning, Cumulative line

    def test_new_wiki_loves_events_taxonomy(self):
        """Test category resolution for newly added Wiki Loves campaigns."""
        self.assertEqual(analytics.code_to_category('wlang22'), 'Images_from_Wiki_Loves_Africa_2022_in_Nigeria')
        self.assertEqual(analytics.code_to_category('wlfoodin22'), 'Images_from_Wiki_Loves_Food_2022_in_India')
        self.assertEqual(analytics.code_to_category('wlsde24'), 'Images_from_Wiki_Loves_Sport_2024_in_Germany')
        self.assertEqual(analytics.code_to_category('wlpa21'), 'Images_from_Wiki_Loves_Public_Art_2021')
        self.assertEqual(analytics.code_to_category('wllh23'), 'Images_from_Wiki_Loves_Living_Heritage_2023')
        # Composite pseudo-event 'all' should resolve to None for category
        self.assertIsNone(analytics.code_to_category('allbd22'))

    def test_all_campaigns_composite_influx_aggregation(self):
        """Test multi-campaign ecosystem aggregation and breakdown in compute_yoy_influx."""
        with patch.object(analytics, 'fetch_all_concurrently') as mock_fetch:
            mock_fetch.return_value = {
                'allbd22': {'user_a', 'user_b', 'user_c'},
                'allbd23': {'user_b', 'user_c', 'user_d', 'user_e'}
            }
            # Also simulate composite breakdown storage
            analytics._COMPOSITE_BREAKDOWNS['allbd22'] = {'Monuments': 2, 'Earth': 1}
            analytics._COMPOSITE_BREAKDOWNS['allbd23'] = {'Monuments': 3, 'Earth': 2, 'Folklore': 1}

            res = analytics.compute_yoy_influx(['allbd22', 'allbd23'])
            self.assertEqual(len(res['records']), 2)
            
            # Edition 2022
            r22 = res['records'][0]
            self.assertEqual(r22['year'], 2022)
            self.assertEqual(r22['total_active'], 3)
            self.assertEqual(r22['new_contributors'], 3)
            self.assertEqual(r22['returning_contributors'], 0)
            self.assertEqual(r22['cumulative_pool'], 3)
            self.assertIn('Earth: 1', r22['breakdown_str'])
            self.assertIn('Monuments: 2', r22['breakdown_str'])

            # Edition 2023
            r23 = res['records'][1]
            self.assertEqual(r23['year'], 2023)
            self.assertEqual(r23['total_active'], 4)
            self.assertEqual(r23['new_contributors'], 2) # user_d, user_e
            self.assertEqual(r23['returning_contributors'], 2) # user_b, user_c
            self.assertEqual(r23['cumulative_pool'], 5) # a, b, c, d, e

            # Summary
            self.assertEqual(res['summary']['total_unique_community'], 5)

    def test_influx_route_with_all_composite_code(self):
        """Test /influx POST submission with composite 'all' campaign sequence."""
        with patch.object(analytics, 'fetch_all_concurrently') as mock_fetch:
            mock_fetch.return_value = {
                'allbd22': {'u1', 'u2', 'u3'},
                'allbd23': {'u2', 'u3', 'u4'}
            }
            res_post = self.client.post('/influx', data={
                'influx_event_type': 'all',
                'influx_country': 'bd',
                'influx_codes': 'allbd22 allbd23'
            })
            self.assertEqual(res_post.status_code, 200)
            html = res_post.data.decode('utf-8')
            self.assertIn('All Campaigns Combined', html)
            self.assertIn('Year-over-Year Influx Breakdown Data Table', html)
            self.assertIn('Cumulative Community Footprint', html)

if __name__ == '__main__':
    unittest.main()
