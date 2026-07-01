import pandas as pd
import pytest

from src.actual_engine import add_actual_daily_columns


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(
                [
                    "2026-06-01",
                    "2026-06-02",
                    "2026-06-03",
                    "2026-06-04",
                ]
            ),
            "sales_target_daily": [10.0, 20.0, 30.0, 40.0],
            "recognized_target_daily": [1.0, 2.0, 3.0, 4.0],
            "sales_actual_cum": [5.0, 12.0, 15.0, pd.NA],
            "recognized_actual_cum": [2.0, 5.0, pd.NA, pd.NA],
        }
    )


def test_actual_daily_is_calculated_from_cumulative_difference() -> None:
    result = add_actual_daily_columns(_df(), "sales", "2026-06-03", {})

    assert result.loc[:2, "sales_actual_daily"].tolist() == pytest.approx(
        [5.0, 7.0, 3.0]
    )


def test_first_input_daily_equals_cumulative_value() -> None:
    result = add_actual_daily_columns(_df(), "sales", "2026-06-03", {})

    assert result.loc[0, "sales_actual_daily"] == pytest.approx(5.0)


def test_missing_actual_cum_through_as_of_date_raises_value_error() -> None:
    df = _df()
    df.loc[0, "sales_actual_cum"] = pd.NA

    with pytest.raises(ValueError, match="actual_cum must be populated"):
        add_actual_daily_columns(df, "sales", "2026-06-03", {})


def test_future_blank_actual_cum_values_are_allowed() -> None:
    result = add_actual_daily_columns(_df(), "sales", "2026-06-02", {})

    assert pd.isna(result.loc[2, "sales_actual_daily"])
    assert pd.isna(result.loc[3, "sales_actual_daily"])


def test_future_actual_daily_is_nan_even_when_future_cum_is_populated() -> None:
    df = _df()
    df.loc[2, "sales_actual_cum"] = 99.0

    result = add_actual_daily_columns(df, "sales", "2026-06-02", {})

    assert result.loc[:1, "sales_actual_daily"].tolist() == pytest.approx([5.0, 7.0])
    assert pd.isna(result.loc[2, "sales_actual_daily"])


def test_negative_actual_flag_is_true_when_cumulative_decreases() -> None:
    df = _df()
    df.loc[1, "sales_actual_cum"] = 3.0

    result = add_actual_daily_columns(df, "sales", "2026-06-03", {})

    assert result.loc[1, "sales_actual_daily"] == pytest.approx(-2.0)
    assert bool(result.loc[1, "negative_actual_flag"]) is True


def test_target_cum_is_calculated_from_target_daily_cumsum() -> None:
    result = add_actual_daily_columns(_df(), "recognized", "2026-06-02", {})

    assert result["recognized_target_cum"].tolist() == pytest.approx(
        [1.0, 3.0, 6.0, 10.0]
    )
    assert result.loc[:1, "recognized_actual_daily"].tolist() == pytest.approx(
        [2.0, 3.0]
    )


def test_status_columns_are_created_from_as_of_date() -> None:
    result = add_actual_daily_columns(_df(), "sales", "2026-06-02", {})

    assert result["is_past_or_current"].tolist() == [True, True, False, False]
    assert result["is_remaining"].tolist() == [False, False, True, True]


def test_input_dataframe_is_not_mutated() -> None:
    df = _df()

    result = add_actual_daily_columns(df, "sales", "2026-06-03", {})

    assert result is not df
    assert "sales_actual_daily" not in df.columns
    assert "sales_target_cum" not in df.columns
