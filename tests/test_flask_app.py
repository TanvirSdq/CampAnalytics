"""
Automated Test Suite for CampAnalytics Flask Application.

This module provides comprehensive unit and integration tests covering:
- Liveness check endpoint (/healthz)
- Navigation and mode-switching routes (/, /tools, /methodology, /?mode=...)
- Retention Analytics route (/retention) across Table, Heatmap, Worldmap views
- Community Health Evaluation route (/health) with baseline comparison & regional peers
- Contributor Influx route (/influx) with multi-year progression & lifecycle segmentation
- Error handling for invalid / non-existent endpoints (404)
- Security response headers inspection
- Adversarial query edge cases (empty strings, malformed syntax, single editions, out-of-scope codes)
"""

import logging
import unittest
from unittest.mock import patch
import flask_app

# Suppress runtime logger output for expected fallback/network handling during tests
logging.disable(logging.CRITICAL)


class BaseTestCase(unittest.TestCase):
    """Base test case providing configured test client and helpers."""

    def setUp(self):
        flask_app.app.config['TESTING'] = True
        self.client = flask_app.app.test_client()


class TestHealthzEndpoint(BaseTestCase):
    """Tests for the /healthz liveness probe endpoint."""

    def test_healthz(self):
        """Verify /healthz returns HTTP 200 OK for Kubernetes/Toolforge probes."""
        response = self.client.get('/healthz')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.decode('utf-8').strip(), 'OK')


