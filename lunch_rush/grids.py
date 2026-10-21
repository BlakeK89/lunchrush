"""Centered, sortable HTML data tables for Lunch Rush.

Native st.dataframe draws header text on a canvas; its alignment option applies
only to *cells*. CSS and Pandas Styler cannot center its column headers.
This renderer uses semantic HTML headers, safe escaped cell text, and a small
local sorter. All source data and CSV export paths in app.py stay unchanged.
"""
from __future__ import annotations

from html import escape
import json
import re

import pandas as pd
import streamlit as st


DISPLAY_ORDER = {
    'lr-restaurant-rankings': ['Rank', 'Restaurant', 'Net Sales', 'Sales Change',
                               'Transactions', 'Transaction Change', 'Average Check',
                               'Region', 'Ownership', 'Format'],
    'lr-channel-breakdown': ['Segment', 'Net Sales', 'Sales Change', 'Transactions',
                             'Transaction Change', 'Sales Mix', 'Average Check'],
    'lr-daypart-breakdown': ['Segment', 'Net Sales', 'Sales Change', 'Transactions',
                             'Transaction Change', 'Sales Mix', 'Average Check'],
    'lr-menu-categories': ['Category', 'Net Sales', 'Sales Mix', 'Units'],
    'lr-menu-items': ['Item', 'Net Sales', 'Comparable Item Growth', 'Units',
                      'Sales Mix', 'Attach Rate', 'Realized Price', 'Category'],
    'lr-data-quality': ['Check', 'Complete Store-Weeks', 'Incomplete Store-Weeks', 'Status'],
}

LABELS = {
    'Complete Store-Weeks': 'Complete Restaurant-Weeks',
    'Incomplete Store-Weeks': 'Incomplete Restaurant-Weeks',
    'Comparable Item Growth': 'Same-Store Item Growth',
    'Realized Price': 'Average Price',
}

IDENTITY_COLUMNS = {'Restaurant', 'Item', 'Category', 'Segment', 'Check'}


def _format_value(kind):
    """Match existing display precision; do not alter numeric data for sorting."""
    def format_number(value):
        if pd.isna(value):
            return '—'
        n = float(value)
        if kind == 'money':
            return f'{"−" if n < 0 else ""}${abs(n):,.0f}'
        if kind == 'price':
            return f'{"−" if n < 0 else ""}${abs(n):,.2f}'
        if kind == 'count':
            return f'{n:,.0f}'
        if kind == 'growth':
            return f'{n:+.1f}%'
        if kind == 'pct':
            return f'{n:.1f}%'
        return str(value)
    return format_number


def _change_style(value):
    """Keep red/green change coloring consistent with one-decimal precision."""
    if pd.isna(value):
        return ''
    rounded = round(float(value), 1)
    if rounded > 0:
        return 'color: #166534; background-color: #DCFCE7; font-weight: bold;'
    if rounded < 0:
        return 'color: #991B1B; background-color: #FEE2E2; font-weight: bold;'
    return ''


def prepare_table(frame, *, key, formats=None, change_columns=()):
    """Reorder columns, preserving every field and its original numeric type."""
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame(frame)
    columns = DISPLAY_ORDER.get(key)
    if columns:
        frame = frame[[c for c in columns if c in frame.columns] +
                      [c for c in frame.columns if c not in columns]]
    return frame, frame.style


def _is_missing(value):
    return value is None or bool(pd.isna(value))


def _display(value, formatter=None):
    if _is_missing(value):
        return '—'
    return formatter(value) if formatter else str(value)


def _cell_width(column, widths):
    default = 80 if column == 'Rank' else 130
    width = widths.get(column, default)
    if not isinstance(width, (int, float)):
        raise ValueError(f'Invalid column width: {column}')
    return max(65, min(800, int(width)))


