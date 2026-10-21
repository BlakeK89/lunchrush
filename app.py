"""Lunch Rush V1 by Brand Rundown.

UI design adapted from the current Shelf Life app and approved Brand Rundown
identity. All restaurant calculations remain in the tested Lunch Rush engine.
"""
from __future__ import annotations

from datetime import date, timedelta
from hashlib import sha256
from io import BytesIO
from zipfile import ZipFile, ZIP_DEFLATED
from html import escape
from pathlib import Path
import json

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from lunch_rush.engine import Analytics, validate
from lunch_rush.grids import render_grid
from lunch_rush.io import load_csv_tabs
from lunch_rush.theme import ELECTRIC_BLUE as BLUE, CORAL, NAVY, LUNCH_GREEN as GREEN, STYLES
from lunch_rush.ui_metrics import (
    category_summary, format_int, format_money, format_pct,
    matched_menu_growth, mix_breakdown, restaurant_table, scope_ids, week_series,
)
from lunch_rush.upload import parse_upload

ROOT = Path(__file__).resolve().parent
SCHEMA = json.loads((ROOT / 'schema.json').read_text(encoding='utf-8'))
LOGO = ROOT / 'assets/lunch-rush-approved-logo.png'

st.set_page_config(
    page_title='Lunch Rush | Brand Rundown',
    page_icon=str(ROOT / 'assets/lunch-rush-app-icon.png'),
    layout='wide', initial_sidebar_state='auto',
)
st.markdown(STYLES, unsafe_allow_html=True)


def chart_style(fig: go.Figure, *, height: int = 295):
    fig.update_layout(
        height=height, margin=dict(l=12, r=20, t=20, b=30),
        paper_bgcolor='#FFFFFF', plot_bgcolor='#FFFFFF',
        font=dict(color=NAVY, family='Inter, Arial, sans-serif', size=12),
        hoverlabel=dict(bgcolor='#FFFFFF', bordercolor='#DDE2F8',
                        font=dict(color=NAVY, size=15)),
        legend=dict(orientation='h', y=1.17, x=.5, xanchor='center'),
    )
    fig.update_xaxes(showgrid=False, linecolor='#C7D1E8', zeroline=False,
                     tickfont=dict(size=12, color=NAVY, family='Arial, sans-serif'),
                     title_font=dict(size=13, color=NAVY, family='Arial, sans-serif'))
    fig.update_yaxes(showgrid=True, gridcolor='#E4E9F5', zeroline=False,
                     tickfont=dict(size=12, color=NAVY, family='Arial, sans-serif'),
                     title_font=dict(size=13, color=NAVY, family='Arial, sans-serif'))
    return fig


def render_chart(fig: go.Figure):
    """Enforce legible navy axis text after individual chart overrides."""
    axes = dict(size=12, color=NAVY, family='Arial, sans-serif')
    titles = dict(size=13, color=NAVY, family='Arial, sans-serif')
    fig.update_xaxes(tickfont=axes, title_font=titles)
    fig.update_yaxes(tickfont=axes, title_font=titles)
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar':False})


def pct_points(value):
    """Store numeric percentages as percentage points for native sorting."""
    return None if value is None else 100 * value


def money_column(label: str, *, decimals=0, width=None):
    """Format currency with thousands separators, keeping source values numeric."""
    return st.column_config.NumberColumn(label, format=f'$%,.{decimals}f', width=width)


def count_column(label: str, *, width=None):
    return st.column_config.NumberColumn(label, format='%,d', width=width)


def percentage_column(label: str, *, signed=True, width=None):
    return st.column_config.NumberColumn(
        label, format=('%+.1f%%' if signed else '%.1f%%'), width=width,
    )


def safe_md(s: object) -> str:
    """Escape dollar signs in dynamically generated Streamlit Markdown."""
    return str(s).replace('$', r'\$')


def delta_percent(current, prior, *, signed=True):
    if current is None or prior in (None, 0):
        return None
    value = current / prior - 1
    return format_pct(value, signed=signed)


def absolute_and_pct(current, prior, *, cash=False):
    if current is None or prior in (None, 0):
        return None
    diff = current - prior
    unit = (f'${abs(diff):,.0f}' if cash else f'{abs(round(diff)):,}')
    sign = '+' if diff > 0 else ('-' if diff < 0 else '')
    if cash and abs(diff) >= 1_000_000:
        unit = format_money(abs(diff), compact=True)
    elif cash:
        unit = f'${abs(diff):,.0f}'
    return f'{sign}{unit} ({format_pct(current / prior - 1)})'


def previous_bounds(start: date, end: date, mode: str):
    if mode == 'none':
        return None, None
    length = len(a._weeks(start, end))
    distance = timedelta(days=364) if mode == 'yoy' else timedelta(weeks=length)
    return start-distance, end-distance


def display_name(engine, rid: str):
    return f'{engine.restaurants[rid]["restaurant_name"]} ({rid})'


@st.cache_resource(show_spinner='Preparing fictional demo data…')
def load_demo():
    files = {p.stem: p.read_bytes() for p in (ROOT / 'data/demo').glob('*.csv')}
    result = validate(load_csv_tabs(files), SCHEMA)
    result.assert_valid()
    return Analytics(result), result


@st.cache_data(show_spinner=False)
def sample_data_zip() -> bytes:
    """Package the exact built-in demo CSVs in an importable archive."""
    buffer = BytesIO()
    with ZipFile(buffer, 'w', compression=ZIP_DEFLATED, compresslevel=6) as zf:
        for path in sorted((ROOT / 'data/demo').glob('*.csv')):
            zf.write(path, arcname=path.name)
    return buffer.getvalue()


