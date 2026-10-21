"""Headless application smoke tests for the Shelf Life-inspired Lunch Rush UI.

Tests import/run the entire Streamlit app with a small public-API stub. They do
not replace a browser-rendered test on Streamlit Community Cloud.
"""
from __future__ import annotations
import runpy
import sys
from types import ModuleType
from pathlib import Path
import unittest
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]


class FakeStreamlit(ModuleType):
    def __init__(self, *, comparison='Same Period Last Year (YoY)', period='Last 13 Weeks (L13W)'):
        super().__init__('streamlit')
        self.sidebar = self
        self.column_config = SimpleNamespace(
            NumberColumn=lambda *args,**kwargs:dict(args=args,kwargs=kwargs),
            TextColumn=lambda *args,**kwargs:dict(args=args,kwargs=kwargs),
        )
        self.session_state = {}
        self.comparison, self.period = comparison, period
        self.figures = 0
        self.tables = 0
        self.dataframes = []
        self.metrics = 0
        self.tabs_created = []
        self.chart_traces = []
        self.warnings = []
        self.downloads = []
        self.markdown_texts = []
        self.captions = []

    def __enter__(self):return self
    def __exit__(self,*_):return False
    def cache_resource(self,**kwargs):return lambda fn:fn
    def cache_data(self,**kwargs):return lambda fn:fn
    def download_button(self,label,data,**kwargs):
        self.downloads.append((label,data,kwargs));return False
    def markdown(self,text,*args,**kwargs):self.markdown_texts.append(text)
    def caption(self,text,*args,**kwargs):self.captions.append(text)
    def set_page_config(self,**kwargs):pass
    def columns(self,widths,**kwargs):return [self for _ in range(widths if isinstance(widths,int) else len(widths))]
    def tabs(self,names):
        self.tabs_created = list(names)
        return [self for _ in names]
    def selectbox(self,label,options,index=0,**kwargs):
        if label=='Reporting Period':return self.period
        if label=='Compare Against':return self.comparison
        return options[index]
    def radio(self,label,options,index=0,**kwargs):return options[index]
    def date_input(self,label,**kwargs):return kwargs['value']
    def multiselect(self,*args,**kwargs):return []
    def metric(self,*args,**kwargs):self.metrics+=1
    def plotly_chart(self,figure,*args,**kwargs):
        self.figures+=1
        self.chart_traces.append(figure.to_dict())
    def dataframe(self,*args,**kwargs):
        self.tables+=1
        self.dataframes.append((args[0],kwargs))
    def expander(self,*args,**kwargs):return self
    def container(self,*args,**kwargs):return self
    def stop(self):raise AssertionError('Unexpected st.stop()')
    def button(self,*args,**kwargs):return False
    def warning(self,*args,**kwargs):self.warnings.append(args[0])
    def __getattr__(self,name):return lambda *args,**kwargs:None


