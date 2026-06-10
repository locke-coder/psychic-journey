# History Schema

This document defines the D03 standard storage schema for forecast history and
final monthly actuals. It is intentionally separate from forecast formulas and
strategy logic.

## Config

History storage paths are managed in `config/history_config.yaml`.

- `storage_paths.forecast_history`: CSV path for daily forecast snapshots.
- `storage_paths.final_actuals`: CSV path for confirmed monthly results.

The default paths are:

- `outputs/history/forecast_history.csv`
- `outputs/history/final_actuals.csv`

## forecast_history

Required columns, in canonical order:

1. `run_id`
2. `run_datetime`
3. `target_month`
4. `as_of_date`
5. `metric`
6. `forecast_model`
7. `strategy_id`
8. `strategy_type`
9. `forecast_amount`
10. `forecast_rate`
11. `target_status`
12. `target_variance`
13. `gap_to_target`
14. `surplus_to_target`
15. `risk_level`
16. `monthly_target`
17. `current_actual_cum`
18. `current_target_cum`
19. `remaining_target`

Duplicate key policy:

- If `run_id` is present, it is the unique key.
- If `run_id` is blank, use
  `target_month + as_of_date + metric + forecast_model + strategy_id + run_datetime`.

## final_actuals

Required columns, in canonical order:

1. `target_month`
2. `metric`
3. `final_actual`
4. `final_achievement_rate`
5. `final_status`
6. `cancellation_amount`
7. `net_actual`
8. `memo`
9. `updated_at`

Duplicate key policy:

- Upsert by `target_month + metric`.

## Implementation Notes

- `src/history_schema.py` owns schema constants, required-column validation,
  duplicate-key helpers, and config loading.
- No original input file is read or modified by this schema layer.
- No forecast model formula is changed by this schema layer.
