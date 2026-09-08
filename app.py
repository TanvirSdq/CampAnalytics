import re
from collections import defaultdict
from pathlib import Path
import numpy as np

import streamlit as st

from analytics import (
    add_codes_from_selectors,
    clear_code_input,
    CODE_RE,
    COUNTRY_MAP,
    COUNTRY_OPTIONS,
    EVENT_MAP,
    EXAMPLE_CODES,
    REGION_COUNTRY_MAPPING,
    build_global_table,
    build_world_data,
    calculate_stars,
    create_heatmap,
    create_worldmap,
    country_display_name,
    fetch_all_concurrently,
    fetch_structural_metrics_concurrently,
    generate_health_metrics,
    generate_insights,
    get_participants,
    render_heatmap_view,
    render_table_view,
    render_worldmap_view,
)

# --- GLOBAL PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Wikimedia Campaign Suite",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- UNIFIED WIKIPEDIA-INSPIRED DARK THEME ---
WIKI_BLUE = "#3366cc"
WIKI_BLUE_LIGHT = "#7aa7ff"
WIKI_BLUE_DARK = "#14428e"
WIKI_INK = "#202122"
WIKI_GRAY = "#54595d"
CARD_LIGHT = "#f7f9fc"
CARD_DARK = "rgba(255, 255, 255, 0.05)"

BG_DEEP = "#0a1526"
BG_MID = "#13284a"
TEXT_LIGHT = "#eef3fc"
TEXT_MUTED = "#a9b9d8"

KORIKATH_LOGO_URL = "https://commons.wikimedia.org/wiki/Special:FilePath/Project_Korikath_Logo-dark.svg"

CSS_PATH = Path(__file__).with_name("styles.css")
with CSS_PATH.open("r", encoding="utf-8") as css_file:
    CUSTOM_CSS = css_file.read()

CUSTOM_CSS = (
    CUSTOM_CSS.replace("__BG_MID__", BG_MID)
    .replace("__BG_DEEP__", BG_DEEP)
    .replace("__TEXT_LIGHT__", TEXT_LIGHT)
    .replace("__TEXT_MUTED__", TEXT_MUTED)
    .replace("__WIKI_BLUE_DARK__", WIKI_BLUE_DARK)
    .replace("__WIKI_BLUE__", WIKI_BLUE)
    .replace("__WIKI_BLUE_LIGHT__", WIKI_BLUE_LIGHT)
    .replace("__CARD_LIGHT__", CARD_LIGHT)
    .replace("__CARD_DARK__", CARD_DARK)
    .replace("__WIKI_GRAY__", WIKI_GRAY)
    .replace("__WIKI_INK__", WIKI_INK)
)

st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)

# --- MAPS & CONSTANTS ---

# --- SESSION STATE INITIALIZATION ---
if "code_input" not in st.session_state:
    st.session_state.code_input = ""
if "last_valid_countries" not in st.session_state:
    st.session_state.last_valid_countries = None

# --- SIDEBAR INTERFACE ---
with st.sidebar:
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="{KORIKATH_LOGO_URL}" alt="Project Korikath Logo" style="width: 140px; height: auto;">
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.title("App Mode")
    app_mode = st.radio("Select Suite Interface", ["Retention Analytics", "Health Evaluation"], horizontal=False)
    
    st.markdown("---")
    
    if app_mode == "Retention Analytics":
        st.subheader("Campaign Selection")
        user_input = st.text_area(
            "Target Campaigns (e.g., wlmbd24)", key="code_input", placeholder=EXAMPLE_CODES, height=110
        )

        with st.expander("Selection Builder"):
            st.multiselect(
                "Event Matrix", options=list(EVENT_MAP.keys()),
                format_func=lambda k: EVENT_MAP[k], key="sel_events"
            )
            st.multiselect(
                "Country Matrices", options=COUNTRY_OPTIONS,
                format_func=country_display_name, key="sel_countries"
            )
            st.slider("Year Range", 2005, 2040, (2021, 2025), key="yr_range")

            b_col1, b_col2 = st.columns(2)
            b_col1.button("Inject", on_click=add_codes_from_selectors, use_container_width=True)
            b_col2.button("Reset", on_click=clear_code_input, use_container_width=True)

        st.markdown("---")
        VIEW_LABELS = {"Table": "Data Table", "Heatmap": "Heatmap Matrix", "Worldmap": "Choropleth"}
        st.subheader("Visualization Model")
        view_mode = st.radio(
            "Visualization Model", list(VIEW_LABELS.keys()),
            format_func=lambda m: VIEW_LABELS[m], horizontal=True, key="view_mode", label_visibility="collapsed"
        )
        run_retention = st.button("Run Retention Analysis", type="primary", use_container_width=True)
        
    else:
        st.subheader("Health Assessment Settings")
        target_event = st.text_input("Target Campaign Registry Code", value="", placeholder="e.g., wlmbd24").strip()
        
        st.markdown("---")
        comp_mode = st.radio("Benchmark Baseline", ["Previous Year Baseline", "Custom Verification Code"])
        baseline_event = ""

        if comp_mode == "Custom Verification Code":
            baseline_event = st.text_input("Custom Baseline Campaign Code", value="", placeholder="e.g., wlmbd22").strip()
        else:
            if target_event:
                match = CODE_RE.match(target_event.lower())
                if match:
                    event, cc, yr = match.groups()
                    baseline_event = f"{event}{cc}{int(yr)-1:02d}"
                    st.info(f"Auto-Computed Reference Vector: {baseline_event.upper()}")
                else:
                    st.warning("Ensure target syntax matches global standards.")
            else:
                st.info("Input a valid target registry parameter to auto-generate baseline mapping.")
            
        region = st.selectbox("Geographic Standardization Framework", list(REGION_COUNTRY_MAPPING.keys()))
        
        st.markdown("---")
        analyze_health = st.button("Evaluate Campaign Health", type="primary", use_container_width=True)

    st.markdown("---")
    st.caption("Integrated Analytics Platform Engine")

