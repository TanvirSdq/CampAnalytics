import re
from collections import defaultdict
from pathlib import Path
import numpy as np

import streamlit as st

from analytics import (
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
    compute_yoy_influx,
    create_influx_plotly_chart,
)

from app_config import (
    PAGE_TITLE, PAGE_ICON, LAYOUT, INITIAL_SIDEBAR_STATE,
    WIKI_BLUE, WIKI_BLUE_LIGHT, WIKI_BLUE_DARK, WIKI_INK, WIKI_GRAY,
    CARD_LIGHT, CARD_DARK, BG_DEEP, BG_MID, TEXT_LIGHT, TEXT_MUTED,
    KORIKATH_LOGO_URL, get_streamlit_css
)

# --- GLOBAL PAGE CONFIGURATION ---
st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon=PAGE_ICON,
    layout=LAYOUT,
    initial_sidebar_state=INITIAL_SIDEBAR_STATE
)

CUSTOM_CSS = get_streamlit_css()
st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)

# --- MAPS & CONSTANTS ---

def add_codes_from_selectors():
    sel_events = st.session_state.get("sel_events", [])
    sel_countries = st.session_state.get("sel_countries", [])
    yr_start, yr_end = st.session_state.get("yr_range", (2021, 2023))

    if not sel_events or not sel_countries:
        st.toast("Select at least one event type and one target country.", icon="⚠️")
        return

    new_codes = []
    for event in sel_events:
        for country in sel_countries:
            for yr in range(yr_start, yr_end + 1):
                new_codes.append(f"{event}{country}{yr % 100:02d}")

    existing = st.session_state.get("code_input", "").split()
    merged = existing + [c for c in new_codes if c not in existing]
    st.session_state.code_input = " ".join(merged)
    st.toast(f"Merged {len(new_codes)} validation vectors.")

def clear_code_input():
    st.session_state.code_input = ""
    st.toast("Input registry cleared.")

import io
import matplotlib.pyplot as plt

def _figure_to_png(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=200, bbox_inches="tight")
    buffer.seek(0)
    return buffer

def render_heatmap_view(valid_countries):
    cols = st.columns(2)
    for idx, (country_code, events) in enumerate(valid_countries.items()):
        fig = create_heatmap(events, COUNTRY_MAP.get(country_code, country_code))
        with cols[idx % 2]:
            with st.container(border=True):
                st.pyplot(fig, use_container_width=True, clear_figure=True)
                png_bytes = _figure_to_png(fig)
                st.download_button(
                    "Download heatmap image",
                    data=png_bytes,
                    file_name=f"{country_code}_retention_heatmap.png",
                    mime="image/png",
                    use_container_width=True,
                )
                plt.close(fig)

def render_table_view(valid_countries):
    table_df = build_global_table(valid_countries)
    if table_df.empty:
        st.info("Insufficient longitudinal data found to populate records.")
        return
    st.dataframe(table_df, use_container_width=True)
    csv_bytes = table_df.to_csv(index=True, index_label="Rank").encode("utf-8")
    st.download_button(
        "Download Data Array (CSV)", data=csv_bytes,
        file_name="wikimedia_retention_suite.csv", mime="text/csv"
    )

def render_worldmap_view(valid_countries):
    metric_choice = st.radio("Metric Vector Selection", ["Average", "Median"], horizontal=True, key="worldmap_metric")
    world_df = build_world_data(valid_countries, metric_choice)
    if world_df.empty:
        st.info("Geographic coordinates unavailable for the current selection.")
        return
    fig = create_worldmap(world_df, metric_choice)
    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(world_df, use_container_width=True, hide_index=True)

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
    app_mode = st.radio(
        "Select Suite Interface",
        ["Retention Analytics", "Health Evaluation", "New User Influx", "Methodology"],
        horizontal=False,
    )
    
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
        
    elif app_mode == "Health Evaluation":
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

    elif app_mode == "New User Influx":
        st.subheader("Series Configuration")
        influx_event = st.selectbox(
            "Campaign Type",
            options=list(EVENT_MAP.keys()),
            format_func=lambda k: f"Wiki Loves {EVENT_MAP[k]} ({k.upper()})",
            key="influx_event"
        )
        default_country_idx = COUNTRY_OPTIONS.index('de') if 'de' in COUNTRY_OPTIONS else 0
        influx_country = st.selectbox(
            "Target Country",
            options=COUNTRY_OPTIONS,
            index=default_country_idx,
            format_func=country_display_name,
            key="influx_country"
        )
        influx_years = st.slider(
            "Year Span",
            2010, 2026, (2020, 2024),
            key="influx_years"
        )
        
        generated_influx_codes = " ".join(
            f"{influx_event}{influx_country}{y % 100:02d}"
            for y in range(influx_years[0], influx_years[1] + 1)
        )
        custom_series = st.text_input(
            "Campaign Sequence",
            value=generated_influx_codes,
            key="custom_influx_series"
        )
        st.markdown("---")
        run_influx = st.button("Evaluate Influx Trends", type="primary", use_container_width=True)

    st.markdown("---")
    st.caption("Integrated Analytics Platform Engine")

