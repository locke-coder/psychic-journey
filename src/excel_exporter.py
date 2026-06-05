"""Excel workbook export helpers for daily closing reports."""

from __future__ import annotations

import json
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


SHEET_NAMES = (
    "Summary",
    "ScenarioGrid",
    "DailyRevisedTargets",
    "CloseCycle",
    "Validation",
    "ReportText",
)

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


def export_daily_report(
    output_path: str | Path,
    summary_dict: Mapping[str, Any],
    scenario_df: pd.DataFrame,
    revised_targets_df: pd.DataFrame,
    close_cycle_df: pd.DataFrame,
    validation_result: Mapping[str, Any] | Any,
    report_text: str,
    *,
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

    _write_mapping_sheet(summary_sheet, summary_dict)
    _write_dataframe_sheet(workbook.create_sheet("ScenarioGrid"), scenario_df)
    _write_dataframe_sheet(workbook.create_sheet("DailyRevisedTargets"), revised_targets_df)
    _write_dataframe_sheet(workbook.create_sheet("CloseCycle"), close_cycle_df)
    _write_mapping_sheet(workbook.create_sheet("Validation"), validation_result)
    _write_report_text_sheet(workbook.create_sheet("ReportText"), report_text)

    workbook.save(resolved_output_path)
    return resolved_output_path


def _resolve_output_path(output_path: str | Path) -> Path:
    path = Path(output_path)
    if path.suffix.lower() != ".xlsx":
        path = path.with_suffix(".xlsx")

    if path.is_absolute():
        return path

    if path.parts and path.parts[0].lower() == "outputs":
        return _REPO_ROOT / path

    return _REPO_ROOT / "outputs" / path.name


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