def render_sample_download():
    # Match Shelf Life's small, secondary sample-data utility. Keep the download
    # available even when users switch to the upload source.
    with st.container(key='br_sample_download'):
        st.download_button(
            'Download The Chicken Coop Sample Data',
            data=sample_data_zip(),
            file_name='The_Chicken_Coop_Sample_Data.zip',
            mime='application/zip',
            help='Eight CSV sheets from the fictional 40-location demonstration dataset. Upload the ZIP directly to Lunch Rush.',
            key='download_chicken_coop_sample',
            type='tertiary',
            use_container_width=False,
        )


def toggle_help():
    st.session_state['lr_show_help'] = not st.session_state.get('lr_show_help', False)


with st.container(key='br_identity_header'):
    header_title, header_actions = st.columns([3, 2], vertical_alignment='center')
    with header_title:
        st.markdown('<h1 class="br-screen-reader-heading">Lunch Rush by Brand Rundown</h1>', unsafe_allow_html=True)
        st.image(str(LOGO), width=300, alt='Lunch Rush by Brand Rundown')
    with header_actions:
        with st.container(horizontal=True, horizontal_alignment='right',
                          vertical_alignment='center', gap='small'):
            st.button('Back to Dashboard' if st.session_state.get('lr_show_help', False) else 'How It Works',
                      icon=':material/arrow_back:' if st.session_state.get('lr_show_help', False) else ':material/help_outline:',
                      on_click=toggle_help, key='how_it_works_nav')

if st.session_state.get('lr_show_help', False):
    st.subheader('How Lunch Rush Works', anchor=False)
    st.markdown('Select the fictional demo or upload a workbook, choose your reporting period, then explore the five dashboard tabs.')
    with st.container(border=True):
        st.markdown('**Key restaurant metrics**')
        st.markdown('''
        - **Net sales:** Restaurant revenue after discounts and refunds, excluding taxes and tips.
        - **Transactions:** Completed orders, not unique guests.
        - **Average check:** Net sales divided by transactions.
        - **Comparable-store growth:** Change across one matched group of established restaurants with complete reporting in both periods.
        - **Average unit volume (AUV):** Average trailing 52-week sales for restaurants with a complete qualifying year.
        ''')
        st.caption('Findings identify measurable changes and possible next checks. They do not establish causes.')
    st.stop()


with st.sidebar:
    st.header('Dashboard Settings', anchor=False)
    st.caption('Choose your data and time period.')
    with st.container(key='br_data_source_control'):
        data_source = st.radio('Data Source',
                               ['The Chicken Coop (Sample Data)', 'Upload Your Data'])
    if data_source == 'The Chicken Coop (Sample Data)':
        a, valid = load_demo()
        is_demo = True
    else:
        is_demo = False
        with st.container(key='br_upload_warning'):
            st.warning('This dashboard is public. Do not upload confidential company data.')
        with st.container(key='br_upload_panel'):
            upload = st.file_uploader('Excel workbook or CSV ZIP', type=['xlsx', 'zip'],
                                      help='Use the Lunch Rush V1 schema. Maximum 25 MB.')
        if upload is None:
            render_sample_download()
            st.info('Upload your data or select the fictional demo.')
            st.stop()
        content = upload.getvalue()
        digest = sha256(content).hexdigest()
        cached = st.session_state.get('lr_uploaded')
        if cached is None or cached['hash'] != digest:
            try:
                rows = parse_upload(upload.name, content, SCHEMA)
                check = validate(rows, SCHEMA)
                if check.errors:
                    st.error('Data validation failed. Correct the file before continuing.')
                    for problem in check.errors[:12]:
                        st.caption('• ' + str(problem))
                    if len(check.errors) > 12:
                        st.caption(f'…and {len(check.errors) - 12} more problems.')
                    st.stop()
                st.session_state['lr_uploaded'] = {'hash': digest,
                                                   'engine': Analytics(check), 'validated': check}
            except (ValueError, KeyError, OSError, TypeError) as exc:
                st.error(f'Cannot read this upload: {exc}')
                st.stop()
        found = st.session_state['lr_uploaded']
        a, valid = found['engine'], found['validated']
        st.success('Workbook validated')

    st.divider()
    period_option = st.selectbox('Reporting Period', [
        'Last 4 Weeks (L4W)', 'Last 13 Weeks (L13W)',
        'Last 26 Weeks (L26W)', 'Last 52 Weeks (L52W)',
        'Year to Date (YTD)', 'Custom Date Range',
    ], index=1)
    compare_label = st.selectbox('Compare Against', [
        'Same Period Last Year (YoY)', 'Previous Equivalent Period', 'No Comparison',
    ])
    mode = {'Same Period Last Year (YoY)': 'yoy',
            'Previous Equivalent Period': 'previous', 'No Comparison': 'none'}[compare_label]
    end_dates = sorted({row['week_end'] for row in a.data['Store_Week_Status']})
    if not end_dates:
        st.error('No reporting weeks were found.'); st.stop()
    end = end_dates[-1]
    if period_option == 'Custom Date Range':
        earliest = end_dates[0]
        default_start = max(earliest, end - timedelta(weeks=12))
        selection = st.date_input('Custom Date Range', value=(default_start, end),
                                  min_value=earliest, max_value=end,
                                  help='Use existing Sunday-ending reporting weeks. Both dates are inclusive.')
        if not isinstance(selection, (tuple, list)) or len(selection) != 2:
            st.info('Choose both dates.'); st.stop()
        start, end = selection
        if start not in end_dates or end not in end_dates or start > end:
            st.warning('Select two dates matching the available week-ending Sundays.'); st.stop()
    else:
        if period_option == 'Year to Date (YTD)':
            start = next((d for d in end_dates if d.year == end.year), None)
            if start is None:
                st.warning('No reporting weeks for the selected year.'); st.stop()
        else:
            rolling = {'Last 4 Weeks (L4W)': 4, 'Last 13 Weeks (L13W)': 13,
                       'Last 26 Weeks (L26W)': 26, 'Last 52 Weeks (L52W)': 52}
            count = rolling[period_option]
            start = end - timedelta(weeks=count - 1)
        with st.expander('Change ending week'):
            end = st.selectbox('Week Ending', list(reversed(end_dates)), index=0,
                               format_func=lambda d: d.strftime('%b %d, %Y'))
            if period_option == 'Year to Date (YTD)':
                start = next((d for d in end_dates if d.year == end.year), None)
                if start is None:
                    st.warning('No reporting weeks for the selected year.'); st.stop()
            else:
                start = end - timedelta(weeks=rolling[period_option] - 1)
    if start < a.earliest:
        st.warning(f'The dataset begins {a.earliest:%b %d, %Y}. Choose a shorter or later period.'); st.stop()

    # Additional filters are retained from V1, but grouped so basic settings remain clean.
    with st.expander('Restaurant filters'):
        regions = {r['region_id']:r['region_name'] for r in a.restaurants.values()}
        region_choice = st.selectbox('Region', ['All regions'] + [regions[k] for k in sorted(regions)])
        region_id = next((key for key, name in regions.items() if name == region_choice), None)
        ownership = st.selectbox('Ownership', ['All ownership', 'Company', 'Franchise'])
        rest_format = st.selectbox('Restaurant format', ['All formats', 'Drive-Thru', 'Dine-In', 'Pickup-Focused'])
        base_ids = scope_ids(a, region_id,
                             None if ownership == 'All ownership' else ownership,
                             None if rest_format == 'All formats' else rest_format)
        selected_ids = st.multiselect('Specific restaurants (optional)', options=base_ids,
                                      format_func=lambda rid: display_name(a, rid),
                                      placeholder='All matching restaurants')
    ids = selected_ids or base_ids
    if not ids:
        st.warning('No restaurants match the selected filters.'); st.stop()

    render_sample_download()