# --- MAIN RUNTIME ROUTER ---
st.markdown("<br>", unsafe_allow_html=True)

if app_mode == "Methodology":
    st.html('<div class=\"hero-title\">Methodology &amp; Usage Guide</div>')
    st.html('<div class=\"hero-subtitle\">Understand how the suite turns Wikimedia Commons campaign data into retention and health signals.</div>')

    st.markdown("### Quick guide")
    guide_col1, guide_col2, guide_col3, guide_col4 = st.columns(4, gap="medium")
    with guide_col1:
        st.html('''<div class="methodology-card">
                <div class="methodology-card-title">1 · Retention Analytics</div>
                <p>Enter two or more campaign codes, such as <code>wlmbd22 wlmbd23</code>.
                Run the analysis, then choose a table, heatmap, or world map to compare
                contributor overlap across campaigns.</p>
            </div>''')
    with guide_col2:
        st.html('''<div class="methodology-card">
                <div class="methodology-card-title">2 · Health Evaluation</div>
                <p>Enter one target code, select a previous-year or custom baseline,
                choose a region, and evaluate. Review the five weighted indicators and
                the peer-relative diagnostic insights.</p>
            </div>''')
    with guide_col3:
        st.html('''<div class="methodology-card">
                <div class="methodology-card-title">3 · New User Influx</div>
                <p>Select a campaign type, country, and multi-year range.
                Examine stacked newcomer vs returning volumes, YoY growth trends,
                and cumulative community expansion.</p>
            </div>''')
    with guide_col4:
        st.html('''<div class="methodology-card">
                <div class="methodology-card-title">4 · Methodology</div>
                <p>Use this tab as the reference layer: it explains the data sources,
                processing stages, scoring model, and interpretation limits behind all
                three analysis modes.</p>
            </div>''')

    st.markdown("---")
    st.markdown("### How the website works")
    st.markdown(
        """
        The website does not store a separate campaign database. When you run an
        analysis, it looks up the requested campaign information from Wikimedia
        Commons and then calculates the result for that request.

        **Step 1 — Read the campaign code.** A code such as `wlmbd24` tells the
        website the event (`wlm`, Wiki Loves Monuments), country (`bd`, Bangladesh),
        and year (`24`, 2024). The code is translated into the matching Commons
        category where that campaign's files are kept.

        **Step 2 — Find the contributors.** The website checks which Wikimedia
        accounts uploaded files in each campaign category. It first tries the faster
        Toolforge source. If that source is unavailable, it asks the official
        Wikimedia Commons Action API instead. The returned accounts are treated as
        a group so that the groups from two campaigns can be compared.

        **Step 3 — Collect supporting file information.** For health evaluation, the
        website also checks a sample of campaign files. It looks at whether files are
        used on Wikimedia projects, whether they belong to Commons quality categories,
        and how uploads are distributed among contributors. This keeps the request
        practical while still providing useful signals.

        **Step 4 — Cache recent results.** A completed lookup is kept for one hour.
        Running the same analysis again during that period is faster and avoids
        sending unnecessary repeat requests. A new campaign or an expired cache
        causes the website to look up fresh information.

        **Step 5 — Show the result.** Retention Analytics shows overlap between
        campaign contributor groups. Health Evaluation compares one target campaign
        with a baseline and with active peers in the selected region. Methodology
        explains how those results should be read.
        """,
    )

    st.markdown("### What each mode measures")
    model_col1, model_col2 = st.columns(2, gap="large")
    with model_col1:
        st.html('''<div class="methodology-panel">
                <h4>Retention Analytics</h4>
                <p><b>Purpose:</b> See whether contributors from one campaign appear
                again in another campaign.</p>
                <p>Enter two or more campaign codes and run the analysis. The website
                groups contributors by country and only compares a country when it has
                at least two campaigns with participants.</p>
                <p>For each pair, it counts the accounts present in both campaigns and
                divides by the number in the first campaign:</p>
                <div class="formula">returning share = accounts in both ÷ accounts in the first campaign × 100</div>
                <p>This is directional. A result from 2022 to 2023 can differ from
                the result from 2023 to 2022 because the two starting groups may have
                different sizes.</p>
                <p><b>Views:</b> The table gives exact rows, the heatmap makes strong
                and weak connections easier to spot, and the world map summarizes
                country-level retention.</p>
            </div>''')
    with model_col2:
        st.html('''<div class="methodology-panel">
                <h4>Health Evaluation</h4>
                <p><b>Purpose:</b> Give one campaign a structured health check compared
                with a previous campaign and with similar campaigns in its region.</p>
                <p>The target and baseline must both have participants. If either
                campaign has not taken place or has no participants, the website stops
                and displays a message instead of producing a score.</p>
                <p>The final score is between 0 and 100. It combines five signals:</p>
                <ul>
                    <li><b>Returning contributors (35%):</b> how many baseline
                    contributors came back.</li>
                    <li><b>New contributors (20%):</b> how much of the target group
                    is new compared with the baseline.</li>
                    <li><b>File usage (20%):</b> how many sampled files are used on
                    Wikimedia projects.</li>
                    <li><b>Image quality (15%):</b> how many sampled files are in
                    Commons quality categories.</li>
                    <li><b>Contributor spread (10%):</b> whether uploads are shared
                    across many people or concentrated among a small group.</li>
                </ul>
                <p>Each signal is compared with the strongest available campaigns in
                the selected region. This makes the result a local comparison, not a
                claim that one fixed score is good everywhere.</p>
            </div>''')

    st.markdown("### How to use the results responsibly")
    st.markdown(
        """
        - A high retention value means more of the earlier contributor group returned;
          it does not prove that every contributor was contacted or that the campaign
          was successful in every other way.
        - A high health score means the target looks strong against the selected
          comparison group. Changing the region or baseline can change the result.
        - File usage and quality values are based on the files the website can inspect.
          They are useful indicators, not a complete review of image quality or impact.
        - Empty or missing campaign data is treated as a data problem, not as a zero
          score. The Health Evaluation mode will not score a target or baseline that
          has no participants.
        - Use the results to start a conversation about follow-up, recruitment, and
          campaign design. Combine them with organizer knowledge and local context.
        """,
    )
    st.markdown("### Common workflow")
    st.markdown(
        """
        1. Start in **Retention Analytics** when you want to compare multiple years
           or countries.
        2. Start in **Health Evaluation** when you want one target campaign's summary.
        3. Use the previous-year baseline for a normal year-over-year comparison, or
           provide a custom baseline when the usual previous year is not appropriate.
        4. Open **Methodology** whenever you need to check what a number includes
           before sharing or interpreting it.
        """,
    )
    st.info(
        "Results describe observable Wikimedia Commons activity, not the full experience "
        "of campaign participants. Missing categories, API limits, sampled files, and "
        "different campaign sizes can affect comparisons."
    )