class TestIndexAndNavigationRoutes(BaseTestCase):
    """Tests for root index (/), /tools, /methodology, and mode switching."""

    def test_index_mode(self):
        """Verify root route (/) and mode query parameter switching."""
        # Bare root route defaults to Tools view
        res_root = self.client.get('/')
        self.assertEqual(res_root.status_code, 200)
        root_text = res_root.data.decode('utf-8')
        self.assertIn('CampAnalytics', root_text)

        # Explicit mode=Tools
        res_tools = self.client.get('/?mode=Tools')
        self.assertEqual(res_tools.status_code, 200)
        tools_text = res_tools.data.decode('utf-8')
        self.assertTrue('Campaign Analytics' in tools_text or 'Tool' in tools_text)

        # Explicit mode=Methodology
        res_method = self.client.get('/?mode=Methodology')
        self.assertEqual(res_method.status_code, 200)
        method_text = res_method.data.decode('utf-8')
        self.assertTrue('Methodology' in method_text or 'KaTeX' in method_text or 'katex' in method_text)

    def test_index_mode_delegation(self):
        """Verify /?mode= delegates to corresponding analytical views."""
        # Mode = Retention
        res_retention = self.client.get('/?mode=Retention')
        self.assertEqual(res_retention.status_code, 200)
        self.assertIn('Retention', res_retention.data.decode('utf-8'))

        # Mode = Health
        res_health = self.client.get('/?mode=Health')
        self.assertEqual(res_health.status_code, 200)
        self.assertIn('Health', res_health.data.decode('utf-8'))

        # Mode = Influx
        res_influx = self.client.get('/?mode=Influx')
        self.assertEqual(res_influx.status_code, 200)
        self.assertIn('Influx', res_influx.data.decode('utf-8'))

        # Mode = Utility
        res_utility = self.client.get('/?mode=Utility')
        self.assertEqual(res_utility.status_code, 200)
        self.assertIn('Content Utility', res_utility.data.decode('utf-8'))

        # Mode = Quality
        res_quality = self.client.get('/?mode=Quality')
        self.assertEqual(res_quality.status_code, 200)
        self.assertIn('Quality Recognition', res_quality.data.decode('utf-8'))

    def test_mobile_drawer_and_5_tools_rendered(self):
        """Verify mobile navigation drawer, hamburger button, and 5-tool cards are rendered."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.data.decode('utf-8')
        # Mobile navigation drawer & hamburger presence
        self.assertIn('nav-hamburger-btn', html)
        self.assertIn('mobile-nav-drawer', html)
        self.assertIn('mobile-nav-backdrop', html)
        # All 5 tools rendered in tools landing suite
        self.assertIn('Tool 01 · Evaluation', html)
        self.assertIn('Tool 02 · Retention', html)
        self.assertIn('Tool 03 · Influx', html)
        self.assertIn('Tool 04 · Utility', html)
        self.assertIn('Tool 05 · Quality', html)

    def test_tools_route(self):
        """Verify dedicated /tools endpoint returns 200 and renders tools."""
        response = self.client.get('/tools')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('CampAnalytics', text)

    def test_methodology_route(self):
        """Verify dedicated /methodology endpoint returns 200 and includes LaTeX/KaTeX components."""
        response = self.client.get('/methodology')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Methodology', text)
        # Check for KaTeX resources or LaTeX mathematical expressions
        self.assertTrue(
            'katex' in text.lower() or '$$' in text or r'\(' in text or 'math' in text.lower(),
            "Expected KaTeX scripts, styles, or LaTeX mathematical notation in methodology view."
        )

    def test_info_route(self):
        """Verify dedicated /info endpoint returns 200 and renders Info tab."""
        response = self.client.get('/info')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Info', text)


class TestRetentionRoute(BaseTestCase):
    """Tests for /retention endpoint across table, heatmap, and worldmap views."""

    def test_retention_route(self):
        """Verify /retention with default query and target campaigns renders retention tables."""
        response = self.client.get('/retention?target_campaigns=wlmde22+wlmde23&view_mode=Table')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Retention Analytics', text)
        # Verify rendered retention data table
        self.assertTrue(
            '<table' in text and 'data-table' in text,
            "Expected HTML table with 'data-table' class in retention table view."
        )
        # Verify Germany / wlmde data appears
        self.assertTrue('Germany' in text or 'wlmde' in text)

    def test_retention_bare_get(self):
        """Verify bare GET /retention renders selection builder without errors."""
        response = self.client.get('/retention')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Retention Analytics', text)

    def test_retention_heatmap_view(self):
        """Verify /retention with view_mode=Heatmap generates base64 heatmap images."""
        response = self.client.get('/retention?target_campaigns=wlmde22+wlmde23&view_mode=Heatmap')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Retention Analytics', text)
        self.assertTrue(
            'data:image/png;base64,' in text or 'chart-card' in text or 'heatmap' in text.lower(),
            "Expected base64 heatmap image or heatmap container in retention heatmap view."
        )

    def test_retention_worldmap_view(self):
        """Verify /retention with view_mode=Worldmap renders world map visualization."""
        response = self.client.get('/retention?target_campaigns=wlmde22+wlmde23&view_mode=Worldmap')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Retention Analytics', text)
        self.assertTrue(
            'plotly' in text.lower() or 'data-table' in text,
            "Expected Plotly container or summary table in retention worldmap view."
        )

    def test_retention_metric_choice(self):
        """Verify /retention respects metric_choice parameter (Average vs Median)."""
        res_avg = self.client.get('/retention?target_campaigns=wlmde22+wlmde23&metric_choice=Average')
        self.assertEqual(res_avg.status_code, 200)

        res_med = self.client.get('/retention?target_campaigns=wlmde22+wlmde23&metric_choice=Median')
        self.assertEqual(res_med.status_code, 200)

    def test_retention_post_request(self):
        """Verify POST /retention processes form data correctly."""
        response = self.client.post('/retention', data={
            'target_campaigns': 'wlmde22 wlmde23',
            'view_mode': 'Table',
            'metric_choice': 'Average'
        })
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Retention Analytics', text)
        self.assertIn('<table', text)

    def test_retention_single_campaign_edge_case(self):
        """Verify single campaign code displays comparative vector requirement notice."""
        response = self.client.get('/retention?target_campaigns=wlmde22')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertTrue(
            'comparative vectors resolved' in text.lower() or 'notice' in text.lower() or 'two' in text.lower(),
            "Expected notice that at least two overlapping temporal editions are required."
        )

    def test_retention_invalid_code_edge_case(self):
        """Verify syntactically invalid campaign codes display validation notice."""
        response = self.client.get('/retention?target_campaigns=invalid99')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertTrue(
            'valid campaign codes' in text.lower() or 'error' in text.lower(),
            "Expected notice prompting for valid campaign codes."
        )

    def test_retention_empty_code_edge_case(self):
        """Verify empty target_campaigns parameter is handled gracefully."""
        response = self.client.get('/retention?target_campaigns=')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Retention Analytics', text)

    def test_retention_out_of_scope_edge_case(self):
        """Verify out-of-scope regional combination (e.g. WLA in Germany) returns scope notice."""
        response = self.client.get('/retention?target_campaigns=wlade22+wlade23')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertTrue(
            'african nations' in text.lower() or 'scope' in text.lower() or 'comparative vectors' in text.lower(),
            "Expected geographical scope notice for Wiki Loves Africa in Germany."
        )

    def test_retention_builder_parameters_fallback(self):
        """Verify submitting builder parameters without target_campaigns auto-assembles target codes."""
        response = self.client.get(
            '/retention?builder_country=de&builder_events=wlm&builder_events=wle&builder_yr_start=2021&builder_yr_end=2022'
        )
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Retention Analytics', text)
        self.assertIn('wlmde21', text)
        self.assertIn('wlede22', text)


class TestHealthRoute(BaseTestCase):
    """Tests for /health 5-dimension community health evaluation route."""

    def test_health_route(self):
        """Verify /health with target_event and region returns 200 and renders health view."""
        response = self.client.get('/health?target_event=wlmbd24&region=South+Asia')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Health Evaluation', text)

    def test_health_bare_get(self):
        """Verify bare GET /health returns 200 and presents initial health evaluation form."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Health Evaluation', text)

    def test_health_with_cached_data(self):
        """Verify /health evaluation using local pre-cached German WLM participant records."""
        response = self.client.get(
            '/health?target_event=wlmde24&comp_mode=Previous+Year+Baseline&region=Western+Europe'
        )
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Health Evaluation', text)

    def test_health_post_request(self):
        """Verify POST /health processes form data correctly."""
        response = self.client.post('/health', data={
            'target_event': 'wlmde24',
            'comp_mode': 'Previous Year Baseline',
            'baseline_event': 'wlmde23',
            'region': 'Western Europe'
        })
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Health Evaluation', text)

    def test_health_custom_baseline_mode(self):
        """Verify /health with Custom Verification Code comparison mode."""
        response = self.client.get(
            '/health?target_event=wlmde24&comp_mode=Custom+Verification+Code&baseline_event=wlmde23&region=Western+Europe'
        )
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Health Evaluation', text)

    def test_health_builder_parameters_fallback(self):
        """Verify submitting builder parameters without target_event auto-assembles target code."""
        response = self.client.get(
            '/health?health_event_type=all&health_country=de&health_year=2022'
        )
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Health Evaluation', text)
        self.assertIn('allde22', text)

    def test_health_builder_mismatch_reconciliation(self):
        """Verify selecting a new event type reconciles mismatched target_event prefix."""
        response = self.client.get(
            '/health?target_event=wlmde22&health_event_type=all'
        )
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Health Evaluation', text)
        self.assertIn('allde22', text)

    def test_health_mocked_scorecard_dimensions(self):
        """Verify all 5 health dimensions, star ratings, and overall score render with valid data."""
        with patch('analytics.fetch_all_concurrently') as mock_fetch, \
             patch('analytics.fetch_structural_metrics_concurrently') as mock_metrics:

            mock_fetch.return_value = {
                'wlmbd24': {f'user_{i}' for i in range(1, 51)},
                'wlmbd23': {f'user_{i}' for i in range(25, 65)},
                'wlmin24': {f'user_in_{i}' for i in range(1, 30)},
                'wlmin23': {f'user_in_{i}' for i in range(1, 20)},
                'wlmld24': {f'user_lk_{i}' for i in range(1, 20)},
                'wlmld23': {f'user_lk_{i}' for i in range(1, 15)},
                'wlmnp24': {f'user_np_{i}' for i in range(1, 25)},
                'wlmnp23': {f'user_np_{i}' for i in range(1, 20)},
                'wlmpk24': {f'user_pk_{i}' for i in range(1, 20)},
                'wlmpk23': {f'user_pk_{i}' for i in range(1, 15)},
            }
            mock_metrics.return_value = {
                'wlmbd24': {
                    'quality_image_share': 3.5,
                    'top10_uploader_share': 42.0,
                    'usage_share': 15.0,
                    'total_uploads': 250
                }
            }

            response = self.client.get('/health?target_event=wlmbd24&region=South+Asia')
            self.assertEqual(response.status_code, 200)
            text = response.data.decode('utf-8')

            # Verify the 5 health dimensions are present
            self.assertIn('Retention Index', text)
            self.assertIn('Content Utility', text)
            self.assertIn('Growth Capacity', text)
            self.assertIn('Contributor Diversity', text)
            self.assertIn('Quality Recognition', text)

            # Verify star ratings and scorecard cards
            self.assertIn('★', text)
            self.assertIn('scorecard-card', text)

            # Verify Export Report button and modal
            self.assertIn('Export Report', text)
            self.assertIn('export-report-modal-overlay', text)

    def test_health_auto_bind_region(self):
        """Verify target campaign code automatically resolves to its native regional cluster if unspecified."""
        response = self.client.get('/health?target_event=wlmde24')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        # DE belongs to Northern & Western Europe
        self.assertIn('Northern & Western Europe', text)

    def test_scoring_zero_floor_and_benchmarks(self):
        """Verify relative scoring zero-floor integrity and benchmark alignment."""
        import analytics
        # Zero activity yields zero points
        self.assertEqual(analytics.calculate_relative_score(0.0, 20.0), 0.0)
        self.assertEqual(analytics.calculate_relative_score(-5.0, 20.0), 0.0)

        # Reaching benchmark yields exactly 70.0 points
        self.assertEqual(analytics.calculate_relative_score(20.0, 20.0), 70.0)
        self.assertEqual(analytics.calculate_relative_score(2.5, 2.5), 70.0)

        # Performance below benchmark is concave and bounded between 0 and 70
        score_half = analytics.calculate_relative_score(10.0, 20.0)
        self.assertTrue(0.0 < score_half < 70.0)

        # Performance above benchmark exhibits diminishing returns bounded by 100
        score_double = analytics.calculate_relative_score(40.0, 20.0)
        self.assertTrue(70.0 < score_double <= 100.0)

    def test_paired_weights_sum_to_100(self):
        """Verify 5 health evaluation dimensions adhere to paired weights summing to 100%."""
        import analytics
        target = {'user1', 'user2'}
        baseline = {'user1', 'user3'}
        structural = {'usage_share': 3.0, 'top10_uploader_share': 60.0, 'quality_image_share': 1.0}
        benchmarks = {'retention': 20.0, 'growth': 50.0, 'usage': 2.5, 'diversity': 70.0, 'quality': 1.5}
        metrics = analytics.generate_health_metrics(target, baseline, structural, benchmarks)

        self.assertEqual(metrics['Retention']['weight'], 25)
        self.assertEqual(metrics['Growth']['weight'], 25)
        self.assertEqual(metrics['Usage']['weight'], 20)
        self.assertEqual(metrics['Quality']['weight'], 15)
        self.assertEqual(metrics['Diversity']['weight'], 15)
        total_weight = sum(metrics[m]['weight'] for m in ['Retention', 'Growth', 'Usage', 'Quality', 'Diversity'])
        self.assertEqual(total_weight, 100)

    def test_health_missing_target_edge_case(self):
        """Verify empty target_event displays required input notice."""
        response = self.client.get('/health?target_event=')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertTrue(
            'target campaign registry code' in text.lower() or 'please provide' in text.lower(),
            "Expected notice prompting for Target Campaign Registry Code."
        )

    def test_health_malformed_syntax_edge_case(self):
        """Verify syntactically malformed target_event displays anomaly notice."""
        response = self.client.get('/health?target_event=not_a_valid_code')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertTrue(
            'anomaly detected' in text.lower() or 'syntax' in text.lower(),
            "Expected anomaly notice for malformed target campaign code syntax."
        )

    def test_health_custom_mode_missing_baseline_edge_case(self):
        """Verify Custom Verification Code mode with missing baseline displays notice."""
        response = self.client.get(
            '/health?target_event=wlmde24&comp_mode=Custom+Verification+Code&baseline_event='
        )
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertTrue(
            'baseline event sequence' in text.lower() or 'baseline' in text.lower(),
            "Expected notice that comparative tracking requires a baseline event sequence."
        )