# --- MAIN RUNTIME ROUTER ---
st.markdown("<br>", unsafe_allow_html=True)

if app_mode == "Retention Analytics":
    st.markdown('<div class="hero-title">Cross-Event Retention Analytics</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Evaluate longitudinal patterns and ecosystem user migration parameters.</div>', unsafe_allow_html=True)
    
    if run_retention:
        raw_input = user_input.strip() or EXAMPLE_CODES
        codes = raw_input.split()
        valid = [c for c in (re.sub(r'\s+', '', cd).lower() for cd in codes) if CODE_RE.match(c)]

        if not valid:
            st.error("Invalid evaluation parameters passed to query tracker.")
            st.stop()

        participant_results = fetch_all_concurrently(valid)

        country_events = defaultdict(dict)
        for code in valid:
            match = CODE_RE.match(code)
            if not match:
                continue
            event, cc, yr = match.groups()
            participants = participant_results.get(code, set())
            if cc in COUNTRY_MAP and participants:
                country_events[cc][code] = participants

        st.session_state.last_valid_countries = {
            code: events for code, events in country_events.items() if len(events) >= 2
        }
        
        if st.session_state.last_valid_countries:
            st.toast("Ecosystem data matrices integrated.")

    results = st.session_state.last_valid_countries

    if results is not None:
        if not results:
            st.info("No comparative vectors resolved. Verify that overlapping temporal pairs exist for your selected countries.")
        else:
            st.markdown("---")
            total_events = sum(len(events) for events in results.values())
            METRIC3_LABELS = {"Table": "Functional Data Rows", "Heatmap": "Heatmaps Generated", "Worldmap": "Polygons Computed"}
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Validated Countries", len(results))
            col_m2.metric("Ecosystem Events Tracked", total_events)
            col_m3.metric(METRIC3_LABELS[view_mode], len(results))

            st.markdown("<br>", unsafe_allow_html=True)

            if view_mode == "Heatmap":
                render_heatmap_view(results)
            elif view_mode == "Table":
                render_table_view(results)
            else:
                render_worldmap_view(results)