regions = {r['region_id']: r['region_name'] for r in a.restaurants.values()}
prior_start, prior_end = previous_bounds(start, end, mode)
period_weeks = len(a._weeks(start, end))
comp = a.compare_sales(start, end, mode=mode, restaurant_ids=ids)
current = comp['current']
same = a.comparable_sales(start, end, mode=mode, restaurant_ids=ids) if mode != 'none' else None
auv = a.average_unit_volume(end=end, restaurant_ids=ids)
findings = a.diagnostics(start, end, comparison=mode, restaurant_ids=ids) if mode != 'none' else []


def date_range(first: date, last: date) -> str:
    left = f'{first:%b} {first.day}'
    if first.year != last.year: left += f', {first.year}'
    return f'{left} – {last:%b} {last.day}, {last.year}'


# Reuse Shelf Life's three-column reporting context without overlong copy.
comparison_short_label = {
    'yoy': 'Same Period Last Year',
    'previous': 'Previous Equivalent Period',
    'none': 'No Comparison',
}[mode]
with st.container(border=True, key='br_reporting_context'):
    c1, c2, c3 = st.columns([1.1, 1.25, 1.25], gap='medium')
    with c1:
        st.caption('Brand')
        st.markdown('**The Chicken Coop**' if is_demo else '**Uploaded Restaurant Data**')
        st.caption(f'{period_option} · {comparison_short_label}')
    with c2:
        st.caption('Selected Reporting Period')
        st.markdown(f'**{date_range(start, end)}**')
    with c3:
        st.caption(comparison_short_label)
        st.markdown(f'**{date_range(prior_start, prior_end)}**' if prior_start else '**Current period only**')
if len(ids) != len(a.restaurants):
    st.caption(f'{len(ids)} of {len(a.restaurants)} restaurants selected by filters.')
if not is_demo:
    st.caption('Uploaded dataset · results reflect only the files supplied')

# Match Shelf Life's five compact KPIs and horizontal navigation.
kpis = st.columns(5, gap='small')
with kpis[0]:
    st.metric('Net Sales', format_money(current['net_sales_usd'], compact=True),
              absolute_and_pct(current['net_sales_usd'], comp['prior']['net_sales_usd'], cash=True)
              if comp['prior'] is not None and comp['sales_growth_pct'] is not None else None,
              help='Restaurant sales after discounts and refunds, excluding taxes and tips.')
with kpis[1]:
    st.metric('Transactions', format_int(current['transactions']),
              absolute_and_pct(current['transactions'], comp['prior']['transactions'])
              if comp['prior'] is not None and comp['transaction_growth_pct'] is not None else None,
              help='Completed orders, not unique customers or visits.')
with kpis[2]:
    st.metric('Average Check', format_money(current['average_check_usd']),
              delta_percent(current['average_check_usd'], comp['prior']['average_check_usd'])
              if comp['prior'] is not None and comp['reason'] is None else None,
              delta_color='off', help='Net sales divided by completed transactions. Higher does not necessarily mean better profitability.')
