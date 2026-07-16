from __future__ import annotations

import ast
from pathlib import Path


APP_PATH = Path("app.py")
UI_FORMATTERS_PATH = Path("src/ui_formatters.py")
APP_SOURCE = APP_PATH.read_text(encoding="utf-8")
UI_FORMATTERS_SOURCE = UI_FORMATTERS_PATH.read_text(encoding="utf-8")


def _top_level_function_names(source: str) -> set[str]:
    module = ast.parse(source)
    return {node.name for node in module.body if isinstance(node, ast.FunctionDef)}


def test_ui_formatters_module_exists() -> None:
    assert UI_FORMATTERS_PATH.exists()


def test_app_imports_ui_formatters() -> None:
    assert "from src.ui_formatters import" in APP_SOURCE
    for name in (
        "_as_float",
        "_is_missing",
        "chart_value_format",
        "format_amount",
        "format_date as _format_date",
        "format_optional_amount as _format_optional_amount",
        "format_rate",
        "format_signed_amount as _format_signed_amount",
        "operation_mode_label as _operation_mode_label",
        "target_status_arrival_label as _target_status_arrival_label",
    ):
        assert name in APP_SOURCE


def test_moved_formatter_definitions_removed_from_app() -> None:
    app_functions = _top_level_function_names(APP_SOURCE)
    moved_function_names = {
        "format_amount",
        "format_rate",
        "_format_signed_amount",
        "_format_optional_amount",
        "_format_date",
        "_target_status_arrival_label",
        "_operation_mode_label",
        "_as_float",
        "_is_missing",
        "chart_value_format",
    }

    assert app_functions.isdisjoint(moved_function_names)


def test_ui_formatters_does_not_import_streamlit_or_formula_modules() -> None:
    forbidden_modules = (
        "streamlit",
        "altair",
        "forecast_models",
        "provision_models",
        "overachievement_models",
        "scenario_runner",
        "report_builder",
        "excel_exporter",
        "history_store",
        "final_actual_store",
        "backtest_engine",
        "model_weight_engine",
        "confidence_band",
        "insight_engine",
    )

    for module in forbidden_modules:
        assert f"import {module}" not in UI_FORMATTERS_SOURCE
        assert f"from src.{module}" not in UI_FORMATTERS_SOURCE
        assert f"from .{module}" not in UI_FORMATTERS_SOURCE


def test_ui_formatters_no_file_or_output_side_effect_terms() -> None:
    forbidden_terms = (
        "open(",
        "Path(",
        "OUTPUT_DIR",
        "outputs/",
        "append_forecast_history",
        "export_daily_report",
        "st.session_state",
    )

    for term in forbidden_terms:
        assert term not in UI_FORMATTERS_SOURCE


def test_no_forbidden_close_day_inference_terms_in_formatter_sources() -> None:
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

    for source_name, source in {
        "app.py": APP_SOURCE,
        "src/ui_formatters.py": UI_FORMATTERS_SOURCE,
    }.items():
        for term in forbidden_terms:
            assert term not in source, f"{source_name} contains {term}"


def test_do_not_move_dataframe_formatters_yet() -> None:
    out_of_scope_terms = (
        "format_display_df",
        "format_daily_forecast_detail_df",
        "format_remaining_operation_direction_df",
        "historical_forecast_comparison",
        "historical_stage",
        "historical_monthly",
    )

    for term in out_of_scope_terms:
        assert term not in UI_FORMATTERS_SOURCE


def test_safe_divide_remains_in_app() -> None:
    assert "safe_divide" in _top_level_function_names(APP_SOURCE)
