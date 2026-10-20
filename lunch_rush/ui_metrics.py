"""Pure calculation/presentation helpers, separate from Streamlit."""
from __future__ import annotations
from datetime import date, timedelta
from collections import defaultdict
from typing import Any


def format_money(value: float | None, *, compact: bool=False) -> str:
    if value is None: return 'N/A'
    if compact and abs(value)>=1_000_000: return f'${value/1_000_000:,.2f}M'
    if compact and abs(value)>=1_000: return f'${value/1_000:,.1f}K'
    return f'${value:,.2f}'


def format_int(value: int | None) -> str:
    return 'N/A' if value is None else f'{value:,}'


def format_pct(value: float | None, *, signed: bool=True) -> str:
    if value is None: return 'N/A'
    return f'{value:+.1%}' if signed else f'{value:.1%}'


def scope_ids(analytics, region: str | None=None, ownership: str | None=None, rest_format: str | None=None):
    return sorted(rid for rid,r in analytics.restaurants.items()
                  if (region is None or r['region_id']==region)
                  and (ownership is None or r['ownership_type']==ownership)
                  and (rest_format is None or r['restaurant_format']==rest_format))


def week_series(analytics, start: date, end: date, ids: list[str]):
    weeks=analytics._weeks(start,end)
    return [{'week_end':w,'net_sales_usd':(m:=analytics.sales_summary(w,w,restaurant_ids=ids))['net_sales_usd'],
             'transactions':m['transactions'],'average_check_usd':m['average_check_usd'],
             'complete':m['complete']} for w in weeks]


def mix_breakdown(analytics,start:date,end:date,ids:list[str],*,by:str):
    if by not in ('channel','daypart'):
        raise ValueError('Breakdown must be channel or daypart')
    categories=sorted({r[by] for r in analytics.data['Sales_Weekly']})
    values=[]
    for category in categories:
        m=analytics.sales_summary(start,end,restaurant_ids=ids,**{by:category})
        values.append({'name':category,**m})
    return sorted(values,key=lambda x:-x['net_sales_usd'])


def restaurant_table(analytics,start:date,end:date,ids:list[str],mode:str='yoy'):
    full=analytics.location_rankings(start,end)
    valid={r['restaurant_id']:r for r in full['restaurants'] if r['restaurant_id'] in ids}
    excluded={rid: full['excluded_restaurants'].get(rid,'not_ranked') for rid in ids if rid not in valid}
    rows=[]
    for rid,row in valid.items():
        record={**row,'ownership_type':analytics.restaurants[rid]['ownership_type'],
                'restaurant_format':analytics.restaurants[rid]['restaurant_format'],
                'region':analytics.restaurants[rid]['region_name']}
        if mode=='none': record['sales_growth_pct']=None;record['transaction_growth_pct']=None
        else:
            comparison=analytics.compare_sales(start,end,mode=mode,restaurant_ids=[rid])
            record['sales_growth_pct']=comparison['sales_growth_pct']
            record['transaction_growth_pct']=comparison['transaction_growth_pct']
        rows.append(record)
    rows.sort(key=lambda x:(-x['net_sales_usd'],x['restaurant_id']))
    for i,row in enumerate(rows,1):row['rank']=i
    return {'restaurants':rows,'excluded_restaurants':excluded,'cohort_size':len(rows)}


def category_summary(menu: dict[str,Any]):
    sums=defaultdict(lambda:{'net_sales_usd':0.,'units_sold':0})
    for row in menu['items']:
        m=sums[row['category']];m['net_sales_usd']+=row['net_sales_usd'];m['units_sold']+=row['units_sold']
    total=sum(row['net_sales_usd'] for row in sums.values())
    return sorted([{'category':cat,**values,'mix_pct':values['net_sales_usd']/total if total else None}
                   for cat,values in sums.items()],key=lambda x:-x['net_sales_usd'])


def matched_menu_growth(analytics,start:date,end:date,ids:list[str],mode:str):
    if mode not in ('yoy','previous'):return {}
    comparable=analytics.comparable_sales(start,end,mode=mode,restaurant_ids=ids)
    eligible=comparable['restaurant_ids']
    if not eligible:return {}
    weeks=len(analytics._weeks(start,end))
    offset=timedelta(days=364) if mode=='yoy' else timedelta(weeks=weeks)
    old_start=start-offset;old_end=end-offset
    curr=analytics.menu_summary(start,end,restaurant_ids=eligible)
    prev=analytics.menu_summary(old_start,old_end,restaurant_ids=eligible)
    if not curr['complete'] or not prev['complete']:return {}
    prev_by_id={r['menu_item_id']:r['net_sales_usd'] for r in prev['items']}
    return {r['menu_item_id']:r['net_sales_usd']/prev_by_id[r['menu_item_id']]-1
            for r in curr['items'] if prev_by_id.get(r['menu_item_id'],0)>0}
