# V1 QA record (2026-10-20)

- [x] 40-location synthetic CSV input generated and validated against schema.
- [x] Original analytics engine's 14 regression tests pass.
- [x] Added 7 app-helper / upload safety tests; all pass.
- [x] Headless Python-flow smoke test covered all five Streamlit views with a test double (not a browser render).
- [x] Confirmed weekly/regional/channel/daypart sales totals reconcile in tests.
- [x] Confirmed selected-region insights do not leak other regions' findings.
- [x] Confirmed comparable menu decline metrics rely on valid matched stores.
- [x] Confirmed fictional chain display name is removed from app source data.
- [x] Compiled Python application/modules without syntax error.
- [ ] Streamlit dependency installation and runtime smoke check (unavailable here).
- [ ] Browser inspection of desktop/mobile UI.
- [ ] Upload interaction test in real Streamlit frontend.
- [ ] Deploy to a dedicated Lunch Rush host and verify public URL.
- [ ] Update Brand Rundown homepage card after successful deployment.

Do not describe these last five items as completed until independently verified.
