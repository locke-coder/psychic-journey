"""Excel workbook export helpers for daily closing reports."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from datetime import date, datetime
from math import isfinite
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from src.report_builder import append_model_error_summary_to_report


SHEET_NAMES = (
    "Summary",
    "ScenarioGrid",
    "DailyRevisedTargets",
    "CloseCycle",
    "Validation",
    "ReportText",
    "ForecastHistory",
    "FinalActuals",
    "BacktestSummary",
    "ModelWeights",
    "ConfidenceBand",
    "Insights",
)
EXPORT_VERSION = "v2"

AMOUNT_NUMBER_FORMAT = '#,##0.0'
RATE_NUMBER_FORMAT = '0.0%'
DATE_NUMBER_FORMAT = 'yyyy-mm-dd'

_HEADER_FILL = PatternFill(fill_type="solid", fgColor="44546A")
_HEADER_FONT = Font(bold=True, color="FFFFFF")
_HEADER_BORDER = Border(bottom=Side(style="thin", color="B7C9D6"))
_REPO_ROOT = Path(__file__).resolve().parents[1]

_AMOUNT_NAME_HINTS = (
    "amount",
    "target",
    "actual",
    "forecast",
    "gap",
    "uplift",
    "sales",
    "recognized",
    "required",
    "allocated",
    "unallocated",
    "remaining",
    "sum",
)
_RATE_NAME_HINTS = ("rate", "ratio", "pct", "percent", "achievement")
_COUNT_NAME_HINTS = ("count", "cycle_id", "day_no", "business_day_no")
_PERCENT_BASIS_COLUMNS = {"achievement_rate"}
_VERSION_TOKEN_PATTERN = re.compile(
    r"(^|[_-])(v\d+|version\d+|generated_at[_-]?\d{8,})([_-]|$)",
    re.IGNORECASE,
)
FORECAST_HISTORY_MESSAGE = "No forecast_history data is available yet."
FINAL_ACTUALS_MESSAGE = "No final_actuals data is available yet."
BACKTEST_SUMMARY_MESSAGE = (
    "No BacktestSummary data is available. Save forecast_history and final_actuals first."
)
MODEL_WEIGHTS_MESSAGE = "No ModelWeights data is available until model error rates exist."
CONFIDENCE_BAND_MESSAGE = "No ConfidenceBand data is available yet."
INSIGHTS_MESSAGE = "No Insights data is available yet."
BACKTEST_SUMMARY_COLUMNS = (
    "forecast_model",
    "sample_count",
    "error_rate",
    "bias",
    "mean_abs_error",
    "mean_error_rate",
    "median_error_rate",
    "best_model_by_error_rate",
)
MODEL_WEIGHTS_COLUMNS = (
    "forecast_model",
    "sample_count",
    "error_rate",
    "bias",
    "model_weight",
)
CONFIDENCE_BAND_COLUMNS = (
    "target_month",
    "as_of_date",
    "metric",
    "forecast_model",
    "forecast_amount",
    "confidence_lower",
    "confidence_upper",
)
INSIGHTS_COLUMNS = ("insight",)
SCENARIO_GRID_REQUIRED_COLUMNS = (
    "target_status",
    "surplus_to_target",
    "strategy_type",
    "overachievement_strategy",
)
CONFIDENCE_BAND_COLUMN_PAIRS = (
    ("confidence_lower", "confidence_upper"),
    ("forecast_lower", "forecast_upper"),
    ("lower_bound", "upper_bound"),
)


def export_daily_report(
    output_path: str | Path,
    summary_dict: Mapping[str, Any],
    scenario_df: pd.DataFrame,
    revised_targets_df: pd.DataFrame,
    close_cycle_df: pd.DataFrame,
    validation_result: Mapping[str, Any] | Any,
    report_text: str,
    *,
    forecast_history_df: pd.DataFrame | Any | None = None,
    final_actuals_df: pd.DataFrame | Any | None = None,
    backtest_summary_df: pd.DataFrame | Any | None = None,
    model_weights_df: pd.DataFrame | Any | None = None,
    confidence_band_df: pd.DataFrame | Any | None = None,
    insights_df: pd.DataFrame | Any | None = None,
    overwrite: bool = True,
) -> Path:
    """Export the daily report workbook and return the saved path."""
    resolved_output_path = _resolve_output_path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)

    if resolved_output_path.exists() and not overwrite:
        raise FileExistsError(
            f"{resolved_output_path} already exists. Set overwrite=True to replace it."
        )

    workbook = Workbook()
    summary_sheet = workbook.active
    summary_sheet.title = "Summary"

    history_tables = _build_history_export_tables(
        forecast_history_df,
        final_actuals_df,
        backtest_summary_df,
        model_weights_df,
        confidence_band_df,
        insights_df,
    )
    report_text = append_model_error_summary_to_report(
        report_text,
        history_tables["BacktestSummary"],
    )

    _write_mapping_sheet(summary_sheet, summary_dict)
    _write_dataframe_sheet(
        workbook.create_sheet("ScenarioGrid"),
        _ensure_dataframe_columns(scenario_df, SCENARIO_GRID_REQUIRED_COLUMNS),
    )
    _write_dataframe_sheet(workbook.create_sheet("DailyRevisedTargets"), revised_targets_df)
    _write_dataframe_sheet(workbook.create_sheet("CloseCycle"), close_cycle_df)
    _write_mapping_sheet(workbook.create_sheet("Validation"), validation_result)
    _write_report_text_sheet(workbook.create_sheet("ReportText"), report_text)
    _write_optional_dataframe_sheet(
        workbook.create_sheet("ForecastHistory"),
        history_tables["ForecastHistory"],
        FORECAST_HISTORY_MESSAGE,
    )
    _write_optional_dataframe_sheet(
        workbook.create_sheet("FinalActuals"),
        history_tables["FinalActuals"],
        FINAL_ACTUALS_MESSAGE,
    )
    _write_optional_dataframe_sheet(
        workbook.create_sheet("BacktestSummary"),
        history_tables["BacktestSummary"],
        BACKTEST_SUMMARY_MESSAGE,
        BACKTEST_SUMMARY_COLUMNS,
    )
    _write_optional_dataframe_sheet(
        workbook.create_sheet("ModelWeights"),
        history_tables["ModelWeights"],
        MODEL_WEIGHTS_MESSAGE,
        MODEL_WEIGHTS_COLUMNS,
    )
    _write_optional_dataframe_sheet(
        workbook.create_sheet("ConfidenceBand"),
        history_tables["ConfidenceBand"],
        CONFIDENCE_BAND_MESSAGE,
        CONFIDENCE_BAND_COLUMNS,
    )
    _write_optional_dataframe_sheet(
        workbook.create_sheet("Insights"),
        history_tables["Insights"],
        INSIGHTS_MESSAGE,
        INSIGHTS_COLUMNS,
    )

    workbook.save(resolved_output_path)
    return resolved_output_path


def _build_history_export_tables(
    forecast_history_df: pd.DataFrame | Any | None,
    final_actuals_df: pd.DataFrame | Any | None,
    backtest_summary_df: pd.DataFrame | Any | None,
    model_weights_df: pd.DataFrame | Any | None,
    confidence_band_df: pd.DataFrame | Any | None,
    insights_df: pd.DataFrame | Any | None,
) -> dict[str, pd.DataFrame]:
    forecast_history = (
        _load_default_forecast_history()
        if forecast_history_df is None
        else _as_dataframe(forecast_history_df)
    )
    final_actuals = (
        _load_default_final_actuals()
        if final_actuals_df is None
        else _as_dataframe(final_actuals_df)
    )
    backtest_summary = (
        _build_default_backtest_summary(forecast_history, final_actuals)
        if backtest_summary_df is None
        else _as_dataframe(backtest_summary_df)
    )
    backtest_summary = _normalize_backtest_summary(backtest_summary)

    model_weights = (
        _build_model_weights(backtest_summary)
        if model_weights_df is None
        else _as_dataframe(model_weights_df)
    )
    confidence_band = (
        _build_confidence_band_frame(forecast_history)
        if confidence_band_df is None
        else _as_dataframe(confidence_band_df)
    )
    insights = (
        _build_insights_frame(forecast_history, final_actuals, backtest_summary)
        if insights_df is None
        else _as_dataframe(insights_df)
    )

    return {
        "ForecastHistory": forecast_history,
        "FinalActuals": final_actuals,
        "BacktestSummary": backtest_summary,
        "ModelWeights": model_weights,
        "ConfidenceBand": confidence_band,
        "Insights": insights,
    }


def _load_default_forecast_history() -> pd.DataFrame:
    try:
        from src import history_schema
        from src.history_store import load_forecast_history

        path = history_schema.get_storage_paths(repo_root=_REPO_ROOT)[
            history_schema.FORECAST_HISTORY
        ]
        return load_forecast_history(path)
    except Exception:  # noqa: BLE001 - export should remain safe without history.
        return pd.DataFrame()


def _load_default_final_actuals() -> pd.DataFrame:
    try:
        from src import history_schema
        from src.final_actual_store import load_final_actuals

        path = history_schema.get_storage_paths(repo_root=_REPO_ROOT)[
            history_schema.FINAL_ACTUALS
        ]
        return load_final_actuals(path)
    except Exception:  # noqa: BLE001 - export should remain safe without final actuals.
        return pd.DataFrame()


def _build_default_backtest_summary(
    forecast_history: pd.DataFrame,
    final_actuals: pd.DataFrame,
) -> pd.DataFrame:
    try:
        from src.backtest_engine import build_backtest_dataset, summarize_by_forecast_model

        backtest_df = build_backtest_dataset(forecast_history, final_actuals)
        return summarize_by_forecast_model(backtest_df)
    except Exception:  # noqa: BLE001 - empty summary is safer than blocking export.
        return pd.DataFrame(columns=BACKTEST_SUMMARY_COLUMNS)


def _normalize_backtest_summary(backtest_summary: pd.DataFrame) -> pd.DataFrame:
    summary = _as_dataframe(backtest_summary)
    if summary.empty and len(summary.columns) == 0:
        return pd.DataFrame(columns=BACKTEST_SUMMARY_COLUMNS)
    if "error_rate" not in summary.columns and "mean_error_rate" in summary.columns:
        summary = summary.copy()
        summary["error_rate"] = summary["mean_error_rate"]

    for column in BACKTEST_SUMMARY_COLUMNS:
        if column not in summary.columns:
            summary[column] = None
    ordered_columns = [
        *BACKTEST_SUMMARY_COLUMNS,
        *(column for column in summary.columns if column not in BACKTEST_SUMMARY_COLUMNS),
    ]
    return summary.loc[:, ordered_columns]


def _build_model_weights(backtest_summary: pd.DataFrame) -> pd.DataFrame:
    if backtest_summary.empty:
        return pd.DataFrame(columns=MODEL_WEIGHTS_COLUMNS)
    if "forecast_model" not in backtest_summary.columns or "error_rate" not in backtest_summary.columns:
        return pd.DataFrame(columns=MODEL_WEIGHTS_COLUMNS)

    weights = backtest_summary.copy()
    weights["error_rate"] = pd.to_numeric(weights["error_rate"], errors="coerce")
    finite_rows = weights.loc[weights["error_rate"].map(_is_finite_number)].copy()
    if finite_rows.empty:
        return pd.DataFrame(columns=MODEL_WEIGHTS_COLUMNS)

    zero_error = finite_rows.loc[finite_rows["error_rate"] == 0]
    if not zero_error.empty:
        finite_rows["model_weight"] = 0.0
        finite_rows.loc[zero_error.index, "model_weight"] = 1.0 / len(zero_error)
    else:
        finite_rows = finite_rows.loc[finite_rows["error_rate"] > 0].copy()
        if finite_rows.empty:
            return pd.DataFrame(columns=MODEL_WEIGHTS_COLUMNS)
        inverse_error = 1.0 / finite_rows["error_rate"]
        finite_rows["model_weight"] = inverse_error / inverse_error.sum()

    for column in MODEL_WEIGHTS_COLUMNS:
        if column not in finite_rows.columns:
            finite_rows[column] = None
    return finite_rows.loc[:, list(MODEL_WEIGHTS_COLUMNS)].reset_index(drop=True)


def _build_confidence_band_frame(forecast_history: pd.DataFrame) -> pd.DataFrame:
    history = _as_dataframe(forecast_history)
    if history.empty:
        return pd.DataFrame(columns=CONFIDENCE_BAND_COLUMNS)

    band_pair = _confidence_band_pair(history)
    if band_pair is None:
        return pd.DataFrame(columns=CONFIDENCE_BAND_COLUMNS)

    lower_column, upper_column = band_pair
    result = history.copy()
    if lower_column != "confidence_lower":
        result["confidence_lower"] = result[lower_column]
    if upper_column != "confidence_upper":
        result["confidence_upper"] = result[upper_column]

    for column in CONFIDENCE_BAND_COLUMNS:
        if column not in result.columns:
            result[column] = None
    return result.loc[:, list(CONFIDENCE_BAND_COLUMNS)].dropna(
        how="all",
        subset=["confidence_lower", "confidence_upper"],
    )


def _confidence_band_pair(df: pd.DataFrame) -> tuple[str, str] | None:
    columns = set(df.columns)
    for lower_column, upper_column in CONFIDENCE_BAND_COLUMN_PAIRS:
        if lower_column in columns and upper_column in columns:
            return lower_column, upper_column
    return None


def _build_insights_frame(
    forecast_history: pd.DataFrame,
    final_actuals: pd.DataFrame,
    backtest_summary: pd.DataFrame,
) -> pd.DataFrame:
    insights: list[str] = []
    if forecast_history.empty:
        insights.append(FORECAST_HISTORY_MESSAGE)
    if final_actuals.empty:
        insights.append(FINAL_ACTUALS_MESSAGE)
    if backtest_summary.empty:
        insights.append(BACKTEST_SUMMARY_MESSAGE)
    else:
        ranked = backtest_summary.copy()
        ranked["error_rate"] = pd.to_numeric(ranked["error_rate"], errors="coerce")
        ranked = ranked.loc[ranked["error_rate"].map(_is_finite_number)].sort_values(
            ["error_rate", "forecast_model"],
            ascending=[True, True],
            kind="mergesort",
        )
        if not ranked.empty:
            best = ranked.iloc[0]
            insights.append(
                "Best model by Backtest error_rate: "
                f"{best.get('forecast_model')} ({best.get('error_rate'):.1%})."
            )
    if not insights:
        insights.append("History export data is available.")
    return pd.DataFrame({"insight": insights})


def _resolve_output_path(output_path: str | Path) -> Path:
    path = Path(output_path)
    if path.suffix.lower() != ".xlsx":
        path = path.with_suffix(".xlsx")
    path = _ensure_versioned_path(path)

    if path.is_absolute():
        return path

    if path.parts and path.parts[0].lower() == "outputs":
        return _REPO_ROOT / path

    return _REPO_ROOT / "outputs" / path.name


def _ensure_versioned_path(path: Path) -> Path:
    if _VERSION_TOKEN_PATTERN.search(path.stem):
        return path
    return path.with_name(f"{path.stem}_{EXPORT_VERSION}{path.suffix}")


def _write_dataframe_sheet(ws: Worksheet, data: pd.DataFrame | Any) -> None:
    df = _as_dataframe(data)

    if df.empty and len(df.columns) == 0:
        ws.append(["message"])
        ws.append(["No data"])
        _apply_common_style(ws)
        return

    headers = [str(column) for column in df.columns]
    ws.append(headers)
    for row in df.itertuples(index=False, name=None):
        ws.append([_to_excel_value(value) for value in row])

    _apply_common_style(ws)
    _apply_column_formats(ws, headers)


def _write_optional_dataframe_sheet(
    ws: Worksheet,
    data: pd.DataFrame | Any,
    empty_message: str,
    fallback_columns: tuple[str, ...] = (),
) -> None:
    df = _as_dataframe(data)
    if df.empty:
        headers = list(df.columns) if len(df.columns) > 0 else list(fallback_columns)
        if not headers:
            headers = ["message"]
        if "message" not in headers:
            headers.append("message")
        ws.append([str(column) for column in headers])
        row = [None] * len(headers)
        row[headers.index("message")] = empty_message
        ws.append(row)
        _apply_common_style(ws)
        _apply_column_formats(ws, [str(column) for column in headers])
        return

    _write_dataframe_sheet(ws, df)


def _ensure_dataframe_columns(
    data: pd.DataFrame | Any,
    required_columns: tuple[str, ...],
) -> pd.DataFrame:
    df = _as_dataframe(data)
    for column in required_columns:
        if column not in df.columns:
            df[column] = None
    return df


def _write_mapping_sheet(ws: Worksheet, data: Mapping[str, Any] | Any) -> None:
    ws.append(["item", "value"])

    if isinstance(data, Mapping):
        items = data.items()
    else:
        items = [("value", data)]

    for key, value in items:
        ws.append([str(key), _to_excel_value(value)])

    _apply_common_style(ws)
    _apply_key_value_formats(ws)


def _write_report_text_sheet(ws: Worksheet, report_text: str) -> None:
    ws.append(["report_text"])
    ws.append([str(report_text)])
    ws["A2"].alignment = Alignment(wrap_text=True, vertical="top")
    ws.column_dimensions["A"].width = 100
    ws.row_dimensions[2].height = 90
    _apply_common_style(ws)


def _as_dataframe(data: pd.DataFrame | Any) -> pd.DataFrame:
    if isinstance(data, pd.DataFrame):
        return data.copy(deep=False)
    if data is None:
        return pd.DataFrame()
    return pd.DataFrame(data)


def _to_excel_value(value: object) -> object:
    if isinstance(value, pd.Timestamp):
        timestamp = value.to_pydatetime()
        return timestamp.replace(tzinfo=None) if timestamp.tzinfo else timestamp

    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value

    if isinstance(value, date):
        return value

    if isinstance(value, Mapping):
        return json.dumps(value, ensure_ascii=False, default=str)

    if isinstance(value, (list, tuple, set)):
        return json.dumps(list(value), ensure_ascii=False, default=str)

    try:
        missing = pd.isna(value)
    except (TypeError, ValueError):
        missing = False

    if isinstance(missing, bool) and missing:
        return None

    if isinstance(value, float) and not isfinite(value):
        return None

    if hasattr(value, "item"):
        try:
            return value.item()
        except ValueError:
            return value

    return value


def _apply_common_style(ws: Worksheet) -> None:
    _style_header(ws)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = _used_range_ref(ws)
    _resize_columns(ws)


def _style_header(ws: Worksheet) -> None:
    for cell in ws[1]:
        cell.fill = _HEADER_FILL
        cell.font = _HEADER_FONT
        cell.border = _HEADER_BORDER
        cell.alignment = Alignment(horizontal="center")


def _used_range_ref(ws: Worksheet) -> str:
    return f"A1:{get_column_letter(ws.max_column)}{max(ws.max_row, 1)}"


def _resize_columns(ws: Worksheet) -> None:
    for column_cells in ws.columns:
        column_letter = get_column_letter(column_cells[0].column)
        if ws.title == "ReportText" and column_letter == "A":
            continue

        max_length = 0
        for cell in column_cells:
            value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, len(value))
        ws.column_dimensions[column_letter].width = min(max(max_length + 2, 10), 42)


def _apply_column_formats(ws: Worksheet, headers: list[str]) -> None:
    for column_index, header in enumerate(headers, start=1):
        for row_index in range(2, ws.max_row + 1):
            cell = ws.cell(row=row_index, column=column_index)
            _apply_cell_format(cell, header)


def _apply_key_value_formats(ws: Worksheet) -> None:
    for row_index in range(2, ws.max_row + 1):
        label = str(ws.cell(row=row_index, column=1).value or "")
        cell = ws.cell(row=row_index, column=2)
        _apply_cell_format(cell, label)


def _apply_cell_format(cell: Any, label: str) -> None:
    if not _is_number(cell.value):
        if _is_date_label(label) and cell.value is not None:
            cell.number_format = DATE_NUMBER_FORMAT
        return

    if _is_rate_label(label):
        if _is_percent_basis_label(label) and abs(cell.value) > 1:
            cell.value = cell.value / 100
        cell.number_format = RATE_NUMBER_FORMAT
        return

    if _is_amount_label(label):
        cell.number_format = AMOUNT_NUMBER_FORMAT


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite_number(value: object) -> bool:
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _is_rate_label(label: str) -> bool:
    normalized = label.lower()
    return any(hint in normalized for hint in _RATE_NAME_HINTS)


def _is_percent_basis_label(label: str) -> bool:
    return label.lower() in _PERCENT_BASIS_COLUMNS


def _is_amount_label(label: str) -> bool:
    normalized = label.lower()
    if any(hint in normalized for hint in _COUNT_NAME_HINTS):
        return False
    if _is_rate_label(normalized) or _is_date_label(normalized):
        return False
    return any(hint in normalized for hint in _AMOUNT_NAME_HINTS)


def _is_date_label(label: str) -> bool:
    return "date" in label.lower()
