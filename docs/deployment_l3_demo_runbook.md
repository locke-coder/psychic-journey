# D06-B L3 Demo Deployment Runbook

## Purpose

Prepare and manually deploy the input-driven month-end sales forecast tool as a public-safe L3 demo.

## Deployment Level

- Target: `L3_PUBLIC_DEMO`
- Public URL: allowed after checks pass
- Real operating data: not allowed
- L4 private real data: not allowed until private QA is complete

## Data Rules

- Use sample or anonymized data only.
- Do not upload private inputs, private outputs, or private screenshots.
- Do not include customer names, phone numbers, addresses, contract numbers, resident registration numbers, or equivalent sensitive identifiers.
- Keep `outputs/latest` limited to public/sample artifacts.

## Required Pre-Deploy Checks

Run and confirm:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe tools\gate_runner.py ALL
```

Also confirm:

- Latest public Excel opens with `openpyxl`.
- `ScenarioGrid` exists and has 9 data rows.
- Required latest `ScenarioGrid` columns are present.
- Enhanced sheets are present: `ForecastHistory`, `FinalActuals`, `BacktestSummary`, `ModelWeights`, `ConfidenceBand`, `Insights`.
- Local Streamlit smoke returns HTTP 200.

## Manual Streamlit Community Cloud Deployment

1. Prepare the GitHub repository and branch for the L3 public demo.
2. Open Streamlit Community Cloud.
3. Select the workspace for the demo app.
4. Choose Create app.
5. Select repository and branch.
6. Set main file path to `app.py`.
7. Review Advanced settings.
8. Enter only required hosted secrets, if any, through Advanced settings.
9. Deploy.
10. Open the deployed URL and complete post-deploy QA.

## Secrets Management

- Do not commit `.streamlit/secrets.toml`.
- Do not include `.streamlit/secrets.toml`, `.env`, `*.key`, or secret-bearing files in `audit_submit` or `audit_submit.zip`.
- Use Streamlit Cloud Advanced settings for required hosted secrets.
- Never log, screenshot, or document secret values.

## Post-Deploy QA

Check these areas with sample/anonymized data:

- Home
- `예측 · 전략 통합`
- Report Memo
- History/Backtest
- Excel Download

Confirm:

- F1/F2/F3 model comparison is visible.
- P1/P2/P3 shortfall strategies remain available.
- O1/O2/O3 overachievement strategies remain distinct as buffer hold, Stretch conversion, and quality defense.
- `ScenarioGrid` remains 9 rows.
- Downloaded Excel opens with `openpyxl`.
- No private data or secrets are exposed.

## Rollback

- Revert to the previous approved commit or previous ZIP SHA.
- Reboot or redeploy the Streamlit Cloud app.
- Re-run the post-deploy QA checklist.
- Record rollback evidence and the restored version identifier.

## Approval Criteria

- L3 demo URL is reachable.
- Sample/anonymized data only.
- No secrets, `.env`, keys, or private artifacts included.
- Local and deployed QA pass.
- Screenshot evidence is stored in the approved evidence location.
