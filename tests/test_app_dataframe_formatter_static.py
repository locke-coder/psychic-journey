from __future__ import annotations

import ast
from pathlib import Path


APP_PATH = Path("app.py")
FORMATTERS_PATH = Path("src/ui_dataframe_formatters.py")
APP_SOURCE = APP_PATH.read_text(encoding="utf-8")
FORMATTERS_SOURCE = FORMATTERS_PATH.read_text(encoding="utf-8")


def _top_level_function_names(source: str) -> set[str]:
    module = ast.parse(source)
    return {node.name for node in module.body if isinstance(node, ast.FunctionDef)}


def test_app_imports_dataframe_formatters_and_shared_contract() -> None:
    assert "from src.ui_dataframe_formatters import" in APP_SOURCE
    for name in (
        "REMAINING_OPERATION_DIRECTION_COLUMNS",
        "display_column_label",
        "format_daily_forecast_detail_df as _format_daily_forecast_detail_df",
        "format_display_df",
        "format_remaining_operation_direction_df as _format_remaining_operation_direction_df",
        "localize_display_value",
    ):
        assert name in APP_SOURCE


def test_moved_dataframe_formatter_definitions_are_removed_from_app() -> None:
    assert _top_level_function_names(APP_SOURCE).isdisjoint(
        {
            "_display_column_label",
            "_format_daily_forecast_detail_df",
            "_format_display_df",
            "_format_named_value",
            "_format_remaining_operation_direction_df",
            "_localize_display_value",
        }
    )


def test_app_binds_generic_formatters_without_moving_app_constants() -> None:
    for binding in (
        "_format_display_df = partial(",
        "_display_column_label = partial(",
        "_localize_display_value = partial(",
    ):
        assert binding in APP_SOURCE
    for constant in (
        "AMOUNT_COLUMNS =",
        "RATE_COLUMNS =",
        "TECHNICAL_CODE_COLUMNS =",
        "DISPLAY_COLUMN_LABELS =",
        "DISPLAY_VALUE_LABELS =",
    ):
        assert constant in APP_SOURCE
        assert constant not in FORMATTERS_SOURCE


def test_dataframe_formatter_module_stays_display_only() -> None:
    forbidden_modules = (
        "streamlit",
        "altair",
        "forecast_models",
        "provision_models",
        "overachievement_models",
        "scenario_runner",
        "excel_exporter",
        "history_store",
        "backtest_engine",
    )
    forbidden_terms = (
        "st.session_state",
        "open(",
        "Path(",
        "OUTPUT_DIR",
        ".sum(",
        ".groupby(",
        ".cumsum(",
        ".diff(",
    )

    for module in forbidden_modules:
        assert f"import {module}" not in FORMATTERS_SOURCE
        assert f"from src.{module}" not in FORMATTERS_SOURCE
        assert f"from .{module}" not in FORMATTERS_SOURCE
    for term in forbidden_terms:
        assert term not in FORMATTERS_SOURCE


def test_dataframe_formatter_module_has_no_close_day_inference() -> None:
    forbidden_terms = (
        "weekday",
        "WEEKDAY",
        "dt.weekday",
        "date.weekday",
        "next_monday",
        "next_thursday",
        "day_name ==",
        "day_name in",
        "월요일",
        "목요일",
    )

    for term in forbidden_terms:
        assert term not in FORMATTERS_SOURCE


def test_historical_formatters_are_not_duplicated_in_app_or_generic_module() -> None:
    app_functions = _top_level_function_names(APP_SOURCE)
    history_formatters = {
        "_format_historical_forecast_comparison_df",
        "_format_historical_stage_df",
        "_format_historical_monthly_summary_df",
    }

    assert app_functions.isdisjoint(history_formatters)
    for name in history_formatters:
        assert name not in FORMATTERS_SOURCE
