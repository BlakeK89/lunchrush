"""Restaurant/region comparison calculations for the Lunch Rush detail builder.

Keep one restaurant in each selected group exactly once. Regional metrics are
recomputed from underlying sales, not averages of location percentages.
"""
from __future__ import annotations

from typing import Iterable

import pandas as pd

METRICS = (
    'Net Sales', 'Sales Change', 'Transactions', 'Transaction Change',
    'Average Check', 'Average Check Change', 'Sales Mix',
    'Complete Weeks', 'Incomplete Weeks',
)
DEFAULT_METRICS = METRICS[:7]
FORMATS = {
    'Rank': 'count', 'Net Sales': 'money', 'Sales Change': 'growth',
    'Transactions': 'count', 'Transaction Change': 'growth',
    'Average Check': 'price', 'Average Check Change': 'growth',
    'Sales Mix': 'pct', 'Complete Weeks': 'count',
    'Incomplete Weeks': 'count',
}
WIDTHS = {
    'Region': 130, 'Restaurant': 200, 'Rank': 78, 'Reporting': 145,
    'Net Sales': 150, 'Sales Change': 140, 'Transactions': 140,
    'Transaction Change': 180, 'Average Check': 155,
    'Average Check Change': 195, 'Sales Mix': 125,
    'Complete Weeks': 140, 'Incomplete Weeks': 155,
}
CHANGE_COLUMNS = ('Sales Change', 'Transaction Change', 'Average Check Change')
GROUPS = ('Restaurant', 'Region', 'Region → Restaurant')


def scoped_restaurants(analytics, dashboard_ids: Iterable[str],
                       regions: Iterable[str] = (),
                       restaurants: Iterable[str] = ()) -> list[str]:
    """Intersect selections; empty filter in either dimension means all."""
    region_set, restaurant_set = set(regions), set(restaurants)
    return sorted(rid for rid in set(dashboard_ids)
                  if rid in analytics.restaurants
                  and (not region_set or analytics.restaurants[rid]['region_id'] in region_set)
                  and (not restaurant_set or rid in restaurant_set))


def _percent_change(current, previous):
    if previous is None or previous <= 0 or current is None:
        return None
    return 100 * (current / previous - 1)


def _status(analytics, ids, start, end, summary):
    if not summary['complete']:
        return 'Incomplete data'
    weeks = analytics._weeks(start, end)
    for rid in ids:
        rm = analytics.restaurants[rid]
        if rm['opened_on'] > end:
            return 'Not yet open'
        if rm['opened_on'] > start:
            return 'Partial period'
        if rm['closed_on'] is not None and rm['closed_on'] < end:
            return 'Partial period'
        for week in weeks:
            status = analytics.status.get((rid, week))
            if status is None:
                continue
            if status['disruption_flag'] or status['actual_operating_days'] != 7 or status['expected_operating_days'] != 7:
                return 'Disrupted / partial'
    return 'Complete'


def comparison_frame(analytics, start, end, restaurant_ids: Iterable[str],
                     mode: str, *, group_by: str = 'Restaurant',
                     metrics: Iterable[str] = DEFAULT_METRICS,
                     rank_by_id: dict[str, int] | None = None) -> pd.DataFrame:
    """Build a CSV-ready numeric frame from the existing validated engine."""
    if group_by not in GROUPS:
        raise ValueError(f'Unknown grouping: {group_by}')
    metrics = list(dict.fromkeys(metrics))
    if any(metric not in METRICS for metric in metrics):
        raise ValueError('Invalid comparison metric')
    ids = sorted(set(restaurant_ids))
    if any(rid not in analytics.restaurants for rid in ids):
        raise ValueError('Unknown restaurant in selection')
    if not ids:
        return pd.DataFrame()
    by_region: dict[str, list[str]] = {}
    for rid in ids:
        region = analytics.restaurants[rid]['region_name']
        by_region.setdefault(region, []).append(rid)
    if group_by == 'Region':
        groups = [(reg, None, members) for reg, members in sorted(by_region.items())]
    elif group_by == 'Region → Restaurant':
        groups = [(reg, rid, [rid]) for reg, members in sorted(by_region.items())
                  for rid in sorted(members, key=lambda x: (analytics.restaurants[x]['restaurant_name'], x))]
    else:
        # Match the legacy ranking by default; unranked stores follow by name.
        ranks = rank_by_id or {}
        groups = [(analytics.restaurants[rid]['region_name'], rid, [rid])
                  for rid in sorted(ids, key=lambda x: (ranks.get(x, 10**9),
                              analytics.restaurants[x]['restaurant_name'], x))]

    total = analytics.sales_summary(start, end, restaurant_ids=ids)['net_sales_usd']
    rows = []
    for region, rid, members in groups:
        comp = analytics.compare_sales(start, end, mode=mode, restaurant_ids=members)
        current, previous = comp['current'], comp['prior']
        previous_check = previous['average_check_usd'] if previous is not None else None
        can_compare = mode != 'none' and comp['reason'] is None
        row = {'Region': region}
        if rid is not None:
            row['Restaurant'] = f'{analytics.restaurants[rid]["restaurant_name"]} ({rid})'
            if group_by == 'Restaurant':
                row['Rank'] = (rank_by_id or {}).get(rid)
        row.update({
            'Net Sales': current['net_sales_usd'],
            'Sales Change': 100 * comp['sales_growth_pct'] if can_compare else None,
            'Transactions': current['transactions'],
            'Transaction Change': 100 * comp['transaction_growth_pct'] if can_compare else None,
            'Average Check': current['average_check_usd'],
            'Average Check Change': _percent_change(current['average_check_usd'], previous_check) if can_compare else None,
            'Sales Mix': 100 * current['net_sales_usd'] / total if total else None,
            'Complete Weeks': current['eligible_store_weeks'],
            'Incomplete Weeks': current['incomplete_store_weeks'],
            'Reporting': _status(analytics, members, start, end, current),
        })
        rows.append(row)
    fixed = (['Region'] if group_by != 'Restaurant' else []) + (['Restaurant'] if group_by != 'Region' else [])
    if group_by == 'Restaurant':
        fixed += ['Rank', 'Region']
    return pd.DataFrame(rows, columns=fixed + metrics + ['Reporting'])
