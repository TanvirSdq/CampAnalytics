import os
os.environ.setdefault('MPLCONFIGDIR', '/tmp/matplotlib')

import base64
import io
import re
from collections import defaultdict
from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg') # Ensure matplotlib can run headlessly
import matplotlib.pyplot as plt

# Import configurations
import app_config
from app_config import (
    PAGE_TITLE, PAGE_ICON, KORIKATH_LOGO_URL,
    WIKI_BLUE, WIKI_BLUE_LIGHT, WIKI_BLUE_DARK, WIKI_INK, WIKI_GRAY,
    CARD_LIGHT, CARD_DARK, BG_DEEP, BG_MID, TEXT_LIGHT, TEXT_MUTED
)

# Import analytics functions and constants
import analytics
from analytics import (
    CODE_RE, COUNTRY_MAP, COUNTRY_OPTIONS, EVENT_MAP, EXAMPLE_CODES,
    REGION_COUNTRY_MAPPING, country_display_name
)

app = Flask(__name__)

# Make config variables available to all templates
@app.context_processor
def inject_config():
    return {
        'PAGE_TITLE': PAGE_TITLE,
        'PAGE_ICON': PAGE_ICON,
        'KORIKATH_LOGO_URL': KORIKATH_LOGO_URL,
        'EVENT_MAP': EVENT_MAP,
        'COUNTRY_OPTIONS': COUNTRY_OPTIONS,
        'COUNTRY_MAP': COUNTRY_MAP,
        'REGION_COUNTRY_MAPPING': REGION_COUNTRY_MAPPING,
        'EXAMPLE_CODES': EXAMPLE_CODES,
        'CUSTOM_CSS': app_config.get_custom_css(),
        'TEXT_MUTED': TEXT_MUTED
    }

def fig_to_base64(fig):
    img = io.BytesIO()
    fig.savefig(img, format='png', bbox_inches='tight', transparent=True)
    img.seek(0)
    plt.close(fig)
    return base64.b64encode(img.getvalue()).decode()

@app.route('/', methods=['GET'])
def index():
    mode = request.args.get('mode', 'Methodology')
    if mode in ('Retention Analytics', 'Retention'):
        return retention()
    elif mode in ('Health Evaluation', 'Health'):
        return health()
    return render_template('index.html', mode='Methodology')

@app.route('/methodology', methods=['GET'])
def methodology():
    return render_template('index.html', mode='Methodology')

@app.route('/retention', methods=['GET', 'POST'])
def retention():
    if request.method == 'POST':
        target_campaigns = request.form.get('target_campaigns', '').strip()
        view_mode = request.form.get('view_mode', 'Table')
        metric_choice = request.form.get('metric_choice', 'Average')
    else:
        target_campaigns = request.args.get('target_campaigns', '').strip()
        view_mode = request.args.get('view_mode', 'Table')
        metric_choice = request.args.get('metric_choice', 'Average')
        # If bare GET request with no parameters, show builder ready to use
        if not target_campaigns and not request.args.get('target_campaigns'):
            return render_template(
                'index.html',
                mode='Retention Analytics',
                target_campaigns=EXAMPLE_CODES,
                view_mode='Table',
                metric_choice='Average',
                error=None,
                tables=[],
                heatmaps=[],
                worldmap_html=''
            )
    
    if not target_campaigns:
        target_campaigns = EXAMPLE_CODES
        
    codes = target_campaigns.split()
    valid = [c for c in (re.sub(r'\s+', '', cd).lower() for cd in codes) if CODE_RE.match(c)]

    error = None
    results_html = ""
    worldmap_html = ""
    tables = []
    heatmaps = []

    if not valid:
        error = "Please provide valid campaign codes (e.g., wlmde21 wlmde22) or use the Selection Builder above."
    else:
        participant_results = analytics.fetch_all_concurrently(valid)
        country_events = defaultdict(dict)
        for code in valid:
            match = CODE_RE.match(code)
            if not match: continue
            event, cc, yr = match.groups()
            participants = participant_results.get(code, set())
            if cc in COUNTRY_MAP and participants:
                country_events[cc][code] = participants

        valid_countries = {code: events for code, events in country_events.items() if len(events) >= 2}

        if not valid_countries:
            error = "No comparative vectors resolved. Verify that at least two overlapping temporal editions exist for your selected countries."
        else:
            if view_mode == 'Table':
                df = analytics.build_global_table(valid_countries)
                if not df.empty:
                    tables.append(df.to_html(classes="data-table", index=False))
            elif view_mode == 'Heatmap':
                for country_code, events in valid_countries.items():
                    fig = analytics.create_heatmap(events, COUNTRY_MAP.get(country_code, country_code))
                    heatmaps.append((COUNTRY_MAP.get(country_code, country_code), fig_to_base64(fig)))
            elif view_mode == 'Worldmap':
                world_df = analytics.build_world_data(valid_countries, metric_choice)
                if not world_df.empty:
                    fig = analytics.create_worldmap(world_df, metric_choice)
                    worldmap_html = fig.to_html(full_html=False, include_plotlyjs='cdn')
                    tables.append(world_df.to_html(classes="data-table", index=False))

    return render_template('index.html', mode='Retention Analytics', 
                           target_campaigns=target_campaigns, view_mode=view_mode,
                           metric_choice=metric_choice,
                           error=error, tables=tables, heatmaps=heatmaps, 
                           worldmap_html=worldmap_html)

