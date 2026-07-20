from pathlib import Path

import pandas as pd
import pytest

from src.loader import load_input, normalize_business_day_no
from src.schema import REQUIRED_INPUT_COLUMNS


def _sample_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "sample" / "input_sample.csv"


def _historical_sample_path() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "data"
        / "sample"
        / "historical_input_sample.csv"
    )


def test_input_sample_loads_successfully() -> None:
    df = load_input(_sample_path())

    assert list(df.columns) == list(REQUIRED_INPUT_COLUMNS)
    assert len(df) == 20
    assert pd.api.types.is_datetime64_any_dtype(df["date"])
    assert pd.api.types.is_integer_dtype(df["business_day_no"])
    assert pd.api.types.is_bool_dtype(df["is_close_day"])
    assert pd.api.types.is_float_dtype(df["sales_target_daily"])
    assert pd.api.types.is_float_dtype(df["recognized_target_daily"])
    assert pd.api.types.is_float_dtype(df["sales_actual_cum"])
    assert pd.api.types.is_float_dtype(df["recognized_actual_cum"])
    assert df["business_day_no"].tolist() == sorted(df["business_day_no"].tolist())


def test_is_close_day_is_standardized_to_boolean(tmp_path: Path) -> None:
    df = pd.read_csv(_sample_path())
    values = [
        "Y",
        "y",
        "YES",
        "yes",
        "TRUE",
        "True",
        "true",
        1,
        "N",
        "n",
        "NO",
        "no",
        "FALSE",
        "False",
        "false",
        0,
        "",
    ]
    df = df.head(len(values)).copy()
    df["is_close_day"] = values
    input_path = tmp_path / "boolean_variants.csv"
    df.to_csv(input_path, index=False)

    loaded = load_input(input_path)

    assert pd.api.types.is_bool_dtype(loaded["is_close_day"])
    assert loaded["is_close_day"].tolist() == [
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    ]


def test_load_input_sorts_by_business_day_no_by_default(tmp_path: Path) -> None:
    df = pd.read_csv(_sample_path()).sort_values("business_day_no", ascending=False)
    input_path = tmp_path / "reversed_input.csv"
    df.to_csv(input_path, index=False)

    loaded = load_input(input_path)

    assert loaded["business_day_no"].tolist() == sorted(df["business_day_no"].tolist())


def test_cp949_csv_file_can_be_loaded_without_korean_text_breaking(tmp_path: Path) -> None:
    df = pd.read_csv(_sample_path())
    input_path = tmp_path / "cp949_input.csv"
    df.to_csv(input_path, index=False, encoding="cp949")

    loaded = load_input(input_path)

    second_business_day = loaded.loc[loaded["business_day_no"] == 2].iloc[0]
    assert second_business_day["day_name"] == "목"
    assert second_business_day["close_type"] == "일반"
    assert second_business_day["sales_actual_cum"] == pytest.approx(51.0)


def test_utf8_bom_csv_file_can_be_loaded(tmp_path: Path) -> None:
    df = pd.read_csv(_sample_path())
    input_path = tmp_path / "utf8_bom_input.csv"
    df.to_csv(input_path, index=False, encoding="utf-8-sig")

    loaded = load_input(input_path)

    assert list(loaded.columns) == list(REQUIRED_INPUT_COLUMNS)
    assert loaded.loc[0, "day_name"] == "수"


def test_future_blank_actual_cum_values_are_allowed_as_nan() -> None:
    df = load_input(_sample_path())
    future_actuals = df.loc[
        df["business_day_no"] > 12,
        ["sales_actual_cum", "recognized_actual_cum"],
    ]

    assert future_actuals.isna().to_numpy().all()


def test_missing_required_column_raises_value_error(tmp_path: Path) -> None:
    df = pd.read_csv(_sample_path()).drop(columns=["memo"])
    input_path = tmp_path / "missing_column.csv"
    df.to_csv(input_path, index=False)

    with pytest.raises(ValueError, match="Missing required input columns: memo"):
        load_input(input_path)


