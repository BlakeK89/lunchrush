# Lunch Rush — Restaurant Comparison + Table and Findings Fix

## Install
1. Extract `Lunch_Rush_Restaurant_Comparison_Update.zip`.
2. Upload its contents to the root of `BlakeK89/lunchrush` in GitHub, **preserving the `lunch_rush/` and `tests/` subfolders**. Replace existing files with matching paths; `lunch_rush/restaurant_explorer.py` and `tests/test_restaurant_explorer.py` are new.
3. Commit to `main`. There is no dependency change, data change, or schema change.
4. Open `https://lunchrush.streamlit.app/`, refresh, and visit **Restaurants → Build a Restaurant Comparison**. This new heading is the deployment marker.

## Changes
- Restaurants: preserves existing rankings, charts, regional findings; adds region and restaurant multiselects (both multi-value), row group modes **Restaurant**, **Region**, **Region → Restaurant**, metric selection, a reset button, reporting flags, and a scoped CSV download.
- A blank selector means all matching choices. This comparison uses **only restaurants already inside the global sidebar scope** and does not change top dashboard KPIs/charts.
- The default restaurant view is ranked by sales when eligible; unranked locations stay visible with a dash for rank and reporting status.
- Regional changes and average checks are recomputed using source totals; they are not averaged restaurant-level growth percentages.
- Tables: actual HTML `<th>` headers, scoped CSS and explicit inline centering/black text; black restaurant and menu names; sorting controls; numeric value display preserved.
- Findings: removes title/evidence colon stacking, simplifies Overview bullet and evidence copy, simplifies regional/menu evidence and next-step presentation.

## Post-deployment check — important
The October 21 screenshot appeared to show the **older native grid** (Restaurant before Rank; no sort arrows), even though the current GitHub code uses custom HTML headers. The screenshot alone cannot establish why the live app did not reflect the latest code. Do not diagnose further header CSS without first verifying the live build uses this new release.

If **Build a Restaurant Comparison** is absent even after committing and refreshing, visit Streamlit Cloud → **Manage app** (bottom-right) → **⋮ → Reboot app**, or reboot from the app's `share.streamlit.io` workspace. Confirm the deployed repository is `BlakeK89/lunchrush`, branch `main`, app file `app.py`. Check deployment logs for errors. [Streamlit documentation](https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app/reboot-your-app).

## Verification performed locally
- 12 interface tests passed separately (`tests/test_app_ui_smoke.py`).
- 5 new restaurant comparison tests passed separately (`tests/test_restaurant_explorer.py`).
- 21 analytics/engine tests passed separately (`tests/test_lunch_rush.py` and `tests/test_ui_metrics.py`).
- Headless Chromium HTML renderer: computed styles confirmed centered headers and cells, bold black text, sort toggles, pinned identity, and horizontal mobile scroll.
- A combined test invocation timed out, so it **is not claimed as a combined pass**.
- **Not verified:** actual Streamlit Community Cloud render, GitHub-to-Streamlit deployment linkage, or live interaction in Streamlit. These must be checked after deployment.