with kpis[3]:
    sss_growth = same['comparable_store_sales_growth_pct'] if same is not None else None
    st.metric('Comparable-Store Sales', format_pct(sss_growth),
              delta=format_pct(sss_growth) + ' vs prior' if sss_growth is not None else None,
              help='Growth among the same eligible established stores with complete data in both periods.')
with kpis[4]:
    same_tx_growth = same['comparable_store_transaction_growth_pct'] if same is not None else None
    st.metric('Comparable Transactions', format_pct(same_tx_growth),
              delta=format_pct(same_tx_growth) + ' vs prior' if same_tx_growth is not None else None,
              help='Order-volume change at the same qualifying stores. Not unique guest traffic.')
if same is not None:
    st.caption(f'Same-store comparisons use the same {same["eligible_restaurants"]} established restaurants in both periods.')
else:
    st.caption('Choose a comparison period to see how established restaurants performed.')
st.caption(f'Average sales per restaurant over the past year: {format_money(auv["average_unit_volume_usd"], compact=True)} '
           f'(based on {auv["eligible_restaurants"]} restaurants with a full year of complete data).')
if comp['reason'] and mode != 'none':
    st.info('All-store comparison unavailable: ' + comp['reason'])
if not current['complete']:
    st.warning(current['warning'] or 'Some POS weeks were incomplete. Reported totals may not represent the entire network.')


def region_breakdown():
    rows = []
    for region in sorted({a.restaurants[rid]['region_id'] for rid in ids}):
        current_region = a.sales_summary(start, end, restaurant_ids=ids, region_id=region)
        delta_region = a.compare_sales(start, end, mode=mode, restaurant_ids=ids, region_id=region)
        rprior = delta_region['prior']
        rows.append({'region': regions[region], 'net_sales_usd': current_region['net_sales_usd'],
                     'transactions': current_region['transactions'],
                     'growth_pct': delta_region['sales_growth_pct'],
                     'sales_delta_usd': None if delta_region['sales_growth_pct'] is None or not rprior else
                         current_region['net_sales_usd']-rprior['net_sales_usd']})
    return rows


def insight_name(d):
    if d['kind'] == 'regional_traffic_decline': return regions.get(d['scope'], d['scope'])
    if d['kind'] == 'menu_item_decline': return a.menu[d['scope']]['menu_item_name']
    return d['scope']


def insight_items(items):
    for d in items:
        st.markdown('**' + escape(insight_name(d)) + ':** ' + safe_md(d['finding']))
        st.markdown('- ' + safe_md(d['investigate']))


def overview_summary():
    st.subheader('Executive Summary', anchor=False)
    with st.container(border=True):
        if mode == 'none':
            st.markdown(f'**Net sales totaled {safe_md(format_money(current["net_sales_usd"], compact=True))} across {len(ids)} selected locations.**')
            st.caption('Select a comparison period to see movements and diagnostic findings.')
        else:
            delta = comp['sales_growth_pct']
            if delta is not None and comp['prior'] is not None:
                diff = current['net_sales_usd']-comp['prior']['net_sales_usd']
                direction = 'increased' if diff>0 else 'decreased' if diff<0 else 'were unchanged'
                st.markdown(f'**Net sales {direction} by {safe_md(format_money(abs(diff), compact=True))} '
                            f'({format_pct(delta)}) versus the comparison period.**')
                if comp['transaction_growth_pct'] is not None:
                    transaction_direction = 'increased' if comp['transaction_growth_pct'] > 0 else (
                    'decreased' if comp['transaction_growth_pct'] < 0 else 'were unchanged')
                st.markdown(f'Transactions {transaction_direction} {format_pct(abs(comp["transaction_growth_pct"]), signed=False)}; '
                            f'average check was {safe_md(format_money(current["average_check_usd"]))}.')
                if same and same.get('comparable_store_transaction_growth_pct') is not None:
                    st.markdown(f'**Established stores:** Sales {format_pct(same["comparable_store_sales_growth_pct"])} '
                                f'· transactions {format_pct(same["comparable_store_transaction_growth_pct"])}.')
            else:
                st.markdown('**A complete all-store comparison is unavailable for the selected period.**')
                st.caption(comp['reason'] or 'Reporting coverage needs review.')
            regional = [r for r in region_breakdown() if r['sales_delta_usd'] is not None]
            if regional:
                st.markdown('**Biggest regional sales movements**')
                for r in sorted(regional, key=lambda item: -abs(item['sales_delta_usd']))[:3]:
                    sign = '+' if r['sales_delta_usd']>=0 else '−'
                    st.markdown(f'- **{escape(r["region"])}:** {safe_md(sign + format_money(abs(r["sales_delta_usd"]), compact=True))}')
            st.markdown('**Priority next checks**')
            if findings:
                for d in findings[:3]:
                    st.markdown(f'- **{escape(insight_name(d))}:** {safe_md(d["investigate"])}')
            else:
                st.caption('No diagnostic thresholds triggered. This does not prove every location is healthy.')
            with st.expander('See more results and next steps'):
                if same is not None:
                    st.markdown('**Comparable-store performance**')
                    st.markdown(f'- Matched locations: **{same["eligible_restaurants"]}**; '
                                f'excluded: **{same["excluded_restaurants"]}**')
                    st.markdown(f'- Comparable sales: **{format_pct(same["comparable_store_sales_growth_pct"])}**; '
                                f'transactions: **{format_pct(same["comparable_store_transaction_growth_pct"])}**')
                if len(findings)>3:
                    st.markdown('**Additional observations**')
                    insight_items(findings[3:])
                elif not findings:
                    st.caption('Explore Restaurants, Channels & Dayparts, and Menu Performance for more detail.')
                # Detailed findings and limits are explained on the Insights tab.


