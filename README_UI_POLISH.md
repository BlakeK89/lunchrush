# Lunch Rush V1: UI polish pass

Prepared October 20, 2026, from the deployed `BlakeK89/lunchrush` code and the approved Shelf Life comparison.

## Included changes
- Header logo safety padding, image accessibility text, and utility-action spacing matched to Shelf Life.
- Sidebar sample-data selector styling with blue radio indicator fallback, readable expanded settings, and removal of the repetitive demo paragraph.
- Added **Download The Chicken Coop Sample Data** to the sidebar: a ZIP of all eight original demo CSV files, compatible with the existing upload parser. It stays available when upload mode is selected before a file is provided.
- Added green/red comparison cues to comparable-store KPI cards and shortened reporting explanations.
- Rounded executive-summary sales movements to reasonable display precision; surfaced the important comparable-store contrast.
- Removed the Plotly legend overlay from Regional Contribution. Both overview charts use external keys.
- Removed the doubled card treatment in the drive-thru vs. other channel summary.
- Shortened fixed-height channel/daypart tables to their row count; added external donut-chart keys and less cluttered labels.
- Kept tables sortable by retaining numeric underlying values. Monetary amounts, counts, and percent columns have visual formatting.
- Removed the repetitive disclaimer footer across all five tabs and the V2 sidebar copy.
- Preserved all analytics formulas, uploaded-data validation, and fictional dataset facts.

## Deployment
Upload the *contents* of this ZIP to the root of the existing GitHub repository on `main`, preserving paths:

- `app.py`
- `lunch_rush/theme.py`
- `tests/test_app_ui_smoke.py`
- `.streamlit/config.toml` (if the hidden folder is not transferred automatically, leave the existing file in place or create this path manually in GitHub)

Streamlit should then auto-redeploy.

## QA
29 automated tests pass with `PYTHONPATH=. pytest -q`, including all five dashboard tabs, default/comparison-free/custom/YTD/previous reporting paths, numeric table dtypes, chart legend configuration, and download ZIP validation against the eight-table schema.

**Not yet verified:** visual rendering on Streamlit Community Cloud after deployment. Test all five tabs, radio-dot color, chart spacing and the sample download in the hosted app before considering the polish complete. No changes were made to Shelf Life.
