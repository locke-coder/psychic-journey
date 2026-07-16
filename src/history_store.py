"""CSV storage helpers for forecast history snapshots."""

from __future__ import annotations

import io
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import pandas as pd

from src import history_schema
from src.private_data_store import (
    PrivateDataStoreUnavailableError,
    is_private_data_store_enabled,
    private_data_display_path,
    read_private_data_file,
    write_private_data_file,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FORECAST_HISTORY_PATH = REPO_ROOT / "data" / "history" / "forecast_history.csv"
PRIVATE_FORECAST_HISTORY_PATH = "history/forecast_history.csv"
SCENARIO_STRATEGY_COLUMN = "provision_strategy"

_CONTEXT_COLUMNS = (
    "run_id",
    "run_datetime",
    "target_month",
    "as_of_date",
    "metric",
)
_SCENARIO_TO_HISTORY_COLUMNS = {
    "forecast_model": "forecast_model",
    SCENARIO_STRATEGY_COLUMN: "strategy_id",
    "strategy_type": "strategy_type",
    "forecast_amount": "forecast_amount",
    "forecast_rate": "forecast_rate",
    "target_status": "target_status",
    "target_variance": "target_variance",
    "gap_to_target": "gap_to_target",
    "surplus_to_target": "surplus_to_target",
    "risk_level": "risk_level",
    "monthly_target": "monthly_target",
    "current_actual_cum": "current_actual_cum",
    "current_target_cum": "current_target_cum",
    "remaining_target": "remaining_target",
}


def ensure_history_dir(path: str | Path | None = None) -> Path:
    """Create the forecast history directory and return the CSV path."""
    history_path = _history_path(path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    return history_path


def build_forecast_history_rows(
    scenario_df: pd.DataFrame,
    run_context: dict[str, Any],
) -> pd.DataFrame:
    """Build schema-valid forecast history rows from scenario runner output."""
    if not isinstance(run_context, dict):
        raise ValueError("run_context must be a mapping.")

    _validate_run_context(run_context)
    _validate_scenario_columns(scenario_df)

    run_id = _context_value(run_context, "run_id") or _generate_run_id()
    context_values = {
        "run_id": run_id,
        "run_datetime": _format_context_value(run_context["run_datetime"]),
        "target_month": _format_target_month(run_context["target_month"]),
        "as_of_date": _format_context_value(run_context["as_of_date"]),
        "metric": str(run_context["metric"]),
    }

    rows = pd.DataFrame(index=scenario_df.index)
    for column in _CONTEXT_COLUMNS:
        rows[column] = context_values[column]
    for scenario_column, history_column in _SCENARIO_TO_HISTORY_COLUMNS.items():
        rows[history_column] = scenario_df[scenario_column].to_numpy(copy=True)

    rows = rows.loc[:, history_schema.FORECAST_HISTORY_COLUMNS].reset_index(drop=True)
    history_schema.validate_required_columns(
        rows.columns,
        history_schema.FORECAST_HISTORY,
    )
    return rows


def append_forecast_history(
    rows: pd.DataFrame | list[dict[str, Any]],
    path: str | Path | None = None,
) -> pd.DataFrame:
    """Append forecast history rows to CSV after schema and duplicate checks."""
    if path is None and is_private_data_store_enabled():
        return _append_private_forecast_history(rows)

    history_path = ensure_history_dir(path)
    incoming = _normalize_history_rows(rows)
    existing = load_forecast_history(history_path)
    conflicts = _find_duplicate_conflicts(existing, incoming)
    if conflicts:
        conflict_text = ", ".join(conflicts)
        raise ValueError(f"Duplicate forecast_history rows blocked: {conflict_text}")

    write_header = not history_path.exists() or history_path.stat().st_size == 0
    incoming.to_csv(
        history_path,
        mode="a",
        header=write_header,
        index=False,
        encoding="utf-8",
    )
    return load_forecast_history(history_path)


def load_forecast_history(path: str | Path | None = None) -> pd.DataFrame:
    """Load forecast history CSV, returning an empty schema frame when absent."""
    if path is None and is_private_data_store_enabled():
        loaded, _sha = _read_private_forecast_history()
        return loaded

    history_path = _history_path(path)
    columns = list(history_schema.FORECAST_HISTORY_COLUMNS)
    if not history_path.exists() or history_path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)

    loaded = pd.read_csv(history_path, encoding="utf-8")
    history_schema.validate_required_columns(
        loaded.columns,
        history_schema.FORECAST_HISTORY,
    )
    return loaded.loc[:, columns]


def forecast_history_location(path: str | Path | None = None) -> str:
    """Return the active durable location without exposing credentials."""
    if path is None and is_private_data_store_enabled():
        return private_data_display_path(PRIVATE_FORECAST_HISTORY_PATH)
    return str(_history_path(path))


def _append_private_forecast_history(
    rows: pd.DataFrame | list[dict[str, Any]],
) -> pd.DataFrame:
    incoming = _normalize_history_rows(rows)
    existing, expected_sha = _read_private_forecast_history()
    conflicts = _find_duplicate_conflicts(existing, incoming)
    if conflicts:
        conflict_text = ", ".join(conflicts)
        raise ValueError(f"Duplicate forecast_history rows blocked: {conflict_text}")
    updated = pd.concat([existing, incoming], ignore_index=True)
    updated = updated.loc[:, list(history_schema.FORECAST_HISTORY_COLUMNS)]
    payload = updated.to_csv(index=False).encode("utf-8-sig")
    write_private_data_file(
        PRIVATE_FORECAST_HISTORY_PATH,
        payload,
        "Append forecast history",
        expected_sha=expected_sha,
    )
    return updated


def _read_private_forecast_history() -> tuple[pd.DataFrame, str | None]:
    columns = list(history_schema.FORECAST_HISTORY_COLUMNS)
    stored = read_private_data_file(PRIVATE_FORECAST_HISTORY_PATH)
    if stored is None or not stored.content:
        return pd.DataFrame(columns=columns), None
    try:
        loaded = pd.read_csv(io.BytesIO(stored.content), encoding="utf-8-sig")
        history_schema.validate_required_columns(
            loaded.columns,
            history_schema.FORECAST_HISTORY,
        )
    except Exception as exc:  # noqa: BLE001 - corrupt remote data must fail closed.
        raise PrivateDataStoreUnavailableError(
            "private forecast history could not be decoded or validated"
        ) from exc
    return loaded.loc[:, columns].copy(), stored.sha or None


def _history_path(path: str | Path | None) -> Path:
    return Path(path) if path is not None else DEFAULT_FORECAST_HISTORY_PATH


def _normalize_history_rows(rows: pd.DataFrame | list[dict[str, Any]]) -> pd.DataFrame:
    if isinstance(rows, pd.DataFrame):
        normalized = rows.copy(deep=True)
    else:
        normalized = pd.DataFrame(rows)

    history_schema.validate_required_columns(
        normalized.columns,
        history_schema.FORECAST_HISTORY,
    )
    return normalized.loc[:, history_schema.FORECAST_HISTORY_COLUMNS].reset_index(drop=True)


def _validate_run_context(run_context: dict[str, Any]) -> None:
    missing = [
        column
        for column in _CONTEXT_COLUMNS
        if column != "run_id" and not _has_value(run_context.get(column))
    ]
    if missing:
        raise ValueError(f"Missing required run_context values: {', '.join(missing)}")


def _validate_scenario_columns(scenario_df: pd.DataFrame) -> None:
    missing = [
        column
        for column in _SCENARIO_TO_HISTORY_COLUMNS
        if column not in scenario_df.columns
    ]
    if missing:
        raise ValueError(f"Missing required scenario columns: {', '.join(missing)}")


def _find_duplicate_conflicts(
    existing: pd.DataFrame,
    incoming: pd.DataFrame,
) -> list[str]:
    if existing.empty:
        return _find_incoming_fallback_duplicates(incoming)

    config = history_schema.load_history_config()
    policy = config["duplicate_keys"][history_schema.FORECAST_HISTORY]
    conflicts: list[str] = []

    if policy.get("run_id_unique") is True:
        existing_run_ids = _non_blank_values(existing["run_id"])
        incoming_run_ids = _non_blank_values(incoming["run_id"])
        conflicts.extend(
            f"run_id={run_id}"
            for run_id in sorted(existing_run_ids.intersection(incoming_run_ids))
        )

    fallback_key = tuple(policy.get("fallback_key", ()))
    if fallback_key:
        existing_fallback_keys = _fallback_keys_for_blank_run_id(existing, fallback_key)
        incoming_fallback_keys = _fallback_keys_for_blank_run_id(incoming, fallback_key)
        conflicts.extend(
            f"fallback_key={key}"
            for key in sorted(existing_fallback_keys.intersection(incoming_fallback_keys))
        )

    conflicts.extend(_find_incoming_fallback_duplicates(incoming))
    return conflicts


def _find_incoming_fallback_duplicates(incoming: pd.DataFrame) -> list[str]:
    config = history_schema.load_history_config()
    fallback_key = tuple(
        config["duplicate_keys"][history_schema.FORECAST_HISTORY].get(
            "fallback_key",
            (),
        )
    )
    if not fallback_key:
        return []

    keys = list(_fallback_key_values_for_blank_run_id(incoming, fallback_key))
    duplicate_keys = sorted({key for key in keys if keys.count(key) > 1})
    return [f"fallback_key={key}" for key in duplicate_keys]


def _fallback_keys_for_blank_run_id(
    rows: pd.DataFrame,
    fallback_key: tuple[str, ...],
) -> set[tuple[Any, ...]]:
    return set(_fallback_key_values_for_blank_run_id(rows, fallback_key))


def _fallback_key_values_for_blank_run_id(
    rows: pd.DataFrame,
    fallback_key: tuple[str, ...],
) -> list[tuple[Any, ...]]:
    values: list[tuple[Any, ...]] = []
    for record in rows.to_dict("records"):
        if _has_value(record.get("run_id")):
            continue
        history_schema.build_duplicate_key(history_schema.FORECAST_HISTORY, record)
        values.append(tuple(record[column] for column in fallback_key))
    return values


def _non_blank_values(series: pd.Series) -> set[str]:
    values: set[str] = set()
    for value in series:
        if _has_value(value):
            values.add(str(value))
    return values


def _context_value(run_context: dict[str, Any], key: str) -> Any:
    value = run_context.get(key)
    return value if _has_value(value) else None


def _generate_run_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"forecast-{now}-{uuid4().hex[:12]}"


def _format_target_month(value: Any) -> str:
    if isinstance(value, pd.Timestamp):
        return value.strftime("%Y-%m")
    if isinstance(value, datetime):
        return value.strftime("%Y-%m")
    if isinstance(value, date):
        return value.strftime("%Y-%m")
    return str(value)


def _format_context_value(value: Any) -> str:
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    try:
        return not bool(pd.isna(value))
    except (TypeError, ValueError):
        return True
