# Deployment instructions

## Preserve existing applications

Create a **separate** repository and deployment for Lunch Rush. Do not replace the existing Shelf Life repository or deployment. The Brand Rundown homepage's Lunch Rush *Coming Soon* state should be changed only after the application URL and workflow are verified.

## Streamlit Community Cloud

1. Upload the contents of this package to a new repository for Lunch Rush. The app entrypoint is `app.py`, at the repository root.
2. Verify `requirements.txt`, `.streamlit/config.toml`, `schema.json`, `assets/`, `lunch_rush/` and `data/demo/` are all included.
3. In Streamlit Community Cloud, choose **Create app → From GitHub**, then the new repository's `main` branch and entrypoint `app.py`.
4. Deploy. Once the service installs dependencies, check startup and the Overview page.
5. Click all five pages. Confirm region, ownership, format and individual restaurant filters change figures. Check 4/13/26/52-week ranges, prior-period comparisons and download buttons.
6. Upload the verified 10-restaurant Excel preview from the project and confirm it loads. Then upload a ZIP containing all eight `data/demo/*.csv` files (the app must reject malformed/unknown tables).
7. Confirm source warnings display, and the app doesn't display invented promotions, COGS or profitability metrics.
8. Check mobile and desktop layout, logo, readability, charts and timing. Test cold-start load time using the actual host.
9. Only after the above: update the Lunch Rush card/link on the Brand Rundown homepage to the working, verified URL.

## Security/operational notes

- Demo data are synthetic. Do not upload sensitive business data to a publicly hosted demo without reviewing the host's security, access controls and data retention rules.
- Uploads are parsed on the app server. The application does not write them to persistent disk, but the hosting platform may have its own logging and operational data policies.
- File limits and ZIP member limits are enforced by `lunch_rush/upload.py` and `lunch_rush/io.py`.
- Re-test and deploy after any changes to the schema or validation calculations.

## Current blocker

This build environment could not install Streamlit, so it was not possible to launch the UI or perform real browser QA here. A fresh hosted runtime is required before this can honestly be considered *live*.
