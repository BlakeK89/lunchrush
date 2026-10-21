# Lunch Rush: Chart, sidebar, and table polish

This update addresses the seven UI issues reported on October 21, 2026.

## Changes

1. Sidebar expander labels and sample-data download text use white on electric blue. Cream radio selections and select boxes keep dark text.
2. Removed the redundant "measurable changes and investigative prompts" caveat from Overview's expanded executive summary. Caveat remains in the appropriate How It Works / Insights context.
3. Chart keys are visibly separated with colored dots and plain labels. Weekly comparison distinguishes "Selected period" and "Same weeks last year". Regional sales uses an explanatory caption and shows legends only when both increases and decreases are present. Plot titles, ticks and axis labels use navy instead of gray.
4. Restaurant tab states that the ranking is by net sales and explains eligibility and exclusions in everyday language. Exclusion details remain grounded in the reporting records.
5. All tables (including the Insights data-quality table) now use the same AG Grid component as Shelf Life, with centered headers and cells, high-contrast bold black headers, sortable raw numeric columns, and widths appropriate to the data.
6. Sales/transaction/menu growth percentages get green or coral comparison coloring, applied only to rounded, visibly nonzero changes. Other numeric values remain neutral.
7. Ordering-channel/daypart chart keys label the category *and its percentage of sales*, rather than concatenating names.

## Files to upload to GitHub

Drag the **contents** of this ZIP to the `main` branch of `BlakeK89/lunchrush`, preserving paths:

- `app.py` (replace)
- `lunch_rush/theme.py` (replace)
- `lunch_rush/grids.py` (new)
- `requirements.txt` (replace; adds `streamlit-aggrid==1.2.1.post2`, matching Shelf Life)
- `tests/test_app_ui_smoke.py` (replace)
- `README_UI_SWEEP_2026_10_21.md` (new)

Do not remove or replace the existing demo CSVs, schema, analytics engine, other tests, assets or `.streamlit/config.toml`.

## Verification

- 13 app smoke tests passed in the Streamlit stub, including all five tabs, four reporting choices, chart labels and color, centered grid definitions, colored change styles, sample-download round trip and plain-language exclusion reasons.
- 7 data/helper tests passed.
- During a longer full run, six analytics tests also passed before the environment timed out. The remaining tests were not completed in this run.
- Python source compilation passed.
- Browser/live Streamlit rendering has **not yet been tested**; verify grid load and all seven visual changes after the new dependency installs.

### Important launch gate

The GitHub repository must be made **private** and the public dashboard access verified before linking Lunch Rush from the Brand Rundown website.
