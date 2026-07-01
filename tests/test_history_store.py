from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

from src import history_schema
from src.history_store import (
    append_forecast_history,
    build_forecast_history_rows,
    ensure_history_dir,
    load_forecast_history,
)


def _scenario_output_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "forecast_model": [
                "F1_CUMULATIVE_RATE",
                "F2_LAST_TWO_CLOSES",
            ],
            "provision_strategy": [
                "P1_ALL_REMAINING",
                "P2_CLOSE_DAY_FOCUSED",
            ],
            "strategy_type": ["PROVISION", "PROVISION"],
            "forecast_amount": [95.0, 98.0],
            "forecast_rate": [0.95, 0.98],
            "target_status": ["UNDER_TARGET", "UNDER_TARGET"],
            "target_variance": [-5.0, -2.0],
            "gap_to_target": [5.0, 2.0],
            "surplus_to_target": [0.0, 0.0],
            "risk_level": ["Yellow", "Yellow"],
            "monthly_target": [100.0, 100.0],
            "current_actual_cum": [60.0, 60.0],
            "current_target_cum": [70.0, 70.0],
            "remaining_target": [30.0, 30.0],
        }
    )


def _run_context(run_id: str | None = "RUN-001") -> dict[str, object]:
    return {
        "run_datetime": datetime(2026, 6, 7, 9, 30),
        "target_month": "2026-06",
        "as_of_date": "2026-06-07",
        "metric": "sales",
        "run_id": run_id,
    }


def test_history_file_is_created(tmp_path: Path) -> None:
    path = tmp_path / "forecast_history.csv"
    rows = build_forecast_history_rows(_scenario_output_df(), _run_context())

    result = append_forecast_history(rows, path)

    assert path.is_file()
    assert list(result.columns) == list(history_schema.FORECAST_HISTORY_COLUMNS)
    assert result.shape[0] == 2


def test_append_saves_additional_run(tmp_path: Path) -> None:
    path = tmp_path / "forecast_history.csv"
    first_rows = build_forecast_history_rows(_scenario_output_df(), _run_context("RUN-001"))
    second_rows = build_forecast_history_rows(_scenario_output_df(), _run_context("RUN-002"))

    append_forecast_history(first_rows, path)
    result = append_forecast_history(second_rows, path)

    assert result.shape[0] == 4
    assert set(result["run_id"]) == {"RUN-001", "RUN-002"}


def test_load_forecast_history_reads_saved_rows(tmp_path: Path) -> None:
    path = tmp_path / "forecast_history.csv"
    rows = build_forecast_history_rows(_scenario_output_df(), _run_context())

    append_forecast_history(rows, path)
    loaded = load_forecast_history(path)

    assert loaded["forecast_model"].tolist() == [
        "F1_CUMULATIVE_RATE",
        "F2_LAST_TWO_CLOSES",
    ]
    assert loaded["strategy_id"].tolist() == [
        "P1_ALL_REMAINING",
        "P2_CLOSE_DAY_FOCUSED",
    ]


def test_duplicate_run_id_is_blocked(tmp_path: Path) -> None:
    path = tmp_path / "forecast_history.csv"
    rows = build_forecast_history_rows(_scenario_output_df(), _run_context("RUN-001"))

    append_forecast_history(rows, path)

    with pytest.raises(ValueError, match="run_id=RUN-001"):
        append_forecast_history(rows, path)


def test_missing_required_scenario_column_raises_error() -> None:
    scenario_df = _scenario_output_df().drop(columns=["forecast_amount"])

    with pytest.raises(
        ValueError,
        match="Missing required scenario columns: forecast_amount",
    ):
        build_forecast_history_rows(scenario_df, _run_context())


def test_append_missing_required_history_column_raises_error(tmp_path: Path) -> None:
    path = tmp_path / "forecast_history.csv"
    rows = build_forecast_history_rows(_scenario_output_df(), _run_context()).drop(
        columns=["forecast_amount"]
    )

    with pytest.raises(
        ValueError,
        match="Missing required forecast_history columns: forecast_amount",
    ):
        append_forecast_history(rows, path)


def test_build_rows_does_not_mutate_source_scenario_df() -> None:
    scenario_df = _scenario_output_df()
    original = scenario_df.copy(deep=True)

    build_forecast_history_rows(scenario_df, _run_context(None))

    pd.testing.assert_frame_equal(scenario_df, original)


def test_ensure_history_dir_returns_requested_path(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "forecast_history.csv"

    result = ensure_history_dir(path)

    assert result == path
    assert path.parent.is_dir()
