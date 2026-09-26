"""Refresh the persistent campaign cache.

Examples:
    python refresh_cache.py --years 2022-2025 --events wlm,wle --countries de,bd
    CAMPAIGN_CACHE_CODES=wlmde22 wlmbd23 python refresh_cache.py
"""

import argparse
import os
from datetime import date

import campaign_cache
from analytics import (
    EVENT_COUNTRY_SCOPE,
    EVENT_MAP,
    COUNTRY_MAP,
    get_campaign_structural_metrics,
    get_participants,
    compute_content_utility_deep,
    compute_quality_recognition_deep,
)


def _parse_years(value):
    start, _, end = value.partition("-")
    first = int(start)
    last = int(end or start)
    return range(min(first, last), max(first, last) + 1)


def configured_codes(args):
    explicit = os.getenv("CAMPAIGN_CACHE_CODES", "").split()
    if explicit:
        return explicit
    events = [item for item in args.events.split(",") if item]
    countries = [item for item in args.countries.split(",") if item]
    codes = []
    for event in events:
        scope = EVENT_COUNTRY_SCOPE.get(event, "*")
        allowed = scope.get("countries", []) if isinstance(scope, dict) else scope
        for country in countries:
            if allowed != "*" and country not in allowed:
                continue
            for year in _parse_years(args.years):
                codes.append(f"{event}{country}{year % 100:02d}")
    return codes


def main():
    current_year = date.today().year
    parser = argparse.ArgumentParser(description="Refresh stale/missing campaign cache entries.")
    parser.add_argument("--years", default=f"{current_year - 4}-{current_year - 1}",
                        help="Year or inclusive range, e.g. 2022-2025.")
    parser.add_argument("--events", default=",".join(EVENT_MAP),
                        help="Comma-separated event codes.")
    parser.add_argument("--countries", default=",".join(sorted(COUNTRY_MAP)),
                        help="Comma-separated country codes.")
    parser.add_argument("--deep", action="store_true",
                        help="Also precompute and persist deep Content Utility and Quality Recognition.")
    parser.add_argument("--sample-depth", type=int, default=1500,
                        help="Maximum file sample depth for deep precomputation (default: 1500).")
    parser.add_argument("--force", action="store_true",
                        help="Force recomputation even if unexpired entries exist in cache.")
    args = parser.parse_args()

    campaign_cache.initialize_cache()
    codes = configured_codes(args)
    for code in codes:
        if args.force:
            # Clear in-memory and force refresh
            pass
        get_participants(code)
        get_campaign_structural_metrics(code)
        if args.deep:
            compute_content_utility_deep(code, max_sample=args.sample_depth)
            compute_quality_recognition_deep(code, max_sample=args.sample_depth)
        print(f"refreshed {code}{' (deep)' if args.deep else ''}")
    print(f"Processed {len(codes)} campaign codes.")


if __name__ == "__main__":
    main()
