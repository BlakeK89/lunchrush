"""Headless view-flow smoke test with a Streamlit stub.

Does not replace an actual Streamlit/browser render test. Catches Python-level
app-flow, Plotly and dataframe errors without the Streamlit package.
"""
from __future__ import annotations
import runpy
import sys
from types import ModuleType
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class FakeStreamlit(ModuleType):
    def __init__(self,view):
        super().__init__('streamlit')
        self.view=view
        self.sidebar=self
        self.session_state={}
        self.figures=0
        self.tables=0
        self.metrics=0

    def __enter__(self):return self
    def __exit__(self,*_):return False
    def cache_resource(self,**kwargs):return lambda fn:fn
    def set_page_config(self,**kwargs):pass
    def columns(self,widths):return [self for _ in range(widths if isinstance(widths,int) else len(widths))]
    def selectbox(self,label,options,index=0,**kwargs):return options[index]
    def radio(self,label,options,index=0,**kwargs):
        return self.view if label=='Explore' else options[index]
    def multiselect(self,*args,**kwargs):return []
    def metric(self,*args,**kwargs):self.metrics+=1
    def plotly_chart(self,figure,*args,**kwargs):
        self.figures+=1
        figure.to_dict() # Ensure a complete, serializable chart config
    def dataframe(self,*args,**kwargs):self.tables+=1
    def expander(self,*args,**kwargs):return self
    def container(self,*args,**kwargs):return self
    def stop(self):raise AssertionError('Unexpected st.stop()')
    def __getattr__(self,name):
        return lambda *args,**kwargs:None


class TestAppFlows(unittest.TestCase):
    def test_all_five_views(self):
        previous=sys.modules.get('streamlit')
        try:
            for view in ['Overview','Restaurants','Channels & Dayparts','Menu Performance','Insights']:
                with self.subTest(view=view):
                    stub=FakeStreamlit(view)
                    sys.modules['streamlit']=stub
                    runpy.run_path(str(ROOT/'app.py'),run_name='__main__')
                    self.assertTrue(stub.figures or stub.tables or view=='Insights')
        finally:
            if previous is None:sys.modules.pop('streamlit',None)
            else:sys.modules['streamlit']=previous


if __name__=='__main__':unittest.main()
