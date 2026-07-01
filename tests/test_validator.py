from pathlib import Path

import pandas as pd
import pytest

from src.loader import load_input
from src.validator import validate_input


def _sample_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "sample" / "input_sample.csv"


def _sample_df() -> pd.DataFrame:
    return load_input(_sample_path())


def _config() -> dict[str, bool]:
    return {"allow_negative_daily_actual": True}


def _has_message(messages: list[str], expected: str) -> bool:
    return any(expected in message for message in messages)


def test_normal_sample_has_no_errors_and_calculates_core_values() -> None:
    df = _sample_df()
    as_of_date = pd.Timestamp("2026-06-10")

    result = validate_input(df, as_of_date, "sales", _config())

    assert result["errors"] == []
    assert result["monthly_target"] == pytest.approx(df["sales_target_daily"].sum())
    assert result["current_target_cum"] == pytest.approx(
        df.loc[df["date"] <= as_of_date, "sales_target_daily"].sum()
    )
    assert result["current_actual_cum"] == pytest.approx(
        df.loc[df["date"] == as_of_date, "sales_actual_cum"].iloc[0]
    )
    assert result["remaining_target"] == pytest.approx(
        df.loc[df["date"] > as_of_date, "sales_target_daily"].sum()
    )


def test_missing_as_of_date_returns_error() -> None:
    df = _sample_df()

    result = validate_input(df, pd.Timestamp("2026-06-03"), "sales", _config())

    assert _has_message(result["errors"], "as_of_date")


def test_missing_actual_cum_through_as_of_date_returns_error() -> None:
    df = _sample_df()
    df.loc[df["date"] == pd.Timestamp("2026-06-09"), "sales_actual_cum"] = pd.NA

    result = validate_input(df, pd.Timestamp("2026-06-10"), "sales", _config())

    assert _has_message(result["errors"], "actual_cum must be populated")


def test_future_actual_cum_returns_warning() -> None:
    df = _sample_df()
    df.loc[df["date"] == pd.Timestamp("2026-06-11"), "sales_actual_cum"] = 72.0

    result = validate_input(df, pd.Timestamp("2026-06-10"), "sales", _config())

    assert _has_message(result["warnings"], "actual_cum after as_of_date")


def test_no_close_day_returns_error() -> None:
    df = _sample_df()
    df["is_close_day"] = False

    result = validate_input(df, pd.Timestamp("2026-06-10"), "sales", _config())

    assert _has_message(result["errors"], "is_close_day=True")


def test_negative_target_daily_returns_error() -> None:
    df = _sample_df()
    df.loc[0, "sales_target_daily"] = -1.0

    result = validate_input(df, pd.Timestamp("2026-06-10"), "sales", _config())

    assert _has_message(result["errors"], "target_daily must not be negative")


def test_fewer_than_two_completed_close_days_returns_warning() -> None:
    df = _sample_df()

    result = validate_input(df, pd.Timestamp("2026-06-02"), "sales", _config())

    assert result["errors"] == []
    assert _has_message(result["warnings"], "F2 fallback warning")
