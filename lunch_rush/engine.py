"""Lunch Rush V1: schema validation and restaurant analytics (Python stdlib only).

Return missing/unsupported comparisons as None and retain explicit reasons.
Input table rows are dictionaries matching Lunch_Rush_V1_Schema.json.
"""
from __future__ import annotations
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import calendar
import json
from typing import Any

from .io import as_date

CENTS = Decimal('0.01')
MONEY = ('gross_sales_usd','discount_usd','refund_usd','net_sales_usd','item_net_sales_usd',
         'discount_cost_usd','financial_net_revenue_usd','food_cogs_usd','labor_cost_usd',
         'other_operating_cost_usd')

class DataError(ValueError):
    pass

@dataclass
class ValidationResult:
    errors: list[str]
    warnings: list[str]
    tables: dict[str, list[dict]]
    def assert_valid(self):
        if self.errors:
            raise DataError('\n'.join(self.errors[:25]) +
                (f'\n... and {len(self.errors)-25} more' if len(self.errors)>25 else ''))
        return self


def _month_shift(d: date, n: int) -> date:
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    return date(year, month, min(d.day, calendar.monthrange(year, month)[1]))


def _number(value: Any, kind: str):
    if value is None or isinstance(value, bool) or (isinstance(value, str) and not value.strip()):
        raise ValueError('missing or nonnumeric')
    try:
        d = Decimal(str(value))
    except InvalidOperation as ex:
        raise ValueError('not numeric') from ex
    if not d.is_finite():
        raise ValueError('non-finite')
    if kind == 'integer':
        if d != d.to_integral_value():
            raise ValueError('not integer')
        return int(d)
    if kind == 'money':
        if d != d.quantize(CENTS):
            raise ValueError('money must be in cents')
        return int(d * 100)  # pennies, without floating rounding
    raise ValueError(f'unknown numeric kind {kind}')


