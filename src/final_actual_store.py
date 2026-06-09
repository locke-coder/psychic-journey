"""Store confirmed month-end actuals for backtesting."""

from __future__ import annotations

import math
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from src.history_schema import (
    FINAL_ACTUALS,
    FINAL_ACTUALS_COLUMNS,
    FINAL_ACTUALS_UPSERT_KEY,
    validate_required_columns,
)
from src.schema import validate_metric


DEFAULT_FINAL_ACTUALS_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "history" / "final_actuals.csv"
)

UNDER_TARGET = "UNDER_TARGET"
ON_TARGET = "ON_TARGET"
OVER_TARGET = "OVER_TARGET"
FINAL_STATUSES = (UNDER_TARGET, ON_TARGET, OVER_TARGET)


def build_final_actual_record(
    *,
    target_month: object,
    metric: object,
    final_actual: object,
    monthly_target: object,
    cancellation_amount: object = None,
    net_actual: object = None,
    memo: object = None,
    updated_at: object = None,
) -> dict[str, object]:
    """Build one final actual record in the canonical storage schema."""
    target_month_value = _required_text(target_month, "target_month")
    metric_value = validate_metric(_required_text(metric, "metric"))
    final_actual_value = _required_number(final_actual, "final_actual")
    monthly_target_value = _required_number(monthly_target, "monthly_target")
    if monthly_target_value <= 0:
        raise ValueError("monthly_target must be greater than 0.")

    return {
        "target_month": target_month_value,
        "metric": metric_value,
        "final_actual": final_actual_value,
        "final_achievement_rate": final_actual_value / monthly_target_value,
        "final_status": _final_status(final_actual_value, monthly_target_value),
        "cancellation_amount": _optional_number(cancellation_amount, "cancellation_amount"),
        "net_actual": _optional_number(net_actual, "net_actual"),
        "memo": "" if _is_blank(memo) else str(memo),
        "updated_at": _updated_at(updated_at),
    }


def upsert_final_actual(
    record: Mapping[str, Any],
    path: str | Path | None = None,
) -> pd.DataFrame:
    """Insert or replace a final actual by target_month and metric."""
    normalized_record = _normalize_record(record)
    final_actuals_path = _resolve_path(path)

    existing = load_final_actuals(final_actuals_path)
    if existing.empty:
        updated = pd.DataFrame(columns=FINAL_ACTUALS_COLUMNS)
    else:
        match = pd.Series(True, index=existing.index)
        for key_column in FINAL_ACTUALS_UPSERT_KEY:
            match &= existing[key_column].astype(str) == str(normalized_record[key_column])
        updated = existing.loc[~match].copy()

    updated = pd.concat(
        [updated, pd.DataFrame([normalized_record], columns=FINAL_ACTUALS_COLUMNS)],
        ignore_index=True,
    )
    updated = updated.loc[:, list(FINAL_ACTUALS_COLUMNS)]

    final_actuals_path.parent.mkdir(parents=True, exist_ok=True)
    updated.to_csv(final_actuals_path, index=False, encoding="utf-8")
    return updated


def load_final_actuals(path: str | Path | None = None) -> pd.DataFrame:
    """Load final actuals from CSV, returning an empty canonical frame when absent."""
    final_actuals_path = _resolve_path(path)
    if not final_actuals_path.exists():
        return pd.DataFrame(columns=FINAL_ACTUALS_COLUMNS)

    final_actuals = pd.read_csv(final_actuals_path, keep_default_na=False)
    validate_required_columns(final_actuals.columns, FINAL_ACTUALS)
    return final_actuals.loc[:, list(FINAL_ACTUALS_COLUMNS)].copy()


def _normalize_record(record: Mapping[str, Any]) -> dict[str, object]:
    if not isinstance(record, Mapping):
        raise ValueError("record must be a mapping.")

    normalized = {
        "target_month": _required_text(record.get("target_month"), "target_month"),
        "metric": validate_metric(_required_text(record.get("metric"), "metric")),
        "final_actual": _required_number(record.get("final_actual"), "final_actual"),
        "final_achievement_rate": _required_number(
            record.get("final_achievement_rate"),
            "final_achievement_rate",
        ),
        "final_status": _required_status(record.get("final_status")),
        "cancellation_amount": _optional_number(
            record.get("cancellation_amount"),
            "cancellation_amount",
        ),
        "net_actual": _optional_number(record.get("net_actual"), "net_actual"),
        "memo": "" if _is_blank(record.get("memo")) else str(record.get("memo")),
        "updated_at": _updated_at(record.get("updated_at")),
    }
    return normalized


def _resolve_path(path: str | Path | None) -> Path:
    return Path(path) if path is not None else DEFAULT_FINAL_ACTUALS_PATH


def _final_status(final_actual: float, monthly_target: float) -> str:
    if math.isclose(final_actual, monthly_target, rel_tol=1e-9, abs_tol=1e-9):
        return ON_TARGET
    if final_actual < monthly_target:
        return UNDER_TARGET
    return OVER_TARGET


def _required_status(value: object) -> str:
    status = _required_text(value, "final_status")
    if status not in FINAL_STATUSES:
        allowed = ", ".join(FINAL_STATUSES)
        raise ValueError(f"Unsupported final_status: {status}. Allowed: {allowed}.")
    return status


def _required_text(value: object, field_name: str) -> str:
    if _is_blank(value):
        raise ValueError(f"{field_name} is required.")
    return str(value).strip()


def _required_number(value: object, field_name: str) -> float:
    if _is_blank(value):
        raise ValueError(f"{field_name} is required.")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric.") from exc
    if not math.isfinite(number):
        raise ValueError(f"{field_name} must be finite.")
    return number


def _optional_number(value: object, field_name: str) -> float | str:
    if _is_blank(value):
        return ""
    return _required_number(value, field_name)


def _updated_at(value: object) -> str:
    if _is_blank(value):
        return datetime.now().isoformat(timespec="seconds")
    return str(value).strip()


def _is_blank(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not value.strip()
    if isinstance(value, float):
        return math.isnan(value)
    return False

