import os
# Ensure headless matplotlib and writable cache directory before any pyplot imports
os.environ.setdefault('MPLCONFIGDIR', '/tmp/matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

import base64
import html
import io
import json
import re
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import permutations
from math import ceil

import numpy as np
import pandas as pd
import plotly.express as px
import requests
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from app_config import (
    NAV_TEAL, NAV_ACCENT, BG_CANVAS, TEXT_INK, TEXT_MUTED, BORDER_COLOR,
    WIKI_BLUE, WIKI_BLUE_HOVER, CARD_LIGHT, CARD_SUBTLE
)

# Load configuration
with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'r') as f:
    config = json.load(f)

EVENT_MAP = config['EVENT_MAP']
COUNTRY_MAP = config['COUNTRY_MAP']
REGION_COUNTRY_MAPPING = config['REGION_COUNTRY_MAPPING']

CODE_RE = re.compile(r'(wlf|wle|wlm|wlb)([a-z]{0,2})(\d{2})')
EXAMPLE_CODES = "wlmde21 wlmde22 wlmbd22 wlmbd23"
COUNTRY_OPTIONS = sorted(COUNTRY_MAP.keys(), key=lambda k: COUNTRY_MAP[k])

# --- IN-MEMORY CACHING ---
_DATA_CACHE = {}

