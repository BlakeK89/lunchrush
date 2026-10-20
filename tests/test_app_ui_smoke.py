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

ROOT = Path(__file__).resolve().parents[1]


class FakeStreamlit(ModuleType):
    def __init__(self, *, comparison='Same Period Last Year (YoY)', period='Last 13 Weeks (L13W)'):
        super().__init__('streamlit')
        self.sidebar = self
        self.session_state = {}
        self.comparison, self.period = comparison, period
        self.figures = 0
        self.tables = 0
        self.metrics = 0
        self.tabs_created = []
        self.chart_traces = []
        self.warnings = []

    def __enter__(self):return self
    def __exit__(self,*_):return False
    def cache_resource(self,**kwargs):return lambda fn:fn
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
    def dataframe(self,*args,**kwargs):self.tables+=1
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
