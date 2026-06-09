"""Input loader for user-driven sales closing forecast files."""

from __future__ import annotations

from numbers import Real
from pathlib import Path
from typing import Literal

import pandas as pd

from src.schema import REQUIRED_INPUT_COLUMNS


TARGET_DAILY_COLUMNS: tuple[str, ...] = (
    "sales_target_daily",
    "recognized_target_daily",
)
ACTUAL_CUM_COLUMNS: tuple[str, ...] = (
    "sales_actual_cum",
    "recognized_actual_cum",
)

_TRUE_TOKENS = {"Y", "YES", "TRUE", "1"}
_FALSE_TOKENS = {"N", "NO", "FALSE", "0", ""}
CSV_ENCODING_CANDIDATES: tuple[str, ...] = (
    "utf-8-sig",
    "utf-8",
    "cp949",
    "euc-kr",
)


def load_input(
    path: str | Path,
    sort_by: Literal["business_day_no", "date"] = "business_day_no",
    strict_business_day_no: bool = True,
) -> pd.DataFrame:
    """Load and normalize a forecast input CSV or XLSX file."""
    input_path = Path(path)
    df = _read_input_file(input_path)

    _validate_required_columns(df)
    if sort_by not in {"business_day_no", "date"}:
        raise ValueError("sort_by must be either 'business_day_no' or 'date'.")

    normalized = _drop_fully_blank_rows(df)
    normalized["date"] = _normalize_date_column(normalized["date"])
    normalized = normalize_business_day_no(
        normalized,
        strict=strict_business_day_no,
    )
    normalized["is_close_day"] = normalized["is_close_day"].map(_to_bool)

    for column in TARGET_DAILY_COLUMNS:
        normalized[column] = pd.to_numeric(normalized[column], errors="raise").astype(
            float
        )

    for column in ACTUAL_CUM_COLUMNS:
        actual_values = normalized[column].replace(r"^\s*$", pd.NA, regex=True)
        normalized[column] = pd.to_numeric(actual_values, errors="raise").astype(float)

    ordered_columns = [
        *REQUIRED_INPUT_COLUMNS,
        *[column for column in normalized.columns if column not in REQUIRED_INPUT_COLUMNS],
    ]
    return normalized.loc[:, ordered_columns].sort_values(sort_by).reset_index(drop=True)


def normalize_business_day_no(df: pd.DataFrame, strict: bool = True) -> pd.DataFrame:
    """Return a copy with a safe integer business-day sequence."""
    normalized = df.copy()
    business_day_no = pd.to_numeric(
        normalized["business_day_no"].replace(r"^\s*$", pd.NA, regex=True),
        errors="coerce",
    )
    missing_business_day_no = business_day_no.isna()

    if _has_fractional_values(business_day_no):
        raise ValueError("business_day_no must contain whole-number values.")

    if missing_business_day_no.any():
        if strict:
            raise ValueError("business_day_no is required and must be numeric.")

        date_order = pd.to_datetime(
            normalized["date"].replace(r"^\s*$", pd.NA, regex=True),
            errors="coerce",
        )
        if date_order.isna().any():
            raise ValueError(
                "date is required to fill missing business_day_no values."
            )

        normalized = (
            normalized.assign(_business_day_date_order=date_order)
            .sort_values("_business_day_date_order", kind="mergesort")
            .drop(columns="_business_day_date_order")
            .reset_index(drop=True)
        )
        normalized["business_day_no"] = range(1, len(normalized) + 1)
        return normalized

    normalized["business_day_no"] = business_day_no.astype(int)
    return normalized


def _read_input_file(path: Path) -> pd.DataFrame:
    suffix = path.suffix.lower()
    if suffix == ".csv":
        return _read_csv_with_encoding_fallbacks(path)
    if suffix == ".xlsx":
        return pd.read_excel(path)
    raise ValueError("Unsupported input file type. Use CSV or XLSX.")


def _read_csv_with_encoding_fallbacks(path: Path) -> pd.DataFrame:
    decode_errors: list[str] = []
    for encoding in CSV_ENCODING_CANDIDATES:
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError as exc:
            decode_errors.append(f"{encoding}: {exc}")

    supported = ", ".join(CSV_ENCODING_CANDIDATES)
    details = " | ".join(decode_errors)
    raise ValueError(
        f"CSV encoding is not supported. Save the file as one of: {supported}. {details}"
    )


def _validate_required_columns(df: pd.DataFrame) -> None:
    missing_columns = [
        column for column in REQUIRED_INPUT_COLUMNS if column not in df.columns
    ]
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Missing required input columns: {missing}")


def _drop_fully_blank_rows(df: pd.DataFrame) -> pd.DataFrame:
    blank_checked = df.loc[:, REQUIRED_INPUT_COLUMNS].replace(
        r"^\s*$",
        pd.NA,
        regex=True,
    )
    fully_blank_rows = blank_checked.isna().all(axis=1)
    if not fully_blank_rows.any():
        return df.copy()
    return df.loc[~fully_blank_rows].copy()


def _normalize_date_column(values: pd.Series) -> pd.Series:
    raw_dates = values.replace(r"^\s*$", pd.NA, regex=True)
    if raw_dates.isna().any():
        raise ValueError("date is required for each input row.")
    return pd.to_datetime(raw_dates, errors="raise")


def _has_fractional_values(values: pd.Series) -> bool:
    valid_values = values.dropna()
    if valid_values.empty:
        return False
    return bool((valid_values % 1 != 0).any())


def _to_bool(value: object) -> bool:
    if pd.isna(value):
        return False

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        token = value.strip().upper()
        if token in _TRUE_TOKENS:
            return True
        if token in _FALSE_TOKENS:
            return False

    if isinstance(value, Real) and value in (0, 1):
        return bool(value)

    raise ValueError(f"Unsupported is_close_day value: {value!r}")
