"""Shared Brand Rundown UI patterns adapted from the live Shelf Life app.

Brand source: Brand Rundown revised brand guidelines and the current Shelf Life
`app.py` on GitHub, reviewed October 20, 2026. Logo assets are not modified.
"""

ELECTRIC_BLUE = '#0032FF'
CREAM = '#FFF2DF'
CORAL = '#FF535C'
NAVY = '#081043'
PAPER = '#FAF8F3'
BORDER = '#DDE2F8'
LUNCH_GREEN = '#00A95C'

STYLES = r"""
<style>
:root {
    --br-electric: #0032FF;
    --br-cream: #FFF2DF;
    --br-coral: #FF535C;
    --br-navy: #081043;
    --br-paper: #FAF8F3;
    --br-border: #DDE2F8;
    --lr-green: #00A95C;
}
.block-container {max-width: 1340px; padding-top: 2rem; padding-bottom: 3rem;}
div[data-testid="stAppViewContainer"] {background:var(--br-paper); color:var(--br-navy);}
h1,h2,h3 {color: var(--br-navy); letter-spacing:-.03em;}
h2,h3 {font-weight:800 !important;}
div[data-testid="stCaptionContainer"],div[data-testid="stCaptionContainer"] p {
    font-size:1rem; line-height:1.5; color:var(--br-navy); opacity:1;
}
/* Header: same position, proportions and Brand Rundown divider as Shelf Life. */
.st-key-br_identity_header {
    position:relative; padding:.95rem .1rem 1.05rem; margin-bottom:.65rem;
    border-bottom:4px solid var(--br-electric); overflow:visible !important;
}
.st-key-br_identity_header::after {
    content:""; position:absolute; bottom:-4px; left:0; height:4px;
    width:94px; background:var(--br-coral);
}
.st-key-br_identity_header [data-testid="stImage"],
.st-key-br_identity_header [data-testid="stImage"] img {overflow:visible !important;}
.st-key-br_identity_header [data-testid="stImage"] img {
    display:block; box-sizing:border-box !important;
    width:min(300px,100%) !important; height:auto !important;
    max-height:none !important; padding:16px 12px 12px 8px !important;
    object-fit:contain !important;
    object-position:left center; clip-path:none !important;
}
.br-screen-reader-heading {
    position:absolute !important; height:1px !important; width:1px !important;
    overflow:hidden !important; clip-path:inset(50%) !important;
}
.st-key-br_identity_header button {
    border:1.5px solid var(--br-electric) !important; background:#fff !important;
    color:var(--br-navy) !important; border-radius:.7rem !important;
    font-weight:750 !important; box-shadow:2px 2px 0 var(--br-border);
}
.st-key-br_identity_header button:hover {border-color:var(--br-coral) !important; color:var(--br-electric) !important;}
/* Blue sidebar and actionable source choices: same foundation as Shelf Life. */
section[data-testid="stSidebar"] {background:var(--br-electric) !important; border-right:0 !important;}
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"],
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p,
section[data-testid="stSidebar"] [data-testid="stRadio"] label p {
    color:#fff !important; opacity:1 !important;
}
section[data-testid="stSidebar"] h2 {font-size:1.25rem !important;font-weight:850 !important;}
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p {font-size:.95rem !important;font-weight:750 !important;}
section[data-testid="stSidebar"] hr {border-color:rgba(255,255,255,.42);}
section[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background:#fff !important; border:1px solid #CAD8FF; border-radius:.6rem;
}
section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] *,
section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] button {color:#fff !important;}
section[data-testid="stSidebar"] [data-testid="stSidebarContent"],
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    scrollbar-color:#fff rgba(255,255,255,.18);
}
section[data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] * {
    color:#fff !important;stroke:#fff !important;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] {
    border-color:rgba(255,255,255,.35);background:rgba(8,16,67,.18);
}
section[data-testid="stSidebar"] [data-testid="stExpander"] summary,
section[data-testid="stSidebar"] [data-testid="stExpander"] summary *,
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderToggleIcon"] {
    color:#fff !important;stroke:#fff !important;opacity:1 !important;font-weight:650;
}
section[data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stWidgetLabel"] p {
    color:#fff !important;
}
section[data-testid="stSidebar"] .st-key-br_data_source_control,
section[data-testid="stSidebar"] .st-key-br_data_source_control [role="radiogroup"],
section[data-testid="stSidebar"] .st-key-br_data_source_control [role="radiogroup"]>div {
    width:100% !important; box-sizing:border-box;
}
section[data-testid="stSidebar"] .st-key-br_data_source_control [data-testid="stRadio"] label:has(input[type="radio"]) {
    position:relative; display:flex !important; align-items:center;
    box-sizing:border-box !important; width:100% !important; min-height:3.6rem;
    padding:.4rem 1.75rem .4rem .65rem;
    border:1.5px solid rgba(255,255,255,.7); border-radius:.7rem;
    background:rgba(8,16,67,.16); margin:.2rem 0; cursor:pointer;
}
/* Avoid default red native radio indicator if the hidden Streamlit theme is missing. */
section[data-testid="stSidebar"] .st-key-br_data_source_control input[type="radio"] {
    accent-color:var(--br-electric) !important;
}
section[data-testid="stSidebar"] .st-key-br_data_source_control [data-testid="stRadio"] label:has(input[type="radio"])::before {
    content:"";position:absolute;left:.7rem;top:50%;transform:translateY(-50%);
    width:12px;height:12px;box-sizing:border-box;border-radius:50%;
    background:#fff;border:2px solid #fff;z-index:2;pointer-events:none;
}
section[data-testid="stSidebar"] .st-key-br_data_source_control [data-testid="stRadio"] label:has(input:checked)::before {
    background:var(--br-electric);border-color:var(--br-electric);
    box-shadow:inset 0 0 0 2px var(--br-cream);
}
section[data-testid="stSidebar"] .st-key-br_data_source_control label:has(input[type="radio"]) [data-checked="true"],
section[data-testid="stSidebar"] .st-key-br_data_source_control label:has(input:checked) [data-testid="stRadio"] svg {
    color:var(--br-electric) !important;fill:var(--br-electric) !important;
}
section[data-testid="stSidebar"] .st-key-br_data_source_control [data-testid="stRadio"] label:has(input:checked) {
    background:var(--br-cream) !important; border-color:var(--br-cream) !important;
    box-shadow:3px 3px 0 var(--br-navy);
}
section[data-testid="stSidebar"] .st-key-br_data_source_control [data-testid="stRadio"] label:has(input:checked) p {
    color:var(--br-navy) !important;font-weight:800 !important;
}
section[data-testid="stSidebar"] .st-key-br_data_source_control [data-testid="stRadio"] label:has(input:checked)::after {
    content:"✓"; position:absolute; right:.7rem; top:50%; transform:translateY(-50%);
    color:var(--br-electric);font-weight:900;
}
section[data-testid="stSidebar"] .st-key-br_upload_panel {
    background:var(--br-cream); padding:.6rem; border:2px solid #fff; border-radius:.8rem;
}
section[data-testid="stSidebar"] .st-key-br_upload_panel [data-testid="stFileUploaderDropzone"] {
    background:var(--br-cream) !important; border:2px dashed var(--br-electric) !important;
    border-radius:.65rem !important;
}
section[data-testid="stSidebar"] .st-key-br_upload_panel [data-testid="stFileUploaderDropzone"] *,
section[data-testid="stSidebar"] .st-key-br_upload_panel [data-testid="stWidgetLabel"] p {color:var(--br-navy) !important;}
section[data-testid="stSidebar"] .st-key-br_upload_warning [data-testid="stAlert"] {
    background:var(--br-cream) !important; color:var(--br-navy) !important;
    border-left:5px solid var(--br-coral);border-radius:.6rem;
}
section[data-testid="stSidebar"] .st-key-br_upload_warning [data-testid="stAlert"] * {color:var(--br-navy) !important;}
/* Download sample data is secondary, at the bottom of the settings sidebar. */
section[data-testid="stSidebar"] .st-key-br_sample_download {
    border-top:1px solid rgba(255,255,255,.42);padding-top:.8rem;margin-top:1.15rem;
}
section[data-testid="stSidebar"] .st-key-br_sample_download button {
    background:transparent !important;border:1px solid rgba(255,255,255,.75) !important;
    color:#fff !important;border-radius:.48rem !important;font-size:.78rem !important;
    font-weight:550 !important;line-height:1.25 !important;min-height:0 !important;
    height:auto !important;padding:.4rem .52rem !important;box-shadow:none !important;
    max-width:100% !important;white-space:normal !important;text-align:left !important;
}
section[data-testid="stSidebar"] .st-key-br_sample_download button * {
    color:#fff !important;font-size:inherit !important;font-weight:inherit !important;
}
section[data-testid="stSidebar"] .st-key-br_sample_download button:hover {
    background:rgba(255,255,255,.13) !important;border-color:#fff !important;
}
/* Shelf Life reporting context. */
.st-key-br_reporting_context {
    background:var(--br-cream); border:1.5px solid var(--br-border);
    border-left:5px solid var(--br-coral); border-radius:.9rem;
}
.st-key-br_reporting_context [data-testid="stVerticalBlockBorderWrapper"] {border-color:transparent;}
/* Five upper metrics: same sizing, accent and surface. */
div[data-testid="stMetric"] {
    background:#fff; border:1px solid var(--br-border);
    border-top:4px solid var(--br-electric); border-radius:.9rem;
    padding:.85rem .95rem; box-shadow:0 3px 12px rgba(8,16,67,.055);
}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] * {
    overflow:visible !important;white-space:normal !important;text-overflow:clip !important;
}
[data-testid="stMetricLabel"] {min-height:2.5rem;align-items:flex-start !important;}
div[data-testid="stMetricLabel"] p {
    font-size:.8rem !important; font-weight:750 !important;
    line-height:1.2;overflow-wrap:anywhere !important;color:var(--br-navy) !important;
}
div[data-testid="stMetricValue"] {
    font-size:clamp(1.25rem,1.55vw,1.8rem) !important;
    font-weight:850 !important;letter-spacing:-.04em !important;color:var(--br-navy) !important;
}
/* Tabs live beneath KPI row, not in sidebar. */
.stTabs [role="tablist"],.stTabs [data-baseweb="tab-list"] {
    display:flex; gap:.5rem; padding:.35rem .1rem .65rem;
    margin-bottom:.35rem;overflow-x:auto;border-bottom:none;
}
.stTabs [role="tablist"]::after {display:none !important;}
.stTabs [role="tab"],.stTabs [data-baseweb="tab"] {
    box-sizing:border-box;min-height:2.8rem;height:auto;
    padding:.65rem 1.05rem;border:1.5px solid var(--br-border) !important;
    border-radius:.65rem !important;background:var(--br-cream) !important;
    color:var(--br-navy) !important;font-weight:800 !important;white-space:nowrap;
}
.stTabs [role="tab"]:hover,.stTabs [data-baseweb="tab"]:hover {
    background:#fff !important;border-color:var(--br-coral) !important;
}
.stTabs [role="tab"][aria-selected="true"],.stTabs [role="tab"][data-selected],
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    background:var(--br-electric) !important;border-color:var(--br-electric) !important;
    color:#fff !important;font-weight:850 !important;
}
.stTabs .react-aria-SelectionIndicator,.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] {display:none !important;}
/* White chart cards on cream canvas, aligned with Shelf Life overview. */
.st-key-br_chart_comparison,.st-key-br_chart_contribution,
.st-key-lr_chart_restaurants_top,.st-key-lr_chart_restaurants_regions,.st-key-lr_chart_menu_categories,
.st-key-lr_breakdown_channel,.st-key-lr_breakdown_daypart {
    background:#fff;border:1px solid var(--br-border);border-radius:.9rem;
    padding:.9rem 1.05rem 1rem;box-shadow:0 3px 12px rgba(8,16,67,.055);
}
.st-key-br_chart_comparison h3,.st-key-br_chart_contribution h3,
.st-key-lr_chart_restaurants_top h3,.st-key-lr_chart_restaurants_regions h3,
.st-key-lr_chart_menu_categories h3,.st-key-lr_breakdown_channel h3,
.st-key-lr_breakdown_daypart h3 {margin-top:0 !important;}
.st-key-br_chart_comparison [data-testid="stCaptionContainer"],
.st-key-br_chart_contribution [data-testid="stCaptionContainer"] {text-align:center;}
/* Use the same single card surface for channel KPI cards as Shelf Life. */
.st-key-lr_drive_card [data-testid="stMetricValue"],
.st-key-lr_other_card [data-testid="stMetricValue"] {
    font-size:clamp(2rem,2.9vw,2.65rem) !important;letter-spacing:-.045em !important;
}
.st-key-lr_drive_card [data-testid="stMetricDelta"],
.st-key-lr_other_card [data-testid="stMetricDelta"] {font-size:1.08rem !important;font-weight:700 !important;}
.st-key-lr_drive_card [data-testid="stMetric"],
.st-key-lr_other_card [data-testid="stMetric"] {padding:1.1rem 1.2rem;}
/* Legends are no longer allowed to float over Plotly data. */
.lr-chart-key {display:flex;justify-content:center;align-items:center;gap:1.45rem;
    min-height:1.6rem;margin:.25rem 0 .2rem;color:var(--br-navy);}
.lr-chart-key-item {display:inline-flex;align-items:center;gap:.45rem;
    font-size:.88rem;font-weight:650;white-space:nowrap;}
.lr-chart-key-dot {display:inline-block;height:.7rem;width:.7rem;flex-shrink:0;border-radius:50%;}
/* Expander text remains readable regardless of light/dark OS theme. */
main div[data-testid="stExpander"] summary {color:var(--br-navy) !important;}
main div[data-testid="stExpander"] summary * {color:var(--br-navy) !important;}
div[data-testid="stExpander"] {border-color:var(--br-border);border-radius:.8rem;}
/* Avoid sidebar native text disappearing on dark backgrounds. */
section[data-testid="stSidebar"] [data-testid="stFileUploader"] {color:var(--br-navy);}
@media(max-width:850px) {
    .lr-chart-key {gap:.7rem;flex-wrap:wrap;}
    .lr-chart-key-item {font-size:.8rem;}
    .block-container {padding-top:1rem;}
    .st-key-br_identity_header {padding:.5rem .1rem .7rem;}
    .st-key-br_identity_header [data-testid="stImage"] img {width:min(245px,100%) !important;}
    div[data-testid="stMetricValue"] {font-size:1.5rem !important;}
    .stTabs [role="tab"],.stTabs [data-baseweb="tab"] {padding:.55rem .8rem !important;}
}
</style>
"""
