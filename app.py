"""Lunch Rush V1 | Restaurant performance, explained.

Streamlit Cloud entrypoint. Actual computations live in lunch_rush/engine.py.
"""
from __future__ import annotations

from datetime import timedelta
from hashlib import sha256
from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lunch_rush.engine import Analytics, validate
from lunch_rush.io import load_csv_tabs
from lunch_rush.ui_metrics import (
    category_summary, format_int, format_money, format_pct, matched_menu_growth,
    mix_breakdown, restaurant_table, scope_ids, week_series,
)
from lunch_rush.upload import parse_upload

ROOT = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / 'schema.json').read_text(encoding='utf-8'))
BRAND_BLUE = '#0032FF'
NAVY = '#081043'
GREEN = '#00A95C'
CORAL = '#FF535C'
PAPER = '#FAF8F3'
SLATE = '#657084'

st.set_page_config(
    page_title='Lunch Rush | Brand Rundown',
    page_icon=str(ROOT / 'assets/lunch-rush-app-icon.png'),
    layout='wide', initial_sidebar_state='auto',
)
st.markdown('''<style>
  .block-container {max-width: 1390px; padding-top: 1.5rem; padding-bottom: 3rem;}
  [data-testid="stSidebar"] {border-right: 1px solid #e6e8f0;}
  div[data-testid="stMetric"] {background:#fff; border:1px solid #e5e8f2;
      border-radius: 15px; padding: 16px 19px; min-height: 118px;}
  [data-testid="stMetricLabel"] {font-weight:650; color:#344060;}
  h1, h2, h3 {color: #081043; letter-spacing: -.025em;}
  h1 {font-weight: 800;}
  section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] {font-weight: 600;}
  div.stButton button[kind="primary"] {background:#0032FF; border-color:#0032FF;}
  [data-testid="stCaptionContainer"] {line-height:1.4;}
  div[data-testid="stAlert"] {border-radius: 12px;}
  .lr-eyebrow {font-size:.76rem; font-weight:800; letter-spacing:.10em;
      color:#0032FF; text-transform:uppercase; margin:0 0 .2rem;}
  .lr-subtitle {font-size:1.05rem; color:#657084; margin-top:-.7rem; margin-bottom:1.15rem;}
  .lr-rule {border:0; border-top:1px solid #e5e8f2; margin:1.5rem 0;}
</style>''', unsafe_allow_html=True)


def chart_style(fig: go.Figure, *, height: int=350, percent: bool=False):
    fig.update_layout(
        height=height, margin=dict(l=12,r=14,t=20,b=18),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color=NAVY, family='Inter, Arial, sans-serif', size=13),
        legend=dict(orientation='h',y=1.10,x=0),
        hoverlabel=dict(bgcolor='white'),
    )
    fig.update_xaxes(showgrid=False, linecolor='#dce2ec', zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor='#edf0f7', zeroline=False)
    if percent: fig.update_yaxes(tickformat='.0%')
    return fig


@st.cache_resource(show_spinner='Preparing fictional demo data…')
def load_demo():
    files={p.stem:p.read_bytes() for p in (ROOT/'data/demo').glob('*.csv')}
    result=validate(load_csv_tabs(files),SCHEMA)
    result.assert_valid()
    return Analytics(result), result


def display_name(analytics, rid: str):
    return f'{analytics.restaurants[rid]["restaurant_name"]} ({rid})'


