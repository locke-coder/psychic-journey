from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.close_cycle_engine import (
    assign_close_cycle_ids,
    build_close_cycle_summary,
    get_completed_close_dates,
    get_last_two_completed_close_dates,
    get_next_close_date,
)
from src.loader import load_input


def _sample_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "sample" / "input_sample.csv"


def _sample_df() -> pd.DataFrame:
    return load_input(_sample_path())


def test_completed_close_dates_are_based_on_is_close_day_only() -> None:
    df = _sample_df()

    completed = get_completed_close_dates(df, "2026-06-10")

    assert completed == [
        date(2026, 6, 1),
        date(2026, 6, 4),
        date(2026, 6, 8),
    ]


def test_last_two_completed_close_dates_are_returned_in_cycle_order() -> None:
    result = get_last_two_completed_close_dates(_sample_df(), "2026-06-10")

    assert result == [date(2026, 6, 4), date(2026, 6, 8)]


def test_next_close_date_uses_next_input_close_row_only() -> None:
    result = get_next_close_date(_sample_df(), "2026-06-10")

    assert result == date(2026, 6, 11)


def test_assign_close_cycle_ids_keeps_rows_after_previous_close_together() -> None:
    result = assign_close_cycle_ids(_sample_df())

    cycle_four_dates = result.loc[result["cycle_id"] == 4, "date"].dt.date.tolist()

    assert cycle_four_dates == [
        date(2026, 6, 9),
        date(2026, 6, 10),
        date(2026, 6, 11),
    ]
    assert len(result) == len(_sample_df())


def test_build_close_cycle_summary_includes_next_close_cycle_rows() -> None:
    summary = build_close_cycle_summary(_sample_df(), "sales", "2026-06-10")

    cycle = summary.loc[summary["cycle_end_date"] == date(2026, 6, 11)].iloc[0]

    assert cycle["cycle_start_date"] == date(2026, 6, 9)
    assert cycle["cycle_end_date"] == date(2026, 6, 11)
    assert cycle["is_completed"] == False
    assert cycle["target_sum"] == pytest.approx(16.7)
    assert cycle["actual_sum"] == pytest.approx(4.4)
    assert cycle["achievement_rate"] == pytest.approx(26.3)
    assert cycle["row_count"] == 3


def test_summary_marks_completed_cycles_through_as_of_date() -> None:
    summary = build_close_cycle_summary(_sample_df(), "sales", "2026-06-10")

    completed = summary.loc[summary["is_completed"], "cycle_end_date"].tolist()

    assert completed == [
        date(2026, 6, 1),
        date(2026, 6, 4),
        date(2026, 6, 8),
    ]


def test_day_name_does_not_create_or_remove_close_days() -> None:
    df = pd.DataFrame(
        {
            "date": pd.to_datetime(
                ["2026-06-01", "2026-06-02", "2026-06-03", "2026-06-04"]
            ),
            "day_name": ["Mon", "Thu", "Thu", "Mon"],
            "business_day_no": [1, 2, 3, 4],
            "is_close_day": [False, False, True, False],
            "close_type": ["", "", "manual_close", ""],
            "sales_target_daily": [1.0, 1.0, 1.0, 1.0],
            "recognized_target_daily": [1.0, 1.0, 1.0, 1.0],
            "sales_actual_cum": [1.0, 2.0, 3.0, 4.0],
            "recognized_actual_cum": [1.0, 2.0, 3.0, 4.0],
            "memo": ["", "", "", ""],
        }
    )

    assert get_completed_close_dates(df, "2026-06-04") == [date(2026, 6, 3)]
    assert get_next_close_date(df, "2026-06-03") is None


def test_build_close_cycle_summary_does_not_mutate_input_dataframe() -> None:
    df = _sample_df()

    result = build_close_cycle_summary(df, "sales", "2026-06-10")

    assert "cycle_id" not in df.columns
    assert "sales_actual_daily" not in df.columns
    assert list(result.columns) == [
        "cycle_id",
        "cycle_start_date",
        "cycle_end_date",
        "is_completed",
        "target_sum",
        "actual_sum",
        "achievement_rate",
        "row_count",
        "close_type",
    ]
