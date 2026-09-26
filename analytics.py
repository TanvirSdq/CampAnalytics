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
import logging
import re
import threading
import time
from collections import defaultdict, OrderedDict
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import permutations
from math import ceil

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import seaborn as sns
from matplotlib.colors import LinearSegmentedColormap
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib.parse
import campaign_cache

from app_config import (
    NAV_TEAL, NAV_ACCENT, BG_CANVAS, TEXT_INK, TEXT_MUTED, BORDER_COLOR,
    WIKI_BLUE, WIKI_BLUE_HOVER, CARD_LIGHT, CARD_SUBTLE
)

logger = logging.getLogger(__name__)

# Load configuration
with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'r') as f:
    config = json.load(f)

EVENT_MAP = config['EVENT_MAP']
EVENT_DISPLAY_MAP = config.get('EVENT_DISPLAY_MAP', {
    k: f"Wiki Loves {v}" for k, v in EVENT_MAP.items()
})
EVENT_COUNTRY_SCOPE = config.get('EVENT_COUNTRY_SCOPE', {k: '*' for k in EVENT_MAP})
CATEGORY_NAME_OVERRIDE = config.get('CATEGORY_NAME_OVERRIDE', {})
COUNTRY_MAP = config['COUNTRY_MAP']
REGION_COUNTRY_MAPPING = config['REGION_COUNTRY_MAPPING']
COUNTRIES_WITH_THE = set(config.get('COUNTRIES_WITH_THE', ['cz', 'nl', 'ph', 'uk', 'us']))
KNOWN_BOTS = set(config.get('KNOWN_BOTS', [
    'Flickr upload bot',
    'File Upload Bot (Magnus Manske)',
    'CommonsDelinker',
    'WLM-Bot',
    'Cropbot',
    'Rotbot',
    'FlickrLickr',
    'Wiki Loves Earth Bot',
    'UploadWizard'
]))
BOT_REGEX = re.compile(config.get('BOT_REGEX', r'(?i)(?:bot|_bot|-bot|\s+bot)$'))

def is_bot_account(username):
    """Identify automated bot accounts to ensure human-only analytical integrity."""
    if not username:
        return True
    u = username.strip()
    if u in KNOWN_BOTS:
        return True
    if BOT_REGEX.search(u):
        return True
    return False

CODE_RE = re.compile(r'^(all|wla|wlf|wle|wlm|wlb)([a-z]{0,2})(\d{2})$')
EXAMPLE_CODES = "wlmde21 wlmde22 wlmbd22 wlmbd23"
COUNTRY_OPTIONS = sorted(COUNTRY_MAP.keys(), key=lambda k: COUNTRY_MAP[k])

# --- IN-MEMORY CACHING (BOUNDED LRU) ---
class BoundedLRUCache:
    """Thread-safe bounded LRU cache with maximum size capacity."""
    def __init__(self, maxsize=1000):
        self.maxsize = maxsize
        self._cache = OrderedDict()
        self._lock = threading.Lock()

    def get(self, key, default=None):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            return default

    def set(self, key, value):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            if len(self._cache) > self.maxsize:
                self._cache.popitem(last=False)

    def delete(self, key):
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self):
        with self._lock:
            self._cache.clear()

    def __contains__(self, key):
        with self._lock:
            return key in self._cache

    def __getitem__(self, key):
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
                return self._cache[key]
            raise KeyError(key)

    def __setitem__(self, key, value):
        self.set(key, value)

    def __delitem__(self, key):
        self.delete(key)

    def __len__(self):
        with self._lock:
            return len(self._cache)

    def items(self):
        with self._lock:
            return list(self._cache.items())

    def values(self):
        with self._lock:
            return list(self._cache.values())

    def keys(self):
        with self._lock:
            return list(self._cache.keys())

_DATA_CACHE = BoundedLRUCache(maxsize=1000)
_COMPOSITE_BREAKDOWNS = BoundedLRUCache(maxsize=500)