def active_data():
    with st.sidebar:
        st.image(str(ROOT/'assets/lunch-rush-approved-logo.png'), width=165)
        st.caption('BY BRAND RUNDOWN  ·  V1')
        st.divider()
        st.markdown('**Data source**')
        dataset=st.radio('Choose a dataset', ['Fictional demo','Upload your data'],
                         label_visibility='collapsed',horizontal=False)
        if dataset=='Fictional demo':
            st.caption('40 locations · 4 regions · 104 weeks · synthetic records')
            return (*load_demo(), True)
        upload=st.file_uploader('Excel workbook or CSV ZIP',type=['xlsx','zip'],
                                 help='Uses the Lunch Rush V1 schema. Max 25 MB.')
        st.caption('Your file is processed for this session. Nothing is sent to an external analytics API.')
        if upload is None:
            st.info('Choose a file to open the dashboard.')
            st.stop()
        content=upload.getvalue()
        digest=sha256(content).hexdigest()
        cached=st.session_state.get('lr_uploaded')
        if cached is None or cached['hash'] != digest:
            try:
                rows=parse_upload(upload.name,content,SCHEMA)
                check=validate(rows,SCHEMA)
                if check.errors:
                    st.error('Data validation failed. Correct the file before continuing.')
                    for problem in check.errors[:12]: st.caption('• '+str(problem))
                    if len(check.errors)>12: st.caption(f'…and {len(check.errors)-12} more problems.')
                    st.stop()
                instance=Analytics(check)
                st.session_state['lr_uploaded']={'hash':digest,'engine':instance,'validated':check}
            except (ValueError, KeyError, OSError, TypeError) as exc:
                st.error(f'Cannot read this upload: {exc}')
                st.stop()
        found=st.session_state['lr_uploaded']
        st.success('Workbook validated')
        return found['engine'],found['validated'],False


a, valid, is_demo=active_data()

with st.sidebar:
    st.divider()
    nav=st.radio('Explore', ['Overview','Restaurants','Channels & Dayparts','Menu Performance','Insights'],
                 index=0)
    st.divider()
    st.markdown('**Analysis settings**')
    regions={r['region_id']:r['region_name'] for r in a.restaurants.values()}
    region_choice=st.selectbox('Region',['All regions']+[regions[key] for key in sorted(regions)])
    region_id=next((key for key,name in regions.items() if name==region_choice),None)
    ownership=st.selectbox('Ownership',['All ownership','Company','Franchise'])
    restaurant_format=st.selectbox('Restaurant format',
        ['All formats','Drive-Thru','Dine-In','Pickup-Focused'])
    base_location_ids=scope_ids(a,region_id,
        None if ownership=='All ownership' else ownership,
        None if restaurant_format=='All formats' else restaurant_format)
    location_selection=st.multiselect('Specific restaurants (optional)',options=base_location_ids,
        format_func=lambda rid:display_name(a,rid),
        placeholder='All matching restaurants')
    weeks=st.selectbox('Period', [4,13,26,52],index=1,format_func=lambda x:f'Last {x} weeks')
    end_dates=sorted({row['week_end'] for row in a.data['Store_Week_Status']}, reverse=True)
    if not end_dates:
        st.error('No reporting weeks were provided.')
        st.stop()
    end=st.selectbox('Week ending',end_dates,format_func=lambda d:d.strftime('%b %d, %Y'))
    compare_label=st.selectbox('Compare with',['Year over year','Previous period','No comparison'])
    mode={'Year over year':'yoy','Previous period':'previous','No comparison':'none'}[compare_label]
    st.divider()
    st.caption('Only verified POS and menu metrics are included. Promotions, COGS, labor and profitability are planned for V2.')

ids=location_selection if location_selection else base_location_ids
if not ids:
    st.warning('No restaurants match these filters.')
    st.stop()
start=end-timedelta(weeks=weeks-1)
if start<a.earliest:
    st.warning(f'The dataset begins {a.earliest:%b %d, %Y}. Choose a shorter period or later end date.')
    st.stop()

st.markdown('<div class="lr-eyebrow">BRAND RUNDOWN / RESTAURANT ANALYTICS</div>',unsafe_allow_html=True)
st.title(nav if nav!='Overview' else 'Lunch Rush')
st.markdown('<div class="lr-subtitle">Performance across restaurants, menus, ordering channels, and dayparts.</div>',unsafe_allow_html=True)
filter_text=f'{len(ids)} of {len(a.restaurants)} locations  ·  {start:%b %d, %Y} – {end:%b %d, %Y}  ·  {compare_label.lower()}'
st.caption(('FICTIONAL DEMO  ·  ' if is_demo else 'UPLOADED DATA  ·  ')+filter_text)


