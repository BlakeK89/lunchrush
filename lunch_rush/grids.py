"""Reliable, sortable Lunch Rush tables using Streamlit's native data grid.

The earlier AG Grid customization distorted cell placement on the deployed app.
Native dataframe columns keep numeric sorting, explicit centered alignment,
positive/negative highlighting, and all original fields available by scrolling.
CSV exports continue to use the original numeric dataframes in app.py.
"""
from __future__ import annotations

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


def _format_value(kind):
    """Format displayed numbers without changing numeric dataframe columns."""
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
    """Readable signed changes, based on displayed one-decimal percentages."""
    if pd.isna(value):
        return ''
    rounded = round(float(value), 1)
    if rounded > 0:
        return 'color: #166534; background-color: #DCFCE7; font-weight: bold;'
    if rounded < 0:
        return 'color: #991B1B; background-color: #FEE2E2; font-weight: bold;'
    return ''


def prepare_table(frame, *, key, formats=None, change_columns=()):
    """Return a styled dataframe with an intuitive, per-page column order."""
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame(frame)
    columns = DISPLAY_ORDER.get(key)
    if columns:
        frame = frame[[c for c in columns if c in frame.columns] +
                      [c for c in frame.columns if c not in columns]]
    style = frame.style
    formats = formats or {}
    applied = {name: _format_value(kind) for name, kind in formats.items() if name in frame}
    if applied:
        style = style.format(applied, na_rep='—')
    for name in change_columns:
        if name in frame:
            style = style.map(_change_style, subset=[name])
    return frame, style


def column_settings(frame, *, widths=None):
    """Use actual Streamlit alignment, not CSS that affects grid positioning."""
    widths = widths or {}
    config = {}
    for name in frame.columns:
        width = widths.get(name)
        # Key identifiers stay visible when horizontal scrolling is necessary.
        pinned = name in {'Restaurant', 'Item'}
        args = {'label': LABELS.get(name, name), 'alignment': 'center',
                'pinned': pinned}
        if width is not None:
            args['width'] = width
        if pd.api.types.is_numeric_dtype(frame[name]):
            config[name] = st.column_config.NumberColumn(**args)
        else:
            config[name] = st.column_config.TextColumn(**args)
    return config


def render_grid(frame, *, key, formats=None, change_columns=(), widths=None,
                height=None):
    """Render with deterministic columns, sorting, and compact height."""
    raw, styled = prepare_table(frame, key=key, formats=formats,
                                change_columns=change_columns)
    if height is None:
        height = min(490, max(120, 38 + 35 * len(raw)))
    return st.dataframe(styled, hide_index=True, width='stretch', height=height,
                        column_config=column_settings(raw, widths=widths), key=key)