def chart_key(items: list[tuple[str, str]]) -> None:
    """Consistent, accessible chart legend outside the plotting surface."""
    legend = ''.join(
        f'<span class="lr-chart-key-item"><span class="lr-chart-key-dot" '
        f'style="background:{color}" aria-hidden="true"></span>{escape(label)}</span>'
        for label, color in items
    )
    st.markdown(f'<div class="lr-chart-key" role="group" aria-label="Chart legend">{legend}</div>',
                unsafe_allow_html=True)


def comparison_chart():
    current_rows = week_series(a, start, end, ids)
    older_rows = week_series(a, prior_start, prior_end, ids) if prior_start and comp['reason'] is None else []
    prior_name = 'Prior year' if mode == 'yoy' else 'Previous period'
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=list(range(1,len(current_rows)+1)),
        y=[r['net_sales_usd'] for r in current_rows], name='Current',
        mode='lines+markers' if len(current_rows)<=13 else 'lines',
        line=dict(color=BLUE,width=3),marker=dict(size=5),
        customdata=[[r['week_end'].strftime('%b %d, %Y')] for r in current_rows],
        hovertemplate='Week %{customdata[0]}<br>$%{y:,.0f}<extra>Current</extra>'))
    if older_rows:
        fig.add_trace(go.Scatter(x=list(range(1,len(older_rows)+1)),
            y=[r['net_sales_usd'] for r in older_rows],name=prior_name,
            mode='lines+markers' if len(older_rows)<=13 else 'lines',
            line=dict(color=NAVY,width=2.7),marker=dict(size=5),
            customdata=[[r['week_end'].strftime('%b %d, %Y')] for r in older_rows],
            hovertemplate='Week %{customdata[0]}<br>$%{y:,.0f}<extra>'+prior_name+'</extra>'))
    chart_style(fig)
    fig.update_layout(showlegend=False)
    period_label = 'Same weeks last year' if mode == 'yoy' else 'Previous period'
    chart_key([('Selected period', BLUE)] + ([(period_label, NAVY)] if older_rows else []))
    fig.update_xaxes(title='Week within selected period',dtick=1 if period_weeks<=13 else None)
    fig.update_yaxes(title='Weekly net sales',tickprefix='$',tickformat='~s',rangemode='normal')
    render_chart(fig)


def contribution_chart():
    rows = region_breakdown()
    has_delta = mode != 'none' and all(r['sales_delta_usd'] is not None for r in rows)
    if has_delta:
        data = pd.DataFrame([{'Region':r['region'],'Amount':r['sales_delta_usd'],
                              'Movement':'Gains' if r['sales_delta_usd']>0 else 'Declines' if r['sales_delta_usd']<0 else 'No change'}
                             for r in rows])
        palette = {'Gains':GREEN,'Declines':CORAL,'No change':'#8190AC'}
        fig = px.bar(data.sort_values('Amount'),x='Amount',y='Region',orientation='h',
                     color='Movement',color_discrete_map=palette)
        xlabel = 'Change in net sales'
    else:
        data = pd.DataFrame([{'Region':r['region'],'Amount':r['net_sales_usd']} for r in rows])
        fig = px.bar(data.sort_values('Amount'),x='Amount',y='Region',orientation='h',
                     color_discrete_sequence=[BLUE])
        xlabel = 'Net sales in selected period'
    chart_style(fig)
    # Plotly legends previously sat on top of the green bars. Keep the key
    # outside the chart and show only categories actually present in the data.
    fig.update_layout(showlegend=False)
    if has_delta:
        present = set(data['Movement'])
        # Single-direction bars are self-explanatory when described below.
        if len(present) > 1:
            chart_key([(label, color) for label, color in
                       [('Sales increased', GREEN), ('Sales decreased', CORAL), ('No change', '#8190AC')]
                       if {'Sales increased':'Gains', 'Sales decreased':'Declines',
                           'No change':'No change'}[label] in present])
    fig.update_traces(marker_line_width=0,hovertemplate='%{y}<br>$%{x:,.0f}<extra></extra>')
    fig.update_xaxes(title=xlabel,tickprefix='$',tickformat='~s',zeroline=True,zerolinecolor='#C7D1E8')
    fig.update_yaxes(title=None,showgrid=False)
    render_chart(fig)


def show_completeness(summary, *, menu=False):
    if not summary.get('complete',True):
        st.warning(summary.get('warning') or ('Some menu weeks are incomplete.' if menu else 'Some POS weeks are incomplete.'))


