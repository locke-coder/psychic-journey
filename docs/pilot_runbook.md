# R03 L3 Pilot Runbook

This runbook describes how to operate the L3 internal pilot with sample or
anonymous data only. It does not approve real data for L3, public broad
real-data use, formula changes, deployment changes, or source-code changes.
R04B separately defines L4-Shadow as restricted internal aggregate real-data
shadow validation under LOCKE approval.

## R03.1A Launch Values

| Field | Value |
| --- | --- |
| Pilot users | LOCKE only. Optional internal reviewer: maximum 1, name recorded only after separate approval. |
| Pilot period | 2026-06-11 to 2026-06-17 KST |
| Access method | Current Streamlit URL + password gate. Sample / anonymous data only. Public Streamlit real-data use prohibited. |
| Password owner | LOCKE |
| Sample dataset | 1 `UNDER_TARGET` sample, 1 `ON_TARGET` sample, 1 `OVER_TARGET` sample. No real customer names, contract numbers, phone numbers, addresses, or real sales data. |
| Feedback owner | LOCKE |
| Go/no-go owner | LOCKE |
| Data scope | sample / anonymous only |
| Real data allowed | no for L3; restricted aggregate real-data allowed only in L4-Shadow under LOCKE approval |
| Public Streamlit real-data use allowed | no |

The current launch approval decision is `CONDITIONAL_GO`. The pilot may start
only within the recorded period, with LOCKE-only operation unless one internal
reviewer is separately approved, and with sample or anonymous data only.

## R04B Stage Update

Operating stages are now defined as:

- L3: sample / anonymous pilot.
- L4-Shadow: restricted internal aggregate real-data shadow validation.
- L4-Production: official production operation.

This runbook remains the L3 runbook. L4-Shadow uses separate policy controls:
restricted invited internal users, password gate, current input columns only,
aggregate target and cumulative performance values only, no identifiers in
`memo` or file names, no external sharing, and no replacement of official
reporting.

R04A deploy source clean local commit:
`5be44e16b31da425d0e6fab326781a01581af25e`.

## 1. Pre-Pilot Checks

Before the pilot starts, confirm and record:

- `audit/l3_pilot_launch_approval.md` final decision is `GO` or
  `CONDITIONAL_GO`.
- `pytest` result is PASS.
- Gate Runner ALL result is PASS.
- `G23_OUTPUTS_LATEST_STRICT` result is PASS.
- `outputs/latest` strict check result is PASS.
- Deploy traceability L3 result is recorded.
- Known warnings are visible, including deploy dirty and remote HEAD not
  verified.
- Input data is sample or anonymous only.
- Pilot user is LOCKE; optional reviewer is not added unless separately
  approved.
- Pilot period is 2026-06-11 to 2026-06-17 KST.
- Access method is the current Streamlit URL + password gate.
- Password owner is LOCKE.
- Sample dataset is the approved `UNDER_TARGET`, `ON_TARGET`, and
  `OVER_TARGET` sample set.
- Feedback owner is LOCKE.
- Public broad Streamlit real-data use is not approved.
- `final_actual` is limited to sample or anonymous completed-month data during
  L3.

## 2. Execution Order

Run each pilot case in this order:

1. Open the Streamlit app through the approved access method.
2. Upload a sample or anonymous input file, or select the configured sample.
3. Confirm input validation results before interpreting forecasts.
4. Review KPI values.
5. Review `target_status`.
6. Review `target_variance`.
7. Review `surplus_to_target`.
8. Review the next-close cumulative-line required amount.
9. Review Scenario Grid.
10. Review P1/P2/P3 for under-target cases or O1/O2/O3 for over-target cases.
11. Review generated report text.
12. Download the Excel report.
13. Confirm whether forecast history is saved.
14. Open the Backtest tab and confirm it is understandable.
15. Record evidence and feedback.

Do not continue to report interpretation if validation fails.