def show_completeness(summary:dict, *, menu:bool=False):
    if not summary.get('complete',True):
        st.warning(summary.get('warning') or
                   ('Some menu weeks are incomplete.' if menu else 'Some POS weeks are incomplete.')+
                   ' Interpret displayed sales as reported coverage only.')


def plot_weekly_trend():
    rows=week_series(a,start,end,ids)
    weekly=pd.DataFrame(rows)
    if not all(r['complete'] for r in rows):
        st.caption('Incomplete weeks were excluded. Reported totals may not represent the full network.')
    t1,t2=st.columns(2)
    with t1:
        st.subheader('Weekly net sales')
        fig=go.Figure(go.Scatter(x=weekly['week_end'],y=weekly['net_sales_usd'],
                                 line=dict(color=BRAND_BLUE,width=3),mode='lines+markers',
                                 marker=dict(size=6),hovertemplate='%{x|%b %d, %Y}<br>$%{y:,.0f}<extra></extra>'))
        chart_style(fig);fig.update_yaxes(tickprefix='$',tickformat='~s')
        st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
    with t2:
        st.subheader('Weekly transactions')
        fig=go.Figure(go.Scatter(x=weekly['week_end'],y=weekly['transactions'],
                                 line=dict(color=GREEN,width=3),mode='lines+markers',
                                 marker=dict(size=6),hovertemplate='%{x|%b %d, %Y}<br>%{y:,} orders<extra></extra>'))
        chart_style(fig);fig.update_yaxes(tickformat='~s')
        st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})


def overview():
    comp=a.compare_sales(start,end,mode=mode,restaurant_ids=ids)
    current=comp['current']
    same=a.comparable_sales(start,end,mode=mode,restaurant_ids=ids) if mode!='none' else None
    auv=a.average_unit_volume(end=end,restaurant_ids=ids)
    st.subheader('Performance at a glance')
    r1=st.columns(3)
    r1[0].metric('Net sales',format_money(current['net_sales_usd'],compact=True),
                 None if mode=='none' or comp['sales_growth_pct'] is None else format_pct(comp['sales_growth_pct']),
                 help='Consumer POS sales after discounts and refunds. Taxes and tips are excluded.')
    r1[1].metric('Transactions',format_int(current['transactions']),
                 None if mode=='none' or comp['transaction_growth_pct'] is None else format_pct(comp['transaction_growth_pct']),
                 help='Completed orders, not unique customers.')
    r1[2].metric('Average check',format_money(current['average_check_usd']),
                 None if not comp['prior'] or not comp['prior']['average_check_usd'] or not current['average_check_usd'] or not current['complete'] or not comp['prior']['complete'] else
                  format_pct(current['average_check_usd']/comp['prior']['average_check_usd']-1),
                 help='Net sales divided by completed transactions.')
    r2=st.columns(3)
    r2[0].metric('Comparable-store sales',
                 'N/A' if same is None else format_pct(same['comparable_store_sales_growth_pct']),
                 help='Fixed matched cohort. Stores must meet 13-month age and coverage rules in both periods.')
    r2[1].metric('Comparable transactions',
                 'N/A' if same is None else format_pct(same['comparable_store_transaction_growth_pct']),
                 help='Completed orders across the same eligible stores. Not guest traffic.')
    r2[2].metric('Rolling 52-week AUV',format_money(auv['average_unit_volume_usd'],compact=True),
                 help=f'Exactly 52 complete trading weeks per qualifying store. {auv["eligible_restaurants"]} stores qualify.')
    if mode!='none' and comp['reason']:
        st.info('All-store comparison unavailable: '+comp['reason'])
    if same is not None:
        st.caption(f'Comparable-store growth uses {same["eligible_restaurants"]} matched restaurants; '
                   f'{same["excluded_restaurants"]} excluded for age, reporting, or disruptions. '
                   f'AUV uses {auv["eligible_restaurants"]} fully covered restaurants.')
    show_completeness(current)
    st.markdown('<hr class="lr-rule">',unsafe_allow_html=True)
    plot_weekly_trend()
    st.markdown('<hr class="lr-rule">',unsafe_allow_html=True)
    regional_overview()
    st.markdown('<hr class="lr-rule">',unsafe_allow_html=True)
    st.subheader('What deserves attention')
    show_insight_cards(limit=3)


