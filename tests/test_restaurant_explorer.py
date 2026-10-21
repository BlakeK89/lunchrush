"""Correctness checks for customizable restaurant + region breakdowns."""
from __future__ import annotations
import json
import unittest
from pathlib import Path

from lunch_rush.engine import Analytics, validate
from lunch_rush.io import load_csv_tabs
from lunch_rush.restaurant_explorer import comparison_frame, scoped_restaurants, METRICS

ROOT = Path(__file__).resolve().parents[1]


class RestaurantComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        schema=json.loads((ROOT/'schema.json').read_text())
        data={p.stem:p.read_bytes() for p in (ROOT/'data/demo').glob('*.csv')}
        v=validate(load_csv_tabs(data),schema)
        v.assert_valid()
        cls.engine=Analytics(v)
        cls.end=max(s['week_end'] for s in cls.engine.data['Store_Week_Status'])
        from datetime import timedelta
        cls.start=cls.end-timedelta(weeks=12)
        cls.ids=sorted(cls.engine.restaurants)

    def test_multiple_regions_and_restaurants_intersect(self):
        a=self.engine
        regions=sorted({a.restaurants[x]['region_id'] for x in self.ids})
        subset=scoped_restaurants(a,self.ids,regions[:2])
        self.assertTrue(subset)
        self.assertTrue(all(a.restaurants[x]['region_id'] in regions[:2] for x in subset))
        some=subset[:3]
        self.assertEqual(scoped_restaurants(a,self.ids,regions[:2],some),some)
        self.assertEqual(scoped_restaurants(a,self.ids,[],some),some)
        self.assertEqual(scoped_restaurants(a,self.ids),self.ids)
        self.assertEqual(scoped_restaurants(a,self.ids,regions[-1:],some),[])

    def test_region_aggregation_recomputes_not_averages_growth(self):
        a=self.engine; ids=self.ids[:8]
        table=comparison_frame(a,self.start,self.end,ids,'yoy',group_by='Region',metrics=METRICS)
        self.assertEqual(len(table),len({a.restaurants[x]['region_name'] for x in ids}))
        current=a.sales_summary(self.start,self.end,restaurant_ids=ids)
        self.assertAlmostEqual(table['Net Sales'].sum(),current['net_sales_usd'],places=2)
        self.assertEqual(table['Transactions'].sum(),current['transactions'])
        self.assertAlmostEqual((table['Net Sales'].sum()/table['Transactions'].sum()),current['average_check_usd'],places=2)
        for _,row in table.iterrows():
            members=[rid for rid in ids if a.restaurants[rid]['region_name']==row['Region']]
            expected=a.compare_sales(self.start,self.end,mode='yoy',restaurant_ids=members)
            self.assertEqual(row['Net Sales'],expected['current']['net_sales_usd'])
            self.assertEqual(row['Transactions'],expected['current']['transactions'])
            if expected['reason'] is None:
                self.assertAlmostEqual(row['Sales Change'],100*expected['sales_growth_pct'],places=6)

    def test_nested_details_and_scope_cover_all_selected_once(self):
        a=self.engine; ids=self.ids[:9]
        table=comparison_frame(a,self.start,self.end,ids,'previous',group_by='Region → Restaurant',metrics=METRICS)
        self.assertEqual(len(table),len(ids))
        self.assertEqual(set(table['Restaurant']),{f'{a.restaurants[rid]["restaurant_name"]} ({rid})' for rid in ids})
        self.assertEqual(table['Region'].tolist(),sorted(table['Region'].tolist()))
        self.assertAlmostEqual(table['Sales Mix'].sum(),100,places=5)

    def test_no_comparison_and_all_metrics_removed(self):
        a=self.engine
        rows=comparison_frame(a,self.start,self.end,self.ids[:2],'none',metrics=['Transactions'])
        self.assertTrue(all(x in rows.columns for x in ('Restaurant','Transactions','Reporting')))
        self.assertNotIn('Sales Change',rows.columns)
        no_metrics=comparison_frame(a,self.start,self.end,self.ids[:2],'none',metrics=[])
        self.assertEqual(len(no_metrics),2)
        with self.assertRaises(ValueError):
            comparison_frame(a,self.start,self.end,self.ids[:2],'yoy',metrics=['COGS'])

    def test_incomplete_or_disrupted_location_remains_visible(self):
        a=self.engine
        rows=comparison_frame(a,self.start,self.end,self.ids,'yoy',metrics=['Net Sales','Sales Change'])
        self.assertEqual(len(rows),len(self.ids))
        # Each location must appear, even if ranked eligibility excludes it.
        for rid in self.ids:
            self.assertTrue(any(s.endswith(f'({rid})') for s in rows['Restaurant']))
        self.assertTrue(set(rows['Reporting']).issubset({'Complete','Incomplete data','Disrupted / partial','Partial period','Not yet open'}))


if __name__=='__main__': unittest.main()