def timed_cache(ttl=3600):
    """In-memory thread-safe cache decorator with TTL (seconds)."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            key = (func.__name__, args, tuple(sorted(kwargs.items())))
            now = time.time()
            if key in _DATA_CACHE:
                val, ts = _DATA_CACHE[key]
                if now - ts < ttl:
                    return val
            result = func(*args, **kwargs)
            _DATA_CACHE[key] = (result, now)
            return result
        return wrapper
    return decorator

# --- RELIABLE HTTP SESSION ---
def get_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504, 429])
    session.mount('https://', HTTPAdapter(max_retries=retries))
    return session

http_session = get_session()

# Refined bright colormaps harmonized with theme
WIKI_CMAP = LinearSegmentedColormap.from_list(
    "campaign_marine", ["#f0fdf4", "#c6f6d5", "#72ded6", "#256d85", "#183f54"]
)
WORLD_SCALE = ["#eef7fa", "#a8dfed", "#72ded6", "#256d85", "#183f54"]

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_HEADERS = {
    "User-Agent": "WikimediaCampaignSuite/1.0 (https://github.com/siddiquetanvir/WebApp)"
}
QUALITY_IMAGE_KEYWORDS = (
    "quality images",
    "featured pictures",
)

def country_display_name(cc):
    return COUNTRY_MAP.get(cc, cc).replace('_', ' ')

def code_to_category(code):
    code = re.sub(r'\s+', '', code).lower()
    match = CODE_RE.match(code)
    if not match:
        return None
    event, cc, yr = match.groups()
    category = f"Images_from_Wiki_Loves_{EVENT_MAP[event]}_{2000 + int(yr)}"
    if cc and event != 'wlb':
        country_label = COUNTRY_MAP.get(cc)
        if not country_label:
            return None
        category += f"_in_{country_label}"
    return category

# --- DATA ACQUISITION LOGIC ---
def _fetch_toolforge_data(category):
    try:
        url = f"https://ptools.toolforge.org/uploadersincat.php?category={category}"
        response = http_session.get(url, timeout=8)
        if response.status_code != 200:
            return None
        matches = re.findall(r'User:([^"\'<>#]+)</a>\s*:\s*(\d+)\s*files', response.text)
        if matches:
            uploader_counts = {html.unescape(user.strip()): int(count) for user, count in matches}
            return uploader_counts
        if "No files found" in response.text or "<fieldset>" in response.text:
            return {}
        return None
    except Exception:
        return None

def _fetch_participants_from_api(category):
    users = set()
    params = {
        "action": "query",
        "format": "json",
        "generator": "categorymembers",
        "gcmtitle": f"Category:{category}",
        "gcmtype": "file",
        "gcmlimit": "500",
        "prop": "imageinfo",
        "iiprop": "user"
    }

    try:
        while True:
            response = http_session.get(COMMONS_API, params=params, headers=COMMONS_HEADERS, timeout=20)
            response.raise_for_status()
            payload = response.json()

            pages = payload.get("query", {}).get("pages", {})
            for page in pages.values():
                imageinfo = page.get("imageinfo", [])
                if imageinfo:
                    user = imageinfo[0].get("user")
                    if user:
                        users.add(user)

            continuation = payload.get("continue")
            if not continuation:
                break
            params["gcmcontinue"] = continuation.get("gcmcontinue")
            params["continue"] = continuation.get("continue", "gcmcontinue||")

        return users
    except Exception as e:
        print(f"Error fetching participants from API for {category}: {e}")
        return set()

@timed_cache(ttl=3600)
def get_participants(code):
    category = code_to_category(code)
    if not category:
        return set()

    # 1. High-speed primary: Toolforge replica scraper
    toolforge_uploaders = _fetch_toolforge_data(category)
    if toolforge_uploaders is not None:
        return set(toolforge_uploaders.keys())

    # 2. Resilient fallback: Commons Action API
    return _fetch_participants_from_api(category)

def _fetch_file_sample_metrics(category, max_sample=1500):
    params = {
        "action": "query",
        "format": "json",
        "generator": "categorymembers",
        "gcmtitle": f"Category:{category}",
        "gcmtype": "file",
        "gcmlimit": "500",
        "prop": "categories|globalusage",
        "clcategories": "Category:Quality images|Category:Featured pictures",
        "gulimit": "10",
    }

    total_sampled = 0
    quality_count = 0
    used_count = 0

    while total_sampled < max_sample:
        try:
            response = http_session.get(COMMONS_API, params=params, headers=COMMONS_HEADERS, timeout=15)
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            print(f"Error sampling files for {category}: {e}")
            break

        pages = payload.get("query", {}).get("pages", {})
        if not pages:
            break

        for page in pages.values():
            total_sampled += 1
            if page.get("categories"):
                quality_count += 1
            if page.get("globalusage"):
                used_count += 1

        continuation = payload.get("continue")
        if not continuation or "gcmcontinue" not in continuation:
            break
        params["gcmcontinue"] = continuation.get("gcmcontinue")
        params["continue"] = continuation.get("continue", "gcmcontinue||")

    return {
        "sampled": total_sampled,
        "quality_count": quality_count,
        "used_count": used_count
    }

@timed_cache(ttl=3600)
def get_campaign_structural_metrics(code):
    category = code_to_category(code)
    if not category:
        return {"quality_image_share": 0.0, "top10_uploader_share": 0.0, "usage_share": 0.0, "total_uploads": 0}

    toolforge_uploaders = _fetch_toolforge_data(category)

    if toolforge_uploaders:
        uploader_counts = toolforge_uploaders
        total_uploads = sum(uploader_counts.values())
    else:
        uploader_counts = {}
        total_uploads = 0

    if uploader_counts:
        top_uploader_count = max(1, ceil(len(uploader_counts) * 0.10))
        sorted_upload_counts = sorted(uploader_counts.values(), reverse=True)
        top_uploads = sum(sorted_upload_counts[:top_uploader_count])
        attributed_uploads = sum(sorted_upload_counts)
        top10_uploader_share = (top_uploads / attributed_uploads) * 100
    else:
        top10_uploader_share = 100.0

    sample = _fetch_file_sample_metrics(category, max_sample=1500)
    sample_size = sample["sampled"]

    if sample_size > 0:
        quality_image_share = (sample["quality_count"] / sample_size) * 100
        usage_share = (sample["used_count"] / sample_size) * 100
    else:
        quality_image_share = 0.0
        usage_share = 0.0

    if total_uploads == 0:
        total_uploads = sample_size

    return {
        "quality_image_share": quality_image_share,
        "top10_uploader_share": top10_uploader_share,
        "usage_share": usage_share,
        "total_uploads": total_uploads,
    }

def fetch_structural_metrics_concurrently(codes, threads=8):
    results = {}
    total = len(codes)
    if total == 0:
        return results

    with ThreadPoolExecutor(max_workers=min(threads, max(1, total))) as executor:
        future_to_code = {executor.submit(get_campaign_structural_metrics, code): code for code in codes}
        for future in as_completed(future_to_code):
            code = future_to_code[future]
            try:
                results[code] = future.result()
            except Exception:
                results[code] = {"quality_image_share": 0.0, "top10_uploader_share": 0.0, "usage_share": 0.0, "total_uploads": 0}

    return results

def fetch_all_concurrently(codes, threads=16):
    """Fetch participant footprints for codes concurrently without Streamlit UI dependencies."""
    results = {}
    total = len(codes)
    if total == 0:
        return results

    with ThreadPoolExecutor(max_workers=min(threads, max(1, total))) as executor:
        future_to_code = {executor.submit(get_participants, code): code for code in codes}
        for future in as_completed(future_to_code):
            code = future_to_code[future]
            try:
                results[code] = future.result()
            except Exception:
                results[code] = set()

    return results

# --- RETENTION SUITE UTILITIES ---
def compute_retention_percentages(events):
    percentages = []
    for source, target in permutations(events.keys(), 2):
        source_users = events[source]
        if not source_users:
            continue
        overlap = len(source_users & events[target])
        percentages.append((overlap / len(source_users)) * 100)
    return percentages

def create_heatmap(events, country_name):
    """Generate high-contrast Seaborn retention heatmap on bright clean canvas."""
    sns.set_theme(style="white")
    event_codes = list(events.keys())
    size = len(event_codes)
    matrix = np.zeros((size, size))

    readable_labels = []
    for code in event_codes:
        match = CODE_RE.match(code)
        if match:
            event, cc, yr = match.groups()
            readable_labels.append(f"{EVENT_MAP.get(event, event.upper())} 20{yr}")
        else:
            readable_labels.append(code)

    for i, source in enumerate(event_codes):
        for j, target in enumerate(event_codes):
            source_users = events[source]
            if not source_users:
                matrix[i, j] = 0.0
            else:
                overlap = len(source_users & events[target])
                matrix[i, j] = (overlap / len(source_users)) * 100

    max_retention = np.nanmax(matrix) if np.size(matrix) else 0.0
    rounded_max = max(10, int(np.ceil(max_retention / 10.0) * 10))
    np.fill_diagonal(matrix, rounded_max)

    fig, ax = plt.subplots(figsize=(max(5, size * 1.2), max(4, size)))
    fig.patch.set_facecolor("#ffffff")
    ax.patch.set_facecolor("#ffffff")

    sns.heatmap(
        matrix, annot=True, fmt=".1f",
        xticklabels=readable_labels, yticklabels=readable_labels,
        cmap=WIKI_CMAP, linewidths=1.5, linecolor="#ffffff",
        cbar_kws={'label': 'Retention (%)'},
        vmin=0, vmax=rounded_max, ax=ax,
        annot_kws={"fontweight": "bold", "fontsize": 10, "color": TEXT_INK}
    )

    ax.set_title(f"{country_name.replace('_', ' ')} Retention Matrix", pad=15, fontweight='bold',
                 fontsize=13, color=TEXT_INK)
    ax.set_ylabel("Source Cohort", fontweight='bold', color=TEXT_MUTED, fontsize=10)
    ax.set_xlabel("Target Cohort", fontweight='bold', color=TEXT_MUTED, fontsize=10)
    plt.xticks(rotation=45, ha='right', color=TEXT_INK, fontsize=9)
    plt.yticks(rotation=0, color=TEXT_INK, fontsize=9)
    plt.tight_layout()
    return fig

def build_global_table(valid_countries):
    rows = []
    for country_code, events in valid_countries.items():
        percentages = compute_retention_percentages(events)
        if not percentages:
            continue
        rows.append({
            "Country": country_display_name(country_code),
            "Occurrences": len(events),
            "Avg Retention (%)": round(float(np.mean(percentages)), 1),
            "Median Retention (%)": round(float(np.median(percentages)), 1),
            "Max Retention (%)": round(float(np.max(percentages)), 1),
            "Std Dev (%)": round(float(np.std(percentages, ddof=1)), 1) if len(percentages) > 1 else 0.0,
        })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values("Avg Retention (%)", ascending=False).reset_index(drop=True)
    df.index += 1
    return df

def build_world_data(valid_countries, metric):
    rows = []
    for country_code, events in valid_countries.items():
        percentages = compute_retention_percentages(events)
        if not percentages:
            continue
        value = float(np.mean(percentages)) if metric == "Average" else float(np.median(percentages))
        rows.append({
            "Country": country_display_name(country_code),
            "Retention (%)": round(value, 1),
            "Occurrences Compared": len(events),
        })
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("Retention (%)", ascending=False).reset_index(drop=True)

def create_worldmap(df, metric_label):
    """Plotly Choropleth map themed to bright natural earth aesthetic matching GLAMtools."""
    max_val = df["Retention (%)"].max() if not df.empty and "Retention (%)" in df.columns else 10.0
    range_max = max(15, float(max_val) * 1.15)
    
    fig = px.choropleth(
        df,
        locations="Country",
        locationmode="country names",
        color="Retention (%)",
        color_continuous_scale=WORLD_SCALE,
        range_color=(0, range_max),
        hover_name="Country",
        hover_data={"Occurrences Compared": True, "Retention (%)": True},
        projection="natural earth",
    )
    fig.update_layout(
        title=dict(
            text=f"{metric_label} Retention Distribution",
            x=0.02,
            font=dict(color=TEXT_INK, size=16, family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif")
        ),
        geo=dict(
            showcountries=True,
            countrycolor="#d0d7de",
            countrywidth=0.7,
            showcoastlines=True,
            coastlinecolor="#d0d7de",
            showland=True,
            landcolor="#e8ecef",
            showocean=True,
            oceancolor="#f8f9fa",
            showlakes=True,
            lakecolor="#ffffff",
            bgcolor="#ffffff",
        ),
        paper_bgcolor="#ffffff",
        plot_bgcolor="#ffffff",
        margin=dict(r=10, t=50, l=10, b=10),
        coloraxis_colorbar=dict(
            title=dict(text="Retention", font=dict(color=TEXT_INK, size=12)),
            tickfont=dict(color=TEXT_INK, size=11),
            ticksuffix="%",
            outlinewidth=1,
            outlinecolor="#e0e0e0",
            bgcolor="rgba(255,255,255,0.9)",
            len=0.75
        ),
        font=dict(color=TEXT_INK, family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"),
        hoverlabel=dict(bgcolor="#ffffff", font_color=TEXT_INK, font_family="Inter, sans-serif", bordercolor="#e0e0e0"),
    )
    return fig

# --- HEALTH ASSESSMENT CORE ENGINE ---
def calculate_stars(score, max_score=100):
    normalized = min(max(score / max_score, 0), 1)
    stars = int(round(normalized * 5))
    stars = min(5, max(1, stars))
    return "★" * stars + "☆" * (5 - stars), stars

def generate_health_metrics(
    target_users,
    baseline_users,
    target_structural_metrics,
    benchmarks
):
    metrics = {}

    def relative_score(metric_value, benchmark_value, positive_is_higher=True):
        if benchmark_value <= 0:
            return 60.0 if metric_value >= 0 else 0.0
        if not positive_is_higher:
            metric_value = max(metric_value, 0.0)
            benchmark_value = max(benchmark_value, 0.0)
            if metric_value <= 0:
                return 0.0
            return min(100.0, max(0.0, (benchmark_value / metric_value) * 60))
        if metric_value <= 0:
            return 0.0
        return min(100.0, max(0.0, (metric_value / benchmark_value) * 60))

    if baseline_users:
        overlap = len(target_users & baseline_users)
        retention_rate = (overlap / len(baseline_users)) * 100
    else:
        retention_rate = 0.0
    metrics['Retention'] = {
        'raw': f"{retention_rate:.1f}%",
        'score': relative_score(retention_rate, benchmarks['retention'], positive_is_higher=True)
    }

    if target_users:
        new_users = len(target_users - baseline_users)
        growth_rate = (new_users / len(target_users)) * 100
    else:
        growth_rate = 0.0
    metrics['Growth'] = {
        'raw': f"{growth_rate:.1f}%",
        'score': relative_score(growth_rate, benchmarks['growth'], positive_is_higher=True)
    }
    
    raw_usage = float(target_structural_metrics.get("usage_share", 0.0))
    usage_baseline = float(benchmarks.get('usage', 0.0))
    metrics['Usage'] = {
        'raw': raw_usage,
        'score': relative_score(raw_usage, usage_baseline, positive_is_higher=True)
    }

    raw_quality = float(target_structural_metrics.get("quality_image_share", 0.0))
    quality_baseline = float(benchmarks.get('quality', 0.0))
    metrics['Quality'] = {
        'raw': raw_quality,
        'score': relative_score(raw_quality, quality_baseline, positive_is_higher=True)
    }

    raw_diversity = float(target_structural_metrics.get("top10_uploader_share", 100.0))
    diversity_baseline = float(benchmarks.get('diversity', 0.0))
    metrics['Diversity'] = {
        'raw': raw_diversity,
        'score': relative_score(raw_diversity, diversity_baseline, positive_is_higher=False)
    }

    overall = (
        (metrics['Retention']['score'] * 0.35) +
        (metrics['Growth']['score'] * 0.20) +
        (metrics['Usage']['score'] * 0.20) +
        (metrics['Quality']['score'] * 0.15) +
        (metrics['Diversity']['score'] * 0.10)
    )
    metrics['Overall'] = round(overall)

    return metrics

def generate_insights(metrics, region_name, benchmarks):
    insights = []

    raw_ret = float(metrics['Retention']['raw'].replace('%', '')) if isinstance(metrics['Retention']['raw'], str) else float(metrics['Retention']['raw'])
    ret_diff = raw_ret - benchmarks['retention']
    region_label = f"{region_name} regional" if region_name else "regional"
    if ret_diff > 5:
        insights.append(f"Retention is healthy: {raw_ret:.1f}% is {ret_diff:.1f} percentage points above the {region_label} baseline, indicating strong continuity of contributors from prior campaigns.")
    elif ret_diff < -5:
        insights.append(f"Retention is under pressure: the campaign is losing more returning contributors than the {region_label} standard, suggesting a likely engagement or follow-up gap.")
    else:
        insights.append(f"Retention is stable: the campaign is tracking near the {region_label} benchmark, with no major churn signal evident.")

    raw_growth = float(metrics['Growth']['raw'].replace('%', '')) if isinstance(metrics['Growth']['raw'], str) else float(metrics['Growth']['raw'])
    if raw_growth > 75 and raw_ret < 10:
        insights.append(f"Growth is strong but fragile: {raw_growth:.1f}% new contributors joined, yet retention remains low, which can create churn without sustained re-engagement work.")
    elif raw_growth > 50:
        insights.append("Growth pipeline is healthy: the campaign is attracting a substantial influx of new contributors and is expanding the contributor base beyond the historical core.")
    elif raw_growth < 20:
        insights.append("Growth momentum is limited: the campaign is not expanding the contributor base enough to offset retention losses.")

    if metrics['Quality']['score'] >= 70:
        insights.append("Quality image signal is outperforming the regional norm: a larger share of uploaded files meets Commons quality standards.")
    elif metrics['Quality']['score'] < 40:
        insights.append("Quality image signal is below benchmark: the campaign is producing fewer files that meet the regional quality threshold.")
    else:
        insights.append("Quality image signal is near benchmark: the campaign is broadly aligned with the regional quality profile.")

    if metrics['Usage']['score'] >= 70:
        insights.append("Content Utility is excellent: a high proportion of uploaded files are actively being used across Wikimedia projects.")
    elif metrics['Usage']['score'] < 40:
        insights.append("Content Utility is low: very few uploaded files are currently in use, suggesting an opportunity to focus on encyclopedic integration.")
    else:
        insights.append("Content Utility is average: file usage across wikis is aligned with regional norms.")

    if metrics['Diversity']['score'] < 40:
        insights.append("Diversity remains concentrated: a small set of contributors accounts for a large share of uploads, which reduces resilience and breadth.")
    else:
        insights.append("Diversity is healthy: upload activity is comparatively spread across a wider contributor base, which supports campaign resilience and participation equity.")

    return insights