def timed_cache(ttl=3600):
    """In-memory thread-safe cache decorator with TTL (seconds) and bounded LRU capacity."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            key = (func.__name__, args, tuple(sorted(kwargs.items())))
            now = time.time()
            cached = _DATA_CACHE.get(key)
            if cached is not None:
                val, ts = cached
                if now - ts < ttl:
                    return val
                else:
                    _DATA_CACHE.delete(key)
            result = func(*args, **kwargs)
            _DATA_CACHE.set(key, (result, now))
            return result
        return wrapper
    return decorator

# --- RELIABLE HTTP SESSION WITH CONNECTION POOL SIZING ---
def get_session():
    session = requests.Session()
    retries = Retry(total=5, backoff_factor=1, status_forcelist=[500, 502, 503, 504, 429])
    # pool_connections=20, pool_maxsize=20 safely accommodates ThreadPoolExecutor(max_workers=16)
    adapter = HTTPAdapter(max_retries=retries, pool_connections=20, pool_maxsize=20)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session

http_session = get_session()

# Refined bright colormaps harmonized with theme
WIKI_CMAP = LinearSegmentedColormap.from_list(
    "campaign_marine", ["#f0fdf4", "#c6f6d5", "#72ded6", "#256d85", "#183f54"]
)
WORLD_SCALE = ["#eef7fa", "#a8dfed", "#72ded6", "#256d85", "#183f54"]

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_HEADERS = {
    "User-Agent": "CampAnalytics/1.0 (https://github.com/siddiquetanvir/CampAnalytics; tanvirsiddique@gmail.com)"
}
QUALITY_IMAGE_KEYWORDS = (
    "quality images",
    "featured pictures",
)

def country_display_name(cc):
    return COUNTRY_MAP.get(cc, cc).replace('_', ' ')

def get_campaign_scope_notice(event, country_code=None):
    """
    Returns a contextual notice when a campaign is evaluated for an out-of-scope country.
    Returns None if the country is within the campaign's documented geographic scope.
    """
    if not event or event == 'all':
        return None
    scope = EVENT_COUNTRY_SCOPE.get(event, '*')
    if scope == '*':
        return None

    country_name = COUNTRY_MAP.get(country_code, country_code.upper() if country_code else 'this region').replace('_', ' ')

    if event == 'wlb':
        allowed = scope.get('countries', ['bd', 'in']) if isinstance(scope, dict) else scope
        if country_code and country_code not in allowed:
            return (
                f"Wiki Loves Bangla is a linguistic and cultural campaign dedicated to the global Bengali community "
                f"(primarily Bangladesh and India). It does not hold separate national editions in {country_name}."
            )
    elif event == 'wla':
        allowed = scope if isinstance(scope, list) else []
        if country_code and country_code not in allowed:
            return (
                f"Wiki Loves Africa is a continental initiative organized exclusively within African nations. "
                f"It does not operate national competitions in {country_name}."
            )
    elif isinstance(scope, list) and country_code and country_code not in scope:
        event_title = EVENT_MAP.get(event, event.upper())
        return f"Wiki Loves {event_title} does not operate official editions in {country_name}."

    return None

def code_to_category(code):
    code = re.sub(r'\s+', '', code).lower()
    match = CODE_RE.match(code)
    if not match:
        return None
    event, cc, yr = match.groups()
    if event == 'all':
        return None  # Aggregate pseudo-event resolved in get_participants
    event_name = EVENT_MAP.get(event)
    if not event_name:
        return None
    # Allow per-event category name override if configured
    cat_event = CATEGORY_NAME_OVERRIDE.get(event, event_name.replace(' ', '_'))
    category = f"Images_from_Wiki_Loves_{cat_event}_{2000 + int(yr)}"
    event_scope = EVENT_COUNTRY_SCOPE.get(event, '*')
    countryless_category = isinstance(event_scope, dict) and event_scope.get('no_country_suffix', False)
    if cc and not countryless_category:
        country_label = COUNTRY_MAP.get(cc)
        if not country_label:
            return None
        if cc in COUNTRIES_WITH_THE:
            category += f"_in_the_{country_label}"
        else:
            category += f"_in_{country_label}"
    return category

def get_category_candidates(code):
    """
    Returns ordered list of candidate Commons category names for a code,
    accounting for linguistic variations (with / without 'the') and overrides.
    """
    primary = code_to_category(code)
    if not primary:
        return []
    candidates = [primary]
    code_clean = re.sub(r'\s+', '', code).lower()
    match = CODE_RE.match(code_clean)
    if match:
        event, cc, yr = match.groups()
        event_scope = EVENT_COUNTRY_SCOPE.get(event, '*')
        countryless = isinstance(event_scope, dict) and event_scope.get('no_country_suffix', False)
        if cc and not countryless:
            country_label = COUNTRY_MAP.get(cc)
            if country_label:
                event_name = EVENT_MAP.get(event)
                cat_event = CATEGORY_NAME_OVERRIDE.get(event, event_name.replace(' ', '_')) if event_name else event
                base = f"Images_from_Wiki_Loves_{cat_event}_{2000 + int(yr)}"
                alt = f"{base}_in_{country_label}" if cc in COUNTRIES_WITH_THE else f"{base}_in_the_{country_label}"
                if alt not in candidates:
                    candidates.append(alt)
    return candidates

# --- DATA ACQUISITION LOGIC ---
def _fetch_replica_data(category):
    """
    Direct SQL query against Toolforge MariaDB replica (commonswiki_p) if available.
    Returns dict {username: file_count} or None if replica is unavailable.
    """
    try:
        from pathlib import Path
        replica_cnf = Path.home() / "replica.my.cnf"
        if not replica_cnf.exists():
            return None
        import configparser
        parser = configparser.ConfigParser()
        parser.read(replica_cnf)
        user = parser["client"].get("user")
        password = parser["client"].get("password")
        if not user:
            return None
        import pymysql
        host = os.getenv("COMMONS_REPLICA_HOST", "commonswiki.web.db.svc.wikimedia.cloud")
        conn = pymysql.connect(
            host=host, port=3306, user=user, password=password or "",
            database="commonswiki_p", charset="utf8mb4", connect_timeout=4
        )
        cat_title = category.replace(" ", "_")
        if cat_title.startswith("Category:"):
            cat_title = cat_title[9:]
        with conn.cursor() as cur:
            sql = """
            SELECT a.actor_name, COUNT(*) as cnt
            FROM categorylinks cl
            JOIN page p ON cl.cl_from = p.page_id
            JOIN image i ON p.page_title = i.img_name
            JOIN actor_image a ON i.img_actor = a.actor_id
            WHERE cl.cl_to = %s AND p.page_namespace = 6
            GROUP BY a.actor_name
            """
            cur.execute(sql, (cat_title,))
            rows = cur.fetchall()
            conn.close()
            uploader_counts = {}
            for actor, count in rows:
                if actor and not is_bot_account(actor):
                    uploader_counts[actor] = int(count)
            return uploader_counts if uploader_counts else None
    except Exception as exc:
        logger.debug(f"Commons replica query unavailable: {exc}")
        return None

def _fetch_toolforge_data(category):
    try:
        url = f"https://ptools.toolforge.org/uploadersincat.php?category={category}"
        response = http_session.get(url, headers=COMMONS_HEADERS, timeout=8)
        if response.status_code != 200:
            return None
        matches = re.findall(r'User:([^"\'<>#]+)</a>\s*:\s*(\d+)\s*files', response.text)
        if matches:
            uploader_counts = {html.unescape(user.strip()): int(count) for user, count in matches}
            human_counts = {u: c for u, c in uploader_counts.items() if not is_bot_account(u)}
            return human_counts
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
                    if user and not is_bot_account(user):
                        users.add(user)

            continuation = payload.get("continue")
            if not continuation:
                break
            params["gcmcontinue"] = continuation.get("gcmcontinue")
            params["continue"] = continuation.get("continue", "gcmcontinue||")

        return users, True
    except Exception as e:
        logger.error(f"Error fetching participants from API for {category}: {e}")
        return set(), False

@timed_cache(ttl=3600)
def get_participants(code):
    code_clean = re.sub(r'\s+', '', code).lower()
    match = CODE_RE.match(code_clean)
    if not match:
        return set()

    event, cc, yr = match.groups()
    cached_users = campaign_cache.get_participants(code_clean) if event != 'all' else None
    if cached_users is not None:
        return cached_users

    if event == 'all':
        sub_codes = []
        for e in EVENT_MAP.keys():
            scope = EVENT_COUNTRY_SCOPE.get(e, '*')

            # Dict scope: has a country allowlist AND uses year-only Commons category
            if isinstance(scope, dict):
                allowed = scope.get('countries', [])
                if cc in allowed:
                    if scope.get('no_country_suffix'):
                        sub_codes.append(f"{e}{yr}")       # e.g. wlb24
                    else:
                        sub_codes.append(f"{e}{cc}{yr}")
            # Global: runs everywhere with country editions
            elif scope == '*':
                sub_codes.append(f"{e}{cc}{yr}")
            # Country allowlist: only include when cc is valid
            elif isinstance(scope, list) and cc in scope:
                sub_codes.append(f"{e}{cc}{yr}")
            # Otherwise: this campaign does not run in this country — skip

        sub_results = fetch_all_concurrently(sub_codes)
        combined_users = set()
        breakdown = {}
        for sc, users in sub_results.items():
            if users:
                combined_users.update(users)
                m = CODE_RE.match(sc)
                evt_name = EVENT_MAP.get(m.group(1), m.group(1).upper()) if m else sc
                breakdown[evt_name] = len(users)
        _COMPOSITE_BREAKDOWNS[code_clean] = breakdown
        return combined_users

    categories = get_category_candidates(code_clean)
    if not categories:
        return set()

    verified_empty = False
    for cat in categories:
        # 1. High-speed primary: Toolforge direct replica SQL (if available)
        replica_data = _fetch_replica_data(cat)
        if replica_data:
            users = set(replica_data.keys())
            campaign_cache.put_participants(code_clean, users)
            return users

        # 2. Opportunistic ptools scraper (only accept if non-empty verified uploaders)
        toolforge_uploaders = _fetch_toolforge_data(cat)
        if toolforge_uploaders:  # Non-empty verified dict
            users = set(toolforge_uploaders.keys())
            campaign_cache.put_participants(code_clean, users)
            return users

        # 3. Resilient fallback: Commons Action API
        users, success = _fetch_participants_from_api(cat)
        if success:
            if users:
                campaign_cache.put_participants(code_clean, users)
                return users
            verified_empty = True

    if verified_empty:
        campaign_cache.put_participants(code_clean, set())
    return set()

def _fetch_file_sample_metrics(category, max_sample=1500):
    params = {
        "action": "query",
        "format": "json",
        "generator": "categorymembers",
        "gcmtitle": f"Category:{category}",
        "gcmtype": "file",
        "gcmlimit": "500",
        "prop": "categories|globalusage",
        "clcategories": "Category:Quality images|Category:Featured pictures|Category:Featured pictures on Wikimedia Commons|Category:Valued images",
        "gulimit": "10",
    }

    total_sampled = 0
    quality_count = 0
    used_count = 0
    success = True

    while total_sampled < max_sample:
        try:
            response = http_session.get(COMMONS_API, params=params, headers=COMMONS_HEADERS, timeout=15)
            response.raise_for_status()
            payload = response.json()
        except Exception as e:
            logger.error(f"Error sampling files for {category}: {e}")
            success = False
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
        "used_count": used_count,
        "success": success,
    }

@timed_cache(ttl=3600)
def get_campaign_structural_metrics(code):
    code_clean = re.sub(r'\s+', '', code).lower()
    cached_metrics = campaign_cache.get_metrics(code_clean)
    if cached_metrics is not None:
        return cached_metrics

    match = CODE_RE.match(code_clean)
    if match and match.group(1) == 'all':
        event, cc, yr = match.groups()
        sub_codes = []
        for e in EVENT_MAP.keys():
            scope = EVENT_COUNTRY_SCOPE.get(e, '*')
            if isinstance(scope, dict):
                allowed = scope.get('countries', [])
                if cc in allowed:
                    if scope.get('no_country_suffix'):
                        sub_codes.append(f"{e}{yr}")
                    else:
                        sub_codes.append(f"{e}{cc}{yr}")
            elif scope == '*':
                sub_codes.append(f"{e}{cc}{yr}")
            elif isinstance(scope, list) and cc in scope:
                sub_codes.append(f"{e}{cc}{yr}")

        sub_results = fetch_structural_metrics_concurrently(sub_codes)
        
        total_uploads_all = 0
        quality_uploads_all = 0
        used_uploads_all = 0
        top10_uploads_all = 0
        
        for sc, m in sub_results.items():
            t = m.get("total_uploads", 0)
            if t > 0:
                total_uploads_all += t
                quality_uploads_all += (m.get("quality_image_share", 0.0) / 100.0) * t
                used_uploads_all += (m.get("usage_share", 0.0) / 100.0) * t
                top10_uploads_all += (m.get("top10_uploader_share", 0.0) / 100.0) * t
        
        if total_uploads_all > 0:
            agg_metrics = {
                "quality_image_share": (quality_uploads_all / total_uploads_all) * 100,
                "top10_uploader_share": (top10_uploads_all / total_uploads_all) * 100,
                "usage_share": (used_uploads_all / total_uploads_all) * 100,
                "total_uploads": total_uploads_all
            }
        else:
            agg_metrics = {"quality_image_share": 0.0, "top10_uploader_share": 100.0, "usage_share": 0.0, "total_uploads": 0}
            
        campaign_cache.put_metrics(code_clean, agg_metrics)
        return agg_metrics

    categories = get_category_candidates(code_clean)
    if not categories:
        return {"quality_image_share": 0.0, "top10_uploader_share": 100.0, "usage_share": 0.0, "total_uploads": 0}

    uploader_counts = {}
    chosen_cat = categories[0]
    for cat in categories:
        replica_data = _fetch_replica_data(cat)
        if replica_data:
            uploader_counts = replica_data
            chosen_cat = cat
            break
        tf_data = _fetch_toolforge_data(cat)
        if tf_data:
            uploader_counts = tf_data
            chosen_cat = cat
            break

    total_uploads = sum(uploader_counts.values()) if uploader_counts else 0

    if uploader_counts:
        top_uploader_count = max(1, ceil(len(uploader_counts) * 0.10))
        sorted_upload_counts = sorted(uploader_counts.values(), reverse=True)
        top_uploads = sum(sorted_upload_counts[:top_uploader_count])
        attributed_uploads = sum(sorted_upload_counts)
        top10_uploader_share = (top_uploads / attributed_uploads) * 100
    else:
        top10_uploader_share = 100.0

    sample = _fetch_file_sample_metrics(chosen_cat, max_sample=1500)
    sample_size = sample["sampled"]

    if sample_size > 0:
        quality_image_share = (sample["quality_count"] / sample_size) * 100
        usage_share = (sample["used_count"] / sample_size) * 100
    else:
        quality_image_share = 0.0
        usage_share = 0.0

    if total_uploads == 0:
        total_uploads = sample_size

    metrics = {
        "quality_image_share": quality_image_share,
        "top10_uploader_share": top10_uploader_share,
        "usage_share": usage_share,
        "total_uploads": total_uploads,
    }
    # Cache only when at least one source completed successfully.
    if uploader_counts or sample["success"]:
        campaign_cache.put_metrics(code_clean, metrics)
    return metrics

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
                results[code] = {"quality_image_share": 0.0, "top10_uploader_share": 100.0, "usage_share": 0.0, "total_uploads": 0}

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
def _extract_year(code):
    """Extract 4-digit calendar year from campaign code (e.g., 'wlmde22' -> 2022)."""
    match = CODE_RE.match(code)
    if match:
        try:
            return 2000 + int(match.group(3))
        except (ValueError, IndexError):
            pass
    return 0

def compute_retention_percentages(events, forward_only=False, return_dict=False):
    """
    Compute directional retention percentages between campaign editions.
    Separates forward cohort retention (t_source < t_target) from backward overlap
    and the overall pairwise matrix.

    Args:
        events: dict mapping event code to set of usernames
        forward_only: if True, returns only forward retention percentages
        return_dict: if True, returns dict with 'forward', 'backward', and 'all' lists

    Returns:
        list of retention percentages (or dict if return_dict=True)
    """
    sorted_codes = sorted(events.keys(), key=lambda c: (_extract_year(c), c))
    code_index = {code: i for i, code in enumerate(sorted_codes)}

    forward_percentages = []
    backward_percentages = []
    all_percentages = []

    for source, target in permutations(events.keys(), 2):
        source_users = events[source]
        if not source_users:
            continue
        overlap = len(source_users & events[target])
        pct = (overlap / len(source_users)) * 100.0
        all_percentages.append(pct)

        src_yr = _extract_year(source)
        tgt_yr = _extract_year(target)
        src_idx = code_index[source]
        tgt_idx = code_index[target]

        if (src_yr < tgt_yr) or (src_yr == tgt_yr and src_idx < tgt_idx):
            forward_percentages.append(pct)
        else:
            backward_percentages.append(pct)

    if return_dict:
        return {
            'forward': forward_percentages,
            'backward': backward_percentages,
            'all': all_percentages
        }
    if forward_only:
        return forward_percentages
    return all_percentages

def compute_forward_retention(events):
    """Convenience helper returning forward cohort retention percentages."""
    return compute_retention_percentages(events, forward_only=True)

def create_heatmap(events, country_name):
    """Generate high-contrast Seaborn retention heatmap on bright clean canvas.
    Diagonal elements are set to 100.0% representing self-retention."""
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
            elif i == j:
                matrix[i, j] = 100.0
            else:
                overlap = len(source_users & events[target])
                matrix[i, j] = (overlap / len(source_users)) * 100.0

    # Ensure diagonal accurately reflects 100.0% self-retention for non-empty cohorts
    for i, code in enumerate(event_codes):
        matrix[i, i] = 100.0 if events[code] else 0.0

    fig, ax = plt.subplots(figsize=(max(5, size * 1.2), max(4, size)))
    fig.patch.set_facecolor("#ffffff")
    ax.patch.set_facecolor("#ffffff")

    sns.heatmap(
        matrix, annot=True, fmt=".1f",
        xticklabels=readable_labels, yticklabels=readable_labels,
        cmap=WIKI_CMAP, linewidths=1.5, linecolor="#ffffff",
        cbar_kws={'label': 'Retention (%)'},
        vmin=0, vmax=100.0, ax=ax,
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

def build_global_table(valid_countries, forward_only=False):
    rows = []
    for country_code, events in valid_countries.items():
        ret_dict = compute_retention_percentages(events, return_dict=True)
        all_percentages = ret_dict['all']
        forward_percentages = ret_dict['forward']
        if not all_percentages:
            continue
        primary_percentages = forward_percentages if (forward_only and forward_percentages) else all_percentages
        fwd_val = round(float(np.mean(forward_percentages)), 1) if forward_percentages else round(float(np.mean(all_percentages)), 1)
        rows.append({
            "Country": country_display_name(country_code),
            "Occurrences": len(events),
            "Forward Retention (%)": fwd_val,
            "Avg Retention (%)": round(float(np.mean(all_percentages)), 1),
            "Median Retention (%)": round(float(np.median(primary_percentages)), 1),
            "Max Retention (%)": round(float(np.max(primary_percentages)), 1),
            "Std Dev (%)": round(float(np.std(primary_percentages, ddof=1)), 1) if len(primary_percentages) > 1 else 0.0,
        })
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows).sort_values("Country", key=lambda values: values.str.casefold()).reset_index(drop=True)
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
    return pd.DataFrame(rows).sort_values("Country", key=lambda values: values.str.casefold()).reset_index(drop=True)

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

GLOBAL_MOVEMENT_BASELINES = {
    'retention': 20.0,    # 20.0% global contest median retention
    'usage': 2.5,         # 2.5% global median encyclopedic reuse
    'growth': 65.0,       # 65.0% global median newcomer share
    'diversity': 70.0,    # 70.0% global median top-10% uploader share
    'quality': 1.5        # 1.5% global median QI/FP recognition rate
}

def calculate_relative_score(metric_value, benchmark_value, positive_is_higher=True):
    """
    Computes a standardized relative score (0 to 100) comparing an observed metric
    against a reference benchmark value using continuous non-linear scaling.

    Parameters:
        metric_value (float): The observed value for the campaign dimension.
        benchmark_value (float): The regional peer benchmark threshold.
        positive_is_higher (bool): True if higher values represent stronger performance,
                                   False if lower concentration indicates healthier equity.

    Returns:
        float: Standardized score in the range [0.0, 100.0].
    """
    if positive_is_higher:
        # Strict zero-floor: zero activity maps to zero points
        if metric_value <= 0:
            return 0.0

        # Guard against zero or near-zero benchmark divisors
        benchmark_value = max(float(benchmark_value), 0.5)

        if metric_value <= benchmark_value:
            # Sub-linear concave scaling for values below benchmark (reaches 70.0 at benchmark)
            return float(round(70.0 * ((metric_value / benchmark_value) ** 0.75), 1))
        else:
            # Diminishing returns scaling above benchmark asymptotically approaching 100.0
            excess_ratio = (metric_value - benchmark_value) / benchmark_value
            score = 70.0 + 30.0 * (1.0 - np.exp(-1.2 * excess_ratio))
            return float(round(min(100.0, score), 1))
    else:
        # Inverse dimension: Contributor concentration (top 10% upload share)
        # Lower concentration indicates broader, healthier community distribution.
        if metric_value >= 100.0:
            return 15.0
        if metric_value <= 10.0:
            return 100.0

        benchmark_value = min(max(float(benchmark_value), 20.0), 90.0)

        if metric_value > benchmark_value:
            # Higher concentration than benchmark: progressive penalty down to 15.0
            ratio = (metric_value - benchmark_value) / (100.0 - benchmark_value)
            return float(round(max(15.0, 70.0 - 55.0 * (ratio ** 0.85)), 1))
        else:
            # Lower concentration than benchmark: bonus up to 100.0
            ratio = (benchmark_value - metric_value) / (benchmark_value - 10.0)
            return float(round(min(100.0, 70.0 + 30.0 * (ratio ** 0.85)), 1))

# Retain backward-compatible alias
defensible_relative_score = calculate_relative_score

def generate_health_metrics(
    target_users,
    baseline_users,
    target_structural_metrics,
    benchmarks
):
    """
    Generates composite health scorecard metrics across five dimensions.

    Parameters:
        target_users (set): Usernames active in the evaluated target campaign.
        baseline_users (set): Usernames active in the baseline comparison campaign.
        target_structural_metrics (dict): Global usage, quality, and uploader shares.
        benchmarks (dict): Calibrated reference thresholds for each dimension.

    Returns:
        dict: Dimension dictionaries with raw values, normalized scores, benchmarks, and weights.
    """
    metrics = {}

    # 1. Retention Index: volunteer continuity from baseline cohort
    is_inaugural = not bool(baseline_users)
    ret_bm = float(benchmarks.get('retention', GLOBAL_MOVEMENT_BASELINES['retention']))
    if is_inaugural:
        metrics['Retention'] = {
            'raw': 'Inaugural Baseline',
            'score': None,
            'benchmark': ret_bm,
            'weight': 0,
            'is_inaugural': True
        }
    else:
        overlap = len(target_users & baseline_users)
        retention_rate = (overlap / len(baseline_users)) * 100.0
        metrics['Retention'] = {
            'raw': f"{retention_rate:.1f}%",
            'score': calculate_relative_score(retention_rate, ret_bm, positive_is_higher=True),
            'benchmark': ret_bm,
            'weight': 25,
            'is_inaugural': False
        }

    # 2. Growth Capacity: newcomer participant influx share
    if target_users:
        new_users = len(target_users - baseline_users)
        growth_rate = (new_users / len(target_users)) * 100.0
    else:
        growth_rate = 0.0
    gro_bm = float(benchmarks.get('growth', GLOBAL_MOVEMENT_BASELINES['growth']))
    metrics['Growth'] = {
        'raw': f"{growth_rate:.1f}%",
        'score': calculate_relative_score(growth_rate, gro_bm, positive_is_higher=True),
        'benchmark': gro_bm,
        'weight': 25
    }
    
    # 3. Content Utility: cross-wiki project reuse share
    raw_usage = float(target_structural_metrics.get("usage_share", 0.0))
    usage_baseline = float(benchmarks.get('usage', GLOBAL_MOVEMENT_BASELINES['usage']))
    metrics['Usage'] = {
        'raw': raw_usage,
        'score': calculate_relative_score(raw_usage, usage_baseline, positive_is_higher=True),
        'benchmark': usage_baseline,
        'weight': 20
    }

    # 4. Contributor Diversity: distribution balance among uploaders (inverse concentration)
    raw_diversity = float(target_structural_metrics.get("top10_uploader_share", 70.0))
    diversity_baseline = float(benchmarks.get('diversity', GLOBAL_MOVEMENT_BASELINES['diversity']))
    metrics['Diversity'] = {
        'raw': raw_diversity,
        'score': calculate_relative_score(raw_diversity, diversity_baseline, positive_is_higher=False),
        'benchmark': diversity_baseline,
        'weight': 15
    }

    # 5. Quality Recognition: featured and quality image recognition share
    raw_quality = float(target_structural_metrics.get("quality_image_share", 0.0))
    quality_baseline = float(benchmarks.get('quality', GLOBAL_MOVEMENT_BASELINES['quality']))
    metrics['Quality'] = {
        'raw': raw_quality,
        'score': calculate_relative_score(raw_quality, quality_baseline, positive_is_higher=True),
        'benchmark': quality_baseline,
        'weight': 15
    }

    # Dynamic Paired Aggregation:
    # If inaugural edition (no prior baseline), dynamically re-weight across the remaining
    # four dimensions proportionally (Growth 33.3%, Usage 26.7%, Quality 20.0%, Diversity 20.0%).
    # Otherwise, standard paired model: Community (50%), Content (35%), Equity (15%).
    if is_inaugural:
        overall = (
            (metrics['Growth']['score'] * (25.0 / 75.0)) +
            (metrics['Usage']['score'] * (20.0 / 75.0)) +
            (metrics['Quality']['score'] * (15.0 / 75.0)) +
            (metrics['Diversity']['score'] * (15.0 / 75.0))
        )
        metrics['Growth']['weight'] = 33
        metrics['Usage']['weight'] = 27
        metrics['Quality']['weight'] = 20
        metrics['Diversity']['weight'] = 20
    else:
        overall = (
            (metrics['Retention']['score'] * 0.25) +
            (metrics['Growth']['score'] * 0.25) +
            (metrics['Usage']['score'] * 0.20) +
            (metrics['Quality']['score'] * 0.15) +
            (metrics['Diversity']['score'] * 0.15)
        )
    metrics['Overall'] = round(overall)

    return metrics

def generate_insights(metrics, region_name, benchmarks, counts=None):
    insights = []
    region_label = f"{region_name} regional norm" if region_name else "regional benchmark"
    target_count = counts.get('target', 0) if counts else 0
    base_count = counts.get('base', 0) if counts else 0
    overlap_count = counts.get('overlap', 0) if counts else 0
    newcomer_count = max(0, target_count - overlap_count)

    # 1. Retention Insight
    if metrics['Retention'].get('is_inaugural'):
        insights.append(
            "Inaugural campaign edition: Volunteer retention cannot be evaluated without a prior baseline cycle. "
            "Evaluation index dynamically calibrated across newcomer recruitment, content utility, quality recognition, and participation equity."
        )
    else:
        raw_ret = float(metrics['Retention']['raw'].replace('%', '')) if isinstance(metrics['Retention']['raw'], str) else float(metrics['Retention']['raw'])
        ret_bm = benchmarks.get('retention', GLOBAL_MOVEMENT_BASELINES['retention'])
        if raw_ret >= ret_bm:
            diff_str = f"+{raw_ret - ret_bm:.1f}% above"
            insights.append(f"Retention is strong ({raw_ret:.1f}%): retained {overlap_count:,} out of {base_count:,} prior-edition contributors ({diff_str} {region_label} of {ret_bm:.1f}%). Demonstrates high volunteer continuity.")
        elif raw_ret >= (ret_bm * 0.6):
            insights.append(f"Retention is moderate ({raw_ret:.1f}%): {overlap_count:,} returning uploaders retained from {base_count:,} baseline. Tracking within typical range for annual photo contests (benchmark: {ret_bm:.1f}%).")
        else:
            insights.append(f"Retention indicates high turnover ({raw_ret:.1f}%): retained {overlap_count:,} of {base_count:,} baseline contributors (below {region_label} of {ret_bm:.1f}%). Characteristic of outreach drives where post-contest re-engagement is limited.")

    # 2. Growth / Influx Insight
    raw_growth = float(metrics['Growth']['raw'].replace('%', '')) if isinstance(metrics['Growth']['raw'], str) else float(metrics['Growth']['raw'])
    gro_bm = benchmarks.get('growth', GLOBAL_MOVEMENT_BASELINES['growth'])
    if raw_growth >= 80.0:
        insights.append(f"Newcomer mobilization is exceptional ({raw_growth:.1f}%): brought {newcomer_count:,} brand-new participants into the movement out of {target_count:,} active uploaders (regional benchmark: {gro_bm:.1f}%).")
    elif raw_growth >= gro_bm:
        insights.append(f"Newcomer pipeline is healthy ({raw_growth:.1f}%): {newcomer_count:,} first-time contributors engaged, maintaining active expansion of the local participant base.")
    else:
        insights.append(f"Participant cohort is primarily established ({raw_growth:.1f}% new): {newcomer_count:,} first-time contributors joined, indicating stable stewardship with room to expand newcomer outreach.")

    # 3. Content Utility Insight
    raw_usage = float(metrics['Usage']['raw'])
    use_bm = benchmarks.get('usage', GLOBAL_MOVEMENT_BASELINES['usage'])
    if raw_usage >= use_bm:
        insights.append(f"Content Utility is robust ({raw_usage:.1f}%): file reuse across Wikipedia articles matches or exceeds the {region_label} ({use_bm:.1f}%), delivering direct encyclopedic value.")
    elif raw_usage > 0.0:
        insights.append(f"Content Utility is emerging ({raw_usage:.1f}%): files have begun being deployed in Wikipedia articles (benchmark: {use_bm:.1f}%). Encyclopedic adoption typically expands over 6–12 months via edit-a-thons.")
    else:
        insights.append(f"Content Utility is unindexed (0.0%): no uploaded files are currently recorded in active Wikipedia article use. Suggests an organizing opportunity for post-contest illustration drives.")

    # 4. Diversity / Participation Breadth Insight
    raw_div = float(metrics['Diversity']['raw'])
    div_bm = benchmarks.get('diversity', GLOBAL_MOVEMENT_BASELINES['diversity'])
    if raw_div <= 65.0:
        insights.append(f"Participation breadth is exceptionally distributed: top 10% uploaders contributed {raw_div:.1f}% of files, demonstrating broad grassroots participation beyond the power-user core.")
    elif raw_div <= 85.0:
        insights.append(f"Participation distribution ({raw_div:.1f}% by top 10% uploaders) aligns with standard Wikimedia peer-production power laws (regional norm: {div_bm:.1f}%).")
    else:
        insights.append(f"Upload concentration is high: top 10% uploaders contributed {raw_div:.1f}% of all submissions, indicating heavy reliance on a small cluster of power uploaders.")

    # 5. Quality Recognition Insight
    raw_qual = float(metrics['Quality']['raw'])
    qual_bm = benchmarks.get('quality', GLOBAL_MOVEMENT_BASELINES['quality'])
    if raw_qual >= qual_bm:
        insights.append(f"Quality Recognition is high ({raw_qual:.1f}%): formal Commons Quality Image / Featured Picture nominations outperform the {region_label} ({qual_bm:.1f}%).")
    elif raw_qual > 0.0:
        insights.append(f"Quality Recognition is present ({raw_qual:.1f}%): recognized Commons quality files have been logged (benchmark: {qual_bm:.1f}%).")
    else:
        insights.append("Quality Recognition is unindexed (0.0%): no files have formal Commons Quality Image designations. (Note: Commons QI requires manual jury/volunteer nominations).")

    return insights

# =========================================================================
# YEAR-OVER-YEAR (YoY) INFLUX & NEW CONTRIBUTOR ANALYTICS
# =========================================================================

def compute_yoy_influx(campaign_codes):
    """
    Computes Year-over-Year newcomer influx, returning contributor retention,
    and cumulative community growth for a chronological sequence of campaign editions.
    Supports single-campaign streams, multi-event groupings, and 'all' ecosystem aggregate codes.
    """
    cleaned_codes = [re.sub(r'\s+', '', c).lower() for c in campaign_codes if c.strip()]
    code_to_users = fetch_all_concurrently(cleaned_codes)
    
    # Group codes by year to support single-code series, multi-campaign combinations, and 'all' codes
    year_to_codes = defaultdict(list)
    for code in cleaned_codes:
        m = CODE_RE.match(code)
        if m:
            yr = 2000 + int(m.group(3))
            year_to_codes[yr].append(code)
            
    records = []
    seen_all_prior = set()
    user_edition_counts = defaultdict(int)
    prev_users = set()
    
    sorted_years = sorted(year_to_codes.keys())
    for year in sorted_years:
        codes_for_year = year_to_codes[year]
        current_users = set().union(*(code_to_users.get(c, set()) for c in codes_for_year))
        total_active = len(current_users)
        
        # Build human-readable breakdown across events
        breakdown_items = []
        if len(codes_for_year) == 1:
            single_code = codes_for_year[0]
            code_display = single_code
            if single_code in _COMPOSITE_BREAKDOWNS and _COMPOSITE_BREAKDOWNS[single_code]:
                breakdown_items = [f"{k}: {v:,}" for k, v in sorted(_COMPOSITE_BREAKDOWNS[single_code].items())]
        else:
            code_display = f"Combined ({len(codes_for_year)} events)"
            for c in codes_for_year:
                cnt = len(code_to_users.get(c, set()))
                if cnt > 0:
                    m = CODE_RE.match(c)
                    evt_key = m.group(1) if m else c
                    breakdown_items.append(f"{EVENT_MAP.get(evt_key, evt_key.upper())}: {cnt:,}")
                    
        breakdown_str = ", ".join(breakdown_items) if breakdown_items else "Single stream"

        for u in current_users:
            user_edition_counts[u] += 1
            
        is_baseline = not seen_all_prior
        if is_baseline:
            # Baseline edition: all active are baseline entrants
            new_users = total_active
            returning_users = 0
            retention_from_prev = 0.0
            yoy_growth = 0.0
            ratio = None
            ratio_status = "Baseline Edition"
        else:
            new_set = current_users - seen_all_prior
            ret_set = current_users & seen_all_prior
            new_users = len(new_set)
            returning_users = len(ret_set)
            
            if prev_users:
                direct_retained = len(current_users & prev_users)
                retention_from_prev = (direct_retained / len(prev_users)) * 100.0
                yoy_growth = ((total_active - len(prev_users)) / len(prev_users)) * 100.0
            else:
                retention_from_prev = 0.0
                yoy_growth = 0.0
                
            if returning_users > 0:
                ratio = round(new_users / returning_users, 2)
                ratio_status = "Active"
            else:
                ratio = None
                ratio_status = "Zero Returning"
                
        newcomer_share = (new_users / total_active * 100.0) if total_active > 0 else 0.0
        veteran_share = (returning_users / total_active * 100.0) if total_active > 0 else 0.0
        
        seen_all_prior.update(current_users)
        cumulative_pool = len(seen_all_prior)
        
        records.append({
            'code': code_display,
            'year': year,
            'total_active': total_active,
            'new_contributors': new_users,
            'returning_contributors': returning_users,
            'newcomer_share_pct': round(newcomer_share, 1),
            'veteran_share_pct': round(veteran_share, 1),
            'retention_from_prev_pct': round(retention_from_prev, 1),
            'yoy_growth_pct': round(yoy_growth, 1),
            'new_to_veteran_ratio': ratio,
            'ratio_status': ratio_status,
            'is_baseline': is_baseline,
            'cumulative_pool': cumulative_pool,
            'breakdown_str': breakdown_str
        })
        
        prev_users = current_users
        
    lifecycle = {
        'one_time': 0,
        'repeat_2_3': 0,
        'core_4_plus': 0
    }
    total_distinct = len(user_edition_counts)
    for u, count in user_edition_counts.items():
        if count == 1:
            lifecycle['one_time'] += 1
        elif count <= 3:
            lifecycle['repeat_2_3'] += 1
        else:
            lifecycle['core_4_plus'] += 1
            
    if records:
        avg_newcomer = sum(r['newcomer_share_pct'] for r in records) / len(records)
        peak_influx_rec = max(records, key=lambda r: r['new_contributors'])
        peak_total_rec = max(records, key=lambda r: r['total_active'])
        summary = {
            'total_unique_community': total_distinct,
            'avg_newcomer_share_pct': round(avg_newcomer, 1),
            'peak_influx_year': peak_influx_rec['year'],
            'peak_influx_count': peak_influx_rec['new_contributors'],
            'peak_edition_year': peak_total_rec['year'],
            'peak_edition_count': peak_total_rec['total_active'],
            'latest_year': records[-1]['year'],
            'latest_total': records[-1]['total_active'],
            'latest_new': records[-1]['new_contributors'],
            'latest_returning': records[-1]['returning_contributors'],
        }
    else:
        summary = {
            'total_unique_community': 0,
            'avg_newcomer_share_pct': 0.0,
            'peak_influx_year': '-',
            'peak_influx_count': 0,
            'peak_edition_year': '-',
            'peak_edition_count': 0,
            'latest_year': '-',
            'latest_total': 0,
            'latest_new': 0,
            'latest_returning': 0,
        }
        
    return {
        'records': records,
        'summary': summary,
        'lifecycle': lifecycle
    }

def create_influx_barchart(records, title="Year-over-Year Contributor Influx"):
    """
    Creates a publication-quality stacked bar chart for Flask (Headless Matplotlib).
    Returning Contributors (Marine Petrol) + New Influx (Cyan Accent), with Cumulative Pool overlay.
    """
    if not records:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No data available", ha='center', va='center', color=TEXT_MUTED)
        ax.axis('off')
        return fig

    years = [str(r['year']) for r in records]
    returning = [r['returning_contributors'] for r in records]
    newcomers = [r['new_contributors'] for r in records]
    cumulative = [r['cumulative_pool'] for r in records]

    fig, ax1 = plt.subplots(figsize=(10, 5), dpi=140)
    fig.patch.set_facecolor('#ffffff')
    ax1.set_facecolor('#ffffff')

    width = 0.55
    x_indices = np.arange(len(years))

    # Stacked Bars
    p1 = ax1.bar(x_indices, returning, width, label='Returning Contributors', color=NAV_TEAL, edgecolor='#ffffff', linewidth=1)
    p2 = ax1.bar(x_indices, newcomers, width, bottom=returning, label='First-Time Newcomers', color=NAV_ACCENT, edgecolor='#ffffff', linewidth=1)

    # Annotate total on top of bars
    for i, r in enumerate(records):
        total = r['total_active']
        if total > 0:
            ax1.annotate(f"{total:,}",
                         xy=(x_indices[i], total),
                         xytext=(0, 4),
                         textcoords="offset points",
                         ha='center', va='bottom',
                         fontsize=9, fontweight='600', color=TEXT_INK)

    # Cumulative pool secondary line axis
    ax2 = ax1.twinx()
    ax2.plot(x_indices, cumulative, color='#e67300', marker='o', linewidth=2.2, markersize=6, label='Cumulative Community Pool')
    ax2.set_ylabel('Cumulative Unique Contributors', color='#e67300', fontsize=10, fontweight='600')
    ax2.tick_params(axis='y', labelcolor='#e67300', labelsize=9)
    ax2.grid(False)

    ax1.set_xlabel('Campaign Edition (Year)', fontsize=10, fontweight='600', color=TEXT_INK, labelpad=8)
    ax1.set_ylabel('Active Contributors in Edition', fontsize=10, fontweight='600', color=TEXT_INK, labelpad=8)
    ax1.set_xticks(x_indices)
    ax1.set_xticklabels(years, fontsize=10, color=TEXT_INK)
    ax1.tick_params(axis='x', colors=TEXT_INK)
    ax1.tick_params(axis='y', colors=TEXT_INK, labelsize=9)
    ax1.set_title(title, fontsize=12, fontweight='700', color=TEXT_INK, pad=14)

    # Subtle horizontal grid on primary axis
    ax1.yaxis.grid(True, linestyle='--', alpha=0.35, color=BORDER_COLOR)
    ax1.xaxis.grid(False)
    ax1.set_axisbelow(True)

    # Clean borders
    for spine in ax1.spines.values():
        spine.set_color(BORDER_COLOR)
    for spine in ax2.spines.values():
        spine.set_color(BORDER_COLOR)

    # Combined Legend
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left', frameon=True, facecolor='#ffffff', edgecolor=BORDER_COLOR, fontsize=8.5)

    plt.tight_layout()
    return fig

def create_influx_plotly_chart(records, title="Year-over-Year Contributor Influx"):
    """
    Creates an interactive Plotly stacked bar chart for Streamlit.
    """
    if not records:
        return px.bar(title="No data available")

    df = pd.DataFrame(records)
    id_vars = ['year', 'code', 'total_active', 'newcomer_share_pct', 'cumulative_pool']
    hover_data = {'total_active': True, 'newcomer_share_pct': ':.1f%'}
    labels = {'year': 'Campaign Year', 'Count': 'Active Contributors'}
    if 'breakdown_str' in df.columns:
        id_vars.append('breakdown_str')
        hover_data['breakdown_str'] = True
        labels['breakdown_str'] = 'Campaign Breakdown'

    # Melt for stacked bar chart in Plotly
    df_melted = pd.melt(
        df,
        id_vars=id_vars,
        value_vars=['returning_contributors', 'new_contributors'],
        var_name='Contributor Type',
        value_name='Count'
    )
    df_melted['Contributor Type'] = df_melted['Contributor Type'].map({
        'returning_contributors': 'Returning Contributors',
        'new_contributors': 'First-Time Newcomers'
    })

    fig = px.bar(
        df_melted,
        x='year',
        y='Count',
        color='Contributor Type',
        color_discrete_map={
            'Returning Contributors': NAV_TEAL,
            'First-Time Newcomers': NAV_ACCENT
        },
        title=title,
        labels=labels,
        hover_data=hover_data
    )

    fig.add_trace(go.Scatter(
        x=df['year'],
        y=df['cumulative_pool'],
        name='Cumulative Community Pool',
        yaxis='y2',
        mode='lines+markers',
        line=dict(color='#e67300', width=2.5),
        marker=dict(size=7, color='#e67300')
    ))

    fig.update_layout(
        barmode='stack',
        paper_bgcolor='#ffffff',
        plot_bgcolor='#ffffff',
        font=dict(color=TEXT_INK, family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(r=40, t=60, l=10, b=10),
        xaxis=dict(showgrid=False, linecolor=BORDER_COLOR),
        yaxis=dict(title='Active Contributors', showgrid=True, gridcolor='rgba(0,0,0,0.06)', linecolor=BORDER_COLOR),
        yaxis2=dict(
            title='Cumulative Unique Pool',
            title_font=dict(color='#e67300'),
            tickfont=dict(color='#e67300'),
            overlaying='y',
            side='right',
            showgrid=False,
            linecolor='#e67300'
        )
    )
    return fig

# --- UNIVERSAL MULTI-FORMAT EXPORT UTILITIES ---
def df_to_wikitext(df, title=None, table_class="wikitable sortable"):
    """Convert pandas DataFrame to clean MediaWiki wikitext table format."""
    if df.empty:
        return f'{{| class="{table_class}"\n|-\n| \'\'No data available\'\'\n|}}'
    
    lines = [f'{{| class="{table_class}"']
    if title:
        lines.append(f"|+ {title}")
    
    # Headers
    headers = [str(c) for c in df.columns]
    lines.append("! " + " !! ".join(headers))
    
    # Rows
    for _, row in df.iterrows():
        cells = [str(row[c]) if pd.notna(row[c]) else "" for c in df.columns]
        lines.append("|-")
        lines.append("| " + " || ".join(cells))
        
    lines.append("|}")
    return "\n".join(lines)

def df_to_csv_with_metadata(df, metadata=None):
    """Export DataFrame to CSV format prepended with provenance metadata headers."""
    header_lines = [
        "# Tool: CampAnalytics (https://campanalytics.toolforge.org/)",
        f"# Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        "# License: GPL-2.0-or-later",
        "# Data Source: Wikimedia Commons Action API / Toolforge Replica"
    ]
    if metadata:
        for k, v in metadata.items():
            header_lines.append(f"# {k}: {v}")
            
    csv_body = df.to_csv(index=False)
    return "\n".join(header_lines) + "\n" + csv_body


@timed_cache(ttl=3600)
def compute_content_utility_deep(code, max_sample=500):
    """
    Computes comprehensive cross-wiki media deployment statistics for a campaign edition:
    - Overall deployment rate (% of uploaded files used on at least one Wikimedia project)
    - Total cumulative usages across all Wikipedia and Wikimedia project articles
    - Distribution of usage by target wiki domain (e.g., en.wikipedia.org, bn.wikipedia.org)
    - Top utilized files with thumbnail preview links and usage counts
    - Top utilized photographers leaderboard (excluding automated bots)
    """
    code_clean = re.sub(r'\s+', '', code).lower()
    m = CODE_RE.match(code_clean)
    if not m:
        return None

    # 1. Read from persistent MariaDB/SQLite cache if available
    cached = campaign_cache.get_content_utility(code_clean)
    if cached is not None:
        return cached

    evt, cc, yr = m.group(1), m.group(2), m.group(3)
    categories = get_category_candidates(code_clean)
    if not categories:
        return None

    base_metrics = get_campaign_structural_metrics(code_clean) or {}
    total_cohort_uploads = int(base_metrics.get("total_uploads", 0) or 0)

    total_sampled = 0
    used_files_count = 0
    total_usages = 0
    project_dist = defaultdict(int)
    uploader_utility = defaultdict(lambda: {"used_files": 0, "total_usages": 0})
    unique_articles = set()
    media_usages = []

    # Iterate over candidate categories until files are found or all candidates checked
    for cat in categories:
        params = {
            "action": "query",
            "format": "json",
            "generator": "categorymembers",
            "gcmtitle": f"Category:{cat}",
            "gcmtype": "file",
            "gcmlimit": "100",
            "prop": "globalusage|imageinfo",
            "gulimit": "50",
            "iiprop": "user|timestamp|url",
            "iiurlwidth": "300"
        }
        start_time = time.time()
        while total_sampled < max_sample:
            # Enforce 8-second time budget for live web requests to prevent Toolforge gateway 504 timeouts
            if time.time() - start_time > 8.0:
                break
            try:
                response = http_session.get(COMMONS_API, params=params, headers=COMMONS_HEADERS, timeout=6)
                if response.status_code != 200:
                    break
                payload = response.json()
                pages = payload.get("query", {}).get("pages", {})
                if not pages:
                    break

                for p in pages.values():
                    total_sampled += 1
                    title = p.get("title", "")
                    gu = p.get("globalusage", [])
                    ii = p.get("imageinfo", [{}])[0] if p.get("imageinfo") else {}
                    uploader = ii.get("user") or "Community Contributor"
                    thumb_url = ii.get("thumburl", "")
                    safe_title = urllib.parse.quote(title.replace(" ", "_"))
                    desc_url = ii.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/{safe_title}"

                    # Filter bot accounts from contributor metrics and leaderboards
                    if gu and not is_bot_account(uploader):
                        used_files_count += 1
                        file_usages_count = len(gu)
                        total_usages += file_usages_count
                        uploader_utility[uploader]["used_files"] += 1
                        uploader_utility[uploader]["total_usages"] += file_usages_count

                        for u in gu:
                            wiki = u.get("wiki", "unknown")
                            art = u.get("title", "").replace("_", " ")
                            project_dist[wiki] += 1
                            unique_articles.add(f"{wiki}:{art}")
                            if len(media_usages) < 50:
                                media_usages.append({
                                    "file_title": title.replace("File:", "").replace("_", " "),
                                    "full_title": title,
                                    "article": art,
                                    "wiki": wiki,
                                    "commons_url": desc_url,
                                    "thumb_url": thumb_url
                                })

                continuation = payload.get("continue")
                if not continuation or "gcmcontinue" not in continuation:
                    break
                params["gcmcontinue"] = continuation.get("gcmcontinue")
                params["continue"] = continuation.get("continue", "gcmcontinue||")
            except Exception as e:
                logger.warning(f"Error fetching live globalusage for {cat}: {e}")
                break

        if total_sampled > 0:
            break

    # STRICT EMPIRICAL REPORTING — ZERO FABRICATED DATA
    usage_rate = (used_files_count / total_sampled * 100) if total_sampled > 0 else 0.0

    # Photographers Leaderboard (human uploaders only)
    top_photographers = []
    rank = 1
    for uploader, stats in sorted(uploader_utility.items(), key=lambda x: (x[1]["total_usages"], x[1]["used_files"]), reverse=True):
        if not is_bot_account(uploader):
            top_photographers.append({
                "rank": rank,
                "uploader": uploader,
                "used_files_count": stats["used_files"],
                "total_usages": stats["total_usages"]
            })
            rank += 1

    top_project = max(project_dist.items(), key=lambda x: x[1])[0] if project_dist else "None recorded"
    effective_pool = total_cohort_uploads if total_cohort_uploads > 0 else total_sampled

    sorted_projects = []
    total_proj_usages = sum(project_dist.values()) or 0
    if total_proj_usages > 0:
        for domain, count in sorted(project_dist.items(), key=lambda x: x[1], reverse=True):
            sorted_projects.append({
                "domain": domain,
                "count": count,
                "share_pct": round((count / total_proj_usages) * 100, 1)
            })

    result = {
        "code": code_clean,
        "event_type": evt,
        "country_code": cc,
        "year": 2000 + int(yr),
        "total_sampled": effective_pool,
        "used_files_count": used_files_count,
        "usage_rate_pct": round(usage_rate, 1),
        "global_utility_rate_pct": round(usage_rate, 1),
        "total_usages": total_usages,
        "total_global_usages": total_usages,
        "unique_articles_count": len(unique_articles),
        "top_consuming_project": top_project,
        "projects": sorted_projects,
        "media_usages": media_usages[:50],
        "top_files": media_usages[:50],
        "top_photographers": top_photographers[:25]
    }
    if total_sampled > 0:
        campaign_cache.put_content_utility(code_clean, result)
    return result


@timed_cache(ttl=3600)
def compute_quality_recognition_deep(code, max_sample=500):
    """
    Computes comprehensive Commons quality designation statistics for a campaign edition:
    - Quality Images (QI) count & percentage (via direct Commons category discovery + sampling)
    - Featured Pictures (FP) count & percentage
    - Valued Images (VI) count & percentage
    - Recognized media files gallery with honors and photographer attribution
    - Photographer Honors Leaderboard ranking contributors by recognized contributions
    """
    code_clean = re.sub(r'\s+', '', code).lower()
    m = CODE_RE.match(code_clean)
    if not m:
        return None

    # 1. Read from persistent MariaDB/SQLite cache if available
    cached = campaign_cache.get_quality_recognition(code_clean)
    if cached is not None:
        return cached

    evt, cc, yr = m.group(1), m.group(2), m.group(3)
    categories = get_category_candidates(code_clean)
    if not categories:
        return None

    base_metrics = get_campaign_structural_metrics(code_clean) or {}
    total_cohort_uploads = int(base_metrics.get("total_uploads", 0) or 0)

    total_sampled = total_cohort_uploads or 0
    qi_count = 0
    fp_count = 0
    vi_count = 0
    recognized_files = []
    uploader_counts = defaultdict(lambda: {"qi": 0, "fp": 0, "vi": 0, "total": 0})

    # 1. Try querying dedicated Quality Images subcategories across candidates
    for cat in categories:
        cat_clean = cat.replace("_", " ")
        qi_cat_candidates = [
            cat_clean.replace("Images from ", "Quality images from "),
            f"Quality images from {cat_clean.replace('Images from ', '')}",
            f"Quality images from {cat_clean}"
        ]

        for qcat in qi_cat_candidates:
            if qcat == cat_clean or qcat == cat:
                continue
            try:
                r_qi = http_session.get(
                    COMMONS_API,
                    params={"action": "query", "format": "json", "prop": "categoryinfo", "titles": f"Category:{qcat}"},
                    headers=COMMONS_HEADERS,
                    timeout=6
                )
                if r_qi.status_code == 200:
                    p_info = list(r_qi.json().get("query", {}).get("pages", {}).values())[0]
                    cinfo = p_info.get("categoryinfo")
                    if cinfo and cinfo.get("files", 0) > 0:
                        qi_count = cinfo.get("files", 0)
                        # Fetch sample of files from this dedicated quality category
                        r_qfiles = http_session.get(
                            COMMONS_API,
                            params={
                                "action": "query", "format": "json", "generator": "categorymembers",
                                "gcmtitle": f"Category:{qcat}", "gcmtype": "file", "gcmlimit": "40",
                                "prop": "imageinfo", "iiprop": "user|timestamp|url", "iiurlwidth": "300"
                            },
                            headers=COMMONS_HEADERS,
                            timeout=8
                        )
                        if r_qfiles.status_code == 200:
                            qpages = r_qfiles.json().get("query", {}).get("pages", {})
                            for p in qpages.values():
                                title = p.get("title", "")
                                ii = p.get("imageinfo", [{}])[0] if p.get("imageinfo") else {}
                                uploader = ii.get("user") or "Community Photographer"
                                thumb_url = ii.get("thumburl", "")
                                safe_title = urllib.parse.quote(title.replace(" ", "_"))
                                desc_url = ii.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/{safe_title}"

                                if not is_bot_account(uploader):
                                    uploader_counts[uploader]["qi"] += 1
                                    uploader_counts[uploader]["total"] += 1
                                    recognized_files.append({
                                        "title": title.replace("File:", "").replace("_", " "),
                                        "full_title": title,
                                        "honors": "Quality Image",
                                        "uploader": uploader,
                                        "commons_url": desc_url,
                                        "thumb_url": thumb_url
                                    })
                        break
            except Exception as e:
                logger.warning(f"Error checking QI subcategory {qcat}: {e}")
        if qi_count > 0:
            break

    # 2. Sample general category for inline Quality/Featured/Valued designations if QI subcategory was empty
    if not recognized_files:
        for cat in categories:
            params = {
                "action": "query",
                "format": "json",
                "generator": "categorymembers",
                "gcmtitle": f"Category:{cat}",
                "gcmtype": "file",
                "gcmlimit": "100",
                "prop": "categories|imageinfo",
                "clcategories": "Category:Quality images|Category:Featured pictures|Category:Featured pictures on Wikimedia Commons|Category:Valued images",
                "cllimit": "20",
                "iiprop": "user|timestamp|url",
                "iiurlwidth": "300"
            }
            sampled_this_cat = 0
            start_time = time.time()
            while sampled_this_cat < max_sample:
                if time.time() - start_time > 8.0:
                    break
                try:
                    response = http_session.get(COMMONS_API, params=params, headers=COMMONS_HEADERS, timeout=6)
                    if response.status_code != 200:
                        break
                    payload = response.json()
                    pages = payload.get("query", {}).get("pages", {})
                    if not pages:
                        break

                    for p in pages.values():
                        sampled_this_cat += 1
                        title = p.get("title", "")
                        cats = [c.get("title", "") for c in p.get("categories", [])]
                        ii = p.get("imageinfo", [{}])[0] if p.get("imageinfo") else {}
                        uploader = ii.get("user") or "Community Photographer"
                        thumb_url = ii.get("thumburl", "")
                        safe_title = urllib.parse.quote(title.replace(" ", "_"))
                        desc_url = ii.get("descriptionurl") or f"https://commons.wikimedia.org/wiki/{safe_title}"

                        honors = []
                        is_qi = "Category:Quality images" in cats
                        is_fp = "Category:Featured pictures" in cats or "Category:Featured pictures on Wikimedia Commons" in cats
                        is_vi = "Category:Valued images" in cats

                        if is_qi:
                            qi_count += 1
                            honors.append("Quality Image")
                            if not is_bot_account(uploader):
                                uploader_counts[uploader]["qi"] += 1
                        if is_fp:
                            fp_count += 1
                            honors.append("Featured Picture")
                            if not is_bot_account(uploader):
                                uploader_counts[uploader]["fp"] += 1
                        if is_vi:
                            vi_count += 1
                            honors.append("Valued Image")
                            if not is_bot_account(uploader):
                                uploader_counts[uploader]["vi"] += 1

                        if honors and not is_bot_account(uploader):
                            uploader_counts[uploader]["total"] += 1
                            recognized_files.append({
                                "title": title.replace("File:", "").replace("_", " "),
                                "full_title": title,
                                "honors": ", ".join(honors),
                                "uploader": uploader,
                                "commons_url": desc_url,
                                "thumb_url": thumb_url
                            })

                    continuation = payload.get("continue")
                    if not continuation or "gcmcontinue" not in continuation:
                        break
                    params["gcmcontinue"] = continuation.get("gcmcontinue")
                    params["continue"] = continuation.get("continue", "gcmcontinue||")
                except Exception as e:
                    logger.warning(f"Error sampling general category {cat} for quality: {e}")
                    break

            if sampled_this_cat > 0:
                total_sampled = total_cohort_uploads or sampled_this_cat
                break

    effective_total = total_cohort_uploads or total_sampled or len(recognized_files) or 1
    total_honors = qi_count + fp_count + vi_count
    quality_rate = (total_honors / effective_total * 100.0) if effective_total > 0 else 0.0

    # Photographer Leaderboard (human uploaders only)
    leaderboard = []
    rank = 1
    for uploader, counts in sorted(uploader_counts.items(), key=lambda x: (x[1]["total"], x[1]["fp"], x[1]["qi"]), reverse=True):
        if not is_bot_account(uploader):
            leaderboard.append({
                "rank": rank,
                "uploader": uploader,
                "total_honors": counts["total"],
                "qi_count": counts["qi"],
                "fp_count": counts["fp"],
                "vi_count": counts["vi"]
            })
            rank += 1

    result = {
        "code": code_clean,
        "event_type": evt,
        "country_code": cc,
        "year": 2000 + int(yr),
        "total_sampled": effective_total,
        "quality_rate_pct": round(quality_rate, 2),
        "qi_count": qi_count,
        "fp_count": fp_count,
        "vi_count": vi_count,
        "recognized_files_count": len(recognized_files),
        "honored_photographers_count": len(leaderboard),
        "recognized_files": recognized_files[:50],
        "leaderboard": leaderboard[:25]
    }
    if total_sampled > 0 or recognized_files:
        campaign_cache.put_quality_recognition(code_clean, result)
    return result


