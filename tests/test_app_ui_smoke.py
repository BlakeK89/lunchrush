"""Headless Streamlit UI checks; real browser QA remains necessary."""
from __future__ import annotations
import runpy
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


class FakeStreamlit(ModuleType):
    def __init__(self, *, comparison='Same Period Last Year (YoY)', period='Last 13 Weeks (L13W)'):
        super().__init__('streamlit')
        self.sidebar = self
        self.column_config = SimpleNamespace(
            NumberColumn=lambda **kw: {'kind': 'numeric', **kw},
            TextColumn=lambda **kw: {'kind': 'text', **kw},
        )
        self.session_state = {}
        self.comparison, self.period = comparison, period
        self.figures, self.metrics = 0, 0
        self.tables, self.downloads = [], []
        self.captions, self.markdown_texts, self.info_texts, self.chart_traces = [], [], [], []
        self.tabs_created = []
        self.subheaders = []
        self.warnings = []
        self.expanders = []

    def __enter__(self): return self
    def __exit__(self,*_): return False
    def cache_resource(self,**kwargs): return lambda f:f
    def cache_data(self,**kwargs): return lambda f:f
    def set_page_config(self,**kwargs): pass
    def markdown(self,text,*args,**kwargs): self.markdown_texts.append(str(text))
    def caption(self,text,*args,**kwargs): self.captions.append(str(text))
    def info(self,text,*args,**kwargs): self.info_texts.append(str(text))
    def download_button(self,label,data,**kwargs):
        self.downloads.append((label,data,kwargs));return False
    def columns(self,n,**kwargs): return [self for _ in range(n if isinstance(n,int) else len(n))]
    def subheader(self,label,*args,**kwargs):
        self.subheaders.append(str(label))
    def tabs(self,names):
        self.tabs_created = list(names);return [self for _ in names]
    def selectbox(self,label,options,index=0,**kwargs):
        if label=='Reporting Period': return self.period
        if label=='Compare Against': return self.comparison
        return options[index]
    def radio(self,label,options,index=0,**kwargs): return options[index]
    def multiselect(self,*args,**kwargs): return []
    def date_input(self,*args,**kwargs): return kwargs['value']
    def metric(self,*args,**kwargs): self.metrics+=1
    def plotly_chart(self,figure,*args,**kwargs):
        self.figures+=1;self.chart_traces.append(figure.to_dict())
    def dataframe(self,styled,*args,**kwargs): self.tables.append((styled,kwargs))
    def html(self,markup,*args,**kwargs): self.tables.append((markup,kwargs))
    def expander(self,label,*args,**kwargs):
        self.expanders.append(str(label));return self
    def container(self,*args,**kwargs): return self
    def warning(self,text,*args,**kwargs):self.warnings.append(str(text))
    def stop(self):raise AssertionError('Unexpected st.stop()')
    def __getattr__(self,name):return lambda *a,**kw: None