class TestInfluxRoute(BaseTestCase):
    """Tests for /influx multi-year contributor influx & lifecycle route."""

    def test_influx_route(self):
        """Verify /influx with influx_codes renders barchart, table, and lifecycle metrics."""
        response = self.client.get('/influx?influx_codes=wlmde22+wlmde23+wlmde24')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('New User Influx', text)
        # Verify Matplotlib chart base64 image
        self.assertIn('data:image/png;base64,', text)
        # Verify table and lifecycle sections
        self.assertTrue('<table' in text or 'table-interactive-wrapper' in text)
        self.assertTrue(
            '1-time entrants' in text.lower() or 'repeaters' in text.lower() or 'veterans' in text.lower() or 'newcomers' in text.lower(),
            "Expected contributor lifecycle segmentation metrics."
        )

    def test_influx_bare_get(self):
        """Verify bare GET /influx returns 200 and presents influx form."""
        response = self.client.get('/influx')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('New User Influx', text)

    def test_influx_with_parameters(self):
        """Verify /influx with structured event, country, and year range parameters."""
        response = self.client.get(
            '/influx?influx_event_type=wlm&influx_country=de&influx_yr_start=2022&influx_yr_end=2024&influx_codes=wlmde22+wlmde23+wlmde24'
        )
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('New User Influx', text)
        self.assertIn('data:image/png;base64,', text)

    def test_influx_post_request(self):
        """Verify POST /influx processes form submissions correctly."""
        response = self.client.post('/influx', data={
            'influx_event_type': 'wlm',
            'influx_country': 'de',
            'influx_yr_start': '2022',
            'influx_yr_end': '2024',
            'influx_codes': 'wlmde22 wlmde23 wlmde24'
        })
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('New User Influx', text)
        self.assertIn('data:image/png;base64,', text)

    def test_influx_single_edition_edge_case(self):
        """Verify single edition input displays notice requiring at least two editions."""
        response = self.client.get('/influx?influx_codes=wlmde22')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertTrue(
            'at least two' in text.lower() or 'chronological' in text.lower(),
            "Expected notice requiring at least two chronological campaign editions."
        )

    def test_influx_invalid_codes_edge_case(self):
        """Verify invalid campaign codes display validation notice."""
        response = self.client.get('/influx?influx_codes=invalid1+invalid2')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertTrue(
            'at least two' in text.lower() or 'valid' in text.lower() or 'chronological' in text.lower(),
            "Expected notice regarding invalid campaign codes."
        )

    def test_influx_invalid_year_inputs(self):
        """Verify non-integer year inputs gracefully fallback to defaults without crashing."""
        response = self.client.get('/influx?influx_yr_start=notayear&influx_yr_end=invalid')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('New User Influx', text)

    def test_influx_out_of_scope_edge_case(self):
        """Verify out-of-scope regional combination (e.g. WLA in Germany) returns scope notice."""
        response = self.client.get(
            '/influx?influx_event_type=wla&influx_country=de&influx_codes=wlade22+wlade23'
        )
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertTrue(
            'african nations' in text.lower() or 'scope' in text.lower() or 'no participant records' in text.lower(),
            "Expected geographic scope notice or no participant notice."
        )

    def test_influx_all_campaigns_builder(self):
        """Verify /influx evaluates multi-campaign influx when 'All Campaigns' is selected."""
        response = self.client.get(
            '/influx?influx_event_type=all&influx_country=de&influx_yr_start=2021&influx_yr_end=2024'
        )
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('New User Influx', text)
        self.assertIn('allde21', text)
        self.assertIn('allde24', text)
        self.assertIn('data:image/png;base64,', text)

    def test_influx_builder_mismatch_reconciliation(self):
        """Verify server reconciles out-of-sync codes when client explicitly selects 'all' campaign type."""
        response = self.client.get(
            '/influx?influx_event_type=all&influx_country=de&influx_yr_start=2021&influx_yr_end=2024&influx_codes=wlmde21+wlmde22+wlmde23'
        )
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('New User Influx', text)
        self.assertIn('allde21', text)
        self.assertIn('data:image/png;base64,', text)


