# Lunch Rush V1

**Lunch Rush by Brand Rundown** is a Streamlit analytics application for corporate quick-service and fast-casual restaurant teams. The app is separate from Shelf Life, but uses its established workbook-validation and UI patterns.

## Current status

**Launch candidate, not yet hosted or browser-tested.** The analytical engine, data upload logic, and Python-level navigation smoke checks pass 22 automated tests. Streamlit was unavailable in the build container, so a real Streamlit runtime check and visual QA still need to happen on a machine or hosting service where its dependencies can be installed.

## Launch

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Deploy this folder as a **separate repository/project**, not over Shelf Life. In Streamlit Community Cloud: connect the new GitHub repository, select branch `main`, entrypoint `app.py`, and Python 3.11 or higher. The app starts with the included 40-location fictional demo. See [DEPLOYMENT.md](DEPLOYMENT.md).

## Navigation

1. **Overview**: net sales, transactions, average check, comparable-store sales/transactions, rolling 52-week AUV, weekly trends, regional breakdown and initial diagnostics.
2. **Restaurants**: ranking of qualifying restaurants; sales, transactions, average check, period growth, ownership, region, format, CSV export; incomplete/disrupted locations shown separately.
3. **Channels & Dayparts**: channel and daypart mixes, net sales, completed orders, average check, period comparisons.
4. **Menu Performance**: category mix, individual item revenue, unit volume, realized price, attach rate if complete, and growth for matched comparable restaurants.
5. **Insights**: rule-based investigation signals, coverage warnings, cohort exclusions and source warnings.

Filters: region, ownership, restaurant format, optional individual restaurant selection, 4/13/26/52-week period, reporting week, and YoY/previous-period/no comparison.

## Fictional demo

- 40 restaurants in West, Southwest, Midwest and Southeast.
- 104 Sunday-ending weekly reporting dates (2024-10-27 through 2026-10-18).
- 19 chicken-focused menu items.
- Restaurant formats: Drive-Thru, Dine-In and Pickup-Focused.
- Channel mix: Drive-Thru, Dine-In, Pickup and Delivery (only at compatible locations).
- Company-owned and franchised locations.
- Generated with fixed random seed `20261020`.
- **The restaurant chain is intentionally unnamed pending approval.** Restaurant records use city names only. Demo figures are not actual business results.

Demo data are in `data/demo/*.csv`. The source generator is included as `generate_demo.py`.

## Data uploads

Upload a Lunch Rush V1 `.xlsx` workbook containing the required schema tabs, or a `.zip` with corresponding CSV tables directly at the ZIP root. Sheet/CSV names must match those in `schema.json`:

- `Restaurant_Master`
- `Menu_Master`
- `Source_Log`
- `Store_Week_Status`
- `Sales_Weekly`
- `Menu_Weekly`
- `Promotions_Weekly` (optional, future)
- `Financials_Weekly` (optional, future)

**Only the six required tables need records.** Optional promotion and financial inputs are retained for future modules and must not be displayed as zero when absent. The Excel template previously provided in the project can be used as a starting point. File upload is limited to 25 MB and is validated before analyses run. Uploaded data are held for the active app session, not written to disk by this application. Standard hosting provider data/security settings still apply.

## Calculation safeguards

- Sales weekly: restaurant + week + ordering channel + daypart.
- Menu weekly: restaurant + week + menu item. These are **never joined row-for-row**.
- Net sales equals gross less discounts and refunds in integer cents.
- Store/week menu revenue reconciles with POS revenue when both feeds are complete.
- All-store growth displays only when both comparison periods have complete POS coverage. A `N/A` value is not zero.
- Comparable-store cohorts are *fixed* between compared periods, with 13-month maturity and strict store/week coverage/disruption rules. The 52-week comparison uses exactly 364 days (52 weeks).
- Average unit volume requires exactly 52 complete seven-day restaurant weeks (not an extrapolation).
- Transactions are **completed orders**, not unique guests.
- Item attach rates require valid item order counts and complete coverage.
- Diagnoses report measurement and investigation options; they never infer causes.

## Deliberate V1 boundaries

Promotional ROI, true item-by-channel/daypart sales, food COGS, labor costs, margins, guest identities, loyalty/retention, service speed, order accuracy, and 53rd-week fiscal mapping are not implemented. V2 metrics are not part of the V1 launch gate.

## Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q app.py lunch_rush
```

Tests use the original synthetic generator plus the packaged CSV data. Browser and deployment smoke tests remain required for a public launch.
