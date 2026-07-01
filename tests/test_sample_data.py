from pathlib import Path

import pandas as pd


EXPECTED_COLUMNS = [
    "date",
    "day_name",
    "business_day_no",
    "is_close_day",
    "close_type",
    "sales_target_daily",
    "recognized_target_daily",
    "sales_actual_cum",
    "recognized_actual_cum",
    "memo",
]


def test_input_sample_loads_with_expected_input_shape() -> None:
    root = Path(__file__).resolve().parents[1]
    sample_path = root / "data" / "sample" / "input_sample.csv"
    df = pd.read_csv(sample_path)

    assert sample_path.is_file()
    assert list(df.columns) == EXPECTED_COLUMNS
    assert len(df) == 18
    assert "sales_actual_daily" not in df.columns
    assert "recognized_actual_daily" not in df.columns
    assert set(df["is_close_day"]) == {"Y", "N"}

    dates = pd.to_datetime(df["date"], format="%Y-%m-%d")
    as_of_date = pd.Timestamp("2026-06-10")

    as_of_actuals = df.loc[
        dates == as_of_date,
        ["sales_actual_cum", "recognized_actual_cum"],
    ]
    assert as_of_actuals.notna().to_numpy().all()

    future_actuals = df.loc[
        dates > as_of_date,
        ["sales_actual_cum", "recognized_actual_cum"],
    ]
    assert future_actuals.isna().to_numpy().all()