def table_html(frame, *, key, formats=None, change_columns=(), widths=None,
               height=None):
    """Create safe standalone markup with real centered <th> elements.

    The header and data columns share an HTML table and <colgroup>; unlike the
    earlier AG Grid CSS, no cell width/position overrides can detach values
    from their column headings. Sorting operates on raw numeric data-sort keys.
    """
    frame, _ = prepare_table(frame, key=key)
    formats = formats or {}
    widths = widths or {}
    change_columns = frozenset(change_columns)
    identifier = 'lr-html-' + re.sub(r'[^A-Za-z0-9_-]+', '-', key)
    grid_height = min(490, max(120, 44 + 36 * len(frame))) if height is None else int(height)
    grid_height = max(100, min(1200, grid_height))
    column_widths = [_cell_width(c, widths) for c in frame.columns]
    numeric = [pd.api.types.is_numeric_dtype(frame[c]) for c in frame.columns]
    pinned = []
    if key == 'lr-restaurant-rankings' and 'Rank' in frame and 'Restaurant' in frame:
        pinned = ['Rank', 'Restaurant']
    elif frame.columns.tolist() and frame.columns[0] in IDENTITY_COLUMNS:
        pinned = [frame.columns[0]]
    left_offsets = {}
    total = 0
    for col in pinned:
        left_offsets[col] = total
        total += column_widths[list(frame.columns).index(col)]
    parts = [
        '<div class="lr-table-widget" id="' + identifier + '">',
        '<style>\n' + _STYLES.replace('__ID__', '#' + identifier) + '\n</style>',
        '<div class="lr-table-scroll" role="region" tabindex="0" '
        f'aria-label="{escape(key.replace("lr-", "").replace("-", " ").title())} table" '
        f'style="max-height:{grid_height}px">',
        '<table><colgroup>',
    ]
    for width in column_widths:
        parts.append(f'<col style="width:{width}px">')
    parts.extend(['</colgroup><thead><tr>'])
    for idx, name in enumerate(frame.columns):
        label = escape(LABELS.get(name, name))
        pin = f' class="lr-pinned" style="left:{left_offsets[name]}px"' if name in pinned else ''
        column_type = 'number' if numeric[idx] else 'text'
        parts.append(
            f'<th scope="col" aria-sort="none" data-kind="{column_type}"{pin}>'
            f'<button type="button" class="lr-sort-button" data-index="{idx}" '
            f'aria-label="Sort by {escape(LABELS.get(name, name), quote=True)}">'
            f'<span>{label}</span><span class="lr-sort-indicator" aria-hidden="true">↕</span>'
            '</button></th>'
        )
    parts.append('</tr></thead><tbody>')
    for _, row in frame.iterrows():
        parts.append('<tr>')
        for idx, name in enumerate(frame.columns):
            value = row[name]
            missing = _is_missing(value)
            display = _display(value, _format_value(formats[name]) if name in formats else None)
            classes = ['lr-td']
            if name in IDENTITY_COLUMNS:
                classes.append('lr-identity')
            if missing:
                classes.append('lr-missing')
            if name in change_columns and not missing:
                style = _change_style(value)
                if '#DCFCE7' in style:
                    classes.append('lr-up')
                elif '#FEE2E2' in style:
                    classes.append('lr-down')
            if name in pinned:
                classes.append('lr-pinned')
            if numeric[idx] and not missing:
                sort_value = f'{float(value):.17g}'
            elif missing:
                sort_value = ''
            else:
                sort_value = str(value)
            attrs = (f'class="{" ".join(classes)}" '
                     f'data-sort="{escape(sort_value, quote=True)}" '
                     f'data-missing="{int(missing)}"')
            if name in pinned:
                attrs += f' style="left:{left_offsets[name]}px"'
            parts.append(f'<td {attrs}>{escape(display)}</td>')
        parts.append('</tr>')
    parts.append('</tbody></table></div></div>')
    # Only the sanitized internal widget ID appears in JavaScript. All data is
    # escaped HTML; table text is never compiled into executable script.
    parts.append('<script>\n' + _SORT_SCRIPT.replace('__ID__', json.dumps(identifier)) + '\n</script>')
    return ''.join(parts)


def render_grid(frame, *, key, formats=None, change_columns=(), widths=None,
                height=None):
    """Display an interactive, centered-header table in Streamlit >=1.52."""
    return st.html(table_html(frame, key=key, formats=formats,
                              change_columns=change_columns, widths=widths,
                              height=height),
                   width='stretch', unsafe_allow_javascript=True)


