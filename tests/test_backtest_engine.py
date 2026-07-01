from __future__ import annotations

import math

import pandas as pd
import pytest

from src.backtest_engine import (
    build_backtest_dataset,
    get_best_model,
    summarize_by_forecast_model,
    summarize_by_strategy,
)


def _forecast_history() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "run_id": ["RUN-001", "RUN-001", "RUN-001", "RUN-002"],
            "run_datetime": [
                "2026-06-10T09:00:00",
                "2026-06-10T09:00:00",
                "2026-06-10T09:00:00",
                "2026-06-11T09:00:00",
            ],
            "target_month": ["2026-06", "2026-06", "2026-06", "2026-07"],
            "as_of_date": [
                "2026-06-10",
                "2026-06-10",
                "2026-06-10",
                "2026-07-10",
            ],
            "metric": ["sales", "sales", "sales", "sales"],
            "forecast_model": [
                "F1_CUMULATIVE_RATE",
                "F2_LAST_TWO_CLOSES",
                "F3_DAY_CLOSE_WEIGHTED",
                "F1_CUMULATIVE_RATE",
            ],
            "strategy_id": [
                "P1_ALL_REMAINING",
                "P2_CLOSE_DAY_FOCUSED",
                "P3_NON_CLOSE_DAY_FOCUSED",
                "P1_ALL_REMAINING",
            ],
            "strategy_type": ["PROVISION", "PROVISION", "PROVISION", "PROVISION"],
            "forecast_amount": [110.0, 96.0, 100.0, 80.0],
            "forecast_rate": [1.1, 0.96, 1.0, 0.8],
            "target_status": [
                "OVER_TARGET",
                "UNDER_TARGET",
                "ON_TARGET",
                "UNDER_TARGET",
            ],
            "target_variance": [10.0, -4.0, 0.0, -20.0],
            "gap_to_target": [0.0, 4.0, 0.0, 20.0],
            "surplus_to_target": [10.0, 0.0, 0.0, 0.0],
            "risk_level": ["Green", "Yellow", "Green", "Red"],
            "monthly_target": [100.0, 100.0, 100.0, 100.0],
            "current_actual_cum": [60.0, 60.0, 60.0, 50.0],
            "current_target_cum": [70.0, 70.0, 70.0, 70.0],
            "remaining_target": [30.0, 30.0, 30.0, 30.0],
        }
    )


def _final_actuals(final_actual: float = 100.0) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "target_month": ["2026-06"],
            "metric": ["sales"],
            "final_actual": [final_actual],
            "final_achievement_rate": [1.0],
            "final_status": ["ON_TARGET"],
            "cancellation_amount": [""],
            "net_actual": [""],
            "memo": [""],
            "updated_at": ["2026-07-01T09:00:00"],
        }
    )


def test_build_backtest_dataset_joins_forecast_history_to_final_actuals() -> None:
    result = build_backtest_dataset(_forecast_history(), _final_actuals())

    assert result.shape[0] == 3
    assert set(result["target_month"]) == {"2026-06"}
    assert result["final_actual"].tolist() == [100.0, 100.0, 100.0]


def test_row_level_error_columns_are_calculated() -> None:
    result = build_backtest_dataset(_forecast_history(), _final_actuals())

    row = result.loc[result["forecast_model"] == "F1_CUMULATIVE_RATE"].iloc[0]

    assert row["forecast_error"] == pytest.approx(10.0)
    assert row["abs_error"] == pytest.approx(10.0)
    assert row["error_rate"] == pytest.approx(0.1)
    assert row["signed_error_rate"] == pytest.approx(0.1)
    assert row["over_forecast_flag"] is True
    assert row["under_forecast_flag"] is False


def test_zero_final_actual_keeps_error_rates_safe() -> None:
    result = build_backtest_dataset(_forecast_history(), _final_actuals(0.0))

    assert result["forecast_error"].tolist() == [110.0, 96.0, 100.0]
    assert result["abs_error"].tolist() == [110.0, 96.0, 100.0]
    assert result["error_rate"].isna().all()
    assert result["signed_error_rate"].isna().all()
    assert not math.isinf(result["error_rate"].fillna(0.0).sum())


def test_summarize_by_forecast_model_builds_model_summary() -> None:
    backtest = build_backtest_dataset(_forecast_history(), _final_actuals())

    summary = summarize_by_forecast_model(backtest)

    f1 = summary.loc[summary["forecast_model"] == "F1_CUMULATIVE_RATE"].iloc[0]
    f3 = summary.loc[summary["forecast_model"] == "F3_DAY_CLOSE_WEIGHTED"].iloc[0]
    assert f1["sample_count"] == 1
    assert f1["mean_abs_error"] == pytest.approx(10.0)
    assert f1["mean_error_rate"] == pytest.approx(0.1)
    assert f1["median_error_rate"] == pytest.approx(0.1)
    assert f1["bias"] == pytest.approx(10.0)
    assert f3["best_model_by_error_rate"] is True


def test_get_best_model_selects_lowest_mean_error_rate() -> None:
    backtest = build_backtest_dataset(_forecast_history(), _final_actuals())
    summary = summarize_by_forecast_model(backtest)

    assert get_best_model(summary) == "F3_DAY_CLOSE_WEIGHTED"


def test_summarize_by_strategy_builds_strategy_summary() -> None:
    backtest = build_backtest_dataset(_forecast_history(), _final_actuals())

    summary = summarize_by_strategy(backtest)

    assert set(summary["strategy_id"]) == {
        "P1_ALL_REMAINING",
        "P2_CLOSE_DAY_FOCUSED",
        "P3_NON_CLOSE_DAY_FOCUSED",
    }
    p2 = summary.loc[summary["strategy_id"] == "P2_CLOSE_DAY_FOCUSED"].iloc[0]
    assert p2["sample_count"] == 1
    assert p2["mean_abs_error"] == pytest.approx(4.0)
    assert p2["bias"] == pytest.approx(-4.0)


def test_empty_dataframes_return_empty_outputs() -> None:
    backtest = build_backtest_dataset(pd.DataFrame(), pd.DataFrame())
    model_summary = summarize_by_forecast_model(backtest)
    strategy_summary = summarize_by_strategy(backtest)

    assert backtest.empty
    assert model_summary.empty
    assert strategy_summary.empty
    assert get_best_model(model_summary) is None