else:
    st.markdown('<div class="hero-title">Campaign Health Evaluation Suite</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">Compute analytical structural health indexes relative to real-time regional performance clusters.</div>', unsafe_allow_html=True)

    if not target_event:
        st.info("System Initialized. Supply an execution identifier (e.g., wlmbd24 or wlmde25) and assign a validation model to begin.")
    
    if target_event and analyze_health:
        match = CODE_RE.match(target_event.lower())
        if not match:
            st.error("Anomaly detected in target campaign code syntax. Please utilize a standard structure (e.g., wlmbd24).")
            st.stop()
            
        event_type, target_cc, year_str = match.groups()
        year_int = int(year_str)
        prev_year_str = f"{year_int - 1:02d}"

        if not baseline_event:
            st.error("Execution halted: Comparative tracking requires a baseline event sequence.")
            st.stop()

        # --- REVISED GLOBAL BENCHMARK CALCULATOR FRAMEWORK ---
        with st.spinner("Calibrating regional peer matrix benchmarks..."):
            regional_countries = REGION_COUNTRY_MAPPING.get(region, [])
            
            # Form baseline validation query stack
            scan_pool = []
            for cc in regional_countries:
                scan_pool.append(f"{event_type}{cc}{year_str}")
                scan_pool.append(f"{event_type}{cc}{prev_year_str}")
            
            if baseline_event:
                scan_pool.append(baseline_event.lower())
            scan_pool.append(target_event.lower())
            scan_pool = list(set(scan_pool))
            
            all_fetched_data = fetch_all_concurrently(scan_pool, threads=16)
            
            # Sort peers transparently based on verified registration footprint volumes
            peer_volumes = {}
            for cc in regional_countries:
                t_code = f"{event_type}{cc}{year_str}"
                peer_volumes[cc] = len(all_fetched_data.get(t_code, set()))
                
            sorted_peers = sorted(peer_volumes.items(), key=lambda x: x[1], reverse=True)
            top_3_countries = [peer[0] for peer in sorted_peers[:3]]

            structural_codes = [f"{event_type}{cc}{year_str}" for cc in top_3_countries]
            structural_codes.append(target_event.lower())
            structural_metrics = fetch_structural_metrics_concurrently(list(set(structural_codes)))
            
            # Extract metrics across top 3 volume drivers
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
            
            top_country_names = [COUNTRY_MAP.get(cc, cc).replace('_', ' ') for cc in top_3_countries if cc in COUNTRY_MAP]
            
            if top_country_names:
                st.success(f"Dynamic Peer Cluster Established: Performance benchmarks calculated from regional leaders: {', '.join(top_country_names)}.")
            else:
                st.info("Establishing regional normalization indices based on standardized baseline coordinates.")

            target_users = all_fetched_data.get(target_event.lower(), set())
            base_users = all_fetched_data.get(baseline_event.lower(), set())
            target_structural_metrics = structural_metrics.get(
                target_event.lower(),
                {"quality_image_share": 0.0, "top10_uploader_share": 100.0, "usage_share": 0.0, "total_uploads": 0}
            )

            if not target_users:
                st.error(f"Empty payload returned for the target campaign matrix request: {target_event.upper()}.")
                st.stop()

            metrics = generate_health_metrics(
                target_users,
                base_users,
                target_structural_metrics,
                benchmarks
            )
            
            col1, col2 = st.columns([1, 1.2], gap="large")
            
            with col1:
                card_html = f"""<div class="health-card">
<div class="health-title">
<span>{target_event.upper()} Metrics Matrix</span>
<span></span>
</div>
<div class="metric-label">Retention Index</div>
<div class="metric-desc">Percentage of users retained from the baseline campaign (35% weight)</div>
<div class="metric-value">{metrics['Retention']['raw']}</div>
<div class="stars">{calculate_stars(metrics['Retention']['score'])[0]}</div>

<div class="metric-label">Growth Capacity</div>
<div class="metric-desc">Percentage of fresh, first-time active contributors (20% weight)</div>
<div class="metric-value">{metrics['Growth']['raw']}</div>
<div class="stars">{calculate_stars(metrics['Growth']['score'])[0]}</div>

<div class="metric-label">Usage / Utility</div>
<div class="metric-desc">Percentage of files actively used on Wikimedia wikis (20% weight)</div>
<div class="metric-value">{metrics['Usage']['raw']:.2f}%</div>
<div class="stars">{calculate_stars(metrics['Usage']['score'])[0]}</div>

<div class="metric-label">Quality Image</div>
<div class="metric-desc">Percentage of quality images across total submissions (15% weight)</div>
<div class="metric-value">{metrics['Quality']['raw']:.2f}%</div>
<div class="stars">{calculate_stars(metrics['Quality']['score'])[0]}</div>

<div class="metric-label">Diversity</div>
<div class="metric-desc">Top 10% uploader share (10% weight)</div>
<div class="metric-value">{metrics['Diversity']['raw']:.1f}%</div>
<div class="stars">{calculate_stars(metrics['Diversity']['score'])[0]}</div>
<hr style="border-color: rgba(255,255,255,0.1); margin: 1.5rem 0;">
<div class="metric-label">Overall Weighted Evaluation Score</div>
<div class="overall-score">{metrics['Overall']}<span style="font-size: 1.2rem; color: #a9b9d8;"> / 100</span></div>
</div>"""
                st.markdown(card_html, unsafe_allow_html=True)
                
            with col2:
                st.markdown("### Diagnostic Context Insights")
                st.markdown(f"<p style='color: {TEXT_MUTED}; margin-bottom: 1.5rem;'>Automated strategic diagnostic evaluations measured relative to peers in the <b>{region}</b> cluster framework.</p>", unsafe_allow_html=True)
                
                insights = generate_insights(metrics, region.split(" (")[0], benchmarks)

                for insight in insights:
                    st.markdown(f"""
                    <div class="insight-box">
                        <p>{insight}</p>
                    </div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("View Quantifiable Cohort Footprints"):
                    st.write(f"**Target Campaign Total Contributors:** {len(target_users)}")
                    st.write(f"**Historical Baseline Group Size:** {len(base_users)}")
                    st.write(f"**Common Intersecting User Core:** {len(target_users & base_users)}")