elif app_mode == "Retention Analytics":
    st.html('<div class=\"hero-title\">Cross-Event Retention Analytics</div>')
    st.html('<div class=\"hero-subtitle\">Evaluate longitudinal patterns and ecosystem user migration parameters.</div>')

    if st.session_state.last_valid_countries is None:
        st.markdown("### Quick start")
        landing_col1, landing_col2, landing_col3 = st.columns(3, gap="medium")
        with landing_col1:
            st.markdown(
                "**Retention Analytics**  \n"
                "Enter two or more campaign codes in the sidebar, then run the analysis "
                "to compare returning contributors."
            )
        with landing_col2:
            st.markdown(
                "**Health Evaluation**  \n"
                "Switch modes, enter a target campaign, choose a baseline and region, "
                "then review its peer-relative scorecard."
            )
        with landing_col3:
            st.markdown(
                "**Methodology**  \n"
                "Open the third mode for the technical data flow, scoring model, and "
                "interpretation guidance."
            )
    
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

elif app_mode == "Health Evaluation":
    st.html('<div class="hero-title">Campaign Health Evaluation Suite</div>')
    st.html('<div class=\"hero-subtitle\">Compute analytical structural health indexes relative to real-time regional performance clusters.</div>')

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

            target_users = all_fetched_data.get(target_event.lower(), set())
            base_users = all_fetched_data.get(baseline_event.lower(), set())
            missing_campaigns = []
            if not base_users:
                missing_campaigns.append(f"previous/baseline campaign {baseline_event.upper()}")
            if not target_users:
                missing_campaigns.append(f"target campaign {target_event.upper()}")
            if missing_campaigns:
                st.warning(
                    "No participants were found for the "
                    + " and ".join(missing_campaigns)
                    + ". The campaign may not have taken place, or its participant data "
                      "is not available, so a health score cannot be calculated."
                )
                st.stop()
            
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

            target_structural_metrics = structural_metrics.get(
                target_event.lower(),
                {"quality_image_share": 0.0, "top10_uploader_share": 100.0, "usage_share": 0.0, "total_uploads": 0}
            )

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
                st.html(card_html)
                
            with col2:
                st.markdown("### Diagnostic Context Insights")
                st.markdown(f"<p style='color: {TEXT_MUTED}; margin-bottom: 1.5rem;'>Automated strategic diagnostic evaluations measured relative to peers in the <b>{region}</b> cluster framework.</p>", unsafe_allow_html=True)
                
                insights = generate_insights(metrics, region.split(" (")[0], benchmarks)

                for insight in insights:
                    st.html(f"""
                    <div class="insight-box">
                        <p>{insight}</p>
                    </div>
                    """)

                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("View Quantifiable Cohort Footprints"):
                    st.write(f"**Target Campaign Total Contributors:** {len(target_users)}")
                    st.write(f"**Historical Baseline Group Size:** {len(base_users)}")
                    st.write(f"**Common Intersecting User Core:** {len(target_users & base_users)}")