def overview():
    overview_summary()
    left,right = st.columns([1.15,1],gap='medium')
    with left:
        with st.container(key='br_chart_comparison'):
            st.subheader('Weekly Sales Comparison' if mode != 'none' and comp['reason'] is None else 'Weekly Sales Trend',anchor=False)
            comparison_chart()
            st.caption(('Prior-period chart unavailable because reporting coverage is incomplete.' if comp['reason'] is not None else
                        'Weeks aligned with the same weeks last year.') if mode=='yoy' else
                       ('Prior-period chart unavailable because reporting coverage is incomplete.' if comp['reason'] is not None else
                        'Weeks aligned with the preceding equivalent period.') if mode=='previous' else
                       'Sales for the selected reporting period.')
    with right:
        with st.container(key='br_chart_contribution'):
            st.subheader('Change in Sales by Region' if mode != 'none' else 'Sales by Region',anchor=False)
            contribution_chart()
            region_changes = [r['sales_delta_usd'] for r in region_breakdown()]
            if mode != 'none' and all(x is not None for x in region_changes):
                if all(x >= 0 for x in region_changes):
                    st.caption('Green bars show how much sales increased in each region.')
                elif all(x <= 0 for x in region_changes):
                    st.caption('Coral bars show how much sales decreased in each region.')
                else:
                    st.caption('Green bars show sales increases; coral bars show decreases.')
            else:
                st.caption('Total sales in each region for the selected period.')

    st.subheader('Where the Sales Happened',anchor=False)
    drive = a.sales_summary(start,end,restaurant_ids=ids,channel='Drive-Thru')
    other_sales = current['net_sales_usd']-drive['net_sales_usd']
    drive_prev = None;other_prev = None
    if prior_start:
        pdrive = a.sales_summary(prior_start,prior_end,restaurant_ids=ids,channel='Drive-Thru')
        if pdrive['complete'] and comp['reason'] is None:
            drive_prev = pdrive['net_sales_usd']
            other_prev = comp['prior']['net_sales_usd']-drive_prev
    c1,c2 = st.columns(2,gap='medium')
    with c1:
        with st.container(key='lr_drive_card'):
            st.metric('Drive-Thru Net Sales',format_money(drive['net_sales_usd'],compact=True),
                      delta_percent(drive['net_sales_usd'],drive_prev) if drive['complete'] else None,
                      help='Sales through the drive-thru ordering channel.')
    with c2:
        with st.container(key='lr_other_card'):
            st.metric('Other Ordering Channels',format_money(other_sales,compact=True),
                      delta_percent(other_sales,other_prev) if current['complete'] else None,
                      help='Dine-in, pickup, and delivery combined.')
    st.caption('Drive-thru and other ordering channels sum to total net sales.')


def restaurants():
    ranking = restaurant_table(a,start,end,ids,mode)
    active=ranking['restaurants']; excluded=ranking['excluded_restaurants']
    st.subheader('Restaurant Sales Rankings',anchor=False)
    st.caption('Restaurants are ranked by total net sales for the selected period. Only restaurants open all seven days each week, with complete sales reporting and no recorded disruptions, are ranked.')
    p1,p2,p3 = st.columns(3,gap='small')
    p1.metric('Restaurants Selected',len(ids),
              help='Number of restaurants included in your current filters.')
    p2.metric('Restaurants Ranked',len(active),
              help='Restaurants with complete sales reporting and no disrupted operating weeks throughout the selected period.')
    p3.metric('Not Ranked',len(excluded),
              help='Restaurants excluded from the sales ranking because they were not open for the full period, had missing data or recorded disruptions.')
    if excluded:
        with st.expander('Why were some restaurants left out of the sales ranking?'):
            def exclusion_explanation(restaurant_id, reason):
                # The ranking engine returns combined codes. Use the original
                # per-week records to explain the specific observed problem.
                if reason == 'partial_or_disrupted':
                    for week in a._weeks(start, end):
                        status = a.status.get((restaurant_id, week))
                        if status is None:
                            continue
                        details = []
                        if status['actual_operating_days'] != 7 or status['expected_operating_days'] != 7:
                            details.append(f"open {status['actual_operating_days']} of 7 days")
                        if status['coverage_status'] != 'Complete':
                            details.append('sales reporting incomplete')
                        if status['disruption_flag']:
                            details.append('operating disruption recorded')
                        if details:
                            return (f'Week ending {week:%b} {week.day}, {week.year}: '
                                    + '; '.join(details) + '.')
                    return 'One or more weeks had incomplete sales reporting or disrupted operations.'
                if reason == 'not_open_or_unreported':
                    return 'Not open for the entire selected period, or weekly sales data was missing.'
                return 'Did not meet the requirements for a full-period restaurant ranking.'

            render_grid(pd.DataFrame([{
                'Restaurant': display_name(a, rid),
                'Reason': exclusion_explanation(rid, reason),
            } for rid, reason in sorted(excluded.items())]),
                key='lr-restaurant-exclusions', widths={'Restaurant':165, 'Reason':530})
    if not active:
        st.info('No restaurants qualify for a full-period ranking.');return
    left,right = st.columns([1.1,1],gap='medium')
    with left:
        with st.container(key='lr_chart_restaurants_top'):
            st.subheader('Top Restaurants by Net Sales',anchor=False)
            rows=pd.DataFrame(active[:10]).sort_values('net_sales_usd')
            rows['label']=[display_name(a,rid) for rid in rows['restaurant_id']]
            fig=px.bar(rows,x='net_sales_usd',y='label',orientation='h',color_discrete_sequence=[BLUE])
            chart_style(fig,height=max(300,38*len(rows)))
            fig.update_xaxes(title='Net sales',tickprefix='$',tickformat='~s')
            fig.update_yaxes(title=None,showgrid=False)
            render_chart(fig)
    with right:
        with st.container(key='lr_chart_restaurants_regions'):
            st.subheader('Sales by Region',anchor=False)
            rows=pd.DataFrame(region_breakdown()).sort_values('net_sales_usd')
            fig=px.bar(rows,x='net_sales_usd',y='region',orientation='h',color_discrete_sequence=[GREEN])
            chart_style(fig,height=380)
            fig.update_xaxes(title='Net sales',tickprefix='$',tickformat='~s')
            fig.update_yaxes(title=None,showgrid=False)
            render_chart(fig)
    st.subheader('Restaurants Ranked by Net Sales',anchor=False)
    table=pd.DataFrame([{
        'Rank':r['rank'],'Restaurant':display_name(a,r['restaurant_id']),
        'Region':r['region'],'Ownership':r['ownership_type'],'Format':r['restaurant_format'],
        'Net Sales':r['net_sales_usd'],
        'Transactions':r['transactions'],
        'Average Check':r['average_check_usd'],
        'Sales Change':pct_points(r['sales_growth_pct']) if mode!='none' else None,
        'Transaction Change':pct_points(r['transaction_growth_pct']) if mode!='none' else None,
    } for r in active])
    render_grid(table, key='lr-restaurant-rankings', height=470,
                formats={'Rank':'count', 'Net Sales':'money', 'Transactions':'count',
                         'Average Check':'price', 'Sales Change':'growth',
                         'Transaction Change':'growth'},
                change_columns=('Sales Change','Transaction Change'),
                widths={'Restaurant':175, 'Region':110, 'Ownership':115,
                        'Format':140, 'Net Sales':140, 'Transactions':125,
                        'Average Check':135, 'Sales Change':130,
                        'Transaction Change':170})
    st.download_button('Download Restaurant Table (CSV)',table.to_csv(index=False).encode('utf-8'),
                       file_name='lunch_rush_restaurants.csv',mime='text/csv')
    if mode != 'none':
        st.caption('Each row shows how that restaurant performed against the selected comparison period. The same-store result above includes only established restaurants with complete data in both periods.')


