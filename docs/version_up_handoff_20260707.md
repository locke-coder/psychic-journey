# Version-Up Handoff File Guide

Generated: 2026-07-07 KST

## Current Diagnosis

- App: `sales-closing-forecast`, Streamlit-based month-end sales closing forecast tool.
- Current documented release state: `U06.2 / L4_REVIEW_CANDIDATE`.
- Main flow: input validation -> F1/F2/F3 forecast -> P1/P2/P3 provision or O1/O2/O3 overachievement strategy -> ScenarioGrid -> report memo -> Excel export -> history/backtest.
- UI structure: 7 routed pages through `app.py` and `src/ui_navigation.py`.
- Important architecture risk: `app.py` is very large, about 12k lines, and contains page rendering, state handling, helper transforms, reporting support, and Streamlit UI logic. Version-up design should include an app decomposition plan.
- Current verification result on this workspace after sample restoration: `391 passed`.
- `data/sample/input_sample.csv` was restored from the 2026-06 18-row deploy source sample and is readable again.
- Working tree is dirty. Do not assume the current tree is the clean U06.2 release state.

## Must Send To GPT

Send these as the minimum context for version-up design:

- `README.md`
- `AGENTS.md`
- `requirements.txt`
- `pytest.ini`
- `app.py`
- `config/model_config.yaml`
- `config/history_config.yaml`
- `config/gate_audit_catalog.yaml`
- `src/`
- `tests/test_schema.py`
- `tests/test_loader.py`
- `tests/test_validator.py`
- `tests/test_forecast_models.py`
- `tests/test_provision_models.py`
- `tests/test_overachievement_models.py`
- `tests/test_scenario_runner.py`
- `tests/test_next_close.py`
- `tests/test_close_cycle_engine.py`
- `tests/test_excel_exporter.py`
- `tests/test_report_builder.py`
- `tests/test_visualization_builder.py`
- `tests/test_ui_navigation.py`
- `tests/test_ui_components.py`
- `tests/test_ui_theme.py`
- `tests/test_app_smoke.py`
- `tests/test_saved_actuals_readonly.py`
- `tests/test_operator_sample_store.py`

## Send These Docs For Business And Release Context

- `docs/monthly_close_user_runbook.md`
- `docs/security_and_deploy_notes.md`
- `docs/release_notes_U06_2_L4_review_candidate.md`
- `docs/l4_release_runbook.md`
- `docs/l3_l4_release_checklist.md`
- `docs/operation_handover_checklist.md`
- `docs/ui_design_notes.md`
- `docs/ui_kpi_scenario_unification.md`
- `docs/navigation_design_notes.md`
- `docs/streamlit_screen_qa_checklist.md`
- `docs/operator_sample_management.md`

## Send Sample Data Carefully

- `data/sample/input_sample.csv` is the restored 2026-06 18-row current-month sample.
- `data/sample/historical_input_sample.csv` is readable text CSV and can be sent if sample data is needed.
- Do not send real customer, contract, person-level, CRM, or private sales files.

## Optional Files By Design Topic

- Excel/report redesign: `src/excel_exporter.py`, `src/report_builder.py`, `tests/test_excel_exporter.py`, `tests/test_report_builder.py`, and a sanitized `outputs/latest/*.xlsx` only if it contains sample or anonymous data.
- Forecast logic redesign: `src/forecast_models.py`, `src/provision_models.py`, `src/overachievement_models.py`, `src/scenario_runner.py`, `src/next_close.py`, `src/close_cycle_engine.py`, plus their matching tests.
- UI/UX redesign: `app.py`, `src/ui_navigation.py`, `src/ui_pages.py`, `src/ui_components.py`, `src/ui_styles.py`, `src/ui_theme.py`, `src/visualization_builder.py`, and the UI docs listed above.
- Data persistence redesign: `src/operator_sample_store.py`, `src/history_store.py`, `src/history_schema.py`, `src/final_actual_store.py`, `config/history_config.yaml`, and matching tests.
- Deployment/release redesign: `tools/gate_runner.py`, `tools/collect_audit_artifacts.py`, `tools/check_deploy_traceability.py`, `docs/deploy_traceability_runbook.md`, `docs/deploy_runbook_l3.md`, `docs/streamlit_cloud_deploy_checklist.md`.

## Do Not Send

- `.venv/`
- `.git/`
- `.streamlit/secrets.toml`
- `.env`
- `*.key`
- `runtime_storage/`
- `operator_data/`
- `local_data/`
- `outputs/gh_auth*/`
- `outputs/gh_config*/`
- `outputs/streamlit_deploy_gitdir_current/`
- `outputs/streamlit_deploy_worktree_current/`
- `outputs/streamlit_deploy_navmerge_*/`
- `outputs/navmerge_gitdb_*/`
- Any file containing real operational data, passwords, tokens, private URLs, customer identifiers, contract identifiers, or person-level information.

## Recommended GPT Brief

Ask GPT to design the next version with this framing:

```text
We are upgrading a Streamlit month-end sales closing forecast app.
Respect AGENTS.md rules: input-driven only, no weekday/date-pattern close-day inference, no generated missing dates, no real PII, original input files must not be mutated.

Current state:
- U06.2 L4 review candidate.
- F1/F2/F3 forecast, P1/P2/P3 provision, O1/O2/O3 overachievement, ScenarioGrid, report memo, Excel export, history/backtest.
- app.py is too large and should be decomposed.
- Current test run after sample restoration: 391 passed.

Please produce a version-up design covering:
1. target user workflow,
2. feature roadmap,
3. architecture/refactoring plan,
4. data/security model,
5. testing and release gates,
6. migration plan from current U06.2 state.
```