class TestUtilityRoute(BaseTestCase):
    """Tests for the Content Utility analytical route (/utility)."""

    def test_utility_bare_get(self):
        """Verify bare GET /utility returns 200 and presents content utility view."""
        response = self.client.get('/utility')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Content Utility', text)
        self.assertIn('Selection Builder', text)

    def test_utility_with_target(self):
        """Verify /utility with target_campaign renders global usage metrics and tables."""
        response = self.client.get('/utility?target_campaign=wlmbd24')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Content Utility', text)
        self.assertIn('Global Utility Rate', text)
        self.assertIn('utility-media-table', text)
        self.assertIn('utility-photographers-table', text)

    def test_utility_post_request(self):
        """Verify POST /utility processes form submissions correctly."""
        response = self.client.post('/utility', data={'target_campaign': 'wlmbd24'})
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Content Utility', text)
        self.assertIn('Global Utility Rate', text)

    def test_utility_builder_params(self):
        """Verify /utility auto-assembles target code from builder parameters."""
        response = self.client.get('/utility?utility_event_type=wlm&utility_country=bd&utility_year=2024')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('wlmbd24', text)
        self.assertIn('Global Utility Rate', text)

    def test_utility_invalid_syntax_edge_case(self):
        """Verify invalid campaign code syntax displays validation notice."""
        response = self.client.get('/utility?target_campaign=invalid123')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Invalid campaign code format', text)

    def test_utility_out_of_scope_edge_case(self):
        """Verify out-of-scope regional combination returns scope notice."""
        response = self.client.get('/utility?target_campaign=wlbde24')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Wiki Loves Bangla', text)