def channels_dayparts():
    show_completeness(current)
    for field,title in [('channel','Ordering Channels'),('daypart','Daypart Performance')]:
        st.subheader(title,anchor=False)
        breakdown=mix_breakdown(a,start,end,ids,by=field)
        if not breakdown or not current['net_sales_usd']:
            st.info('No sales in the selected scope.');continue
        # Put the breakdown chart above the full-width table so long column labels
        # and comma-separated values stay legible on a typical laptop screen.
        with st.container(key=f'lr_breakdown_{field}'):
            st.subheader('Share of Net Sales',anchor=False)
            fig=go.Figure(go.Pie(labels=[r['name'] for r in breakdown],
                values=[r['net_sales_usd'] for r in breakdown],hole=.58,
                marker=dict(colors=[BLUE,GREEN,CORAL,'#8190AC','#BCC5D7'][:len(breakdown)]),
                textinfo='percent',textposition='inside',insidetextorientation='horizontal',
                textfont=dict(size=13,color='#FFFFFF'),
                hovertemplate='%{label}<br>Net sales: $%{value:,.0f}<extra></extra>'))
            chart_style(fig,height=275)
            fig.update_layout(
                showlegend=False,
                hoverlabel=dict(bgcolor='#FFFFFF', bordercolor='#DDE2F8',
                                font=dict(color=NAVY, size=16, family='Arial, sans-serif'),
                                align='left'),
            )
            chart_key([(f"{r['name']}: {100 * r['net_sales_usd'] / current['net_sales_usd']:.1f}% of sales", color)
                       for r, color in zip(breakdown, [BLUE,GREEN,CORAL,'#8190AC','#BCC5D7'])])
            render_chart(fig)
        rows=[]
        for r in breakdown:
            comparison=a.compare_sales(start,end,mode=mode,restaurant_ids=ids,**{field:r['name']})
            rows.append({'Segment':r['name'],'Net Sales':r['net_sales_usd'],
                'Sales Mix':pct_points(r['net_sales_usd']/current['net_sales_usd']),
                'Transactions':r['transactions'],
                'Average Check':r['average_check_usd'],
                'Sales Change':pct_points(comparison['sales_growth_pct']) if mode!='none' else None,
                'Transaction Change':pct_points(comparison['transaction_growth_pct']) if mode!='none' else None})
        with st.container(key=f'lr_table_{field}'):
            render_grid(pd.DataFrame(rows), key=f'lr-{field}-breakdown',
                        formats={'Net Sales':'money','Sales Mix':'pct','Transactions':'count',
                                 'Average Check':'price','Sales Change':'growth',
                                 'Transaction Change':'growth'},
                        change_columns=('Sales Change','Transaction Change'),
                        widths={'Segment':135,'Net Sales':145,'Sales Mix':110,
                                'Transactions':140,'Average Check':135,
                                'Sales Change':145,'Transaction Change':170})
        if field == 'daypart':
            st.caption('Channel and daypart are different views of the same sales; do not add them together.')