class TestAppFlows(unittest.TestCase):
    def run_app(self, **kwargs):
        old_st=sys.modules.get('streamlit')
        old_grids=sys.modules.pop('lunch_rush.grids', None)
        try:
            stub=FakeStreamlit(**kwargs)
            sys.modules['streamlit']=stub
            runpy.run_path(str(ROOT/'app.py'), run_name='__main__')
            return stub
        finally:
            if old_st is None:sys.modules.pop('streamlit',None)
            else:sys.modules['streamlit']=old_st
            sys.modules.pop('lunch_rush.grids',None)
            if old_grids is not None:sys.modules['lunch_rush.grids']=old_grids

    def test_all_tabs_tables_and_charts_render(self):
        st=self.run_app()
        self.assertEqual(st.tabs_created,['Overview','Restaurants','Channels & Dayparts','Menu Performance'])
        self.assertGreaterEqual(st.figures,5)
        self.assertGreaterEqual(len(st.tables),6)
        self.assertGreaterEqual(st.metrics,11)
        self.assertEqual(st.warnings,[])
        self.assertEqual(len(st.downloads),3)
        self.assertTrue(all('<table>' in html for html,_ in st.tables))
        self.assertTrue(all(opts.get('unsafe_allow_javascript') for _,opts in st.tables))

    def test_real_html_headers_centered_and_sortable(self):
        import re
        from html import unescape
        st=self.run_app()
        for markup,kw in st.tables:
            self.assertEqual(kw['width'],'stretch')
            self.assertIn('text-align:center !important',markup)
            self.assertIn('font-weight:800',markup)
            self.assertIn('body.replaceChildren(...rows)',markup)
            self.assertNotIn('ag-cell-value',markup)
            headers=re.findall(r'<th\b[^>]*>.*?</th>', markup, re.S)
            rows=re.findall(r'<tr>(.*?)</tr>', markup.partition('<tbody>')[2].partition('</tbody>')[0], re.S)
            self.assertTrue(headers)
            self.assertTrue(all('<button' in h and 'lr-sort-button' in h for h in headers))
            self.assertTrue(all(len(re.findall(r'<td\b', row))==len(headers) for row in rows))
            if 'data-missing="1"' in markup:
                self.assertIn('>—</td>',markup)
        restaurant=[html for html,_ in st.tables if 'id="lr-html-lr-restaurant-rankings"' in html]
        self.assertEqual(len(restaurant),1)
        restaurant_headers=re.findall(r'<th\b[^>]*>.*?</th>',restaurant[0],re.S)
        labels=[unescape(re.search(r'<span>(.*?)</span>',h).group(1)) for h in restaurant_headers]
        self.assertEqual(labels[:4],['Rank','Restaurant','Net Sales','Sales Change'])
        self.assertIn('lr-pinned',restaurant[0]);self.assertIn('data-kind="number"',restaurant[0])
        item=[html for html,_ in st.tables if 'id="lr-html-lr-menu-items"' in html]
        self.assertEqual(len(item),1)
        self.assertIn('Same-Store Item Growth',item[0])
        self.assertIn('lr-pinned',item[0])

    def test_short_tables_fully_visible_and_category_mix_full_width(self):
        import re
        st=self.run_app()
        def table_for(key):
            return next(markup for markup,_ in st.tables if f'id="lr-html-{key}"' in markup)
        channels=table_for('lr-channel-breakdown')
        daypart=table_for('lr-daypart-breakdown')
        categories=table_for('lr-menu-categories')
        def rows(markup):
            return len(re.findall(r'<tr>',markup.partition('<tbody>')[2].partition('</tbody>')[0]))
        self.assertEqual(rows(channels),4)
        self.assertEqual(rows(daypart),3)
        self.assertIn('max-height:188px',channels)
        self.assertIn('max-height:152px',daypart)
        self.assertEqual(rows(categories),8)
        self.assertIn('width:100%', categories)

    def test_plain_english_diagnostics_and_reconciliation(self):
        st=self.run_app()
        body=' '.join(st.markdown_texts+' '.join(st.captions).splitlines()+st.info_texts)
        self.assertIn('Worth investigating: Orders at established restaurants fell',body)
        self.assertIn('What to check:',body)
        self.assertIn('Menu-item growth compares',body)
        self.assertIn('Menu Items to Review',body)
        self.assertIn('Data quality and reporting details', ' '.join(st.expanders))
        ex=[html for html,k in st.tables if 'id="lr-html-lr-restaurant-exclusions"' in html]
        self.assertEqual(len(ex),1)
        self.assertIn('open 3 of 7 days',ex[0])

    def test_insights_routed_to_relevant_tabs(self):
        st=self.run_app()
        body=' '.join(st.markdown_texts + st.info_texts)
        self.assertNotIn('Insights',st.tabs_created)
        self.assertIn('Regional Trends to Review',st.subheaders)
        self.assertIn('Menu Items to Review',body)
        self.assertIn('What to check:',body)
        self.assertIn('Data quality and reporting details',st.expanders)
        self.assertIn('Spicy Crispy Sandwich',body)
        self.assertIn('Midwest',body)
        self.assertIn('West',body)
        self.assertIn('Ordering-channel changes worth reviewing',body)

    def test_sidebar_borders_and_dark_table_text(self):
        theme=(ROOT/'lunch_rush/theme.py').read_text()
        self.assertIn('stSidebar"] [data-testid="stExpander"] {',theme)
        self.assertIn('border:1.5px solid rgba(255,255,255,.9) !important',theme)
        st=self.run_app()
        tables={key:next(markup for markup,_ in st.tables if f'id="lr-html-{key}"' in markup)
                for key in ('lr-restaurant-rankings','lr-menu-items','lr-data-quality')}
        for key in ('lr-restaurant-rankings','lr-menu-items'):
            table=tables[key]
            self.assertIn('color:#081043',table)
            self.assertIn('font-weight:800',table)
            self.assertIn('color:#000 !important',table)
            self.assertIn('background:#EAF0FF',table)

    def test_sample_zip_roundtrip_and_exports(self):
        import json
        from lunch_rush.upload import parse_upload
        from lunch_rush.engine import validate
        st=self.run_app()
        label,data,meta=st.downloads[0]
        self.assertIn('Chicken Coop',label)
        self.assertEqual(meta['file_name'],'The_Chicken_Coop_Sample_Data.zip')
        schema=json.loads((ROOT/'schema.json').read_text())
        validated=validate(parse_upload(meta['file_name'],data,schema),schema)
        self.assertEqual(validated.errors,[])
        self.assertEqual(len(validated.tables['Restaurant_Master']),40)
        self.assertTrue(any('Restaurant Table' in name for name,_,_ in st.downloads))
        self.assertTrue(any('Menu Table' in name for name,_,_ in st.downloads))

    def test_legends_and_pie_hover_fonts(self):
        st=self.run_app()
        self.assertTrue(any('lr-chart-key' in t for t in st.markdown_texts))
        for f in st.chart_traces:
            if any(t.get('type')=='pie' for t in f.get('data',[])):
                self.assertGreaterEqual(f['layout']['hoverlabel']['font']['size'],16)

    def test_previous_and_no_comparison(self):
        for c in ('Previous Equivalent Period','No Comparison'):
            st=self.run_app(comparison=c)
            self.assertEqual(len(st.tabs_created),4)
            self.assertGreater(st.figures,3)

    def test_custom_and_ytd(self):
        for period in ('Custom Date Range','Year to Date (YTD)'):
            st=self.run_app(period=period)
            self.assertEqual(len(st.tabs_created),4)


