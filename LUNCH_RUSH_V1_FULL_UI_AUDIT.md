# Lunch Rush V1 | Five-Tab Brand-Team Audit

**Date:** October 21, 2026  
**Reference:** Uploaded full-page screenshots of Overview, Restaurants, Channels & Dayparts, Menu Performance, and Insights; current Lunch Rush V1 code; approved Shelf Life layout.

## Executive assessment

**Prior version: not launch-ready.** The AG Grid customization was rendering row values far away from their column headers, sometimes outside the visible table. This breaks the Restaurants, Channels & Dayparts, Menu, and Data Quality workflows. A brand manager cannot confidently read, compare, or export what appears on screen in that state.

**Patch goal:** Restore a dependable, straightforward V1 dashboard without adding new financial/promotional modules or changing any restaurant analytics. All changes in this release affect the UI, labeling, table rendering, and test/dependency support.

## Findings by page

| Page | User-impacting issue | Change in this update |
| --- | --- | --- |
| Overview | Overall sales growth (+9.7%) dominates the narrative even though comparable-store orders fell (-5.2%). A director could miss the more urgent signal. | Executive Summary now leads with the established-store order decline when it is negative. Clarifies that overall company totals can include newer locations. |
| Overview | Regional sales increases could be mistaken for same-store gains. | Chart caption explicitly notes that regional totals include newer locations. |
| Overview | Chart labels are small at full-page viewing scale. | Increased chart typography and hover-label clarity. |
| Restaurants | Major **blocking defect**: rows and headers misaligned; some values appear in wrong visual positions. | Replaced the AG Grid customization with Streamlit's native sortable table, with explicit centered column alignment. |
| Restaurants | Ranking table shows ownership/format before the metrics a brand manager needs most. | Columns now lead with restaurant, sales, sales change, transactions, and transaction change. Restaurant identity stays visible during horizontal scrolling. |
| Restaurants | Raw size rankings do not, by themselves, reveal growth performance. | Sales growth and transaction change brought forward in the sortable table. CSV download retains all columns. |
| Channels & Dayparts | Both tables have wrong-positioned values, with colored cells detached from their headers. | Native tables with positive/negative highlighting and fixed data-to-column alignment. |
| Channels & Dayparts | Essential growth values require too much horizontal hunting. | Sales and transaction change moved near their corresponding amounts; segment retained first. |
| Channels & Dayparts | Donut charts occupy large white panels with little context. | Existing chart breakdown retained for V1; hover/readability improvements preserved. More complex interaction deferred. |
| Menu Performance | Category table is squeezed into a narrow column, cutting off sales/mix data. | Full-width category table; adjacent chart area now explains the highest-selling menu category. |
| Menu Performance | Menu-item table hides the declining item or change column offscreen. | Item identity pinned, and comparable item sales growth moved near revenue. A data-derived item-decline prompt appears above the table when relevant. |
| Insights | Diagnostic cards repeat machine-generated phrasing such as “aligned comparison” and “materially declined.” | Human-readable finding titles, measurable change, and next investigation shown separately. No unverified causal claims. |
| Insights | Two-row data-quality table wastes large vertical space and uses “store-weeks” jargon. | Short summary of complete restaurant-weeks, with detailed records and comparison exclusions in an expandable section. |
| All tabs | Hardcoded AG Grid CSS broke important layout behavior. | Dropped `streamlit-aggrid` in favor of native `st.dataframe` with reliable numeric sorting, centered columns, CSV-preserving raw values, dark headers, and accessible colors. |

## Brand-team usability perspective

- **Director:** Can now identify the main risk without diving into four tabs: total revenue is rising, but established-restaurant order volume is declining. This is a diagnostic flag, not a causal explanation.
- **Brand manager:** Can go from the network warning to regional/restaurants tables and menu performance, with signed changes visible and sortable.
- **Associate brand manager:** Should be able to understand the rankings and investigate flagged items without a course. Data completeness remains available for context.

## Not changed

- No formula changes, source-data changes, synthetic restaurant names, new metrics, financial assumptions, or generated causal conclusions.
- Existing filters, reporting dates, comparisons, uploaded-file validation, and downloads are preserved.
- All analytics tied to V2 (promotions, COGS, labor, profitability, loyalty) stay deferred.

## Verification completed

- `PYTHONPATH=. pytest tests/test_lunch_rush.py tests/test_ui_metrics.py -q`: **21 passed**.
- `PYTHONPATH=. pytest tests/test_app_ui_smoke.py -q`: **9 passed**.
- Source compilation: passed.
- Verified number-formatting helpers produce comma-separated dollars/counts and signed, color-coded changes without changing source numeric values.
- Verified the sample ZIP still imports successfully through the required 8-table schema in smoke tests.
- The combined all-tests invocation did not finish within the test runner's time limit. The two constituent suites passed when run separately.

## Still required before public launch

1. Upload the patch to the `BlakeK89/lunchrush` GitHub repository, replacing files at their existing paths.
2. Confirm Streamlit builds successfully using the updated `requirements.txt`, with no `st_aggrid` import needed.
3. Check the Restaurants, Channels & Dayparts, Menu, and Insights tables with browser screenshots. **The value under every header must be the right value**, including when horizontally scrolling.
4. Check sorting, filtering, sample ZIP import/export, and the new descriptive cards on the actual hosted app.
5. Check mobile/narrow desktop layout and data privacy warnings.
6. Make the Lunch Rush GitHub repository **private**, as explicitly required by the project, and confirm the public Streamlit app still runs after permission changes.
7. Only then link Lunch Rush from Brand Rundown / Netlify.

**Browser-rendered QA is not yet completed.** Do not treat headless tests as proof of visual correctness.