def validate(tabs: dict[str, list[dict]], schema: dict) -> ValidationResult:
    errors, warnings = [], []
    result = {}
    spec = schema['tables']
    for name, meta in spec.items():
        if name not in tabs:
            if meta['required']:
                errors.append(f'{name}: missing required sheet')
            result[name] = []
            continue
        fields = meta['fields']; cols = [f['name'] for f in fields]
        raw = tabs[name]
        if not isinstance(raw, list):
            errors.append(f'{name}: expected list of records'); result[name] = []; continue
        # Empty optional sheets can have headers but no records.
        if not raw and meta['required']:
            errors.append(f'{name}: required sheet has no records')
        if raw:
            extra = set(raw[0]) - set(cols)
            missing = set(cols) - set(raw[0])
            if missing or extra or list(raw[0]) != cols:
                errors.append(f'{name}: column headers/order differ from the input contract: missing={sorted(missing)}, extra={sorted(extra)}')
        out, keys = [], set()
        for i, rawrow in enumerate(raw, 2):
            row = {}
            for f in fields:
                col, kind = f['name'], f['type']; val=rawrow.get(col)
                try:
                    if val is None or val == '':
                        if f['required']:
                            raise ValueError('required value missing')
                        row[col] = None; continue
                    if kind == 'date':
                        row[col] = as_date(val)
                    elif kind in ('integer','money'):
                        row[col] = _number(val,kind)
                    elif kind == 'boolean':
                        if isinstance(val, bool): row[col] = val
                        elif val in (0,1): row[col] = bool(val)
                        elif isinstance(val,str) and val.upper() in ('TRUE','FALSE'):
                            row[col] = val.upper()=='TRUE'
                        else: raise ValueError('expected TRUE or FALSE')
                    else:
                        if not isinstance(val,str): raise ValueError('expected text')
                        row[col] = val.strip()
                        if not row[col]: raise ValueError('blank text')
                        if kind=='enum' and row[col] not in f['allowed_values']:
                            raise ValueError('unexpected enum')
                except (ValueError, TypeError, OverflowError) as ex:
                    if len(errors)<100:
                        errors.append(f'{name} row {i}, {col}: {ex}')
                    row[col] = None
            key = tuple(row.get(k) for k in meta['primary_key'])
            if key in keys:
                errors.append(f'{name} row {i}: duplicate key {key}')
            keys.add(key); out.append(row)
        result[name]=out
    if errors:
        return ValidationResult(errors[:125],warnings,result)

    restaurants={r['restaurant_id']:r for r in result['Restaurant_Master']}
    products={m['menu_item_id']:m for m in result['Menu_Master']}
    sources={s['source_id']:s for s in result['Source_Log']}
    status={(s['restaurant_id'],s['week_end']):s for s in result['Store_Week_Status']}
    region_names={}
    for r in restaurants.values():
        existing=region_names.setdefault(r['region_id'],r['region_name'])
        if existing!=r['region_name']: errors.append(f'inconsistent region name for {r["region_id"]}')
        if r['closed_on'] and r['closed_on']<r['opened_on']:
            errors.append(f'{r["restaurant_id"]}: close before open date')
    for m in products.values():
        if m['retired_on'] and m['retired_on']<m['introduced_on']:
            errors.append(f'{m["menu_item_id"]}: retire before introduction')

    allfact=('Store_Week_Status','Sales_Weekly','Menu_Weekly','Promotions_Weekly','Financials_Weekly')
    for name in allfact:
        for r in result[name]:
            k=(r['restaurant_id'],r['week_end']); week=r['week_end']; rid=r['restaurant_id']
            if rid not in restaurants:
                errors.append(f'{name}: unknown restaurant {rid}'); continue
            rm=restaurants[rid]
            if week.weekday()!=6: errors.append(f'{name}: non-Sunday {week} at {rid}')
            if week < rm['opened_on'] or (rm['closed_on'] and week - timedelta(days=6)>rm['closed_on']):
                errors.append(f'{name}: {rid} week {week} outside operating history')
            if r['source_id'] not in sources:
                errors.append(f'{name}: missing source {r["source_id"]}')
            elif week > sources[r['source_id']]['extracted_on']:
                errors.append(f'{name}: {rid} week {week} after source extraction')
            if name!='Store_Week_Status' and k not in status:
                errors.append(f'{name}: missing store-week status for {rid} {week}')

    pos_by_week=defaultdict(list); menu_by_week=defaultdict(list)
    for r in result['Store_Week_Status']:
        if not 1<=r['expected_operating_days']<=7:
            errors.append(f'status: expected days outside 1..7 {r["restaurant_id"]} {r["week_end"]}')
        if not 0<=r['actual_operating_days']<=r['expected_operating_days']:
            errors.append(f'status: actual days exceed expected {r["restaurant_id"]} {r["week_end"]}')
    for r in result['Sales_Weekly']:
        key=r['restaurant_id'],r['week_end']; pos_by_week[key].append(r)
        for f in ('gross_sales_usd','discount_usd','refund_usd','transaction_count'):
            if r[f]<0: errors.append(f'Sales_Weekly: negative {f} at {key}')
        if r['gross_sales_usd'] - r['discount_usd'] - r['refund_usd'] != r['net_sales_usd']:
            errors.append(f'Sales_Weekly: row net-sales mismatch at {key} {r["channel"]}/{r["daypart"]}')
        if r['net_sales_usd']<0: errors.append(f'Sales_Weekly: negative net sales at {key}')
        if r['transaction_count']==0 and r['gross_sales_usd']!=0:
            errors.append(f'Sales_Weekly: positive sales with zero transactions at {key}')
        source=sources.get(r['source_id'],{})
        if 'consumer restaurant pos' not in source.get('sales_basis','').lower():
            errors.append(f'Sales_Weekly: source {r["source_id"]} is not designated consumer restaurant POS')
    for r in result['Menu_Weekly']:
        key=r['restaurant_id'],r['week_end']; menu_by_week[key].append(r)
        mid=r['menu_item_id']; item=products.get(mid)
        if item is None: errors.append(f'Menu_Weekly: unknown item {mid}'); continue
        if r['week_end']<item['introduced_on'] or (item['retired_on'] and r['week_end']-timedelta(days=6)>item['retired_on']):
            errors.append(f'Menu_Weekly: {mid} {key} outside item life')
        if r['units_sold']<0 or r['item_net_sales_usd']<0:
            errors.append(f'Menu_Weekly: negative units or revenue at {key}')
        if r['item_net_sales_usd']>0 and r['units_sold']==0:
            errors.append(f'Menu_Weekly: revenue without units at {key}')
        if r['item_order_count'] is not None:
            if not 0<=r['item_order_count']<=r['units_sold']:
                errors.append(f'Menu_Weekly: invalid item order count {key} {mid}')
            if status.get(key,{}).get('coverage_status')=='Complete':
                tran=sum(s['transaction_count'] for s in pos_by_week.get(key,()))
                if r['item_order_count']>tran:
                    errors.append(f'Menu_Weekly: item orders exceed transactions {key} {mid}')
    for key, st in status.items():
        pos=pos_by_week.get(key,[]); menu=menu_by_week.get(key,[])
        if st['coverage_status']=='Complete' and not pos:
            errors.append(f'Store_Week_Status: marked Complete but no POS row at {key}')
        if st['coverage_status']=='Missing' and pos:
            errors.append(f'Store_Week_Status: marked Missing but POS rows supplied {key}')
        if st['menu_coverage_status']=='Missing' and menu:
            errors.append(f'Store_Week_Status: marked menu Missing but item rows supplied {key}')
        if st['coverage_status']=='Complete' and st['menu_coverage_status']=='Complete':
            pos_net=sum(r['net_sales_usd'] for r in pos)
            menu_net=sum(r['item_net_sales_usd'] for r in menu)
            if abs(menu_net-pos_net)>1:
                errors.append(f'menu/POS reconciliation mismatch {key}: menu={menu_net}c POS={pos_net}c')
    for r in result['Promotions_Weekly']:
        if r['redemption_count']<0 or r['discount_cost_usd']<0:
            errors.append(f'Promotions_Weekly: negative expense/redemptions')
    promos=defaultdict(int)
    for r in result['Promotions_Weekly']:
        promos[(r['restaurant_id'],r['week_end'])]+=r['discount_cost_usd']
    for key,c in promos.items():
        if status.get(key,{}).get('coverage_status')=='Complete':
            discounted=sum(x['discount_usd'] for x in pos_by_week[key])
            if c > discounted+1: errors.append(f'Promotion discounts exceed POS discounts at {key}')
    for r in result['Financials_Weekly']:
        for f in ('financial_net_revenue_usd','food_cogs_usd','labor_cost_usd','other_operating_cost_usd'):
            if r[f]<0: errors.append(f'Financials_Weekly: negative {f}')
    for name in ('Promotions_Weekly','Financials_Weekly'):
        if not result[name]: warnings.append(f'{name} not provided: related metrics unavailable')
    return ValidationResult(errors[:150],warnings,result)


