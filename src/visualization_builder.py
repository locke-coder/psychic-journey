"""Build chart-ready dataframes for Streamlit visualizations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pandas as pd


FORECAST_TREND_COLUMNS: tuple[str, ...] = (
    "target_month",
    "as_of_date",
    "metric",
    "forecast_model",
    "forecast_amount",
    "forecast_count",
)
MODEL_ERROR_COLUMNS: tuple[str, ...] = (
    "forecast_model",
    "sample_count",
    "mean_abs_error",
    "mean_error_rate",
    "median_error_rate",
    "bias",
)
TARGET_STATUS_DISTRIBUTION_COLUMNS: tuple[str, ...] = (
    "target_month",
    "as_of_date",
    "metric",
    "target_status",
    "scenario_count",
    "scenario_share",
)
GAP_SURPLUS_TREND_COLUMNS: tuple[str, ...] = (
    "target_month",
    "as_of_date",
    "metric",
    "forecast_model",
    "gap_to_target",
    "surplus_to_target",
)
STRATEGY_MIX_COLUMNS: tuple[str, ...] = (
    "target_month",
    "as_of_date",
    "metric",
    "strategy_id",
    "strategy_type",
    "scenario_count",
    "scenario_share",
)
VISUALIZATION_KEYS: tuple[str, ...] = (
    "forecast_trend",
    "model_error",
    "target_status_distribution",
    "gap_surplus_trend",
    "strategy_mix",
    "warnings",
)
PROJECTION_BAND_COLUMNS: tuple[str, ...] = (
    "date",
    "day_name",
    "business_day_no",
    "is_close_day",
    "actual_cum",
    "target_cum",
    "forecast_low",
    "forecast_mid",
    "forecast_high",
    "projection_mid",
    "point_type",
    "zone",
    "is_actual_period",
    "is_projection_period",
    "is_current_point",
    "is_next_close_day",
)
CLOSE_DAY_MARKER_COLUMNS: tuple[str, ...] = (
    "date",
    "day_name",
    "business_day_no",
    "is_close_day",
    "is_next_close_day",
)
FORECAST_MODEL_MINI_CHART_COLUMNS: tuple[str, ...] = (
    "model_key",
    "forecast_model",
    "label",
    "value",
    "target_status",
    "is_selected_model",
)
CLOSE_CYCLE_CUMULATIVE_COLUMNS: tuple[str, ...] = (
    "cycle_id",
    "cycle_end_date",
    "is_completed",
    "target_sum",
    "actual_sum",
    "achievement_rate",
    "target_cum",
    "actual_cum",
    "cumulative_achievement_rate",
    "row_count",
    "close_type",
)
STRATEGY_ARRIVAL_COMPARE_COLUMNS: tuple[str, ...] = (
    "scenario_id",
    "strategy_key",
    "strategy_type",
    "monthly_target",
    "forecast_after_provision",
    "target_variance",
    "revised_monthly_target",
    "remaining_surplus_buffer",
    "stretch_uplift",
    "relief_amount",
    "minimum_remaining_to_hit_target",
    "recommended_action",
    "compare_metric",
    "compare_label",
    "compare_value",
    "is_selected",
)
FORECAST_MODEL_VALUE_KEYS: dict[str, tuple[str, ...]] = {
    "F1": ("F1", "f1", "F1_CUMULATIVE_RATE", "f1_cumulative_rate"),
    "F2": ("F2", "f2", "F2_LAST_TWO_CLOSES", "f2_last_two_closes"),
    "F3": ("F3", "f3", "F3_DAY_CLOSE_WEIGHTED", "f3_day_close_weighted"),
}
FORECAST_MID_KEYS: tuple[str, ...] = (
    "forecast_mid",
    "representative_forecast",
    "forecast_amount",
    "forecast_after_provision",
)
PROJECTION_EMPTY_INPUT_MESSAGE = (
    "입력 데이터를 불러오면 달성 추이와 잔여기간 예측 구간이 표시됩니다."
)
PROJECTION_FORECAST_EMPTY_MESSAGE = "예측 계산 후 Projection 차트를 표시합니다."
PROJECTION_ACTUAL_EMPTY_MESSAGE = "현재 누적 실적이 입력되면 실제 추이선이 표시됩니다."
FORECAST_MODEL_MINI_EMPTY_MESSAGE = "F1/F2/F3 모델별 예측값 3개가 모두 있어야 비교 차트를 표시합니다."
STRATEGY_COMPARE_LABELS: dict[str, str] = {
    "forecast_after_provision": "월말 예상 실적",
    "revised_monthly_target": "운영 기준 목표",
    "remaining_surplus_buffer": "잔여 안전버퍼",
    "stretch_uplift": "Stretch 전환분",
    "relief_amount": "품질관리 여유분",
    "minimum_remaining_to_hit_target": "목표 달성 최소 잔여 실적",
    "target_variance": "목표 대비 차이",
    "surplus_to_target": "초과 예상분",
    "gap_to_target": "목표 미달 예상분",
}
STRATEGY_COMPARE_NUMERIC_COLUMNS: tuple[str, ...] = (
    "monthly_target",
    "forecast_after_provision",
    "target_variance",
    "revised_monthly_target",
    "remaining_surplus_buffer",
    "stretch_uplift",
    "relief_amount",
    "minimum_remaining_to_hit_target",
    "surplus_to_target",
    "gap_to_target",
)
STRATEGY_OPERATION_FALLBACK_COLUMNS: tuple[str, ...] = (
    "revised_monthly_target",
    "remaining_surplus_buffer",
    "stretch_uplift",
    "relief_amount",
    "minimum_remaining_to_hit_target",
    "target_variance",
    "surplus_to_target",
    "gap_to_target",
)


def build_forecast_trend_df(forecast_history: pd.DataFrame | Any) -> pd.DataFrame:
    """Return forecast amount trend rows by month, as-of date, metric, and model."""
    history = _as_dataframe(forecast_history)
    required = ("target_month", "as_of_date", "metric", "forecast_model", "forecast_amount")
    if history.empty or not _has_columns(history, required):
        return pd.DataFrame(columns=FORECAST_TREND_COLUMNS)

    working = history.loc[:, list(required)].copy()
    working["forecast_amount"] = pd.to_numeric(
        working["forecast_amount"],
        errors="coerce",
    )
    trend = (
        working.dropna(subset=["forecast_amount"])
        .groupby(["target_month", "as_of_date", "metric", "forecast_model"], dropna=False)
        .agg(
            forecast_amount=("forecast_amount", "mean"),
            forecast_count=("forecast_amount", "size"),
        )
        .reset_index()
    )
    return _ordered(trend, FORECAST_TREND_COLUMNS, ["target_month", "as_of_date", "forecast_model"])


def build_model_error_df(backtest_df: pd.DataFrame | Any) -> pd.DataFrame:
    """Return model-level Backtest error summary for visualization."""
    backtest = _as_dataframe(backtest_df)
    required = ("forecast_model", "abs_error", "error_rate", "forecast_error")
    if backtest.empty or not _has_columns(backtest, required):
        return pd.DataFrame(columns=MODEL_ERROR_COLUMNS)

    working = backtest.loc[:, list(required)].copy()
    for column in ("abs_error", "error_rate", "forecast_error"):
        working[column] = pd.to_numeric(working[column], errors="coerce")

    summary = (
        working.groupby("forecast_model", dropna=False)
        .agg(
            sample_count=("error_rate", "size"),
            mean_abs_error=("abs_error", "mean"),
            mean_error_rate=("error_rate", "mean"),
            median_error_rate=("error_rate", "median"),
            bias=("forecast_error", "mean"),
        )
        .reset_index()
    )
    return _ordered(summary, MODEL_ERROR_COLUMNS, ["mean_error_rate", "forecast_model"])


def build_target_status_distribution_df(
    forecast_history: pd.DataFrame | Any,
) -> pd.DataFrame:
    """Return scenario-count shares by target status for stacked charts."""
    history = _as_dataframe(forecast_history)
    required = ("target_month", "as_of_date", "metric", "target_status")
    if history.empty or not _has_columns(history, required):
        return pd.DataFrame(columns=TARGET_STATUS_DISTRIBUTION_COLUMNS)

    grouped = (
        history.loc[:, list(required)]
        .groupby(list(required), dropna=False)
        .size()
        .rename("scenario_count")
        .reset_index()
    )
    total_keys = ["target_month", "as_of_date", "metric"]
    totals = grouped.groupby(total_keys, dropna=False)["scenario_count"].transform("sum")
    grouped["scenario_share"] = grouped["scenario_count"] / totals.mask(totals == 0)
    return _ordered(
        grouped,
        TARGET_STATUS_DISTRIBUTION_COLUMNS,
        ["target_month", "as_of_date", "target_status"],
    )


def build_gap_surplus_trend_df(forecast_history: pd.DataFrame | Any) -> pd.DataFrame:
    """Return average gap and surplus trend rows by model."""
    history = _as_dataframe(forecast_history)
    required = (
        "target_month",
        "as_of_date",
        "metric",
        "forecast_model",
        "gap_to_target",
        "surplus_to_target",
    )
    if history.empty or not _has_columns(history, required):
        return pd.DataFrame(columns=GAP_SURPLUS_TREND_COLUMNS)

    working = history.loc[:, list(required)].copy()
    for column in ("gap_to_target", "surplus_to_target"):
        working[column] = pd.to_numeric(working[column], errors="coerce")

    trend = (
        working.groupby(["target_month", "as_of_date", "metric", "forecast_model"], dropna=False)
        .agg(
            gap_to_target=("gap_to_target", "mean"),
            surplus_to_target=("surplus_to_target", "mean"),
        )
        .reset_index()
    )
    return _ordered(trend, GAP_SURPLUS_TREND_COLUMNS, ["target_month", "as_of_date", "forecast_model"])


def build_strategy_mix_df(forecast_history: pd.DataFrame | Any) -> pd.DataFrame:
    """Return strategy mix rows for scenario composition visuals."""
    history = _as_dataframe(forecast_history)
    required = ("target_month", "as_of_date", "metric", "strategy_id", "strategy_type")
    if history.empty or not _has_columns(history, required):
        return pd.DataFrame(columns=STRATEGY_MIX_COLUMNS)

    grouped = (
        history.loc[:, list(required)]
        .groupby(list(required), dropna=False)
        .size()
        .rename("scenario_count")
        .reset_index()
    )
    total_keys = ["target_month", "as_of_date", "metric"]
    totals = grouped.groupby(total_keys, dropna=False)["scenario_count"].transform("sum")
    grouped["scenario_share"] = grouped["scenario_count"] / totals.mask(totals == 0)
    return _ordered(grouped, STRATEGY_MIX_COLUMNS, ["target_month", "as_of_date", "strategy_id"])


def build_visualization(
    forecast_history: pd.DataFrame | Any | None = None,
    backtest_df: pd.DataFrame | Any | None = None,
) -> dict[str, pd.DataFrame | list[str]]:
    """Return all visualization-ready tables for the history and Backtest tab."""
    warnings: list[str] = []
    history = pd.DataFrame() if forecast_history is None else _as_dataframe(forecast_history)
    backtest = pd.DataFrame() if backtest_df is None else _as_dataframe(backtest_df)

    if history.empty:
        warnings.append("forecast_history is empty; forecast history visuals are empty.")
    if backtest.empty:
        warnings.append("backtest_df is empty; model error visuals are empty.")

    return {
        "forecast_trend": build_forecast_trend_df(history),
        "model_error": build_model_error_df(backtest),
        "target_status_distribution": build_target_status_distribution_df(history),
        "gap_surplus_trend": build_gap_surplus_trend_df(history),
        "strategy_mix": build_strategy_mix_df(history),
        "warnings": warnings,
    }


def build_forecast_model_mini_chart_source(
    model_rows: pd.DataFrame | Any,
    selected_row: Mapping[str, Any] | pd.Series | None = None,
    *,
    monthly_target: object | None = None,
) -> pd.DataFrame:
    """Return exactly the F1/F2/F3 model rows for the mini comparison chart."""
    rows = _as_dataframe(model_rows)
    selected = _as_mapping(selected_row)
    if rows.empty or not _has_columns(rows, ("forecast_model", "forecast_amount")):
        return _empty_forecast_model_mini_source()

    working = rows.copy()
    working["_model_key"] = working["forecast_model"].map(_forecast_model_key)
    working["forecast_amount"] = pd.to_numeric(working["forecast_amount"], errors="coerce")
    selected_model_key = _selected_model_key(selected)

    result_rows: list[dict[str, object]] = []
    for model_key in ("F1", "F2", "F3"):
        matches = working.loc[working["_model_key"] == model_key]
        if matches.empty:
            return _empty_forecast_model_mini_source()
        row = matches.iloc[0]
        value = row.get("forecast_amount")
        if not _is_finite_number(value):
            return _empty_forecast_model_mini_source()
        result_rows.append(
            {
                "model_key": model_key,
                "forecast_model": row.get("forecast_model"),
                "label": model_key,
                "value": float(value),
                "target_status": row.get("target_status"),
                "is_selected_model": model_key == selected_model_key,
            }
        )

    source = pd.DataFrame(result_rows, columns=FORECAST_MODEL_MINI_CHART_COLUMNS)
    source.attrs["empty_state"] = ""
    source.attrs["target_line_value"] = _first_finite_value(
        monthly_target,
        selected.get("monthly_target"),
    )
    source.attrs["representative_value"] = _first_finite_value(
        selected.get("forecast_after_provision"),
        selected.get("forecast_amount"),
    )
    source.attrs["representative_model_key"] = selected_model_key
    return source


def build_close_cycle_cumulative_source(close_cycle_df: pd.DataFrame | Any) -> pd.DataFrame:
    """Return close-cycle rows with cumulative target, actual, and achievement."""
    df = _as_dataframe(close_cycle_df)
    if df.empty or not _has_columns(df, ("cycle_end_date", "target_sum", "actual_sum")):
        result = pd.DataFrame(columns=CLOSE_CYCLE_CUMULATIVE_COLUMNS)
        result.attrs["close_marker_basis"] = "is_close_day"
        return result

    columns = [column for column in CLOSE_CYCLE_CUMULATIVE_COLUMNS if column in df.columns]
    working = df.loc[:, columns].copy()
    for column in ("target_sum", "actual_sum", "achievement_rate"):
        if column in working.columns:
            working[column] = pd.to_numeric(working[column], errors="coerce")

    working["target_cum"] = working["target_sum"].fillna(0.0).cumsum()
    working["actual_cum"] = working["actual_sum"].fillna(0.0).cumsum()
    working["cumulative_achievement_rate"] = (
        working["actual_cum"] / working["target_cum"].where(working["target_cum"] != 0)
    )

    result = _ordered(
        working,
        CLOSE_CYCLE_CUMULATIVE_COLUMNS,
        ["cycle_end_date", "cycle_id"],
    )
    result.attrs["close_marker_basis"] = "is_close_day"
    return result


def build_strategy_arrival_compare_source(
    scenario_df: pd.DataFrame | Any,
    selected_scenario_id: str | None = None,
) -> pd.DataFrame:
    """Return strategy comparison rows and classify identical arrival values."""
    df = _as_dataframe(scenario_df)
    if df.empty or "scenario_id" not in df.columns:
        result = pd.DataFrame(columns=STRATEGY_ARRIVAL_COMPARE_COLUMNS)
        result.attrs.update(_strategy_compare_attrs("NO_DATA", "table", True, True, ""))
        return result

    working = df.copy()
    selected_forecast = _selected_forecast_key(selected_scenario_id)
    if selected_forecast:
        focused = working.loc[working["scenario_id"].astype(str).str.startswith(f"{selected_forecast}_")]
        if not focused.empty:
            working = focused

    working["scenario_id"] = working["scenario_id"].astype(str)
    working["strategy_key"] = working["scenario_id"].map(_strategy_key_from_scenario_id)
    for column in STRATEGY_COMPARE_NUMERIC_COLUMNS:
        if column in working.columns:
            working[column] = pd.to_numeric(working[column], errors="coerce")
        else:
            working[column] = pd.NA
    for column in ("strategy_type", "recommended_action"):
        if column not in working.columns:
            working[column] = ""

    forecast_identical = _column_values_identical(working, "forecast_after_provision")
    compare_metric = "forecast_after_provision"
    display_mode = "chart"
    fallback_used = False
    classification = "DISPLAY_OK"

    if forecast_identical:
        fallback_used = True
        display_mode = "table"
        compare_metric = _first_meaningful_difference_column(
            working,
            STRATEGY_OPERATION_FALLBACK_COLUMNS,
        )
        if compare_metric:
            classification = "TRUE_IDENTICAL_BY_DESIGN"
        else:
            compare_metric = "forecast_after_provision"
            classification = (
                "TRUE_IDENTICAL_BY_DESIGN"
                if _has_textual_strategy_difference(working)
                else "NEEDS_LOGIC_REVIEW"
            )

    working["compare_metric"] = compare_metric
    working["compare_label"] = STRATEGY_COMPARE_LABELS.get(compare_metric, compare_metric)
    working["compare_value"] = pd.to_numeric(working[compare_metric], errors="coerce")
    working["is_selected"] = working["scenario_id"] == str(selected_scenario_id or "")

    result = _ordered(
        working,
        STRATEGY_ARRIVAL_COMPARE_COLUMNS,
        ["strategy_key", "scenario_id"],
    )
    result.attrs.update(
        _strategy_compare_attrs(
            classification,
            display_mode,
            fallback_used,
            forecast_identical,
            compare_metric,
        )
    )
    return result


def build_projection_band_data(
    input_df: pd.DataFrame | Any,
    forecast_result: Mapping[str, Any] | Any,
    target_status: object,
    *,
    current_day_no: object | None = None,
    target_daily_column: str = "sales_target_daily",
    actual_cum_column: str = "sales_actual_cum",
) -> pd.DataFrame:
    """Return chart-ready rows for achievement trend and expected arrival band.

    The helper only reuses rows already present in ``input_df``. Projection values
    are display interpolation between the current actual point and existing
    forecast outputs; they do not replace the forecast model calculations.
    """
    df = _as_dataframe(input_df)
    required = ("date", "business_day_no", "is_close_day", target_daily_column, actual_cum_column)
    if df.empty or not _has_columns(df, required):
        return _empty_projection(PROJECTION_EMPTY_INPUT_MESSAGE)

    working = df.copy()
    if "day_name" not in working.columns:
        working["day_name"] = pd.NA

    try:
        working["date"] = pd.to_datetime(working["date"], errors="raise").dt.normalize()
        working["business_day_no"] = working["business_day_no"]
        working["_target_daily_numeric"] = pd.to_numeric(
            working[target_daily_column],
            errors="coerce",
        )
        actual_values = working[actual_cum_column].replace(r"^\s*$", pd.NA, regex=True)
        working["_actual_cum_numeric"] = pd.to_numeric(actual_values, errors="coerce")
        working["_is_close_day_bool"] = _coerce_close_day_flags(working["is_close_day"])
    except Exception:  # noqa: BLE001 - display source should fail closed.
        return _empty_projection(PROJECTION_EMPTY_INPUT_MESSAGE)

    working = working.sort_values(["business_day_no"], kind="mergesort").reset_index(drop=True)
    working["_target_cum"] = working["_target_daily_numeric"].fillna(0.0).cumsum()

    forecast_values = _extract_forecast_values(forecast_result)
    f_values = [forecast_values.get(key) for key in ("F1", "F2", "F3")]
    finite_f_values = [value for value in f_values if _is_finite_number(value)]
    if len(finite_f_values) < 3:
        return _empty_projection(PROJECTION_FORECAST_EMPTY_MESSAGE)

    forecast_low = min(finite_f_values)
    forecast_high = max(finite_f_values)
    forecast_mid = forecast_values.get("mid")
    if not _is_finite_number(forecast_mid):
        forecast_mid = sum(finite_f_values) / len(finite_f_values)

    current_position = _current_position_index(working, current_day_no)
    if current_position is None:
        return _empty_projection(PROJECTION_ACTUAL_EMPTY_MESSAGE)

    current_actual = working.loc[current_position, "_actual_cum_numeric"]
    if not _is_finite_number(current_actual):
        return _empty_projection(PROJECTION_ACTUAL_EMPTY_MESSAGE)

    current_business_day_no = working.loc[current_position, "business_day_no"]
    next_close_day_no = _next_close_business_day_no(working, current_business_day_no)
    zone = _zone_label(target_status)
    projection_positions = [index for index in working.index if index >= current_position]
    last_projection_position = max(projection_positions) if projection_positions else current_position
    projection_span = max(last_projection_position - current_position, 1)

    result = pd.DataFrame(
        {
            "date": working["date"],
            "day_name": working["day_name"],
            "business_day_no": working["business_day_no"],
            "is_close_day": working["_is_close_day_bool"],
            "actual_cum": working["_actual_cum_numeric"],
            "target_cum": working["_target_cum"],
        }
    )
    result["forecast_low"] = pd.NA
    result["forecast_mid"] = pd.NA
    result["forecast_high"] = pd.NA
    result["projection_mid"] = pd.NA
    result["zone"] = zone
    result["is_actual_period"] = result.index <= current_position
    result["is_projection_period"] = result.index >= current_position
    result["is_current_point"] = result.index == current_position
    result["is_next_close_day"] = (
        False
        if next_close_day_no is None
        else result["business_day_no"].astype(str) == str(next_close_day_no)
    )
    result["point_type"] = "future"
    result.loc[result["actual_cum"].notna(), "point_type"] = "actual"
    result.loc[result["is_projection_period"], "point_type"] = "projection"
    result.loc[result["is_current_point"], "point_type"] = "current"

    for index in projection_positions:
        fraction = (index - current_position) / projection_span
        result.loc[index, "forecast_low"] = _interpolate(current_actual, forecast_low, fraction)
        result.loc[index, "forecast_mid"] = _interpolate(current_actual, forecast_mid, fraction)
        result.loc[index, "forecast_high"] = _interpolate(current_actual, forecast_high, fraction)
        result.loc[index, "projection_mid"] = result.loc[index, "forecast_mid"]

    result = result.loc[:, list(PROJECTION_BAND_COLUMNS)].reset_index(drop=True)
    result.attrs["empty_state"] = ""
    result.attrs["forecast_low_final"] = forecast_low
    result.attrs["forecast_mid_final"] = forecast_mid
    result.attrs["forecast_high_final"] = forecast_high
    return result


def build_pace_projection_chart_data(
    input_df: pd.DataFrame | Any,
    forecast_result: Mapping[str, Any] | Any,
    target_status: object,
    *,
    current_day_no: object | None = None,
    target_daily_column: str = "sales_target_daily",
    actual_cum_column: str = "sales_actual_cum",
) -> pd.DataFrame:
    """Compatibility wrapper for the pace projection chart source."""
    return build_projection_band_data(
        input_df,
        forecast_result,
        target_status,
        current_day_no=current_day_no,
        target_daily_column=target_daily_column,
        actual_cum_column=actual_cum_column,
    )


def build_close_day_markers(
    input_df: pd.DataFrame | Any,
    *,
    current_day_no: object | None = None,
) -> pd.DataFrame:
    """Return close-day marker rows using only the user-provided is_close_day column."""
    df = _as_dataframe(input_df)
    if df.empty or not _has_columns(df, ("date", "business_day_no", "is_close_day")):
        return pd.DataFrame(columns=CLOSE_DAY_MARKER_COLUMNS)

    working = df.copy()
    if "day_name" not in working.columns:
        working["day_name"] = pd.NA

    try:
        working["date"] = pd.to_datetime(working["date"], errors="coerce").dt.normalize()
        working["_is_close_day_bool"] = _coerce_close_day_flags(working["is_close_day"])
    except Exception:  # noqa: BLE001 - display source should fail closed.
        return pd.DataFrame(columns=CLOSE_DAY_MARKER_COLUMNS)

    markers = working.loc[working["_is_close_day_bool"]].copy()
    if markers.empty:
        return pd.DataFrame(columns=CLOSE_DAY_MARKER_COLUMNS)

    next_close_day_no = _next_close_business_day_no(markers, current_day_no)
    markers["is_close_day"] = True
    markers["is_next_close_day"] = (
        False
        if next_close_day_no is None
        else markers["business_day_no"].astype(str) == str(next_close_day_no)
    )
    return markers.loc[:, list(CLOSE_DAY_MARKER_COLUMNS)].reset_index(drop=True)


def _empty_forecast_model_mini_source() -> pd.DataFrame:
    result = pd.DataFrame(columns=FORECAST_MODEL_MINI_CHART_COLUMNS)
    result.attrs["empty_state"] = FORECAST_MODEL_MINI_EMPTY_MESSAGE
    result.attrs["target_line_value"] = float("nan")
    result.attrs["representative_value"] = float("nan")
    result.attrs["representative_model_key"] = ""
    return result


def _as_mapping(value: Mapping[str, Any] | pd.Series | None) -> dict[str, Any]:
    if isinstance(value, pd.Series):
        return value.to_dict()
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _forecast_model_key(value: object) -> str:
    text = "" if pd.isna(value) else str(value)
    upper = text.upper()
    for model_key, aliases in FORECAST_MODEL_VALUE_KEYS.items():
        if upper == model_key:
            return model_key
        if any(upper == alias.upper() for alias in aliases):
            return model_key
    if upper.startswith("F1"):
        return "F1"
    if upper.startswith("F2"):
        return "F2"
    if upper.startswith("F3"):
        return "F3"
    return text


def _selected_model_key(selected: Mapping[str, Any]) -> str:
    scenario_id = selected.get("scenario_id")
    if scenario_id is not None and not pd.isna(scenario_id):
        forecast_key = _selected_forecast_key(str(scenario_id))
        if forecast_key:
            return forecast_key
    return _forecast_model_key(selected.get("forecast_model"))


def _selected_forecast_key(scenario_id: str | None) -> str:
    if not scenario_id:
        return ""
    text = str(scenario_id)
    if "_" not in text:
        return _forecast_model_key(text)
    return _forecast_model_key(text.split("_", maxsplit=1)[0])


def _strategy_key_from_scenario_id(scenario_id: object) -> str:
    text = str(scenario_id)
    if "_" not in text:
        return ""
    return text.split("_", maxsplit=1)[1]


def _first_finite_value(*values: object) -> float:
    for value in values:
        if _is_finite_number(value):
            return float(value)
    return float("nan")


def _column_values_identical(df: pd.DataFrame, column: str) -> bool:
    if column not in df.columns:
        return True
    values = pd.to_numeric(df[column], errors="coerce").dropna()
    if values.empty:
        return True
    return values.nunique(dropna=True) <= 1


def _first_meaningful_difference_column(
    df: pd.DataFrame,
    columns: tuple[str, ...],
) -> str:
    for column in columns:
        if column in df.columns and not _column_values_identical(df, column):
            return column
    return ""


def _has_textual_strategy_difference(df: pd.DataFrame) -> bool:
    for column in ("strategy_type", "recommended_action"):
        if column in df.columns and df[column].astype(str).nunique(dropna=True) > 1:
            return True
    return False


def _strategy_compare_attrs(
    classification: str,
    display_mode: str,
    fallback_used: bool,
    identical_forecast_values: bool,
    compare_metric: str,
) -> dict[str, object]:
    return {
        "classification": classification,
        "display_mode": display_mode,
        "fallback_used": bool(fallback_used),
        "identical_forecast_values": bool(identical_forecast_values),
        "compare_metric": compare_metric,
        "compare_label": STRATEGY_COMPARE_LABELS.get(compare_metric, compare_metric),
    }


def _as_dataframe(value: pd.DataFrame | Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if value is None:
        return pd.DataFrame()
    raise ValueError("visualization input must be a DataFrame.")


def _has_columns(df: pd.DataFrame, columns: tuple[str, ...]) -> bool:
    return set(columns).issubset(df.columns)


def _ordered(df: pd.DataFrame, columns: tuple[str, ...], sort_by: list[str]) -> pd.DataFrame:
    result = df.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = pd.NA
    if result.empty:
        return pd.DataFrame(columns=columns)
    available_sort = [column for column in sort_by if column in result.columns]
    if available_sort:
        result = result.sort_values(available_sort, kind="mergesort")
    return result.loc[:, list(columns)].reset_index(drop=True)


def _empty_projection(message: str) -> pd.DataFrame:
    result = pd.DataFrame(columns=PROJECTION_BAND_COLUMNS)
    result.attrs["empty_state"] = message
    return result


def _coerce_close_day_flags(values: pd.Series) -> pd.Series:
    truthy = {"true", "t", "1", "y", "yes"}
    falsy = {"false", "f", "0", "n", "no", ""}

    def coerce(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if pd.isna(value):
            return False
        text = str(value).strip().lower()
        if text in truthy:
            return True
        if text in falsy:
            return False
        return False

    return values.map(coerce).astype(bool)


def _extract_forecast_values(forecast_result: Mapping[str, Any] | Any) -> dict[str, float]:
    if not isinstance(forecast_result, Mapping):
        return {}

    result: dict[str, float] = {}
    for model_key, aliases in FORECAST_MODEL_VALUE_KEYS.items():
        for alias in aliases:
            value = _forecast_value_at_key(forecast_result, alias)
            if _is_finite_number(value):
                result[model_key] = float(value)
                break

    for key in FORECAST_MID_KEYS:
        value = _forecast_value_at_key(forecast_result, key)
        if _is_finite_number(value):
            result["mid"] = float(value)
            break

    for nested_key in ("forecast_summary", "forecast_by_model", "models", "model_results"):
        nested = forecast_result.get(nested_key)
        if isinstance(nested, Mapping):
            nested_values = _extract_forecast_values(nested)
            result = {**nested_values, **result}

    return result


def _forecast_value_at_key(source: Mapping[str, Any], key: str) -> float:
    if key not in source:
        return float("nan")
    value = source.get(key)
    if isinstance(value, Mapping):
        for nested_key in ("forecast_amount", "amount", "value"):
            nested_value = value.get(nested_key)
            if _is_finite_number(nested_value):
                return float(nested_value)
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _current_position_index(working: pd.DataFrame, current_day_no: object | None) -> int | None:
    if current_day_no is not None:
        matches = working.index[working["business_day_no"].astype(str) == str(current_day_no)].tolist()
        if matches:
            matched_index = matches[-1]
            if _is_finite_number(working.loc[matched_index, "_actual_cum_numeric"]):
                return int(matched_index)

    actual_rows = working.index[working["_actual_cum_numeric"].notna()].tolist()
    if not actual_rows:
        return None
    return int(actual_rows[-1])


def _next_close_business_day_no(
    working: pd.DataFrame,
    current_day_no: object | None,
) -> object | None:
    close_rows = working.loc[working["_is_close_day_bool"]].copy()
    if close_rows.empty:
        return None
    if current_day_no is None:
        return close_rows.iloc[0].get("business_day_no")

    close_day_numbers = pd.to_numeric(close_rows["business_day_no"], errors="coerce")
    current_number = pd.to_numeric(pd.Series([current_day_no]), errors="coerce").iloc[0]
    if pd.isna(current_number):
        return close_rows.iloc[0].get("business_day_no")

    future = close_rows.loc[close_day_numbers > float(current_number)]
    if future.empty:
        return None
    return future.iloc[0].get("business_day_no")


def _zone_label(target_status: object) -> str:
    status = "" if pd.isna(target_status) else str(target_status)
    labels = {
        "UNDER_TARGET": "UNDER_TARGET: 목표선 미달 구간",
        "ON_TARGET": "ON_TARGET: 계획선 근접 구간",
        "OVER_TARGET": "OVER_TARGET: 초과달성 관리 구간",
    }
    return labels.get(status, "UNKNOWN_TARGET_STATUS: 계산 확인 구간")


def _interpolate(start: float, end: float, fraction: float) -> float:
    return float(start) + (float(end) - float(start)) * float(fraction)


def _is_finite_number(value: object) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return pd.notna(number) and number not in {float("inf"), float("-inf")}
