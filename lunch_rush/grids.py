"""Centered, sortable Lunch Rush tables using Shelf Life's AG Grid approach.

All JavaScript formatters are static. Raw numeric values remain available for
numeric sorting and existing CSV exports. No data is interpolated into JS.
"""
from __future__ import annotations

from st_aggrid import AgGrid, JsCode


GRID_CSS = {
    '.ag-root-wrapper': {
        '--ag-header-foreground-color': '#000000',
        '--ag-header-background-color': '#EAF0FF',
        'font-size': '13px',
    },
    '.ag-header': {'background-color': '#EAF0FF !important', 'color': '#000000 !important'},
    '.ag-header-cell': {'color': '#000000 !important'},
    '.ag-header .ag-header-cell-text': {
        'color': '#000000 !important', 'font-weight': '750 !important',
        'opacity': '1 !important', 'text-align': 'center !important',
    },
    '.ag-header .ag-header-cell-label': {'justify-content': 'center !important'},
    '.ag-cell': {'text-align': 'center !important', 'color': '#081043'},
    '.ag-cell-value': {'width': '100% !important', 'text-align': 'center !important'},
    '.ag-header .ag-icon': {'color': '#000000 !important', 'opacity': '1 !important'},
}

# Signed changes are in percentage points, not fractions. Round to the same
# one decimal displayed by the formatter before applying color.
CHANGE_CELL_STYLE = JsCode("""function(p) {
  const base = {textAlign:'center', display:'flex', justifyContent:'center'};
  if (p.value == null || p.value === '') return base;
  const n = Number(p.value);
  if (!Number.isFinite(n) || Math.round(n * 10) === 0) return base;
  if (n > 0) return {...base, color:'#166534', backgroundColor:'#DCFCE7', fontWeight:'700'};
  return {...base, color:'#991B1B', backgroundColor:'#FEE2E2', fontWeight:'700'};
}""")

FORMATTERS = {
    'money': JsCode("""function(p) {
      if (p.value == null || !Number.isFinite(Number(p.value))) return 'N/A';
      const n = Number(p.value);
      return (n < 0 ? '-$' : '$') + Math.abs(n).toLocaleString('en-US',
        {minimumFractionDigits:0,maximumFractionDigits:0});
    }"""),
    'price': JsCode("""function(p) {
      if (p.value == null || !Number.isFinite(Number(p.value))) return 'N/A';
      return '$' + Number(p.value).toLocaleString('en-US',
        {minimumFractionDigits:2,maximumFractionDigits:2});
    }"""),
    'count': JsCode("""function(p) {
      if (p.value == null || !Number.isFinite(Number(p.value))) return 'N/A';
      return Number(p.value).toLocaleString('en-US',{maximumFractionDigits:0});
    }"""),
    'pct': JsCode("""function(p) {
      if (p.value == null || !Number.isFinite(Number(p.value))) return 'N/A';
      return Number(p.value).toFixed(1) + '%';
    }"""),
    'growth': JsCode("""function(p) {
      if (p.value == null || !Number.isFinite(Number(p.value))) return 'N/A';
      const n = Number(p.value);
      const rounded = Number(n.toFixed(1));
      return (rounded > 0 ? '+' : '') + rounded.toFixed(1) + '%';
    }"""),
}


def make_grid_options(frame, *, formats=None, change_columns=(), widths=None):
    """Fully center every data cell and header, retaining native numeric sorting."""
    formats = formats or {}
    widths = widths or {}
    change_columns = frozenset(change_columns)
    cols = []
    for name in frame.columns:
        opts = {
            'field': name, 'headerName': name,
            'headerClass': 'lr-center-header',
            'cellStyle': {'textAlign': 'center', 'display': 'flex', 'justifyContent': 'center'},
            'minWidth': widths.get(name, 120),
            'sortable': True, 'resizable': True,
            'wrapHeaderText': True, 'autoHeaderHeight': True,
            'tooltipField': name,
        }
        if name in change_columns:
            opts['cellStyle'] = CHANGE_CELL_STYLE
        if name in formats:
            opts['valueFormatter'] = FORMATTERS[formats[name]]
        cols.append(opts)
    return {
        'columnDefs': cols,
        'defaultColDef': {'sortable': True, 'resizable': True, 'filter': False},
        'rowHeight': 38,
        'headerHeight': 55,
        'suppressMovableColumns': True,
        'suppressRowClickSelection': True,
        'ensureDomOrder': True,
        'tooltipShowDelay': 350,
    }


def render_grid(frame, *, key, formats=None, change_columns=(), widths=None,
                height=None):
    """Show a bounded interactive table; short tables are fully visible."""
    opts = make_grid_options(frame, formats=formats,
                             change_columns=change_columns, widths=widths)
    if len(frame) <= 8:
        opts['domLayout'] = 'autoHeight'
    target_height = min(490, max(132, 64 + 38 * len(frame)))
    if height is not None:
        target_height = height
    return AgGrid(
        frame, gridOptions=opts, custom_css=GRID_CSS,
        theme='streamlit', height=target_height,
        fit_columns_on_grid_load=False,
        allow_unsafe_jscode=True,
        enable_enterprise_modules=False,
        update_on=[], key=key,
    )