@app.route('/health', methods=['GET', 'POST'])
def health():
    if request.method == 'POST':
        target_event = request.form.get('target_event', '').strip()
        comp_mode = request.form.get('comp_mode', 'Previous Year Baseline')
        baseline_event_input = request.form.get('baseline_event', '').strip()
        region = request.form.get('region', 'South Asia')
    else:
        target_event = request.args.get('target_event', '').strip()
        comp_mode = request.args.get('comp_mode', 'Previous Year Baseline')
        baseline_event_input = request.args.get('baseline_event', '').strip()
        region = request.args.get('region', 'South Asia')
        # If bare GET request with no parameters, show form ready to use
        if not target_event and not request.args.get('target_event'):
            return render_template(
                'index.html',
                mode='Health Evaluation',
                target_event='wlmbd24',
                comp_mode='Previous Year Baseline',
                baseline_event='',
                region='South Asia',
                error=None,
                metrics=None,
                insights=None,
                target_users_count=0,
                base_users_count=0,
                intersect_users_count=0
            )

    error = None
    metrics = None
    insights = None
    target_users_count = 0
    base_users_count = 0
    intersect_users_count = 0

    if not target_event:
        error = "Please provide a Target Campaign Registry Code (e.g., wlmbd24) or select a preset benchmark."
    else:
        match = CODE_RE.match(target_event.lower())
        if not match:
            error = f"Anomaly detected in target campaign code syntax ('{target_event}'). Expected standard format: event prefix + 2-letter country code + 2-digit year (e.g., wlmbd24)."
        else:
            event_type, target_cc, year_str = match.groups()
            year_int = int(year_str)
            prev_year_str = f"{year_int - 1:02d}"

            baseline_event = baseline_event_input
            if comp_mode == "Previous Year Baseline":
                baseline_event = f"{event_type}{target_cc}{prev_year_str}"
            
            if not baseline_event:
                error = "Comparative tracking requires a baseline event sequence."
            else:
                regional_countries = REGION_COUNTRY_MAPPING.get(region, [])
                scan_pool = []
                for cc in regional_countries:
                    scan_pool.append(f"{event_type}{cc}{year_str}")
                    scan_pool.append(f"{event_type}{cc}{prev_year_str}")
                scan_pool.append(baseline_event.lower())
                scan_pool.append(target_event.lower())
                scan_pool = list(set(scan_pool))

                all_fetched_data = analytics.fetch_all_concurrently(scan_pool, threads=16)

                target_users = all_fetched_data.get(target_event.lower(), set())
                base_users = all_fetched_data.get(baseline_event.lower(), set())

                if not base_users or not target_users:
                    error = f"Data acquisition notice: Could not retrieve participant data for baseline ({baseline_event}) or target ({target_event}). Please verify the campaign codes or network connectivity."
                else:
                    target_users_count = len(target_users)
                    base_users_count = len(base_users)
                    intersect_users_count = len(target_users & base_users)

                    peer_volumes = {}
                    for cc in regional_countries:
                        t_code = f"{event_type}{cc}{year_str}"
                        peer_volumes[cc] = len(all_fetched_data.get(t_code, set()))
                        
                    sorted_peers = sorted(peer_volumes.items(), key=lambda x: x[1], reverse=True)
                    top_3_countries = [peer[0] for peer in sorted_peers[:3]]

                    structural_codes = [f"{event_type}{cc}{year_str}" for cc in top_3_countries]
                    structural_codes.append(target_event.lower())
                    structural_metrics = analytics.fetch_structural_metrics_concurrently(list(set(structural_codes)))

                    rep_retentions, rep_growths, rep_quality_rates, rep_diversities, rep_usages = [], [], [], [], []
                    for cc in top_3_countries:
                        t_code = f"{event_type}{cc}{year_str}"
                        b_code = f"{event_type}{cc}{prev_year_str}"
                        t_u = all_fetched_data.get(t_code, set())
                        b_u = all_fetched_data.get(b_code, set())
                        structural = structural_metrics.get(t_code, {})
                        
                        if t_u or b_u:
                            ret_val = (len(t_u & b_u) / len(b_u) * 100) if b_u else 15.0
                            gro_val = (len(t_u - b_u) / len(t_u) * 100) if t_u else 40.0
                            rep_retentions.append(ret_val)
                            rep_growths.append(gro_val)
                        rep_quality_rates.append(float(structural.get("quality_image_share", 0.0)))
                        rep_diversities.append(float(structural.get("top10_uploader_share", 100.0)))
                        rep_usages.append(float(structural.get("usage_share", 0.0)))
                    
                    benchmarks = {
                        'retention': float(np.mean(rep_retentions)) if rep_retentions else 15.0,
                        'growth': float(np.mean(rep_growths)) if rep_growths else 40.0,
                        'quality': float(np.mean(rep_quality_rates)) if rep_quality_rates else 0.0,
                        'diversity': float(np.mean(rep_diversities)) if rep_diversities else 100.0,
                        'usage': float(np.mean(rep_usages)) if rep_usages else 0.0
                    }
                    
                    target_structural_metrics = structural_metrics.get(
                        target_event.lower(),
                        {"quality_image_share": 0.0, "top10_uploader_share": 100.0, "usage_share": 0.0, "total_uploads": 0}
                    )

                    metrics = analytics.generate_health_metrics(
                        target_users, base_users, target_structural_metrics, benchmarks
                    )
                    
                    for m in metrics:
                        if m != 'Overall':
                            metrics[m]['stars'] = analytics.calculate_stars(metrics[m]['score'])[0]

                    insights = analytics.generate_insights(metrics, region.split(" (")[0], benchmarks)

    return render_template('index.html', mode='Health Evaluation', 
                           target_event=target_event, comp_mode=comp_mode, 
                           baseline_event=baseline_event_input, region=region,
                           error=error, metrics=metrics, insights=insights,
                           target_users_count=target_users_count, 
                           base_users_count=base_users_count, 
                           intersect_users_count=intersect_users_count)

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)

