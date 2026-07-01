# Post Launch Verification Checklist

## Release Identity

- release_commit: `70139e39c25f12749c92b8906266dac8a26e8c89`
- app_url_primary: `https://locke-coder-psychic-journey-app-cxfzqk.streamlit.app/`
- app_url_alias: `https://sales-closing-forecast.streamlit.app/`
- operational_status: `L4_READY_WITH_UI_EVIDENCE_LIMITATION`
- data_scope: `sample_anonymous_non_identifying_aggregate_only`

## Verification Rules

- Use only sample, anonymous, or non-identifying aggregate data.
- Do not upload real operational data to the Public URL.
- Do not upload or enter customer names, phone numbers, addresses, contract
  numbers, resident registration numbers, account numbers, responsible person
  names, branch names, center names, or internal sales secret raw figures.
- Do not read, print, copy, or change `.streamlit/secrets.toml`.
- Do not click Save, Apply, Invite, Share, Reboot, Deploy, or settings-changing
  controls without separate approval.
- Close-day judgment must remain based only on the `is_close_day` column.
- `day_name` is display-only and must not be used to infer close days.

## First Screen Load

- [ ] Open `app_url_primary`.
- [ ] Confirm the first screen loads without an import error.
- [ ] Confirm the first screen loads without a module error.
- [ ] Confirm the first screen loads without a secrets error.
- [ ] If primary URL is blocked or redirected, open `app_url_alias`.
- [ ] Record whether the observed result is full UI load, auth redirect, or
  other limitation.

## Current And Close Pace Check

- [ ] Confirm the current as-of date or selected base date is visible.
- [ ] Confirm close-day rows are identified only by `is_close_day`.
- [ ] Confirm current pace metrics are visible.
- [ ] Confirm close-day pace or close-cycle indicators are visible where
  expected.
- [ ] Confirm no weekday or date-pattern inference is presented as close-day
  logic.

## Input And Data

- [ ] Confirm required input columns are present:
  `date`, `day_name`, `business_day_no`, `is_close_day`, `close_type`,
  `sales_target_daily`, `recognized_target_daily`, `sales_actual_cum`,
  `recognized_actual_cum`, `memo`.
- [ ] Confirm future cumulative actual fields may remain blank.
- [ ] Confirm cumulative actuals up to the as-of date are provided when needed.
- [ ] Confirm memo fields contain no prohibited identifiers or secrets.
- [ ] Confirm uploaded or entered data is sample, anonymous, or
  non-identifying aggregate data only.

## KPI And Forecast

- [ ] Confirm monthly forecast values are displayed.
- [ ] Confirm sales and recognized metrics are displayed where expected.
- [ ] Confirm target gap or surplus values are displayed.
- [ ] Confirm target status is displayed as shortfall, near target, met target,
  or over target according to the release behavior.
- [ ] Confirm calculation output is treated as decision-support material and is
  reviewed before final reporting.

## Scenarios

- [ ] Confirm P1 shortfall scenario is available when applicable.
- [ ] Confirm P2 shortfall scenario is available when applicable.
- [ ] Confirm P3 shortfall scenario is available when applicable.
- [ ] Confirm O1 over-target scenario is available when applicable.
- [ ] Confirm O2 over-target scenario is available when applicable.
- [ ] Confirm O3 over-target scenario is available when applicable.
- [ ] Confirm O1/O2/O3 are not reduced to a simple `NO_GAP` replacement.

## Forecast History

- [ ] Confirm forecast history is visible or downloadable where expected.
- [ ] Confirm history entries use non-identifying data only.
- [ ] Confirm no customer, contract, person, branch, center, address, phone,
  account, or secret values appear in history.

## Excel Sharing

- [ ] Confirm Excel reports are generated only from Public-safe input data.
- [ ] Confirm Excel reports inherit the sensitivity of the input data.
- [ ] Confirm Excel files are shared only within the approved scope.
- [ ] Confirm Excel files generated from prohibited data are not shared and are
  removed from circulation.

## Required Field Visibility

- [ ] Confirm O1/O2/O3 display is present in over-target cases.
- [ ] Confirm `target_status` is displayed.
- [ ] Confirm `target_variance` is displayed.
- [ ] Confirm `surplus_to_target` is displayed when over target.

## Excel Report Generation

- [ ] Generate an Excel report from sample or anonymous data.
- [ ] Confirm the workbook downloads successfully.
- [ ] Confirm required sheets and expected columns are present.
- [ ] Confirm the workbook contains no prohibited identifiers or secrets.
- [ ] Confirm the workbook may be shared only under the Excel sharing criteria.

## Streamlit Logs

- [ ] Check Streamlit logs if access is approved and available.
- [ ] Confirm no import error is present.
- [ ] Confirm no module error is present.
- [ ] Confirm no secrets error is present.
- [ ] Confirm no customer data or prohibited identifiers appear in logs.

## Reflected Commit

- [ ] Confirm source repository is `psychic-journey`.
- [ ] Confirm source branch is `main`.
- [ ] Confirm main file is `app.py`.
- [ ] Confirm reflected commit is
  `70139e39c25f12749c92b8906266dac8a26e8c89`.
- [ ] If the reflected commit is not directly visible, record the limitation and
  use R04 through R09-P fallback evidence only as conditional evidence.

## Stop Criteria

Stop verification and escalate before further use if any item below occurs:

- real operational data is uploaded to the Public URL
- customer, phone, address, contract, resident registration, account,
  responsible person, branch, center, or internal sales secret data is present
- secrets, API keys, tokens, passwords, or `.streamlit/secrets.toml` values are
  entered or exposed
- app import, module, or secrets errors are observed
- O1/O2/O3 scenarios are missing in applicable over-target cases
- P1/P2/P3 shortfall scenarios are missing in applicable shortfall cases
- `is_close_day` is not the only close-day judgment source
- Excel output contains prohibited data
- Streamlit reflected commit, Running status, or Last deploy Success conflicts
  with the release identity
- unauthorized settings changes, redeploy, share, invite, reboot, save, or
  apply actions are required

## Checklist Decision

- result: `pending_user_side_verification`
- current_operational_status: `L4_READY_WITH_UI_EVIDENCE_LIMITATION`
- required_for_unrestricted_public_safe_level:
  `direct_user_side_streamlit_ui_evidence_for_first_load_running_last_deploy_success_and_reflected_commit`