class TestAppFlows(unittest.TestCase):
    def run_app(self,**kwargs):
        previous=sys.modules.get('streamlit')
        try:
            stub=FakeStreamlit(**kwargs)
            sys.modules['streamlit']=stub
            runpy.run_path(str(ROOT/'app.py'),run_name='__main__')
            return stub
        finally:
            if previous is None:sys.modules.pop('streamlit',None)
            else:sys.modules['streamlit']=previous

    def test_all_five_tabs_render(self):
        stub=self.run_app()
        self.assertEqual(stub.tabs_created,['Overview','Restaurants','Channels & Dayparts','Menu Performance','Insights'])
        self.assertGreaterEqual(stub.figures, 5)
        self.assertGreaterEqual(stub.tables, 4)
        self.assertGreaterEqual(stub.metrics, 12)
        self.assertEqual(len(stub.warnings),0)
        self.assertEqual(len(stub.downloads),3)
        self.assertTrue(any('Chicken Coop' in row[0] for row in stub.downloads))

    def test_demo_download_round_trips(self):
        import json
        from lunch_rush.upload import parse_upload
        from lunch_rush.engine import validate
        stub=self.run_app()
        label,data,kwargs=stub.downloads[0]
        self.assertEqual(kwargs['file_name'],'The_Chicken_Coop_Sample_Data.zip')
        schema=json.loads((ROOT/'schema.json').read_text())
        checked=validate(parse_upload(kwargs['file_name'],data,schema),schema)
        self.assertEqual(checked.errors,[])
        self.assertEqual(len(checked.tables['Restaurant_Master']),40)

    def test_comparison_legend_outside_plots(self):
        stub=self.run_app()
        self.assertTrue(any('lr-chart-key' in text for text in stub.markdown_texts))
        # All plotly charts should have built-in legend hidden.
        self.assertFalse(stub.chart_traces[1]['layout'].get('showlegend',True))

    def test_data_tables_sort_numerically_and_do_not_show_blank_padding(self):
        import pandas as pd
        stub=self.run_app()
        money_tables=[(df,kws) for df,kws in stub.dataframes
                      if isinstance(df,pd.DataFrame) and 'Net Sales' in df.columns]
        self.assertGreaterEqual(len(money_tables),4)
        for df,kws in money_tables:
            self.assertTrue(pd.api.types.is_numeric_dtype(df['Net Sales']),str(df.columns))
        segments=[(df,kws) for df,kws in money_tables if 'Segment' in df.columns]
        self.assertEqual([len(df) for df,_ in segments],[4,3])
        self.assertEqual([kws['height'] for _,kws in segments],[185,150])

    def test_number_grouping_and_readable_column_widths(self):
        stub = self.run_app()
        tables = [(df, kws) for df, kws in stub.dataframes if 'Net Sales' in df.columns]
        self.assertGreaterEqual(len(tables), 4)
        for df, kwargs in tables:
            net_sales = kwargs['column_config']['Net Sales']['kwargs']
            self.assertEqual(net_sales['format'], '$%,.0f')
            self.assertGreaterEqual(net_sales['width'], 125)
            self.assertTrue(df['Net Sales'].dtype.kind in 'fi')
        channels = [(df,kws) for df,kws in tables if 'Segment' in df.columns]
        self.assertEqual([len(df) for df,_ in channels], [4,3])
        for df,kws in channels:
            configs = kws['column_config']
            self.assertEqual(configs['Transactions']['kwargs']['format'], '%,d')
            self.assertEqual(configs['Average Check']['kwargs']['format'], '$%,.2f')
            self.assertGreaterEqual(configs['Transaction Change']['kwargs']['width'], 150)
            self.assertEqual(kws['use_container_width'], True)

    def test_plain_english_labels_and_exclusion_reasons(self):
        stub = self.run_app()
        captions = ' '.join(map(str, stub.captions))
        self.assertIn('Same-store comparisons use the same', captions)
        self.assertIn('Average sales per restaurant over the past year:', captions)
        self.assertIn('menu-item sales add up', captions)
        self.assertIn('percentage of orders that included an item', captions)
        self.assertIn('Menu-item growth compares sales', captions)
        self.assertIn('Each row shows how that restaurant performed', captions)
        reasons = [df for df, _ in stub.dataframes if 'Reason' in df.columns]
        self.assertTrue(reasons)
        self.assertTrue(all('_' not in reason and len(reason.split()) > 7
                            for df in reasons for reason in df['Reason']))
        self.assertTrue(any('open 3 of 7 days' in reason and 'operating disruption recorded' in reason
                            for df in reasons for reason in df['Reason']))

    def test_pie_chart_hover_text_is_larger(self):
        stub = self.run_app()
        pies = [f for f in stub.chart_traces
                if any(trace.get('type') == 'pie' for trace in f.get('data', []))]
        self.assertEqual(len(pies), 2)
        for fig in pies:
            hover = fig['layout']['hoverlabel']
            self.assertGreaterEqual(hover['font']['size'], 16)
            self.assertIn('Net sales:', fig['data'][0]['hovertemplate'])

    def test_previous_period(self):
        stub=self.run_app(comparison='Previous Equivalent Period')
        self.assertEqual(len(stub.tabs_created),5)
        self.assertGreater(stub.figures,3)

    def test_without_comparison(self):
        stub=self.run_app(comparison='No Comparison')
        self.assertEqual(len(stub.tabs_created),5)
        self.assertGreater(stub.figures,3)

    def test_custom_date_range(self):
        stub=self.run_app(period='Custom Date Range')
        self.assertEqual(len(stub.tabs_created),5)
        self.assertGreater(stub.figures,3)

    def test_year_to_date(self):
        stub=self.run_app(period='Year to Date (YTD)')
        self.assertEqual(len(stub.tabs_created),5)
        self.assertGreater(stub.figures,3)


if __name__=='__main__':unittest.main()
