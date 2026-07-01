from pathlib import Path

import pandas as pd
import pytest

from src.final_actual_store import (
    ON_TARGET,
    OVER_TARGET,
    UNDER_TARGET,
    build_final_actual_record,
    load_final_actuals,
    upsert_final_actual,
)


def test_new_final_actual_is_saved(tmp_path: Path) -> None:
    path = tmp_path / "final_actuals.csv"
    record = build_final_actual_record(
        target_month="2026-06",
        metric="sales",
        final_actual=120.0,
        monthly_target=100.0,
        updated_at="2026-07-01T09:00:00",
    )

    upsert_final_actual(record, path)

    loaded = load_final_actuals(path)
    assert len(loaded) == 1
    assert loaded.loc[0, "target_month"] == "2026-06"
    assert loaded.loc[0, "metric"] == "sales"
    assert loaded.loc[0, "final_actual"] == pytest.approx(120.0)


def test_same_target_month_and_metric_is_upserted(tmp_path: Path) -> None:
    path = tmp_path / "final_actuals.csv"
    first_record = build_final_actual_record(
        target_month="2026-06",
        metric="recognized",
        final_actual=90.0,
        monthly_target=100.0,
        updated_at="2026-07-01T09:00:00",
    )
    second_record = build_final_actual_record(
        target_month="2026-06",
        metric="recognized",
        final_actual=110.0,
        monthly_target=100.0,
        memo="confirmed adjustment",
        updated_at="2026-07-02T09:00:00",
    )

    upsert_final_actual(first_record, path)
    upsert_final_actual(second_record, path)

    loaded = load_final_actuals(path)
    assert len(loaded) == 1
    assert loaded.loc[0, "final_actual"] == pytest.approx(110.0)
    assert loaded.loc[0, "final_status"] == OVER_TARGET
    assert loaded.loc[0, "memo"] == "confirmed adjustment"


def test_final_status_and_achievement_rate_are_calculated() -> None:
    under = build_final_actual_record(
        target_month="2026-06",
        metric="sales",
        final_actual=90.0,
        monthly_target=100.0,
    )
    on_target = build_final_actual_record(
        target_month="2026-06",
        metric="sales",
        final_actual=100.0,
        monthly_target=100.0,
    )
    over = build_final_actual_record(
        target_month="2026-06",
        metric="sales",
        final_actual=110.0,
        monthly_target=100.0,
    )

    assert under["final_status"] == UNDER_TARGET
    assert under["final_achievement_rate"] == pytest.approx(0.9)
    assert on_target["final_status"] == ON_TARGET
    assert on_target["final_achievement_rate"] == pytest.approx(1.0)
    assert over["final_status"] == OVER_TARGET
    assert over["final_achievement_rate"] == pytest.approx(1.1)


def test_optional_columns_allow_blank_values(tmp_path: Path) -> None:
    path = tmp_path / "final_actuals.csv"
    record = build_final_actual_record(
        target_month="2026-06",
        metric="sales",
        final_actual=100.0,
        monthly_target=100.0,
        updated_at="2026-07-01T09:00:00",
    )

    upsert_final_actual(record, path)

    loaded = load_final_actuals(path)
    assert loaded.loc[0, "cancellation_amount"] == ""
    assert loaded.loc[0, "net_actual"] == ""
    assert loaded.loc[0, "memo"] == ""


def test_missing_required_values_raise_value_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="target_month is required"):
        build_final_actual_record(
            target_month="",
            metric="sales",
            final_actual=100.0,
            monthly_target=100.0,
        )

    with pytest.raises(ValueError, match="monthly_target is required"):
        build_final_actual_record(
            target_month="2026-06",
            metric="sales",
            final_actual=100.0,
            monthly_target=None,
        )

    with pytest.raises(ValueError, match="final_achievement_rate is required"):
        upsert_final_actual(
            {
                "target_month": "2026-06",
                "metric": "sales",
                "final_actual": 100.0,
                "final_status": ON_TARGET,
            },
            tmp_path / "final_actuals.csv",
        )


def test_load_missing_final_actuals_returns_canonical_empty_frame(tmp_path: Path) -> None:
    loaded = load_final_actuals(tmp_path / "missing.csv")

    assert loaded.empty
    assert list(loaded.columns) == [
        "target_month",
        "metric",
        "final_actual",
        "final_achievement_rate",
        "final_status",
        "cancellation_amount",
        "net_actual",
        "memo",
        "updated_at",
    ]


def test_load_rejects_files_missing_required_columns(tmp_path: Path) -> None:
    path = tmp_path / "final_actuals.csv"
    pd.DataFrame({"target_month": ["2026-06"]}).to_csv(path, index=False)

    with pytest.raises(ValueError, match="Missing required final_actuals columns"):
        load_final_actuals(path)
