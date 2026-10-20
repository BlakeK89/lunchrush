"""Regression and deliberately bad-input tests. Run: python -m unittest discover -s tests -v"""
from __future__ import annotations
import copy,json,unittest
from collections import defaultdict
from datetime import date,timedelta
from decimal import Decimal
from pathlib import Path

from generate_demo import create,WEEKS,SEED
from lunch_rush import Analytics,validate

ROOT=Path(__file__).resolve().parents[1]
SCHEMA=json.loads((ROOT/'schema.json').read_text())

class TestLunchRush(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw=create();cls.valid=validate(cls.raw,SCHEMA);cls.analytics=Analytics(cls.valid)

    def mutated(self,tab,index,updates):
        t=dict(self.raw)
        t[tab]=list(t[tab]);t[tab][index]={**t[tab][index],**updates}
        return t

    def test_schema_and_provenance(self):
        self.assertEqual(self.valid.errors,[])
        self.assertEqual(len(self.valid.tables['Restaurant_Master']),40)
        self.assertEqual(len(self.valid.tables['Menu_Master']),19)
        self.assertEqual(len(set(x['region_id'] for x in self.raw['Restaurant_Master'])),4)
        self.assertEqual(len(WEEKS),104)
        self.assertEqual(WEEKS[0],date(2024,10,27))
        self.assertEqual(WEEKS[-1],date(2026,10,18))
        self.assertTrue(all('synthetic' in x['origin_description'].lower() or 'fictional' in x['origin_description'].lower() for x in self.raw['Source_Log']))
        self.assertTrue(any(x['coverage_status']=='Partial' for x in self.valid.tables['Store_Week_Status']))

    def test_independent_totals_and_channel_daypart(self):
        a=self.analytics;start,end,_,_=a.period(weeks=4)
        t=a.sales_summary(start,end)
        raw_status={(s['restaurant_id'],s['week_end']):s for s in self.valid.tables['Store_Week_Status']}
        rows=[r for r in self.valid.tables['Sales_Weekly'] if start<=r['week_end']<=end and
              raw_status[(r['restaurant_id'],r['week_end'])]['coverage_status']=='Complete']
        expected_cents=sum(r['net_sales_usd'] for r in rows)
        expected_tx=sum(r['transaction_count'] for r in rows)
        self.assertEqual(round(t['net_sales_usd']*100),expected_cents)
        self.assertEqual(t['transactions'],expected_tx)
        self.assertAlmostEqual(t['average_check_usd'],t['net_sales_usd']/t['transactions'],places=4)
        channel_sums=sum(a.sales_summary(start,end,channel=c)['net_sales_usd'] for c in
                ('Drive-Thru','Dine-In','Pickup','Delivery','Other'))
        self.assertAlmostEqual(channel_sums,t['net_sales_usd'],places=2)
        daypart_sums=sum(a.sales_summary(start,end,daypart=c)['net_sales_usd'] for c in
                ('Breakfast','Lunch','Dinner','Late Night','Other'))
        self.assertAlmostEqual(daypart_sums,t['net_sales_usd'],places=2)

    def test_menu_no_double_count_and_reconcile(self):
        a=self.analytics;start,end,_,_=a.period(weeks=13)
        menu=a.menu_summary(start,end);sales=a.sales_summary(start,end)
        self.assertTrue(menu['complete']);self.assertTrue(sales['complete'])
        self.assertEqual(round(menu['menu_total_usd']*100),round(sales['net_sales_usd']*100))
        self.assertAlmostEqual(sum(r['mix_pct'] for r in menu['items']),1,places=8)
        with self.assertRaises(TypeError):
            a.menu_summary(start,end,channel='Delivery')

    def test_comparable_fixed_cohort_and_disruption(self):
        a=self.analytics;start,end,_,_=a.period(weeks=13)
        c=a.comparable_sales(start,end)
        self.assertTrue(0<c['eligible_restaurants']<40)
        self.assertNotIn('R018',c['restaurant_ids'])
        self.assertTrue(c['comparable_store_transaction_growth_pct']<0)
        cur=prev=0
        for rid in c['restaurant_ids']:
            for week in a._weeks(start,end):
                cur+=sum(r['net_sales_usd'] for r in a.sales[(rid,week)])
                prev+=sum(r['net_sales_usd'] for r in a.sales[(rid,week-timedelta(days=364))])
        self.assertEqual(c['current_sales_usd'],round(cur/100,2))
        self.assertEqual(c['prior_sales_usd'],round(prev/100,2))
        self.assertAlmostEqual(c['comparable_store_sales_growth_pct'],cur/prev-1,places=12)
        # A new restaurant may lift all-store revenue but not enter the SSS cohort.
        self.assertNotAlmostEqual(a.compare_sales(start,end)['sales_growth_pct'],c['comparable_store_sales_growth_pct'],places=3)

    def test_scenarios_diagnostics(self):
        a=self.analytics;start,end,_,_=a.period(weeks=13)
        kinds={(d['kind'],d['scope']) for d in a.diagnostics(start,end)}
        self.assertIn(('traffic_check_divergence','Matched comparable stores'),kinds)
        self.assertIn(('regional_traffic_decline','MIDWEST'),kinds)
        self.assertIn(('menu_item_decline','M002'),kinds)
        self.assertTrue(all('investigate' in d and d['finding'] for d in a.diagnostics(start,end)))
        # Supplied incomplete status is never interpreted as true zero.
        start=date(2026,6,28);tot=a.sales_summary(start,start,restaurant_ids={'R009'})
        self.assertFalse(tot['complete']);self.assertEqual(tot['incomplete_store_weeks'],1)
        c=a.compare_sales(start,start,restaurant_ids={'R009'})
        self.assertIsNone(c['sales_growth_pct']);self.assertIn('Incomplete',c['reason'])

    def test_location_ranking_and_full_year_auv(self):
        a=self.analytics;start,end,_,_=a.period(weeks=13)
        ranks=a.location_rankings(start,end)
        self.assertNotIn('R018',[x['restaurant_id'] for x in ranks['restaurants']])
        self.assertEqual(ranks['restaurants'][0]['rank'],1)
        self.assertTrue(all(ranks['restaurants'][i]['net_sales_usd']>=ranks['restaurants'][i+1]['net_sales_usd']
                            for i in range(len(ranks['restaurants'])-1)))
        auv=a.average_unit_volume()
        self.assertLess(auv['eligible_restaurants'],40)
        self.assertGreater(auv['average_unit_volume_usd'],1000000)
        self.assertEqual(auv['period_end'],date(2026,10,18))

    def test_new_item_attach_rate_not_guessed(self):
        a=self.analytics;start,end,_,_=a.period(weeks=52)
        m=a.menu_summary(start,end)
        honey=next(r for r in m['items'] if r['menu_item_id']=='M019')
        self.assertIsNone(honey['attach_rate']) # absent before first introduction, not zero

    def test_region_aggregation_reconciles(self):
        a=self.analytics;start,end,_,_=a.period(weeks=13)
        by_region=sum(a.sales_summary(start,end,region_id=r)['net_sales_usd']
            for r in ('WEST','SOUTHWEST','MIDWEST','SOUTHEAST'))
        self.assertAlmostEqual(by_region,a.sales_summary(start,end)['net_sales_usd'],places=2)

    def test_duplicate_key_rejected(self):
        t=dict(self.raw);t['Sales_Weekly']=list(t['Sales_Weekly'])+[dict(t['Sales_Weekly'][0])]
        self.assertTrue(any('duplicate key' in e for e in validate(t,SCHEMA).errors))

    def test_non_sunday_week_rejected(self):
        t=self.mutated('Sales_Weekly',0,{'week_end':'2024-10-28'})
        self.assertTrue(any('non-Sunday' in e for e in validate(t,SCHEMA).errors))

    def test_unreconciled_pos_row_rejected(self):
        row=self.raw['Sales_Weekly'][0]
        t=self.mutated('Sales_Weekly',0,{'net_sales_usd':f"{Decimal(row['net_sales_usd'])+Decimal('1.00'):.2f}"})
        self.assertTrue(any('net-sales mismatch' in e for e in validate(t,SCHEMA).errors))

    def test_unreconciled_menu_week_rejected(self):
        row=self.raw['Menu_Weekly'][0]
        t=self.mutated('Menu_Weekly',0,{'item_net_sales_usd':f"{Decimal(row['item_net_sales_usd'])+Decimal('5.00'):.2f}"})
        self.assertTrue(any('menu/POS reconciliation' in e for e in validate(t,SCHEMA).errors))

    def test_invalid_source_rejected(self):
        t=self.mutated('Sales_Weekly',0,{'source_id':'NOT-LOGGED'})
        self.assertTrue(any('missing source' in e for e in validate(t,SCHEMA).errors))

    def test_missing_source_log_and_header_rejected(self):
        t=dict(self.raw);t.pop('Source_Log')
        self.assertTrue(any('missing required sheet' in e for e in validate(t,SCHEMA).errors))
        t=dict(self.raw);t['Menu_Master']=[dict(x) for x in t['Menu_Master']]; t['Menu_Master'][0]['random_field']='oops'
        self.assertTrue(any('column headers/order' in e for e in validate(t,SCHEMA).errors))

if __name__=='__main__':unittest.main()
