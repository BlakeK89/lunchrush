# Lunch Rush V1 UI redesign — QA status

Review date: October 20, 2026

## Source of design

- Current `BlakeK89/brand-performance-analyzer` (Shelf Life) `main` branch `app.py` and `.streamlit/config.toml`, reviewed via connected GitHub.
- Approved Brand Rundown guidelines and supplied Lunch Rush logo/app icon.
- This redesign keeps the existing restaurant analytics engine, fictional dataset, and input schema unchanged.

## Automated checks

- **25/25 Python unit and headless app-flow tests pass** (run `python -m unittest discover -s tests -v`).
- Includes all five tab views, no-comparison mode, custom date range, year-to-date mode, POS/menu validation, matched same-store cohorts, and channel totals.
- Default sample KPI reconciliation independently checked: net sales $24,783,583.35, 1,466,211 transactions, comparable-store sales +0.35%, comparable transactions -5.17%, drive-thru and other channels sum exactly to net sales.
- Python source compiles cleanly.

## Not yet verified

- This build environment does not have Streamlit and cannot download it. No actual hosted Streamlit/browser visual test has been completed for the **revised** UI.
- GitHub write access was rejected by the integration (HTTP 403). The local redesign must be uploaded to `BlakeK89/lunchrush` before it can replace the deployed page.
- After upload, verify the live page on desktop/mobile, all five tabs, demo data, date controls, filter changes and workbook upload.

## Known limitations

- Promotions, profitability, food COGS and labor costs remain V2 scope.
- UI visual consistency is implemented from the reference code/CSS, but exact browser rendering is still pending.
- Placeholder demo location names are neutral. No rejected fictional chain name was introduced.
