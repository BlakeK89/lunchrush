"""Independent UI-helper and upload tests. These run without Streamlit installed."""
from __future__ import annotations
import io
import json
from pathlib import Path
import unittest
import zipfile

from lunch_rush import Analytics, validate
from lunch_rush.io import load_csv_tabs
from lunch_rush.ui_metrics import (
    category_summary, format_money, format_pct, matched_menu_growth,
    mix_breakdown, restaurant_table, scope_ids, week_series,
)
from lunch_rush.upload import parse_upload

ROOT=Path(__file__).resolve().parents[1]
SCHEMA=json.loads((ROOT/'schema.json').read_text())


class TestUIMetrics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files={p.stem:p.read_bytes() for p in (ROOT/'data/demo').glob('*.csv')}
        cls.valid=validate(load_csv_tabs(cls.files),SCHEMA)
        cls.valid.assert_valid()
        cls.a=Analytics(cls.valid)
        cls.start,cls.end,_,_=cls.a.period(weeks=13)

    def test_demo_names_do_not_include_rejected_brand(self):
        names={r['restaurant_name'] for r in self.a.restaurants.values()}
        self.assertTrue('Costa Mesa' in names)
        self.assertTrue(all('Crispy Junction' not in n for n in names))

    def test_scope_breakdown_and_weekly_reconcile(self):
        ids=scope_ids(self.a)
        current=self.a.sales_summary(self.start,self.end,restaurant_ids=ids)
        weekly=week_series(self.a,self.start,self.end,ids)
        self.assertEqual(len(weekly),13)
        self.assertEqual(round(sum(r['net_sales_usd'] for r in weekly)*100),round(current['net_sales_usd']*100))
        channels=mix_breakdown(self.a,self.start,self.end,ids,by='channel')
        days=mix_breakdown(self.a,self.start,self.end,ids,by='daypart')
        self.assertEqual(round(sum(r['net_sales_usd'] for r in channels)*100),round(current['net_sales_usd']*100))
        self.assertEqual(round(sum(r['net_sales_usd'] for r in days)*100),round(current['net_sales_usd']*100))
        with self.assertRaises(ValueError):mix_breakdown(self.a,self.start,self.end,ids,by='item')

    def test_restaurant_cohort_and_region_filter(self):
        ids=scope_ids(self.a,region='MIDWEST')
        self.assertEqual(len(ids),10)
        ranks=restaurant_table(self.a,self.start,self.end,ids)
        self.assertEqual(len(ranks['restaurants'])+len(ranks['excluded_restaurants']),10)
        self.assertTrue(all(row['region']=='Midwest' for row in ranks['restaurants']))
        self.assertEqual([row['rank'] for row in ranks['restaurants']],list(range(1,len(ranks['restaurants'])+1)))
        signals=self.a.diagnostics(self.start,self.end,restaurant_ids=ids)
        self.assertFalse(any(x['kind']=='regional_traffic_decline' and x['scope']!='MIDWEST' for x in signals))

    def test_menu_growth_and_category_totals(self):
        menu=self.a.menu_summary(self.start,self.end)
        cats=category_summary(menu)
        self.assertEqual(round(sum(x['net_sales_usd'] for x in cats)*100),round(menu['menu_total_usd']*100))
        delta=matched_menu_growth(self.a,self.start,self.end,scope_ids(self.a),'yoy')
        self.assertLess(delta['M002'],-.2)
        self.assertEqual(matched_menu_growth(self.a,self.start,self.end,scope_ids(self.a),'none'),{})

    def test_display_formats(self):
        self.assertEqual(format_pct(-.0517),'-5.2%')
        self.assertEqual(format_money(None),'N/A')
        self.assertEqual(format_money(24000000,compact=True),'$24.00M')

    def test_upload_csv_zip(self):
        src=io.BytesIO()
        with zipfile.ZipFile(src,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            for name,data in self.files.items(): archive.writestr(name+'.csv',data)
        payload=parse_upload('uploads.zip',src.getvalue(),SCHEMA)
        valid=validate(payload,SCHEMA)
        self.assertEqual(valid.errors,[])
        self.assertEqual(len(valid.tables['Restaurant_Master']),40)

    def test_zip_rejects_traversal_and_wrong_file(self):
        data=io.BytesIO()
        with zipfile.ZipFile(data,'w') as z:z.writestr('../Restaurant_Master.csv',b'abc')
        with self.assertRaisesRegex(ValueError,'top level'):
            parse_upload('bad.zip',data.getvalue(),SCHEMA)
        with self.assertRaises(ValueError):parse_upload('bad.json',b'{}',SCHEMA)


if __name__=='__main__':unittest.main()
