# Lunch Rush V1 interface refresh — deployment

The GitHub repository is `BlakeK89/lunchrush`. Streamlit automatically rebuilds the public deployment at https://lunchrush.streamlit.app/ when its `main` branch changes.

## Upload this patch

1. Extract `Lunch_Rush_Shelf_Style_Update.zip`.
2. In GitHub, open https://github.com/BlakeK89/lunchrush and select **Add file > Upload files**.
3. Drag the **contents** of the extracted folder into the upload area, preserving their paths. Confirm `app.py`, `lunch_rush/theme.py`, `tests/test_app_ui_smoke.py`, `QA_STATUS.md`, and `DEPLOYMENT.md` are shown as changed/new files.
4. Commit changes to `main`.
5. The hidden `.streamlit/config.toml` file was skipped by the first web upload. Check whether it appears in GitHub after this upload. If absent, create it from the patch by choosing **Add file > Create new file**, entering `.streamlit/config.toml` in the filename box, and pasting the supplied configuration file's text.
6. Open https://lunchrush.streamlit.app/, wait for Streamlit to redeploy, and inspect the new Overview page.

## Required live checks

- Verify branded blue sidebar, primary logo at top, cream reporting band, five KPI cards, horizontal navigation, two comparison charts and channel sales tiles.
- Confirm the five tabs open and report values.
- Test No Comparison, Previous Period, 4/13/26/52-week modes, YTD, custom range, region/ownership/format filters, and an upload.
- Confirm no previous rejected fictional chain name appears and no V2 financial metrics are shown as real values.
- Verify mobile layout. If anything fails, capture the error screen and Streamlit logs before making unrelated edits.

The patch does not modify the live Shelf Life repository, restaurant engine, data, or existing logos.
