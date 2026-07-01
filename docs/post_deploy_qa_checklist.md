# D06-C Post-Deploy QA Checklist

Use only sample or anonymized data for every public URL check.
Do not upload private or production data to the public Streamlit app.

## Required QA

- [ ] URL is reachable.
- [ ] Sample data loads successfully.
- [ ] Home displays the month-end status board.
- [ ] The integrated page `예측 · 전략 통합` displays.
- [ ] `target_status` displays.
- [ ] `target_variance` displays.
- [ ] `surplus_to_target` displays.
- [ ] Next close cumulative required amount displays.
- [ ] F1/F2/F3 model comparison displays.
- [ ] `ScenarioGrid` has exactly 9 rows.
- [ ] P1/P2/P3 remain available.
- [ ] O1/O2/O3 labels remain distinct.
- [ ] O1 label is `버퍼 유지`.
- [ ] O2 label is `Stretch 전환`.
- [ ] O3 label is `품질 방어`.
- [ ] Raw `ScenarioGrid` expander displays.
- [ ] `ForecastHistory`, Backtest, `ModelWeights`, `ConfidenceBand`, and `Insights` display safely.
- [ ] Excel download works.
- [ ] Downloaded Excel loads with `openpyxl`.
- [ ] No private data is uploaded.
- [ ] No secrets are exposed in the UI, logs, screenshots, or downloads.
- [ ] `archive_invalid` is not exposed.
- [ ] Screenshot evidence is stored with sample or anonymized data only.

## Deployment Record

- Target URL: `https://sales-closing-forecast.streamlit.app/`
- Deployment target: `L3_PUBLIC_DEMO`
- Public URL allowed: yes
- Real data allowed: no
- Private QA required for L4: yes