def regional_overview():
    st.subheader('Regional sales')
    rows=[]
    for region in sorted({a.restaurants[rid]['region_id'] for rid in ids}):
        summary=a.sales_summary(start,end,restaurant_ids=ids,region_id=region)
        growth=a.compare_sales(start,end,mode=mode,restaurant_ids=ids,region_id=region)
        rows.append({'region':regions[region],'net_sales_usd':summary['net_sales_usd'],
                     'transactions':summary['transactions'],
                     'growth_pct':growth['sales_growth_pct']})
    chart=px.bar(pd.DataFrame(rows).sort_values('net_sales_usd'),y='region',x='net_sales_usd',
                 orientation='h',text='net_sales_usd',color_discrete_sequence=[BRAND_BLUE])
    chart.update_traces(texttemplate='$%{x:,.0f}',textposition='outside',cliponaxis=False,
                        hovertemplate='%{y}<br>$%{x:,.0f}<extra></extra>')
    chart_style(chart,height=260)
    chart.update_yaxes(title=None)
    chart.update_xaxes(title=None,tickprefix='$',tickformat='~s')
    st.plotly_chart(chart,use_container_width=True,config={'displayModeBar':False})
    st.dataframe(pd.DataFrame([{'Region':r['region'],'Net sales':format_money(r['net_sales_usd']),
                               'Transactions':format_int(r['transactions']),
                               'Sales growth':format_pct(r['growth_pct']) if mode!='none' else '—'}
                              for r in rows]),hide_index=True,use_container_width=True)


def restaurants():
    ranking=restaurant_table(a,start,end,ids,mode)
    active=ranking['restaurants'];excluded=ranking['excluded_restaurants']
    st.subheader('Location performance')
    st.caption('Rankings include only locations with complete, disruption-free operating weeks across the entire selected period.')
    m1,m2,m3=st.columns(3)
    m1.metric('Locations selected',len(ids))
    m2.metric('Eligible for ranking',len(active))
    m3.metric('Excluded from ranking',len(excluded))
    if excluded:
        with st.expander('Why were some locations excluded?'):
            st.dataframe(pd.DataFrame([{'Location':display_name(a,rid),'Reason':reason.replace('_',' ')}
                                       for rid,reason in sorted(excluded.items())]),
                         hide_index=True,use_container_width=True)
    if not active:
        st.info('No locations qualify for a ranking in this period.')
        return
    top=active[:10]
    st.subheader('Top locations by net sales')
    df=pd.DataFrame(top).sort_values('net_sales_usd')
    df['label']=[display_name(a,rid) for rid in df['restaurant_id']]
    fig=px.bar(df,x='net_sales_usd',y='label',orientation='h',color_discrete_sequence=[BRAND_BLUE])
    chart_style(fig,height=max(280,len(df)*37))
    fig.update_yaxes(title=None);fig.update_xaxes(title=None,tickprefix='$',tickformat='~s')
    fig.update_traces(hovertemplate='%{y}<br>$%{x:,.0f}<extra></extra>')
    st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
    st.subheader('All qualifying locations')
    table=pd.DataFrame([{'Rank':r['rank'],'Restaurant':display_name(a,r['restaurant_id']),
            'Region':r['region'],'Ownership':r['ownership_type'],'Format':r['restaurant_format'],
            'Net sales':format_money(r['net_sales_usd']),'Transactions':format_int(r['transactions']),
            'Avg. check':format_money(r['average_check_usd']),
            'Sales change':format_pct(r['sales_growth_pct']) if mode!='none' else '—',
            'Transaction change':format_pct(r['transaction_growth_pct']) if mode!='none' else '—'}
            for r in active])
    st.dataframe(table,hide_index=True,use_container_width=True,height=440)
    st.download_button('Download location table (CSV)',table.to_csv(index=False).encode('utf-8'),
                       file_name='lunch_rush_restaurants.csv',mime='text/csv')
    if mode!='none':
        st.caption('Growth is an all-store comparison per restaurant. New locations without a valid prior period show N/A.')


