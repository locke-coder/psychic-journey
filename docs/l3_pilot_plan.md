# L3 Internal Pilot Plan

This plan defines the L3 internal pilot for the input-driven month-end sales
forecasting tool. The pilot is limited to 1 to 3 named users and is intended to
prove that daily forecast history, final actual storage, Backtest review, report
generation, and security controls are ready for controlled business use.

## Pilot Objective

Validate that a small operating group can use the Streamlit app and Excel
report workflow every business day without breaking the existing forecast
models, provision strategies, over-target strategies, or Gate Runner audit
rules.

The pilot must confirm:

- Daily forecast results can be saved without missing snapshots.
- Confirmed month-end actuals can be stored after close.
- Backtest results compare forecast history against final actuals.
- F1/F2/F3 model-level error rates are visible and usable.
- Dynamic model weighting preparation data can be reviewed without changing
  existing formulas.
- Confidence-band and visualization-ready data are generated.
- Existing P1/P2/P3 and O1/O2/O3 strategy behavior remains available.
- Real sensitive information is not introduced into tests, samples, reports, or
  pilot notes.

## Scope

In scope:

- Daily input-file operation.
- Streamlit execution and screen review.
- Forecast history save operation.
- Report text generation.
- Excel report download and review.
- Month-end final actual entry.
- Backtest execution and model-error review.
- Weekly feedback collection for screen, report, and data-quality improvement.

Out of scope:

- Formula changes to F1/F2/F3.
- Removal or simplification of P1/P2/P3, O1/O2/O3 scenarios.
- Automatic close-day inference from weekday, date pattern, or `day_name`.
- Creation of dates that are not already present in the input table.
- Modification of the original source input file.
- Use of customer names, phone numbers, addresses, contract numbers, resident
  registration numbers, or other sensitive identifiers.

## Pilot Period

Minimum duration: 2 weeks.

Recommended duration: 1 full month, from the first available business day of a
target month through the post-close Backtest review.

If the first pilot starts mid-month, run at least 2 weeks of daily operation and
continue through the next month-end when possible so final actuals and Backtest
can be reviewed with a complete close cycle.

## Pilot Users

The pilot is restricted to the following user group:

| Role | User | Responsibility |
| --- | --- | --- |
| Pilot owner | LOCKE | Owns daily operation, issue triage, and final go/no-go recommendation. |
| Sales operations user | 1 named sales management person | Updates the working input file and verifies daily business context. |
| Leader / report recipient | 1 named leader or report recipient | Reviews report usefulness, decision value, and rollout readiness. |

Do not expand access during the L3 pilot unless a new approval note is added to
the pilot record.

## Operating Guardrails

- Determine close days only from the `is_close_day` column.
- Use `day_name` only as a display label.
- Do not use weekday logic, weekday names, date patterns, or calendar inference
  to decide close days.
- Use only dates already present in the input table.
- Keep the original source input file unchanged. Operate on a controlled working
  copy.
- Keep outputs, downloaded reports, and audit notes in the approved pilot
  folder only.
- Use aggregate operating notes only. Do not record sensitive identifiers.
- Treat F2/F3 fallback behavior as an operating observation, not as a reason to
  change formulas during the pilot.

## Daily Operating Procedure

Run once per operating day during the pilot.

| Step | Activity | Expected evidence |
| --- | --- | --- |
| 1 | Update the working input file. | Required columns exist, actuals are populated through selected `as_of_date`, and future actuals are blank unless intentionally maintained as defaults. |
| 2 | Run Streamlit. | App opens for the approved pilot users. |
| 3 | Select the base date / `as_of_date`. | Selected date exists in the input table. |
| 4 | Review F1/F2/F3. | Forecast rows are visible, and fallback notes are understood when shown. |
| 5 | Review `target_status`. | Status is interpreted as below target, near target, over target, or equivalent current app status. |
| 6 | Review P/O/N strategy results. | P1/P2/P3, O1/O2/O3, or normal/no-gap behavior is visible as applicable. |
| 7 | Save forecast history. | Forecast snapshot is appended to `outputs/history/forecast_history.csv` or the configured history path. |
| 8 | Save report text and Excel report. | Report text is reviewed, Excel is downloaded, opened, and stored in the approved pilot folder. |

