# Data Accumulation Guide

This guide defines what the pilot should save each day and how the accumulated
history can support future model improvement. It does not change F1/F2/F3,
P1/P2/P3, or O1/O2/O3 formulas.

## 1. Daily Data To Save

Save one forecast history snapshot after each approved daily forecast run.

- Save the exact `target_month`, `as_of_date`, and `metric` used in the run.
- Save all scenario rows produced for F1/F2/F3 and the active strategy set.
- Save forecast amount, forecast rate, target status, gap or surplus, risk
  level, monthly target, current cumulative actual, current cumulative target,
  and remaining target.
- Save the final monthly actual once per metric after month close is confirmed.
- Keep working input files and history outputs separate. Do not modify original
  source input files.
- Treat a newly uploaded current-month input file as the latest actual default
  source. The app may persist the cumulative actual columns as defaults, but it
  must not commit original upload files or sensitive actual files to public
  GitHub.
- Use historical monthly uploads for comparison only. Do not register them as
  current-month latest defaults.

During pilot operation, daily history should answer these questions:

- What did each forecast model expect on each operating day?
- Which strategy was recommended for under-target, on-target, or over-target
  conditions?
- How far was each forecast from the confirmed month-end actual?
- Which model had the lowest error for each metric and month?

## 2. `forecast_history` Column Guide

Default path: `outputs/history/forecast_history.csv`.

| Column | Meaning | Quality expectation |
| --- | --- | --- |
| `run_id` | Unique identifier for one saved forecast snapshot | Present for app-generated saves. |
| `run_datetime` | Timestamp when the forecast was saved | Use ISO-like timestamp from the app. |
| `target_month` | Month being forecast, such as `2026-06` | Match final actual month exactly. |
| `as_of_date` | Input-table date used as the forecast basis | Must exist in the input file. |
| `metric` | `sales` or `recognized` | Must match final actual metric. |
| `forecast_model` | F1/F2/F3 model id | Keep canonical ids. |
| `strategy_id` | P1/P2/P3, O1/O2/O3, or neutral strategy id | Keep canonical ids. |
| `strategy_type` | `PROVISION`, `OVERACHIEVEMENT`, or `NEUTRAL` | Should align with target status. |
| `forecast_amount` | Expected month-end amount before final confirmation | Numeric aggregate amount. |
| `forecast_rate` | Forecast amount divided by monthly target | Numeric ratio. |
| `target_status` | `UNDER_TARGET`, `ON_TARGET`, or `OVER_TARGET` | Must come from forecast result. |
| `target_variance` | Forecast amount minus monthly target | Numeric amount. |
| `gap_to_target` | Positive shortfall to target | Zero when not under target. |
| `surplus_to_target` | Positive surplus over target | Zero when not over target. |
| `risk_level` | Green, Yellow, Red, Black, or N/A | Review Black and N/A rows. |
| `monthly_target` | Sum of daily target values in the input table | Numeric aggregate amount. |
| `current_actual_cum` | Actual cumulative amount at `as_of_date` | Must be present for valid runs. |
| `current_target_cum` | Target cumulative amount through `as_of_date` | Calculated from input rows. |
| `remaining_target` | Target amount after `as_of_date` | Calculated from input rows only. |

## 3. `final_actuals` Column Guide

Default path: `outputs/history/final_actuals.csv`.

| Column | Meaning | Quality expectation |
| --- | --- | --- |
| `target_month` | Confirmed month, such as `2026-06` | Match forecast history month. |
| `metric` | `sales` or `recognized` | Match forecast history metric. |
| `final_actual` | Confirmed month-end actual amount | Numeric aggregate amount. |
| `final_achievement_rate` | `final_actual / monthly_target` | Calculated by storage helper. |
| `final_status` | `UNDER_TARGET`, `ON_TARGET`, or `OVER_TARGET` | Calculated from final actual and target. |
| `cancellation_amount` | Optional aggregate cancellation or adjustment amount | Blank if not used. |
| `net_actual` | Optional aggregate net amount after adjustments | Blank if not used. |
| `memo` | Optional non-sensitive operating note | No customer or contract identifiers. |
| `updated_at` | Timestamp of final actual save | Keep latest confirmed save. |

`final_actuals` uses an upsert rule by `target_month + metric`. If a confirmed
value changes, save the corrected aggregate row rather than appending a duplicate.

## 4. Improvement Timeline

### After 3 Months

- Compare F1/F2/F3 average absolute error by metric.
- Identify whether fallback-heavy models need more close-cycle data before use.
- Review whether one model consistently over-forecasts or under-forecasts.
- Use results as reporting context, not as automatic model replacement.

### After 6 Months

- Prepare error-based model weights for pilot review.
- Segment error by metric and target status.
- Compare close-day focused and non-close-day focused strategy outcomes.
- Review confidence-band width and whether operational decisions need a wider
  or narrower planning range.

### After 12 Months

- Evaluate seasonal patterns by month and business-day stage.
- Consider metric-specific default model weights.
- Compare normal, under-target, and over-target periods separately.
- Decide whether to graduate the pilot to a controlled broader rollout.

Any formula or model change still requires a separate reviewed implementation
step with tests. Do not tune test expectations to match changed code.

## 5. Data Quality Checklist

- `date` values are unique within the operating input file.
- `business_day_no` values are ordered and unique within the month.
- `is_close_day` is populated from the business calendar and not inferred.
- Daily target columns are numeric and non-blank.
- Cumulative actuals are populated through `as_of_date`.
- Cumulative actuals after `as_of_date` are blank unless intentionally saved as
  future defaults.
- `target_month` format is consistent between forecast history and final actuals.
- `metric` values are only `sales` or `recognized`.
- Each daily save has a unique `run_id`.
- Final actuals contain one current row per `target_month + metric`.
- Memo fields contain only aggregate, anonymous operating notes.
- History CSV files are backed up according to the pilot folder policy.
- Excel reports are checked for sensitive data before sharing.
- Gate Runner and pytest status are recorded before pilot start and after any
  code or configuration change.