def channels_dayparts():
    current=a.sales_summary(start,end,restaurant_ids=ids)
    show_completeness(current)
    for field,label in [('channel','Ordering channels'),('daypart','Dayparts')]:
        st.subheader(label)
        breakdown=mix_breakdown(a,start,end,ids,by=field)
        if not breakdown or not current['net_sales_usd']:
            st.info('No sales in the selected scope.')
            continue
        left,right=st.columns([1,1.2])
        with left:
            fig=go.Figure(go.Pie(labels=[x['name'] for x in breakdown],
                                  values=[x['net_sales_usd'] for x in breakdown],hole=.62,
                                  marker=dict(colors=[BRAND_BLUE,GREEN,CORAL,'#8190AC','#BCC5D7'][:len(breakdown)]),
                                  textinfo='label+percent',hovertemplate='%{label}<br>$%{value:,.0f}<extra></extra>'))
            chart_style(fig,height=350)
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
        with right:
            data=[]
            for row in breakdown:
                c=a.compare_sales(start,end,mode=mode,restaurant_ids=ids,**{field:row['name']})
                data.append({'Segment':row['name'],'Net sales':format_money(row['net_sales_usd']),
                   'Sales mix':format_pct(row['net_sales_usd']/current['net_sales_usd'],signed=False),
                   'Transactions':format_int(row['transactions']),
                   'Avg. check':format_money(row['average_check_usd']),
                   'Sales change':format_pct(c['sales_growth_pct']) if mode!='none' else '—',
                   'Transaction change':format_pct(c['transaction_growth_pct']) if mode!='none' else '—'})
            st.dataframe(pd.DataFrame(data),hide_index=True,use_container_width=True,height=300)
            st.caption('Ordering channel and daypart each partition POS sales independently. '
                       'Do not add the two breakdowns together.')
        st.markdown('<hr class="lr-rule">',unsafe_allow_html=True)


def menu_performance():
    menu=a.menu_summary(start,end,restaurant_ids=ids)
    show_completeness(menu,menu=True)
    st.subheader('Menu overview')
    r=st.columns(3)
    r[0].metric('Reported menu sales',format_money(menu['menu_total_usd'],compact=True))
    r[1].metric('Menu items',len(menu['items']))
    r[2].metric('Complete menu store-weeks',format_int(menu['eligible_store_weeks']))
    if not menu['items']:
        st.info('No menu records in this selection.')
        return
    st.caption('Item revenues are reported from their own menu table, not summed after a POS channel join.')
    cats=category_summary(menu)
    left,right=st.columns([1.1,1])
    with left:
        st.subheader('Sales by menu category')
        d=pd.DataFrame(cats).sort_values('net_sales_usd')
        fig=px.bar(d,x='net_sales_usd',y='category',orientation='h',
                   color_discrete_sequence=[GREEN])
        chart_style(fig,height=max(280,len(d)*39))
        fig.update_yaxes(title=None);fig.update_xaxes(title=None,tickprefix='$',tickformat='~s')
        st.plotly_chart(fig,use_container_width=True,config={'displayModeBar':False})
    with right:
        st.subheader('Category mix')
        st.dataframe(pd.DataFrame([{'Category':r['category'],'Net sales':format_money(r['net_sales_usd']),
                                   'Sales mix':format_pct(r['mix_pct'],signed=False),
                                   'Units':format_int(r['units_sold'])}
                                  for r in cats]),hide_index=True,use_container_width=True,height=320)
    st.subheader('Menu-item performance')
    matched_growth=matched_menu_growth(a,start,end,ids,mode)
    if mode!='none':
        st.caption('Item growth uses the same eligible comparable-store cohort in each period. '
                   'N/A means no valid matched comparison or item history.')
    table=pd.DataFrame([{'Item':r['menu_item_name'],'Category':r['category'],
       'Net sales':format_money(r['net_sales_usd']),'Units':format_int(r['units_sold']),
       'Sales mix':format_pct(r['mix_pct'],signed=False),
       'Realized price':format_money(r['realized_item_price_usd']),
       'Attach rate':format_pct(r['attach_rate'],signed=False),
       'Comparable item growth':format_pct(matched_growth.get(r['menu_item_id'])) if mode!='none' else '—'}
       for r in menu['items']])
    st.dataframe(table,hide_index=True,use_container_width=True,height=490)
    st.download_button('Download menu table (CSV)',table.to_csv(index=False).encode('utf-8'),
                       file_name='lunch_rush_menu.csv',mime='text/csv')
    st.caption('Attach rate = transactions containing item ÷ completed transactions, where item-order coverage is complete. '
               'It is not available for missing item history.')