class TestQualityRoute(BaseTestCase):
    """Tests for the Quality Recognition analytical route (/quality)."""

    def test_quality_bare_get(self):
        """Verify bare GET /quality returns 200 and presents quality recognition view."""
        response = self.client.get('/quality')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Quality Recognition', text)
        self.assertIn('Selection Builder', text)

    def test_quality_with_target(self):
        """Verify /quality with target_campaign renders quality distinction metrics and tables."""
        response = self.client.get('/quality?target_campaign=wlmde24')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Quality Recognition', text)
        self.assertIn('Overall Quality Rate', text)
        self.assertIn('quality-files-table', text)
        self.assertIn('quality-hall-of-fame-table', text)

    def test_quality_post_request(self):
        """Verify POST /quality processes form submissions correctly."""
        response = self.client.post('/quality', data={'target_campaign': 'wlmde24'})
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Quality Recognition', text)
        self.assertIn('Overall Quality Rate', text)

    def test_quality_builder_params(self):
        """Verify /quality auto-assembles target code from builder parameters."""
        response = self.client.get('/quality?quality_event_type=wlm&quality_country=de&quality_year=2024')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('wlmde24', text)
        self.assertIn('Overall Quality Rate', text)

    def test_quality_invalid_syntax_edge_case(self):
        """Verify invalid campaign code syntax displays validation notice."""
        response = self.client.get('/quality?target_campaign=invalid123')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Invalid campaign code format', text)

    def test_quality_out_of_scope_edge_case(self):
        """Verify out-of-scope regional combination returns scope notice."""
        response = self.client.get('/quality?target_campaign=wlbde24')
        self.assertEqual(response.status_code, 200)
        text = response.data.decode('utf-8')
        self.assertIn('Wiki Loves Bangla', text)