def menu_performance():
    menu=a.menu_summary(start,end,restaurant_ids=ids)
    show_completeness(menu,menu=True)
    st.subheader('Menu Overview',anchor=False)
    col=st.columns(3,gap='small')
    col[0].metric('Reported Menu Sales',format_money(menu['menu_total_usd'],compact=True))
    col[1].metric('Menu Items',len(menu['items']))
    col[2].metric('Complete Menu Store-Weeks',format_int(menu['eligible_store_weeks']))
    if not menu['items']:
        st.info('No menu records in this selection.');return
    st.caption('For weeks with complete data, menu-item sales add up to the restaurant sales reported in Lunch Rush.')
    cats=category_summary(menu)
    left,right=st.columns([1,1.18],gap='medium')
    with left:
        with st.container(key='lr_chart_menu_categories'):
            st.subheader('Sales by Menu Category',anchor=False)
            rows=pd.DataFrame(cats).sort_values('net_sales_usd')
            fig=px.bar(rows,x='net_sales_usd',y='category',orientation='h',color_discrete_sequence=[BLUE])
            chart_style(fig,height=max(290,len(rows)*39))
            fig.update_xaxes(title='Net sales',tickprefix='$',tickformat='~s')
            fig.update_yaxes(title=None,showgrid=False)
            render_chart(fig)
    with right:
        st.subheader('Category Mix',anchor=False)
        render_grid(pd.DataFrame([{'Category':r['category'],
            'Net Sales':r['net_sales_usd'],
            'Sales Mix':pct_points(r['mix_pct']),
            'Units':r['units_sold']} for r in cats]),
            key='lr-menu-categories',
            formats={'Net Sales':'money','Sales Mix':'pct','Units':'count'},
            widths={'Category':135,'Net Sales':150,'Sales Mix':125,'Units':125})
    st.subheader('Menu-Item Performance',anchor=False)
    matched=matched_menu_growth(a,start,end,ids,mode)
    if mode!='none':st.caption('Menu-item growth compares sales at the same established restaurants in both time periods.')
    rows=pd.DataFrame([{'Item':r['menu_item_name'],'Category':r['category'],
        'Net Sales':r['net_sales_usd'],'Units':r['units_sold'],
        'Sales Mix':pct_points(r['mix_pct']),
        'Realized Price':r['realized_item_price_usd'],
        'Attach Rate':pct_points(r['attach_rate']),
        'Comparable Item Growth':pct_points(matched.get(r['menu_item_id'])) if mode!='none' else None}
        for r in menu['items']])
    render_grid(rows, key='lr-menu-items', height=480,
                formats={'Net Sales':'money','Units':'count','Sales Mix':'pct',
                         'Realized Price':'price','Attach Rate':'pct',
                         'Comparable Item Growth':'growth'},
                change_columns=('Comparable Item Growth',),
                widths={'Item':205,'Category':130,'Net Sales':145,'Units':115,
                        'Sales Mix':115,'Realized Price':150,'Attach Rate':125,
                        'Comparable Item Growth':205})
    st.download_button('Download Menu Table (CSV)',rows.to_csv(index=False).encode('utf-8'),
                       file_name='lunch_rush_menu.csv',mime='text/csv')
    st.caption('Attach rate is the percentage of orders that included an item. It appears only when complete order-level data is available.')


def insights():
    st.subheader('Performance Signals',anchor=False)
    st.caption('Rules identify measurable changes, not verified causes. They reflect the selected restaurants and comparison period.')
    if mode=='none':st.info('Select a comparison period to view diagnostics.')
    elif not findings:st.info('No diagnostic thresholds were crossed. This does not prove all performance is healthy.')
    else:
        for d in findings:
            with st.container(border=True):
                st.markdown('**'+escape(insight_name(d))+' · Watch**')
                st.write(d['finding'])
                evidence=[]
                for k,v in d['evidence'].items():
                    if k.endswith('_pct') and v is not None:
                        evidence.append(k.replace('_pct','').replace('_',' ').capitalize()+': '+format_pct(v))
                    elif k=='eligible_restaurants': evidence.append(f'Matched locations: {v}')
                if evidence: st.caption(' · '.join(evidence))
                st.markdown('**Investigate:** '+safe_md(d['investigate']))
    st.subheader('Data Quality & Exclusions',anchor=False)
    sales=a.sales_summary(start,end,restaurant_ids=ids)
    menu=a.menu_summary(start,end,restaurant_ids=ids)
    render_grid(pd.DataFrame([
        {'Check':'POS store-weeks','Complete Store-Weeks':sales['eligible_store_weeks'],
         'Incomplete Store-Weeks':sales['incomplete_store_weeks'],
         'Status':'Complete' if sales['complete'] else 'Review'},
        {'Check':'Menu store-weeks','Complete Store-Weeks':menu['eligible_store_weeks'],
         'Incomplete Store-Weeks':menu['incomplete_store_weeks'],
         'Status':'Complete' if menu['complete'] else 'Review'},
    ]), key='lr-data-quality',
        formats={'Complete Store-Weeks':'count','Incomplete Store-Weeks':'count'},
        widths={'Check':180,'Complete Store-Weeks':220,
                'Incomplete Store-Weeks':230,'Status':130})
    if same:
        st.caption(f'Comparable cohort: {same["eligible_restaurants"]} included, '
                   f'{same["excluded_restaurants"]} excluded.')
        if same['exclusions_by_reason']:
            with st.expander('Comparable-store exclusions'):
                for why,count in same['exclusions_by_reason'].items():
                    st.markdown(f'- {escape(why.replace("_"," ").capitalize())}: **{count}**')
    if valid.warnings:
        with st.expander('Source warnings'):
            for warning in valid.warnings:st.caption('• '+warning)


tab_overview, tab_locations, tab_channels, tab_menu, tab_insights = st.tabs([
    'Overview','Restaurants','Channels & Dayparts','Menu Performance','Insights',
])
with tab_overview:overview()
with tab_locations:restaurants()
with tab_channels:channels_dayparts()
with tab_menu:menu_performance()
with tab_insights:insights()

