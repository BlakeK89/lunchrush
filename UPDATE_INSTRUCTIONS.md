# Lunch Rush — Table Header Alignment Fix

## Why another change was needed

Streamlit's native `st.dataframe` renders its column headers in a canvas.
The `column_config` `alignment="center"` option affects *cell contents*, not
column headers. Neither the prior Pandas Styler nor global CSS can center those
canvas-rendered headings. This was the reason earlier patches were ineffective.

## What changed

`lunch_rush/grids.py` now renders HTML tables with real, centered, bold,
black table headers. There are no global geometry overrides. Tables retain:
- Column click sorting, with numeric sorting using raw numbers;
- Scrollable wide/long tables and pinned restaurant/menu-item identities;
- Currency/count/percentage formatting, red-green change highlights;
- Dark names and clearly visible missing values;
- Original column order and existing separate CSV exports (untouched app.py).

Tradeoff: The new tables do **not** have Streamlit's native grid toolbar,
column resizing or hide-column menu. They retain the capabilities essential
to V1 analytics: sorting, horizontal/vertical scrolling and CSV downloads.

This approach requires Streamlit 1.52+ for `st.html(...,
unsafe_allow_javascript=True)`. The existing repository already requires
`streamlit>=1.56,<2`, so `requirements.txt` needs **no change**.

## Upload to GitHub

Extract this ZIP. Upload `lunch_rush/grids.py` to the *lunch_rush* folder,
replacing the existing file. Upload `tests/test_app_ui_smoke.py` to *tests*.
Do not upload both files to the repository root. Commit to `main` and allow
Streamlit Community Cloud to redeploy.

No `app.py`, `theme.py`, `requirements.txt`, analytics engine, data or branding
changes are needed for this fix.

## Verification performed

- 11 headless app UI tests passed; 21 analytics tests passed separately.
- Standalone Chromium browser checked that the computed column-header styles
  were `text-align: center`, bold weight 800, and black (#000000).
- Chromium compared the visual bounds of all ten restaurant-table header and
  body columns: maximum difference was **0 px**.
- Chromium tested ascending/descending numeric sorting, missing values
  remaining last, pinned restaurant name while horizontally scrolling,
  and both desktop and narrow-viewport rendering.
- Uploaded names are HTML escaped before insertion.

**Limit:** These are local app-stub and standalone-browser checks. The live
Streamlit integration cannot be browser-tested here; verify visually after
deployment and report any runtime or browser issues.
