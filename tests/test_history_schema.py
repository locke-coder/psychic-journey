from pathlib import Path

import pytest

from src import history_schema


def test_forecast_history_schema_columns_are_defined_in_required_order() -> None:
    assert history_schema.FORECAST_HISTORY_COLUMNS == (
        "run_id",
        "run_datetime",
        "target_month",
        "as_of_date",
        "metric",
        "forecast_model",
        "strategy_id",
        "strategy_type",
        "forecast_amount",
        "forecast_rate",
        "target_status",
        "target_variance",
        "gap_to_target",
        "surplus_to_target",
        "risk_level",
        "monthly_target",
        "current_actual_cum",
        "current_target_cum",
        "remaining_target",
    )


def test_final_actuals_schema_columns_are_defined_in_required_order() -> None:
    assert history_schema.FINAL_ACTUALS_COLUMNS == (
        "target_month",
        "metric",
        "final_actual",
        "final_achievement_rate",
        "final_status",
        "cancellation_amount",
        "net_actual",
        "memo",
        "updated_at",
    )


def test_missing_required_forecast_history_column_raises_value_error() -> None:
    columns = [
        column
        for column in history_schema.FORECAST_HISTORY_COLUMNS
        if column != "forecast_amount"
    ]

    with pytest.raises(
        ValueError,
        match="Missing required forecast_history columns: forecast_amount",
    ):
        history_schema.validate_required_columns(
            columns,
            history_schema.FORECAST_HISTORY,
        )


def test_missing_required_final_actuals_column_raises_value_error() -> None:
    columns = [
        column
        for column in history_schema.FINAL_ACTUALS_COLUMNS
        if column != "net_actual"
    ]

    with pytest.raises(ValueError, match="Missing required final_actuals columns: net_actual"):
        history_schema.validate_required_columns(columns, history_schema.FINAL_ACTUALS)


def test_history_config_loads_storage_paths_schema_and_duplicate_keys() -> None:
    config = history_schema.load_history_config()

    assert config["storage_paths"] == {
        "forecast_history": "outputs/history/forecast_history.csv",
        "final_actuals": "outputs/history/final_actuals.csv",
    }
    assert tuple(config["schemas"]["forecast_history"]["required_columns"]) == (
        history_schema.FORECAST_HISTORY_COLUMNS
    )
    assert tuple(config["schemas"]["final_actuals"]["required_columns"]) == (
        history_schema.FINAL_ACTUALS_COLUMNS
    )
    assert tuple(config["duplicate_keys"]["forecast_history"]["fallback_key"]) == (
        history_schema.FORECAST_HISTORY_FALLBACK_KEY
    )
    assert tuple(config["duplicate_keys"]["final_actuals"]["upsert_key"]) == (
        history_schema.FINAL_ACTUALS_UPSERT_KEY
    )


def test_storage_paths_are_resolved_from_config(tmp_path: Path) -> None:
    paths = history_schema.get_storage_paths(repo_root=tmp_path)

    assert paths[history_schema.FORECAST_HISTORY] == (
        tmp_path / "outputs" / "history" / "forecast_history.csv"
    )
    assert paths[history_schema.FINAL_ACTUALS] == (
        tmp_path / "outputs" / "history" / "final_actuals.csv"
    )


def test_forecast_history_duplicate_key_uses_run_id_when_available() -> None:
    record = {
        "run_id": "RUN-001",
        "target_month": "2026-06",
        "as_of_date": "2026-06-10",
        "metric": "sales",
        "forecast_model": "F1_CUMULATIVE_RATE",
        "strategy_id": "P1_ALL_REMAINING",
        "run_datetime": "2026-06-10T09:00:00",
    }

    assert history_schema.select_forecast_history_key_columns(record) == ("run_id",)
    assert history_schema.build_duplicate_key(
        history_schema.FORECAST_HISTORY,
        record,
    ) == ("RUN-001",)


def test_forecast_history_duplicate_key_falls_back_when_run_id_is_blank() -> None:
    record = {
        "run_id": "",
        "target_month": "2026-06",
        "as_of_date": "2026-06-10",
        "metric": "sales",
        "forecast_model": "F1_CUMULATIVE_RATE",
        "strategy_id": "P1_ALL_REMAINING",
        "run_datetime": "2026-06-10T09:00:00",
    }

    assert history_schema.select_forecast_history_key_columns(record) == (
        history_schema.FORECAST_HISTORY_FALLBACK_KEY
    )
    assert history_schema.build_duplicate_key(
        history_schema.FORECAST_HISTORY,
        record,
    ) == (
        "2026-06",
        "2026-06-10",
        "sales",
        "F1_CUMULATIVE_RATE",
        "P1_ALL_REMAINING",
        "2026-06-10T09:00:00",
    )


def test_final_actuals_duplicate_key_supports_metric_month_upsert() -> None:
    record = {
        "target_month": "2026-06",
        "metric": "recognized",
        "final_actual": 120.0,
    }

    assert history_schema.get_duplicate_key_policy(history_schema.FINAL_ACTUALS) == {
        "upsert": True,
        "upsert_key": ("target_month", "metric"),
    }
    assert history_schema.build_duplicate_key(history_schema.FINAL_ACTUALS, record) == (
        "2026-06",
        "recognized",
    )


def test_missing_duplicate_key_value_raises_value_error() -> None:
    record = {
        "run_id": "",
        "target_month": "2026-06",
        "as_of_date": "2026-06-10",
        "metric": "sales",
        "forecast_model": "F1_CUMULATIVE_RATE",
        "strategy_id": "P1_ALL_REMAINING",
    }

    with pytest.raises(
        ValueError,
        match="Missing required forecast_history key values: run_datetime",
    ):
        history_schema.build_duplicate_key(history_schema.FORECAST_HISTORY, record)
