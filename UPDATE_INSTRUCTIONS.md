# Lunch Rush: Full Five-Tab UI Audit Update

Upload the **contents** of this ZIP (not the outer folder) into the root of [BlakeK89/lunchrush](https://github.com/BlakeK89/lunchrush) using **Add file → Upload files**; commit to `main`.

Files to replace or add:
- `app.py`
- `lunch_rush/grids.py` (replaces the previous AG Grid renderer)
- `requirements.txt` (removes `streamlit-aggrid`; uses supported native Streamlit column controls)
- `tests/test_app_ui_smoke.py`
- `LUNCH_RUSH_V1_FULL_UI_AUDIT.md` (audit and launch verification checklist)

There are **no** changes to `lunch_rush/engine.py`, `data/demo/`, `schema.json`, brand assets, or Shelf Life.

Streamlit should automatically redeploy. Inspect table alignment carefully before further releases. See the audit report for the full QA status and mandatory pre-launch repository privacy step.
