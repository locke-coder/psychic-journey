from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.loader import load_input
from src.next_close import calculate_next_close_required


def _sample_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "sample" / "input_sample.csv"


def _sample_df() -> pd.DataFrame:
    return load_input(_sample_path())


def test_next_close_date_after_2026_06_10_uses_input_close_day_only() -> None:
    result = calculate_next_close_required(_sample_df(), "2026-06-10", "sales", {})

    assert result["as_of_date"] == date(2026, 6, 10)
    assert result["next_close_date"] == date(2026, 6, 11)
    assert result["warnings"] == []


def test_next_close_target_cum_is_calculated_from_daily_targets() -> None:
    result = calculate_next_close_required(_sample_df(), "2026-06-10", "sales", {})

    assert result["current_actual_cum"] == pytest.approx(70.5)
    assert result["current_target_cum"] == pytest.approx(75.7)
    assert result["next_close_target_cum"] == pytest.approx(87.2)
    assert result["required_to_recover_next_close_cum"] == pytest.approx(16.7)


def test_current_cycle_required_amount_uses_actual_daily_difference() -> None:
    result = calculate_next_close_required(_sample_df(), "2026-06-10", "sales", {})

    assert result["current_cycle_target"] == pytest.approx(16.7)
    assert result["current_cycle_actual_to_date"] == pytest.approx(4.4)
    assert result["required_to_hit_current_cycle"] == pytest.approx(12.3)


def test_required_to_recover_next_close_cum_never_becomes_negative() -> None:
    df = _sample_df()
    df.loc[df["date"] == pd.Timestamp("2026-06-10"), "sales_actual_cum"] = 100.0

    result = calculate_next_close_required(df, "2026-06-10", "sales", {})

    assert result["next_close_target_cum"] == pytest.approx(87.2)
    assert result["required_to_recover_next_close_cum"] == pytest.approx(0.0)


def test_required_to_hit_current_cycle_never_becomes_negative() -> None:
    df = _sample_df()
    df.loc[df["date"] == pd.Timestamp("2026-06-10"), "sales_actual_cum"] = 100.0

    result = calculate_next_close_required(df, "2026-06-10", "sales", {})

    assert result["current_cycle_target"] == pytest.approx(16.7)
    assert result["current_cycle_actual_to_date"] > result["current_cycle_target"]
    assert result["required_to_hit_current_cycle"] == pytest.approx(0.0)


def test_no_next_close_day_returns_warning() -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-06-01", "2026-06-02"]),
            "is_close_day": [False, True],
            "sales_target_daily": [10.0, 20.0],
            "recognized_target_daily": [1.0, 1.0],
            "sales_actual_cum": [5.0, 25.0],
            "recognized_actual_cum": [0.5, 1.5],
        }
    )

    result = calculate_next_close_required(df, "2026-06-02", "sales", {})

    assert result["next_close_date"] is None
    assert result["next_close_target_cum"] is None
    assert result["required_to_recover_next_close_cum"] is None
    assert result["current_cycle_target"] is None
    assert result["current_cycle_actual_to_date"] is None
    assert result["required_to_hit_current_cycle"] is None
    assert result["warnings"] == ["No next close day is present after as_of_date."]
