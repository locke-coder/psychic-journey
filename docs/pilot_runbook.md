# Pilot Runbook

This runbook is for a limited LOCKE pilot with 1 to 3 named users. The pilot
uses direct input files and the Streamlit UI to run daily month-end sales
forecasts, save forecast history, enter confirmed month-end actuals, and review
Backtest results.

## Operating Principles

- Use only the dates already present in the input file.
- Decide close days only with the `is_close_day` column.
- Use `day_name` only as a display label.
- Do not edit the original source input file in place. Work from a copied
  operating file for the pilot day.
- Do not enter customer names, phone numbers, addresses, contract numbers,
  resident registration numbers, or any other sensitive identifiers.
- Keep the pilot group limited to the approved 1 to 3 users. Do not forward the
  app URL, input files, output Excel files, or audit bundles outside the pilot.

## 1. Daily Input File Update

1. Copy the latest approved input file to the daily working location.
2. Confirm the required columns exist:
   `date`, `day_name`, `business_day_no`, `is_close_day`, `close_type`,
   `sales_target_daily`, `recognized_target_daily`, `sales_actual_cum`,
   `recognized_actual_cum`, and `memo`.
3. Update daily target values only for dates already present in the table.
4. Update cumulative actual values through the selected `as_of_date`.
5. Leave cumulative actual values after `as_of_date` blank unless the user has
   intentionally entered future defaults for later operation.
6. Confirm `is_close_day` is accurate for each input row. Do not infer close days
   from day labels or date patterns.
7. Save the working copy. Keep the original source file unchanged.

## 2. Forecast Execution

1. Start the Streamlit app from the project root.

   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\tools\start_streamlit_server.ps1
   ```

2. Open the local or deployed Streamlit URL provided for the pilot.
3. Upload the daily working input file or use the configured sample only for
   non-production testing.
4. Select the metric: `sales` or `recognized`.
5. Select the `as_of_date` from the dates present in the input table.
6. Review validation errors first. If errors exist, stop and fix the working
   input file before using scenario results.
7. Review F1/F2/F3 forecast rows and P1/P2/P3 or O1/O2/O3 strategy rows.

## 3. Saving Forecast History

1. Open the `예측 이력 / Backtest` tab.
2. Confirm the current metric and `as_of_date` are correct.
3. Click `예측 이력 저장`.
4. Confirm the success message shows rows appended to `forecast_history`.
5. The default history location is `outputs/history/forecast_history.csv`.
6. If duplicate-run blocking appears, do not edit the CSV manually. Re-run the
   forecast only after confirming whether the same run was already saved.

## 4. Entering Confirmed Month-End Actuals

1. After month close is confirmed, prepare the final actual values by metric.
2. Store only aggregate monthly values:
   `target_month`, `metric`, `final_actual`, `monthly_target`, optional
   cancellation or net amount, optional memo, and update timestamp.
3. Use the app-supported final actual workflow when available. If a controlled
   admin script is used, write through `src.final_actual_store` helpers rather
   than hand-editing rows.
4. Confirm the saved CSV exists at `outputs/history/final_actuals.csv`.
5. Confirm one row per `target_month + metric`. Later saves replace the existing
   row for the same month and metric.

## 5. Backtest Review

1. Open the `예측 이력 / Backtest` tab.
2. Confirm both `forecast_history` and `final_actuals` tables are visible.
3. Review row-level forecast error, absolute error, `error_rate`, and signed
   error direction where the month and metric match.
4. Review the model summary by `forecast_model`.
5. Treat the current Backtest as directional during the first pilot month. Use
   model weighting only after enough monthly samples have accumulated.

## 6. Report Text and Excel Download

1. Select the forecast and strategy row that will be used for reporting.
2. Review the generated report text for:
   target status, forecast amount, gap or surplus, risk level, selected strategy,
   and operational recommendation.
3. Confirm no sensitive identifiers appear in report text or memo fields.
4. Download the Excel report from the Streamlit export control.
5. Open the workbook and confirm these sheets are present:
   `Summary`, `ScenarioGrid`, `DailyRevisedTargets`, `CloseCycle`, `Validation`,
   `ReportText`, `ForecastHistory`, `FinalActuals`, `BacktestSummary`,
   `ModelWeights`, `ConfidenceBand`, and `Insights`.
6. Store the Excel output in the approved pilot folder only.

## 7. Error Handling

| Symptom | Likely cause | Action |
| --- | --- | --- |
| Validation error blocks calculation | Missing column, invalid numeric value, missing actual through `as_of_date`, or missing close-day marker | Fix the working input file and re-run validation. |
| Forecast result is unavailable | Required target or actual context is incomplete | Check cumulative actuals through `as_of_date` and target columns. |
| F2 or F3 falls back | Not enough completed close-cycle or close/non-close history | Document the fallback in the daily note; do not change formulas. |
| `CAPACITY_LIMITED` appears | Target uplift cannot be allocated within cap rules | Escalate capacity, target, or operating-calendar assumptions. |
| History save duplicate error | Same `run_id` or fallback key was already saved | Confirm whether the run is already captured before retrying. |
| Backtest table is empty | No matching `target_month + metric` between history and final actuals | Confirm month format and metric spelling. |
| Excel export fails | File is open, output path is blocked, or dependencies are unavailable | Close the workbook, retry export, then run pytest if the issue repeats. |

## 8. Real Data Security

- Keep pilot files in a restricted folder with access only for named pilot users.
- Do not paste raw customer data into chat, tests, sample files, memo fields, or
  issue reports.
- Use aggregated amounts only. Replace customer-specific context with anonymous
  operational notes such as `large deal moved`, `cancellation risk`, or
  `payment pending`.
- Check Excel reports before sharing. Remove any sheet, memo, or downloaded file
  that includes sensitive identifiers.
- Do not commit `outputs/history`, downloaded Excel files, local secrets, or
  working input files containing real business data.
- If sensitive data is accidentally included, stop the pilot run, delete the
  shared artifact, rotate access if needed, and record the incident in the pilot
  checklist without repeating the sensitive value.