elif app_mode == "New User Influx":
    st.html('<div class=\"hero-title\">Year-over-Year New User Influx</div>')
    st.html('<div class=\"hero-subtitle\">Track newcomer acquisition, returning veteran retention, and community expansion across consecutive campaign editions.</div>')
    
    series_codes = [c for c in custom_series.strip().split() if CODE_RE.match(c)]
    
    if run_influx or series_codes:
        if len(series_codes) < 2:
            st.warning("Please provide at least two chronological campaign editions to compute Year-over-Year influx.")
        else:
            with st.spinner("Analyzing multi-year campaign cohort influx across Wikimedia Commons..."):
                influx_data = compute_yoy_influx(series_codes)
                
            if not influx_data['records'] or all(r['total_active'] == 0 for r in influx_data['records']):
                st.info("No participant records identified for this sequence on Wikimedia Commons.")
            else:
                summary = influx_data['summary']
                lifecycle = influx_data['lifecycle']
                
                # Metrics Strip
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Cumulative Community", f"{summary['total_unique_community']:,}")
                m2.metric("Avg Newcomer Influx", f"{summary['avg_newcomer_share_pct']}%")
                m3.metric("Peak Influx Year", f"{summary['peak_influx_year']} (+{summary['peak_influx_count']:,})")
                m4.metric("Latest Edition", f"{summary['latest_total']:,} ({summary['latest_year']})")
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Plotly Chart
                country_name = country_display_name(influx_country)
                event_name = EVENT_MAP.get(influx_event, influx_event.upper())
                chart_title = f"Wiki Loves {event_name} ({country_name}) — Contributor Influx & Growth"
                fig = create_influx_plotly_chart(influx_data['records'], title=chart_title)
                st.plotly_chart(fig, use_container_width=True)
                
                # Contributor Longevity Profile
                st.markdown("### Contributor Longevity Profile")
                l1, l2, l3 = st.columns(3)
                l1.info(f"**1-Time Entrants (One-off):** {lifecycle['one_time']:,}")
                l2.success(f"**Repeaters (2–3 Editions):** {lifecycle['repeat_2_3']:,}")
                l3.warning(f"**Core Veterans (4+ Editions):** {lifecycle['core_4_plus']:,}")

                # Data Table
                st.markdown("### Longitudinal Influx Breakdown")
                import pandas as pd
                df_records = pd.DataFrame(influx_data['records'])
                rename_cols = {
                    'year': 'Year',
                    'code': 'Campaign',
                    'total_active': 'Total Active',
                    'new_contributors': 'New Entrants (It)',
                    'returning_contributors': 'Returning (Rt)',
                    'newcomer_share_pct': 'Newcomer %',
                    'retention_from_prev_pct': 'Direct Retention %',
                    'yoy_growth_pct': 'YoY Growth %',
                    'new_to_veteran_ratio': 'New/Veteran Ratio',
                    'cumulative_pool': 'Cumulative Pool'
                }
                df_display = df_records[list(rename_cols.keys())].rename(columns=rename_cols)
                st.dataframe(df_display, use_container_width=True, hide_index=True)
                
                # Download CSV
                csv = df_display.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="⬇ Download Influx Matrix (CSV)",
                    data=csv,
                    file_name=f"influx_{influx_event}_{influx_country}_{influx_years[0]}_{influx_years[1]}.csv",
                    mime="text/csv",
                )