def usd(cents: int | None) -> float | None:
    return None if cents is None else round(cents/100,2)


class Analytics:
    def __init__(self, valid: ValidationResult):
        valid.assert_valid()
        self.data=valid.tables
        self.restaurants={r['restaurant_id']:r for r in self.data['Restaurant_Master']}
        self.menu={m['menu_item_id']:m for m in self.data['Menu_Master']}
        self.status={(r['restaurant_id'],r['week_end']):r for r in self.data['Store_Week_Status']}
        self.sales=defaultdict(list); self.items=defaultdict(list)
        for r in self.data['Sales_Weekly']:
            self.sales[(r['restaurant_id'],r['week_end'])].append(r)
        for r in self.data['Menu_Weekly']:
            self.items[(r['restaurant_id'],r['week_end'])].append(r)
        self.latest=max(s['week_end'] for s in self.data['Store_Week_Status'])
        self.earliest=min(s['week_end'] for s in self.data['Store_Week_Status'])

    def period(self, end: date | None=None, weeks: int=13, comparison: str='yoy'):
        end=end or self.latest
        if end.weekday()!=6 or not 1<=weeks<=104:
            raise ValueError('Use a Sunday end and 1..104 weeks')
        start=end-timedelta(weeks=weeks-1)
        if comparison=='yoy': prior_start=start-timedelta(days=364)
        elif comparison=='previous': prior_start=start-timedelta(weeks=weeks)
        elif comparison=='none': prior_start=None
        else: raise ValueError('comparison must be yoy, previous, none')
        return start,end,prior_start,(prior_start+timedelta(weeks=weeks-1) if prior_start else None)

    def _ids(self, restaurant_ids=None, region_id=None):
        ids=set(restaurant_ids) if restaurant_ids is not None else set(self.restaurants)
        if ids-set(self.restaurants): raise ValueError('Unknown restaurant selection')
        if region_id: ids={i for i in ids if self.restaurants[i]['region_id']==region_id}
        return ids

    def _weeks(self,start,end):
        if start.weekday()!=6 or end.weekday()!=6 or start>end:
            raise ValueError('Reporting period must include Sunday-ending weeks')
        return [start+timedelta(weeks=i) for i in range(((end-start).days//7)+1)]

    def sales_summary(self,start,end,*,restaurant_ids=None,region_id=None,channel=None,daypart=None):
        ids=self._ids(restaurant_ids,region_id); weeks=set(self._weeks(start,end))
        active_keys={(rid,week) for (rid,week) in self.status if rid in ids and week in weeks}
        # Missing store-week feed record for an open site should be surfaced, not treated as zero.
        missing_status=[]
        for rid in ids:
            rm=self.restaurants[rid]
            for week in weeks:
                if week < rm['opened_on'] or (rm['closed_on'] and week-timedelta(days=6)>rm['closed_on']): continue
                if (rid,week) not in self.status: missing_status.append((rid,week))
        excluded=sorted(k for k in active_keys if self.status[k]['coverage_status']!='Complete')
        selected=active_keys-set(excluded)
        rows=[r for key in selected for r in self.sales.get(key,()) if (channel is None or r['channel']==channel) and (daypart is None or r['daypart']==daypart)]
        net=sum(r['net_sales_usd'] for r in rows)
        tran=sum(r['transaction_count'] for r in rows)
        gross=sum(r['gross_sales_usd'] for r in rows)
        discount=sum(r['discount_usd'] for r in rows)
        return {'net_sales_usd':usd(net),'transactions':tran,
                'average_check_usd':None if tran==0 else round(net/100/tran,4),
                'gross_sales_usd':usd(gross),'discount_rate':None if gross==0 else discount/gross,
                'eligible_store_weeks':len(selected), 'incomplete_store_weeks':len(excluded)+len(missing_status),
                'complete':not excluded and not missing_status,'warning':
                  None if not excluded and not missing_status else f'{len(excluded)+len(missing_status)} store-weeks incomplete; totals exclude them'}

    def compare_sales(self,start,end,*,mode='yoy',restaurant_ids=None,region_id=None,channel=None,daypart=None):
        w=len(self._weeks(start,end)); _,_,pstart,pend=self.period(end=end,weeks=w,comparison=mode)
        current=self.sales_summary(start,end,restaurant_ids=restaurant_ids,region_id=region_id,channel=channel,daypart=daypart)
        if pstart is None: return {'current':current,'prior':None,'sales_growth_pct':None,'transaction_growth_pct':None,'reason':'No comparison requested'}
        prior=self.sales_summary(pstart,pend,restaurant_ids=restaurant_ids,region_id=region_id,channel=channel,daypart=daypart)
        if not current['complete'] or not prior['complete']:
            return {'current':current,'prior':prior,'sales_growth_pct':None,'transaction_growth_pct':None,'reason':'Incomplete reporting in compared periods'}
        if prior['net_sales_usd']<=0 or prior['transactions']<=0:
            return {'current':current,'prior':prior,'sales_growth_pct':None,'transaction_growth_pct':None,'reason':'Zero or missing prior-period denominator'}
        return {'current':current,'prior':prior,
                'sales_growth_pct':current['net_sales_usd']/prior['net_sales_usd']-1,
                'transaction_growth_pct':current['transactions']/prior['transactions']-1,'reason':None}

    def comparable_sales(self,start,end,*,mode='yoy',restaurant_ids=None,region_id=None):
        cur_weeks=self._weeks(start,end)
        if mode not in ('yoy','previous'): raise ValueError('SSS requires yoy or previous comparison')
        offset=timedelta(days=364) if mode=='yoy' else timedelta(weeks=len(cur_weeks))
        ids=self._ids(restaurant_ids,region_id)
        cohort=set(); reasons=Counter(); current=previous=0; cur_tx=prev_tx=0
        for rid in ids:
            rm=self.restaurants[rid]
            valid=True; why=None
            for week in cur_weeks:
                prev=week-offset
                a=self.status.get((rid,week)); b=self.status.get((rid,prev))
                if rm['opened_on'] > _month_shift(week,-13):
                    valid=False;why='younger_than_13_months';break
                if a is None or b is None:
                    valid=False;why='unmatched_store_week';break
                if (a['coverage_status']!='Complete' or b['coverage_status']!='Complete' or
                    not a['expected_operating_days']==a['actual_operating_days'] or
                    not b['expected_operating_days']==b['actual_operating_days'] or
                    a['actual_operating_days']==0 or b['actual_operating_days']==0 or
                    a['disruption_flag'] or b['disruption_flag']):
                    valid=False;why='coverage_or_disruption';break
            if valid:
                cohort.add(rid)
                current+=sum(r['net_sales_usd'] for week in cur_weeks for r in self.sales[(rid,week)])
                previous+=sum(r['net_sales_usd'] for week in cur_weeks for r in self.sales[(rid,week-offset)])
                cur_tx+=sum(r['transaction_count'] for week in cur_weeks for r in self.sales[(rid,week)])
                prev_tx+=sum(r['transaction_count'] for week in cur_weeks for r in self.sales[(rid,week-offset)])
            else: reasons[why]+=1
        return {'eligible_restaurants':len(cohort),'restaurant_ids':sorted(cohort),'excluded_restaurants':len(ids-cohort),
                'exclusions_by_reason':dict(reasons),'current_sales_usd':usd(current),'prior_sales_usd':usd(previous),
                'current_transactions':cur_tx,'prior_transactions':prev_tx,
                'comparable_store_transaction_growth_pct':None if prev_tx==0 else cur_tx/prev_tx-1,
                'comparable_store_sales_growth_pct':None if previous<=0 else current/previous-1,
                'reason':None if previous>0 else 'No valid matched cohort or prior sales'}

    def menu_summary(self,start,end,*,restaurant_ids=None,region_id=None):
        ids=self._ids(restaurant_ids,region_id); weeks=set(self._weeks(start,end))
        keys=[k for k,s in self.status.items() if k[0] in ids and k[1] in weeks and
              s['coverage_status']=='Complete' and s['menu_coverage_status']=='Complete']
        pending=[k for k,s in self.status.items() if k[0] in ids and k[1] in weeks and
              (s['coverage_status']!='Complete' or s['menu_coverage_status']!='Complete')]
        # No channel/daypart input because item-by-channel breakdown isn't supported.
        sums=defaultdict(lambda: {'units_sold':0,'item_net_sales_cents':0,'item_orders':0,'item_orders_available':True,'reported_keys':set()})
        pos_transactions=sum(r['transaction_count'] for key in keys for r in self.sales[key])
        total=0
        for key in keys:
            for row in self.items[key]:
                s=sums[row['menu_item_id']]
                s['units_sold']+=row['units_sold']; s['item_net_sales_cents']+=row['item_net_sales_usd']
                s['reported_keys'].add(key)
                if row['item_order_count'] is None: s['item_orders_available']=False
                else: s['item_orders']+=row['item_order_count']
                total+=row['item_net_sales_usd']
        breakdown=[]
        for mid,v in sums.items():
            breakdown.append({'menu_item_id':mid,'menu_item_name':self.menu[mid]['menu_item_name'],
                 'category':self.menu[mid]['menu_category'],'units_sold':v['units_sold'],
                 'net_sales_usd':usd(v['item_net_sales_cents']),
                 'mix_pct':None if total==0 else v['item_net_sales_cents']/total,
                 'realized_item_price_usd':None if v['units_sold']==0 else round(v['item_net_sales_cents']/100/v['units_sold'],4),
                 'attach_rate':None if (not v['item_orders_available'] or pos_transactions==0 or len(v['reported_keys'])!=len(keys)) else v['item_orders']/pos_transactions})
        breakdown.sort(key=lambda x:x['net_sales_usd'],reverse=True)
        return {'items':breakdown,'menu_total_usd':usd(total),'eligible_store_weeks':len(keys),
                'incomplete_store_weeks':len(pending),'complete':not pending,
                'warning':None if not pending else f'{len(pending)} incomplete store-week menus omitted; do not use these figures as full-chain totals'}

    def location_rankings(self,start,end,*,region_id=None):
        """Rank only restaurants with a complete, disruption-free matched window.

        New openings and partial trading weeks are not ranked against full-window peers.
        """
        weeks=self._weeks(start,end); qualifying=[]; exclusions={}
        for rid in self._ids(region_id=region_id):
            reasons=[]
            for week in weeks:
                st=self.status.get((rid,week))
                if st is None: reasons.append('not_open_or_unreported');break
                if (st['coverage_status']!='Complete' or st['disruption_flag'] or
                    st['actual_operating_days']!=7 or st['expected_operating_days']!=7):
                    reasons.append('partial_or_disrupted');break
            if reasons:
                exclusions[rid]=reasons[0];continue
            rows=[r for week in weeks for r in self.sales[(rid,week)]]
            net=sum(r['net_sales_usd'] for r in rows)
            tx=sum(r['transaction_count'] for r in rows)
            qualifying.append({'restaurant_id':rid,'restaurant_name':self.restaurants[rid]['restaurant_name'],
                     'region_id':self.restaurants[rid]['region_id'],
                     'net_sales_usd':usd(net),'transactions':tx,
                     'average_check_usd':None if tx==0 else round(net/100/tx,4)})
        qualifying.sort(key=lambda r:(-r['net_sales_usd'],r['restaurant_id']))
        for i,r in enumerate(qualifying,1):r['rank']=i
        return {'restaurants':qualifying,'excluded_restaurants':exclusions,
                'cohort_size':len(qualifying),'ranking_window_weeks':len(weeks)}

    def average_unit_volume(self,end=None,*,restaurant_ids=None,region_id=None):
        """Unannualized 52-week restaurant AUV for exactly 52 complete 7-day weeks."""
        end=end or self.latest
        weeks=self._weeks(end-timedelta(weeks=51),end)
        ids=self._ids(restaurant_ids,region_id)
        rank=self.location_rankings(weeks[0],weeks[-1],region_id=region_id)
        eligible=[r for r in rank['restaurants'] if r['restaurant_id'] in ids]
        return {'full_year':True,'period_start':weeks[0],'period_end':end,'eligible_restaurants':len(eligible),
                'excluded_restaurants':len(ids)-len(eligible),
                'average_unit_volume_usd':None if not eligible else round(sum(r['net_sales_usd'] for r in eligible)/len(eligible),2),
                'note':'Exactly 52 complete seven-day restaurant weeks; excludes partial stores, new openings and disruptions.'}

    def diagnostics(self,start,end,*,comparison='yoy',restaurant_ids=None,region_id=None):
        """Measured signals only; investigation prompts never assert causes."""
        findings=[]
        selected_ids=self._ids(restaurant_ids,region_id)
        # Use one matched fixed cohort to avoid confusing new-store openings with traffic growth.
        if comparison in ('yoy','previous'):
            overall=self.comparable_sales(start,end,mode=comparison,restaurant_ids=selected_ids)
            growth=overall['comparable_store_sales_growth_pct']
            traffic_growth=overall['comparable_store_transaction_growth_pct']
            if growth is not None and traffic_growth is not None and growth>0 and traffic_growth < -0.01:
                findings.append({'kind':'traffic_check_divergence','scope':'Matched comparable stores','severity':'watch',
                  'evidence':{'sales_growth_pct':growth,'transaction_growth_pct':traffic_growth,
                              'eligible_restaurants':overall['eligible_restaurants']},
                  'finding':'Comparable-store sales increased while comparable-store transactions decreased.',
                  'investigate':'Check average check, channel mix, pricing and promotion activity; this does not establish cause.'})
        if comparison in ('yoy','previous'):
          for region in sorted({self.restaurants[rid]['region_id'] for rid in selected_ids}):
            r=self.comparable_sales(start,end,mode=comparison,region_id=region,restaurant_ids=selected_ids)
            if r['comparable_store_transaction_growth_pct'] is not None and r['comparable_store_transaction_growth_pct'] < -0.045:
                findings.append({'kind':'regional_traffic_decline','scope':region,'severity':'watch',
                'evidence':{'transaction_growth_pct':r['comparable_store_transaction_growth_pct'],
                            'eligible_restaurants':r['eligible_restaurants']},
                'finding':'Transactions declined materially versus the aligned comparison period.',
                'investigate':'Review location cohorts, local marketing, competitive conditions and operational changes.'})
        # A valid menu diagnosis must compare the same item with complete, matched store-week coverage.
        if comparison=='yoy':
            weeks=len(self._weeks(start,end)); pstart=start-timedelta(days=364);pend=end-timedelta(days=364)
            cohort=self.comparable_sales(start,end,mode='yoy',restaurant_ids=selected_ids)['restaurant_ids']
            cur=self.menu_summary(start,end,restaurant_ids=cohort)
            old=self.menu_summary(pstart,pend,restaurant_ids=cohort)
            if cohort and cur['complete'] and old['complete']:
                old_by_id={x['menu_item_id']:x for x in old['items']}
                for x in cur['items']:
                    olditem=old_by_id.get(x['menu_item_id'])
                    if olditem and olditem['net_sales_usd']>0 and x['net_sales_usd']/olditem['net_sales_usd']-1 < -0.2:
                        findings.append({'kind':'menu_item_decline','scope':x['menu_item_id'],'severity':'watch',
                        'evidence':{'net_sales_growth_pct':x['net_sales_usd']/olditem['net_sales_usd']-1},
                        'finding':f'{x["menu_item_name"]} sales decreased versus the aligned prior period.',
                        'investigate':'Review availability, menu placement, pricing and possible substitution; not a causal conclusion.'})
        return findings