## 3. Result Interpretation Guide

Use the following operating interpretation during the pilot:

| Output | Meaning | Operating response |
| --- | --- | --- |
| `UNDER_TARGET` | Forecast is below target. | Review P1/P2/P3 and decide whether target recovery is operationally plausible. |
| `ON_TARGET` | Forecast is near target or maintaining target. | Maintain current plan and monitor next-close requirements. |
| `OVER_TARGET` | Forecast is above target. | Review O1/O2/O3 and decide how to manage surplus without quality loss. |
| O1 | Keep buffer. | Preserve surplus as delivery or closing-risk buffer. |
| O2 | Convert to stretch. | Consider controlled stretch target if capacity and quality allow. |
| O3 | Defend quality. | Protect quality, risk controls, and fulfillment stability. |

The next-close cumulative-line required amount is not the full monthly gap. It
is the required performance needed to align with the plan line by the next close
day.

## 4. Excel Sharing Rules

Excel reports may be shared only when all of the following are true:

- The report came from `outputs/latest` or Streamlit download.
- `archive_old_format` is not used.
- `archive_invalid` is not used.
- File name and generated date are recorded.
- For L3, the file contains sample or anonymous data only.
- No sensitive information appears in any sheet, memo, report text, file name,
  or screenshot.
- Sharing is limited to approved internal pilot users.

Do not attach or forward reports outside the approved pilot group.

## 5. Issue Handling

Use the following response guide when issues occur:

| Issue | Immediate action | Evidence to record |
| --- | --- | --- |
| Validation fail | Stop interpretation, correct the sample or anonymous input, and rerun. | Validation message, corrected field category, rerun result. |
| Upload error | Confirm file type, schema, and sample/anonymous status. | File name, error message, retry result. |
| Excel download failure | Retry once, confirm the workbook is not already open, then escalate if repeated. | Screenshot, generated file name if any, error time. |
| Result value looks wrong | Stop decision use and compare input assumptions, selected metric, and selected date. | KPI screenshot, selected date, input case id. |
| Streamlit access error | Confirm approved access method and user authorization. | URL type, user role, error screenshot. |
| Sensitive information found | Stop sharing, remove the artifact from pilot circulation, and record the incident without repeating the sensitive value. | Incident id, artifact type, owner, containment action. |
| Unauthorized access | Stop pilot access and escalate to LOCKE. | User role, access method, time, containment action. |

Formula-change requests are recorded as feedback only and must not be
implemented during R03.

## 6. Evidence To Record

For each pilot case, record:

- KPI screenshot.
- Scenario Grid screenshot.
- P1/P2/P3 or O1/O2/O3 screenshot.
- Report Text screenshot.
- Backtest screenshot.
- Excel file name.
- Excel generated date.
- Test and Gate log references.
- Pilot feedback form entry.
- Any known warning acknowledgement.

Screenshots must not include real customer, contract, personal, or other
sensitive information.

## 7. Data and Security Rules

- Use sample or anonymous data only for L3.
- Do not use actual sales records in L3.
- Do not use real completed-month actuals in L3 `final_actual` tests.
- For L4-Shadow, use only LOCKE-approved aggregate inputs and aggregate monthly
  final_actual values under LOCKE ownership.
- Do not include identifiers in `memo`, file names, feedback, screenshots, or
  outputs.
- Do not paste raw data into chat, tickets, feedback, reports, or screenshots.
- Do not read, copy, print, or share secret files.
- Do not approve public broad Streamlit real-data operation.
- Do not use app results as official reporting during L4-Shadow.

## 8. Completion Rule

A pilot run is complete only when:

- Validation is passed or the validation issue is documented as the run result.
- KPI and Scenario Grid are reviewed.
- Relevant strategy output is reviewed.
- Excel report is downloaded or the failure is recorded.
- History and Backtest flow are reviewed where applicable.
- Feedback is captured.
- Sensitive-data check is complete.
