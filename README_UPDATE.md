# Lunch Rush V1: Four-tab navigation and table readability update

This update addresses the user-approved October 21 UI review. It starts from the latest deployed source (`app.py`, `lunch_rush/theme.py`, `lunch_rush/grids.py`). Analytics formulas and demo data were not modified.

## Changes

- White outlines for **Change ending week** and **Restaurant filters** in the blue sidebar.
- Native Streamlit table styling now explicitly sets dark text for all data cells, heavier black text for restaurant and item names, and a visible dash (`—`) for missing values. Column headers request bold black centered text through Styler and CSS. Native Grid column alignment remains centered. This is a best-effort header treatment; canvas-based Streamlit rendering still needs browser verification.
- Remove the redundant **Insights** tab. The app now has four tabs: Overview, Restaurants, Channels & Dayparts, Menu Performance.
- Route existing diagnostic types to their relevant sections: established-restaurant order declines → Overview; regional order declines → Restaurants; menu-item declines → Menu Performance. Any new/unknown diagnostic type defaults to Overview so findings are not silently lost.
- Show factual ordering-channel movements in Channels & Dayparts when a comparison is available.
- Preserve report completeness, missing-data warnings, and comparable-store exclusions inside a **Data quality and reporting details** expander on Overview. Restaurant-ranking exclusions remain accessible on the Restaurants tab.
- Updated source-warning descriptions in the new reporting expander to avoid internal worksheet names.

## Install

Upload the ZIP **contents** to the root of `BlakeK89/lunchrush` on `main`, preserving paths:

1. `app.py`
2. `lunch_rush/theme.py`
3. `lunch_rush/grids.py`
4. `tests/test_app_ui_smoke.py`
5. `README_UPDATE.md` (optional documentation)

GitHub web upload may skip hidden folders; this release does **not** change `.streamlit/config.toml`.

## Verification

- 11 UI smoke tests passed separately.
- 21 analytics/unit tests passed separately.
- A combined test command timed out and is **not** counted as a pass.
- The live Streamlit browser has **not** been inspected after this release. Confirm white sidebar borders; non-muted restaurant and item labels; clear blank values; bold black centered headers; four tabs; and that every finding and data-quality note remains accessible.
- Complete pre-launch GitHub repository privacy change before launch.