class TestErrorHandlingAndSecurity(BaseTestCase):
    """Tests for HTTP error handling (404) and security headers."""

    def test_error_handling(self):
        """Verify requesting a non-existent endpoint returns HTTP 404 Not Found."""
        response = self.client.get('/nonexistent_route_404_test')
        self.assertEqual(response.status_code, 404)

    def test_security_headers(self):
        """Verify security response headers if present on endpoints."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)

        # If security headers are configured, verify they conform to best practices
        if 'X-Content-Type-Options' in response.headers:
            self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')

        if 'X-Frame-Options' in response.headers:
            self.assertIn(response.headers['X-Frame-Options'].upper(), ('DENY', 'SAMEORIGIN'))

        if 'Referrer-Policy' in response.headers:
            self.assertIn(
                response.headers['Referrer-Policy'],
                ('no-referrer', 'strict-origin-when-cross-origin', 'same-origin', 'no-referrer-when-downgrade')
            )

        if 'Content-Security-Policy' in response.headers:
            self.assertTrue(len(response.headers['Content-Security-Policy']) > 0)

    def test_content_type_headers(self):
        """Verify successful page responses return standard HTML content type."""
        for route in ('/', '/tools', '/methodology', '/healthz'):
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200)
            if route == '/healthz':
                self.assertIn('text/html', response.content_type.lower())
            else:
                self.assertIn('text/html', response.content_type.lower())


if __name__ == '__main__':
    unittest.main()