class TestTableFormatting(unittest.TestCase):
    def test_formatting_and_color_rules(self):
        # The helpers are pure except for the Streamlit import, which is stubbed.
        old=sys.modules.get('streamlit')
        old_grids=sys.modules.pop('lunch_rush.grids',None)
        try:
            sys.modules['streamlit']=FakeStreamlit()
            from lunch_rush.grids import _change_style,_format_value,prepare_table
            self.assertEqual(_format_value('money')(6913932),'$6,913,932')
            self.assertEqual(_format_value('count')(729816),'729,816')
            self.assertEqual(_format_value('growth')(-44.4),'-44.4%')
            self.assertIn('#FEE2E2',_change_style(-44.4))
            self.assertIn('#DCFCE7',_change_style(12.5))
            frame=pd.DataFrame({'Segment':['Drive-Thru','Delivery'], 'Net Sales':[1234000.,500000.],
                                'Sales Change':[-4.4,12.5]})
            raw,styled=prepare_table(frame,key='lr-channel-breakdown',
                formats={'Net Sales':'money','Sales Change':'growth'},change_columns=['Sales Change'])
            self.assertTrue(pd.api.types.is_numeric_dtype(raw['Sales Change']))
            self.assertTrue(styled.data.equals(raw))
            from lunch_rush.grids import table_html
            markup=table_html(frame,key='lr-channel-breakdown',
                formats={'Net Sales':'money','Sales Change':'growth'},
                change_columns=['Sales Change'])
            self.assertIn('$1,234,000',markup)
            self.assertIn('class="lr-td lr-up"',markup)
            self.assertIn('class="lr-td lr-down"',markup)
            self.assertIn('data-sort="1234000"',markup)
            malicious='<script>alert("malicious")</script>'
            safe=table_html(pd.DataFrame({'Restaurant':[malicious], 'Net Sales':[2]}),
                            key='lr-restaurant-exclusions')
            self.assertNotIn(malicious,safe)
            self.assertIn('&lt;script&gt;',safe)
            self.assertIn('data-sort="&lt;script&gt;',safe)
        finally:
            if old is None:sys.modules.pop('streamlit',None)
            else:sys.modules['streamlit']=old
            sys.modules.pop('lunch_rush.grids',None)
            if old_grids is not None:sys.modules['lunch_rush.grids']=old_grids


if __name__=='__main__':unittest.main()
