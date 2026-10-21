# Lunch Rush — two pending fixes

This small update bundles both changes requested after the Restaurant Comparison release:

1. **Restaurant and item names:** black text with normal weight, not bold. All table headers remain bold and centered. No sorting or export logic changes.
2. **Restaurant Comparison explanation:** replace the technical note below the table with two short plain-English paragraphs, including that incomplete/disrupted restaurants remain visible but might not qualify for rankings.

## Upload

Extract the ZIP, upload its contents to the root of the existing `BlakeK89/lunchrush` GitHub repository as usual, and replace the matching files:
- `app.py`
- `lunch_rush/grids.py`

Do not upload the ZIP file itself as a single file. No other code files need replacing.

## Verification

The files were based on the live GitHub `main` version before these edits. Separately passing regression suites: **12 UI tests**, **5 restaurant-comparison tests**, and **21 analytics tests**. Python compilation succeeded. Live Streamlit rendering still requires confirmation after deployment.
