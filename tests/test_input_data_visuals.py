from __future__ import annotations

import pandas as pd

import app


def _sample_input() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2026-07-01", "2026-07-02", "2026-07-03"],
            "day_name": ["수", "목", "금"],
            "business_day_no": [1, 2, 3],
            "is_close_day": [False, True, False],
            "close_type": ["일반", "1차", "일반"],
            "sales_target_daily": [10.0, 20.0, 15.0],
            "recognized_target_daily": [9.0, 18.0, 14.0],
            "sales_actual_cum": [8.0, None, 30.0],
            "recognized_actual_cum": [7.0, None, 27.0],
            "memo": ["", "마감", ""],
        }
    )


def test_input_completeness_frame_counts_missing_cells() -> None:
    result = app._build_input_completeness_frame(_sample_input())

    sales_actual = result.loc[result["field"] == "sales_actual_cum"].iloc[0]
    memo = result.loc[result["field"] == "memo"].iloc[0]

    assert sales_actual["filled_count"] == 2
    assert sales_actual["missing_count"] == 1
    assert round(float(sales_actual["completion_pct"]), 1) == 66.7
    assert memo["missing_count"] == 0
    assert memo["excluded_count"] == 2


def test_input_coverage_frame_locates_row_and_field_gap() -> None:
    result = app._build_input_coverage_frame(_sample_input())

    gap = result.loc[
        (result["row_label"] == "2일")
        & (result["field_label"] == app._display_column_label("sales_actual_cum"))
    ]

    assert len(result) == len(_sample_input()) * len(app.INPUT_TEMPLATE_HEADERS)
    assert gap["input_state"].tolist() == ["확인 필요"]