def show_insight_cards(limit:int|None=None):
    if mode=='none':
        st.info('Choose a comparison period to view diagnostics.')
        return
    findings=a.diagnostics(start,end,comparison=mode,restaurant_ids=ids)
    if not findings:
        st.info('No rule-based findings crossed their configured thresholds for this scope and comparison. '
                'This does not establish that performance is healthy.')
        return
    for d in findings[:limit] if limit is not None else findings:
        name=(regions.get(d['scope'],d['scope']) if d['kind']=='regional_traffic_decline' else
              a.menu[d['scope']]['menu_item_name'] if d['kind']=='menu_item_decline' else d['scope'])
        with st.container(border=True):
            st.markdown(f'**{name}**  ·  Watch')
            st.write(d['finding'])
            detail=[]
            for k,v in d['evidence'].items():
                if k.endswith('_pct') and v is not None:
                    detail.append(f'{k.replace("_pct", "").replace("_", " ").capitalize()}: {format_pct(v)}')
                elif k=='eligible_restaurants':detail.append(f'Matched locations: {v}')
            if detail:st.caption('  ·  '.join(detail))
            st.caption('Investigate: '+d['investigate'])
    if limit is not None and len(findings)>limit:
        st.caption(f'{len(findings)-limit} additional finding(s) on the Insights page.')


def insights():
    st.subheader('Performance signals')
    st.caption('Rules flag measurable changes, not verified causes or recommended decisions. '
               'Results reflect the selected locations and comparison period.')
    show_insight_cards()
    st.markdown('<hr class="lr-rule">',unsafe_allow_html=True)
    st.subheader('Data quality and exclusions')
    sales=a.sales_summary(start,end,restaurant_ids=ids)
    menu=a.menu_summary(start,end,restaurant_ids=ids)
    st.dataframe(pd.DataFrame([
        {'Check':'POS store-weeks','Complete rows':sales['eligible_store_weeks'],
         'Incomplete rows':sales['incomplete_store_weeks'],'Status':'Complete' if sales['complete'] else 'Review'},
        {'Check':'Menu store-weeks','Complete rows':menu['eligible_store_weeks'],
         'Incomplete rows':menu['incomplete_store_weeks'],'Status':'Complete' if menu['complete'] else 'Review'},
    ]),hide_index=True,use_container_width=True)
    if mode!='none':
        c=a.comparable_sales(start,end,mode=mode,restaurant_ids=ids)
        st.caption(f'Comparable cohort: {c["eligible_restaurants"]} included, {c["excluded_restaurants"]} excluded.')
        if c['exclusions_by_reason']:
            st.write({reason.replace('_',' '):n for reason,n in c['exclusions_by_reason'].items()})
    if valid.warnings:
        with st.expander('Source warnings'):
            for warning in valid.warnings:st.caption('• '+warning)
    st.caption('Promotion and financial inputs are optional future tables; absent values are unavailable, not zero.')


if nav=='Overview':overview()
elif nav=='Restaurants':restaurants()
elif nav=='Channels & Dayparts':channels_dayparts()
elif nav=='Menu Performance':menu_performance()
else:insights()

st.divider()
st.caption('Lunch Rush by Brand Rundown  ·  Data-informed investigation, not automated causal conclusions. '
           'Demo figures are entirely fictional.' if is_demo else
           'Lunch Rush by Brand Rundown  ·  Data-informed investigation, not automated causal conclusions.')