Daily completion rule:

- A day is complete only when forecast history is saved and the report artifact
  is reviewed.
- If the app blocks calculation with validation errors, the daily run remains
  open until the working input file is corrected and the run is repeated.
- If a save or export issue occurs, record the issue with root-cause class and
  owner before the next pilot day.

## Weekly Operating Procedure

Run once per week during the pilot.

| Step | Activity | Expected evidence |
| --- | --- | --- |
| 1 | Review forecast history. | Daily snapshots exist for every intended pilot operating day. |
| 2 | Review accumulated error signals. | Backtest or provisional error summary is reviewed where final actuals are available. |
| 3 | Collect screen and report improvement requests. | Requests are grouped as usability, wording, visualization, report, data, or export. |
| 4 | Check data gaps. | Missing actuals, missing close-day markers, invalid targets, and duplicate history attempts are documented. |

Weekly review notes should separate:

- Must-fix before broader rollout.
- Nice-to-have improvement.
- Training or runbook clarification.
- Formula-change request, which must be escalated rather than implemented inside
  this pilot step.

## Month-End Procedure

Run after the month-end result is confirmed.

| Step | Activity | Expected evidence |
| --- | --- | --- |
| 1 | Enter `final_actual`. | Aggregate final actual is stored by `target_month + metric`. |
| 2 | Run Backtest. | Forecast history joins to final actual rows for the same month and metric. |
| 3 | Review model-level error rates. | F1/F2/F3 absolute error and error-rate summary is available. |
| 4 | Write next-month improvement notes. | Recommendations identify data-quality, UI/report, process, and model-weighting preparation items. |

Month-end review must not change F1/F2/F3 formulas. If the pilot evidence
indicates a formula change is needed, record it as an escalation item for a
separate approved task.

## Pilot Issue Classification

Classify each issue before attempting a fix.

| Class | Examples | Default action |
| --- | --- | --- |
| Data quality | Missing required column, blank actual through `as_of_date`, invalid numeric value | Correct the working input file and re-run. |
| Close-day setup | Incorrect `is_close_day`, missing close type | Correct only the input marker from approved business calendar evidence. |
| History save | Duplicate snapshot, missing save, invalid configured path | Confirm existing history first, then retry or escalate. |
| Backtest | No final actual match, unexpected error-rate output | Check `target_month + metric` keys and final actual storage. |
| Report / Excel | Missing sheet, stale report text, export failure | Re-run export and record artifact evidence. |
| Security | Sensitive identifier found in input, memo, report, or output | Stop sharing the artifact, remove it from the pilot folder, and record incident without repeating the sensitive value. |
| Formula / strategy | Request to change F1/F2/F3 or remove P/O scenarios | Escalate outside the pilot. Do not self-fix in this step. |

## Required Pilot Records

Maintain the following pilot records in the approved pilot folder:

- Daily run log with date, metric, `as_of_date`, operator, save result, report
  result, and issue note.
- Weekly review note.
- Month-end final actual evidence.
- Backtest summary evidence.
- User feedback summary.
- Security incident log, even if the result is "none found".
- L3 acceptance checklist.

## Exit Decision

At the end of the pilot, LOCKE prepares one recommendation:

- Continue pilot: use when core operation works but more samples are needed.
- Expand carefully: use when acceptance criteria are met and risks are minor.
- Pause and fix: use when a critical error, history gap, report failure, or
  security issue blocks broader use.

The exit decision is approved only after the acceptance criteria in
`audit/l3_pilot_acceptance.md` are reviewed.
