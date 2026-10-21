# Lunch Rush: Combined Table and Plain-English UI Fixes

Combines the pending table-formatting update with nine new refinements.

### Included changes
1. Simplified same-store comparison and trailing annual average sales captions.
2. Dark navy Overview chart captions with full opacity.
3. Specific restaurant ranking exclusions using actual operating-week information (e.g., Peoria: 3 of 7 days open with recorded disruption).
4. Commas in sales, transactions, and menu-unit figures while retaining numeric sort order.
5. Clear explanation of per-restaurant growth versus same-store growth.
6. Larger, higher-contrast pie-chart hover labels for Channels and Dayparts.
7. Plain-English explanation that menu sales add up to reported restaurant sales when both feeds are complete.
8. Plain-English explanation of menu-item comparison across the same established restaurants.
9. Plain-English explanation of item attach rate and missing order data.

There are no changes to the analytics engine, demo dataset, calculations, or Insights body.

### GitHub upload
Replace: `app.py` at the repository root, `lunch_rush/theme.py` in the `lunch_rush` folder, and `tests/test_app_ui_smoke.py` in `tests`. Add `PRELAUNCH_CHECKLIST.md` to the repository root if it is not already there. Do not upload the ZIP directly.

### Testing
- Python syntax compilation passed.
- 21 analytics and unit tests passed.
- 2 targeted headless UI tests passed (copy/exclusion reasons, hover labels).
- Previous full UI suite was interrupted during extended demo-import tests, so no claim that the entire UI suite passed.
- Live Streamlit rendering still requires verification after deployment.

The pre-launch checklist still requires making the GitHub repository private and confirming Streamlit remains accessible to visitors.