def test_invalid_date_value_raises_actionable_error(tmp_path: Path) -> None:
    df = pd.DataFrame(
        {
            "date": ["2026-07-01", "2026-07-02 Thu"],
            "day_name": ["Wed", "Thu"],
            "business_day_no": [1, 2],
            "is_close_day": ["Y", "N"],
            "close_type": ["month_start", "normal"],
            "sales_target_daily": [35.0, 2.5],
            "recognized_target_daily": [32.0, 2.3],
            "sales_actual_cum": [pd.NA, pd.NA],
            "recognized_actual_cum": [pd.NA, pd.NA],
            "memo": ["", ""],
        }
    )
    input_path = tmp_path / "invalid_date.csv"
    df.to_csv(input_path, index=False)

    with pytest.raises(ValueError) as exc_info:
        load_input(input_path)

    message = str(exc_info.value)
    assert "date contains invalid values" in message
    assert "YYYY-MM-DD" in message
    assert "row 3" in message
    assert "2026-07-02" in message


def test_xlsx_file_can_be_loaded_after_csv_round_trip(tmp_path: Path) -> None:
    df = pd.read_csv(_sample_path())
    xlsx_path = tmp_path / "input_sample.xlsx"
    df.to_excel(xlsx_path, index=False)

    loaded = load_input(xlsx_path)

    assert list(loaded.columns) == list(REQUIRED_INPUT_COLUMNS)
    assert len(loaded) == len(df)
    assert loaded.loc[0, "date"] == pd.Timestamp("2026-07-01")
    assert loaded["sales_actual_cum"].isna().sum() == 8


def test_historical_sample_loads_with_non_strict_business_day_no() -> None:
    loaded = load_input(
        _historical_sample_path(),
        sort_by="date",
        strict_business_day_no=False,
    )

    assert not loaded.empty
    assert loaded["business_day_no"].isna().sum() == 0
    assert pd.api.types.is_integer_dtype(loaded["business_day_no"])


def test_missing_business_day_no_raises_in_strict_mode(tmp_path: Path) -> None:
    df = pd.read_csv(_sample_path()).head(3)
    df.loc[1, "business_day_no"] = pd.NA
    input_path = tmp_path / "missing_business_day_no.csv"
    df.to_csv(input_path, index=False)

    with pytest.raises(ValueError, match="business_day_no is required"):
        load_input(input_path)


def test_non_strict_business_day_no_is_filled_by_date_order(tmp_path: Path) -> None:
    df = pd.read_csv(_sample_path()).head(3)
    df = df.sort_values("date", ascending=False).reset_index(drop=True)
    df["business_day_no"] = [pd.NA, 7, pd.NA]
    input_path = tmp_path / "partial_business_day_no.csv"
    df.to_csv(input_path, index=False)

    loaded = load_input(
        input_path,
        sort_by="date",
        strict_business_day_no=False,
    )

    assert loaded["date"].tolist() == sorted(loaded["date"].tolist())
    assert loaded["business_day_no"].tolist() == [1, 2, 3]
    assert pd.api.types.is_integer_dtype(loaded["business_day_no"])


def test_normalize_business_day_no_does_not_mutate_source_df() -> None:
    source = pd.DataFrame(
        {
            "date": ["2026-06-02", "2026-06-01"],
            "business_day_no": [pd.NA, 4],
        }
    )
    original = source.copy(deep=True)

    normalized = normalize_business_day_no(source, strict=False)

    pd.testing.assert_frame_equal(source, original)
    assert normalized["business_day_no"].tolist() == [1, 2]


def test_non_strict_business_day_no_requires_date_for_ordering() -> None:
    source = pd.DataFrame(
        {
            "date": [pd.NA],
            "business_day_no": [pd.NA],
        }
    )

    with pytest.raises(ValueError, match="date is required"):
        normalize_business_day_no(source, strict=False)
