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
        self.grids = []
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
        previous_ag=sys.modules.get('st_aggrid')
        previous_grid=sys.modules.pop('lunch_rush.grids',None)
        try:
            stub=FakeStreamlit(**kwargs)
            ag_stub=ModuleType('st_aggrid')
            ag_stub.JsCode=lambda code: {'javascript':code}
            ag_stub.AgGrid=lambda frame,**opts:stub.grids.append((frame,opts))
            sys.modules['streamlit']=stub
            sys.modules['st_aggrid']=ag_stub
            runpy.run_path(str(ROOT/'app.py'),run_name='__main__')
            return stub
        finally:
            if previous is None:sys.modules.pop('streamlit',None)
            else:sys.modules['streamlit']=previous
            if previous_ag is None:sys.modules.pop('st_aggrid',None)
            else:sys.modules['st_aggrid']=previous_ag
            sys.modules.pop('lunch_rush.grids',None)
            if previous_grid is not None:sys.modules['lunch_rush.grids']=previous_grid

    def test_all_five_tabs_render(self):
        stub=self.run_app()
        self.assertEqual(stub.tabs_created,['Overview','Restaurants','Channels & Dayparts','Menu Performance','Insights'])
        self.assertGreaterEqual(stub.figures, 5)
        self.assertGreaterEqual(len(stub.grids), 6)
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
        money_tables=[(df,kws) for df,kws in stub.grids
                      if isinstance(df,pd.DataFrame) and 'Net Sales' in df.columns]
        self.assertGreaterEqual(len(money_tables),4)
        for df,kws in money_tables:
            self.assertTrue(pd.api.types.is_numeric_dtype(df['Net Sales']),str(df.columns))
        segments=[(df,kws) for df,kws in money_tables if 'Segment' in df.columns]
        self.assertEqual([len(df) for df,_ in segments],[4,3])
        self.assertEqual([kws['gridOptions'].get('domLayout') for _,kws in segments],['autoHeight','autoHeight'])

    def test_number_grouping_and_readable_column_widths(self):
        stub = self.run_app()
        tables = [(df, kws) for df, kws in stub.grids if 'Net Sales' in df.columns]
        self.assertGreaterEqual(len(tables), 4)
        for df, kwargs in tables:
            config = {x['field']:x for x in kwargs['gridOptions']['columnDefs']}
            self.assertIn('valueFormatter',config['Net Sales'])
            self.assertGreaterEqual(config['Net Sales']['minWidth'], 125)
            self.assertTrue(df['Net Sales'].dtype.kind in 'fi')
            self.assertTrue(all(x['sortable'] for x in config.values()))
            self.assertTrue(all(x['cellStyle'] for x in config.values()))
        channels = [(df,kws) for df,kws in tables if 'Segment' in df.columns]
        self.assertEqual([len(df) for df,_ in channels], [4,3])
        for df,kws in channels:
            config = {x['field']:x for x in kws['gridOptions']['columnDefs']}
            self.assertIn('valueFormatter',config['Transactions'])
            self.assertIn('valueFormatter',config['Average Check'])
            self.assertGreaterEqual(config['Transaction Change']['minWidth'],150)
            self.assertTrue(kws['allow_unsafe_jscode'])

    def test_plain_english_labels_and_exclusion_reasons(self):
        stub = self.run_app()
        captions = ' '.join(map(str, stub.captions))
        self.assertIn('Same-store comparisons use the same', captions)
        self.assertIn('Average sales per restaurant over the past year:', captions)
        self.assertIn('menu-item sales add up', captions)
        self.assertIn('percentage of orders that included an item', captions)
        self.assertIn('Menu-item growth compares sales', captions)
        self.assertIn('Each row shows how that restaurant performed', captions)
        reasons = [df for df, _ in stub.grids if 'Reason' in df.columns]
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

    def test_grid_centered_bold_and_comparison_colors(self):
        stub = self.run_app()
        self.assertGreaterEqual(len(stub.grids), 6)
        for df, kwargs in stub.grids:
            css = kwargs['custom_css']
            self.assertIn('center !important', css['.ag-header .ag-header-cell-label']['justify-content'])
            self.assertIn('750', css['.ag-header .ag-header-cell-text']['font-weight'])
            options = kwargs['gridOptions']
            self.assertTrue(all(col['headerClass'] == 'lr-center-header' for col in options['columnDefs']))
        ranked = [(df,kw) for df,kw in stub.grids if 'Sales Change' in df.columns and 'Restaurant' in df.columns]
        self.assertEqual(len(ranked), 1)
        ranked_columns = {c['field']:c for c in ranked[0][1]['gridOptions']['columnDefs']}
        self.assertIn('javascript', ranked_columns['Sales Change']['cellStyle'])
        self.assertIn('javascript', ranked_columns['Transaction Change']['cellStyle'])
        self.assertTrue(any('Selected period' in t for t in stub.markdown_texts))
        self.assertTrue(any('of sales' in t for t in stub.markdown_texts))
        self.assertFalse(any('These are measurable changes and investigative prompts' in t for t in stub.captions))

    def test_chart_text_colors(self):
        stub=self.run_app()
        for figure in stub.chart_traces:
            for axis in ('xaxis','yaxis'):
                if axis in figure['layout']:
                    self.assertEqual(figure['layout'][axis]['tickfont']['color'],'#081043')
                    self.assertEqual(figure['layout'][axis]['title']['font']['color'],'#081043')

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