_STYLES = r'''
__ID__ { width:100%; font-family:inherit; color:#081043; }
__ID__ .lr-table-scroll { width:100%; overflow:auto; border:1px solid #DDE2F8;
  border-radius:8px; background:#FFF; scrollbar-gutter:stable; }
__ID__ table { border-spacing:0; border-collapse:separate; table-layout:fixed;
  width:max-content; min-width:100%; font-size:12px; line-height:1.35; }
__ID__ th, __ID__ td { box-sizing:border-box; padding:9px 8px;
  border-right:1px solid #E7EAF2; border-bottom:1px solid #E7EAF2;
  text-align:center !important; vertical-align:middle; overflow-wrap:anywhere; }
__ID__ th:last-child, __ID__ td:last-child { border-right:0; }
__ID__ tbody tr:last-child td { border-bottom:0; }
__ID__ thead th { position:sticky; top:0; z-index:3; padding:0;
  color:#000 !important; font-weight:800 !important; background:#EAF0FF;
  height:46px; }
__ID__ .lr-sort-button { display:flex; align-items:center; justify-content:center;
  text-align:center !important; width:100%; min-height:46px; gap:5px;
  font-family:inherit; font-size:12px; font-weight:800; line-height:1.25;
  color:#000 !important; background:transparent; border:0; border-radius:0;
  padding:5px 7px; cursor:pointer; box-sizing:border-box; }
__ID__ .lr-sort-button:hover { background:#DDE7FF; }
__ID__ .lr-sort-button:focus-visible { outline:2px solid #003BFF; outline-offset:-3px; }
__ID__ .lr-sort-indicator { flex:0 0 auto; color:#5F6B86; font-size:11px; }
__ID__ tbody tr { --lr-row-bg:#FFF; }
__ID__ tbody tr:nth-child(even) { --lr-row-bg:#FAFBFF; }
__ID__ td { background:var(--lr-row-bg); color:#081043; font-weight:500; }
__ID__ tbody tr:hover { --lr-row-bg:#F0F4FF; }
__ID__ td.lr-identity { color:#000 !important; font-weight:650; }
__ID__ td.lr-missing { color:#344054 !important; font-weight:650; }
__ID__ td.lr-up { color:#166534; background:#DCFCE7; font-weight:700; }
__ID__ td.lr-down { color:#991B1B; background:#FEE2E2; font-weight:700; }
__ID__ .lr-pinned { position:sticky; z-index:2; background:var(--lr-row-bg); }
__ID__ thead .lr-pinned { z-index:4; background:#EAF0FF; }
'''

_SORT_SCRIPT = r'''(() => {
  const widget = document.getElementById(__ID__);
  if (!widget) return;
  const table = widget.querySelector('table');
  const body = table.tBodies[0];
  const headers = Array.from(table.tHead.rows[0].cells);
  let current = -1;
  let ascending = true;
  const collator = new Intl.Collator(undefined, {numeric:true, sensitivity:'base'});
  for (const [index, th] of headers.entries()) {
    const button = th.querySelector('button');
    button.addEventListener('click', () => {
      ascending = current === index ? !ascending : true;
      current = index;
      const isNumeric = th.dataset.kind === 'number';
      const rows = Array.from(body.rows);
      rows.sort((a, b) => {
        const ac = a.cells[index], bc = b.cells[index];
        const am = ac.dataset.missing === '1', bm = bc.dataset.missing === '1';
        if (am !== bm) return am ? 1 : -1; // Always put missing values last.
        if (am) return 0;
        const aKey = ac.dataset.sort, bKey = bc.dataset.sort;
        const comparison = isNumeric
          ? Number(aKey) - Number(bKey) : collator.compare(aKey, bKey);
        return ascending ? comparison : -comparison;
      });
      body.replaceChildren(...rows);
      headers.forEach((header, position) => {
        header.setAttribute('aria-sort', position === index
          ? (ascending ? 'ascending' : 'descending') : 'none');
        header.querySelector('.lr-sort-indicator').textContent = position === index
          ? (ascending ? '↑' : '↓') : '↕';
      });
    });
  }
})();'''
