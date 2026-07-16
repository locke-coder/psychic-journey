from __future__ import annotations

import io
from pathlib import Path

import pandas as pd
import pytest

import src.final_actual_store as final_actual_store
from src.private_data_store import (
    PrivateDataFile,
    PrivateDataStoreConflictError,
)


def _record(
    *,
    metric: str = "sales",
    final_actual: float = 100.0,
    memo: str = "",
) -> dict[str, object]:
    return final_actual_store.build_final_actual_record(
        target_month="2026-06",
        metric=metric,
        final_actual=final_actual,
        monthly_target=100.0,
        memo=memo,
        updated_at="2026-07-01T09:00:00",
    )


def _stored_frame(rows: list[dict[str, object]], sha: str = "old-sha") -> PrivateDataFile:
    content = pd.DataFrame(
        rows,
        columns=final_actual_store.FINAL_ACTUALS_COLUMNS,
    ).to_csv(index=False).encode("utf-8-sig")
    return PrivateDataFile(
        path=final_actual_store.PRIVATE_FINAL_ACTUALS_PATH,
        content=content,
        sha=sha,
        size=len(content),
    )


def test_remote_load_missing_returns_canonical_empty_frame(monkeypatch) -> None:
    monkeypatch.setattr(final_actual_store, "is_private_data_store_enabled", lambda: True)
    monkeypatch.setattr(final_actual_store, "read_private_data_file", lambda _path: None)

    loaded = final_actual_store.load_final_actuals()

    assert loaded.empty
    assert list(loaded.columns) == list(final_actual_store.FINAL_ACTUALS_COLUMNS)


def test_remote_load_reads_utf8_csv_and_reports_private_location(monkeypatch) -> None:
    stored = _stored_frame([_record(memo="확정")])
    monkeypatch.setattr(final_actual_store, "is_private_data_store_enabled", lambda: True)
    monkeypatch.setattr(
        final_actual_store,
        "read_private_data_file",
        lambda path: stored
        if path == final_actual_store.PRIVATE_FINAL_ACTUALS_PATH
        else None,
    )
    monkeypatch.setattr(
        final_actual_store,
        "private_data_display_path",
        lambda path: f"github://private/{path}",
    )

    loaded = final_actual_store.load_final_actuals()

    assert loaded.loc[0, "memo"] == "확정"
    assert final_actual_store.final_actuals_location() == (
        "github://private/history/final_actuals.csv"
    )


def test_remote_upsert_replaces_matching_key_and_uses_observed_sha(monkeypatch) -> None:
    stored = _stored_frame(
        [
            _record(final_actual=90.0, memo="old"),
            _record(metric="recognized", final_actual=80.0),
        ]
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(final_actual_store, "is_private_data_store_enabled", lambda: True)
    monkeypatch.setattr(final_actual_store, "read_private_data_file", lambda _path: stored)

    def fake_write(
        path: str,
        content: bytes,
        message: str,
        *,
        expected_sha: str | None,
    ) -> dict[str, object]:
        captured.update(
            path=path,
            content=content,
            message=message,
            expected_sha=expected_sha,
        )
        return {}

    monkeypatch.setattr(final_actual_store, "write_private_data_file", fake_write)

    updated = final_actual_store.upsert_final_actual(
        _record(final_actual=110.0, memo="confirmed")
    )

    assert len(updated) == 2
    sales = updated.loc[updated["metric"] == "sales"].iloc[0]
    recognized = updated.loc[updated["metric"] == "recognized"].iloc[0]
    assert sales["final_actual"] == pytest.approx(110.0)
    assert sales["memo"] == "confirmed"
    assert recognized["final_actual"] == pytest.approx(80.0)
    assert captured["path"] == final_actual_store.PRIVATE_FINAL_ACTUALS_PATH
    assert captured["expected_sha"] == "old-sha"
    assert captured["message"] == "Upsert final actual"

    written = pd.read_csv(
        io.BytesIO(captured["content"]),
        encoding="utf-8-sig",
        keep_default_na=False,
    )
    assert len(written) == 2
    assert written.loc[written["metric"] == "sales", "memo"].item() == "confirmed"


def test_remote_upsert_new_file_uses_none_sha(monkeypatch) -> None:
    captured: dict[str, object] = {}
    monkeypatch.setattr(final_actual_store, "is_private_data_store_enabled", lambda: True)
    monkeypatch.setattr(final_actual_store, "read_private_data_file", lambda _path: None)

    def fake_write(
        _path: str,
        _content: bytes,
        _message: str,
        *,
        expected_sha: str | None,
    ) -> dict[str, object]:
        captured["expected_sha"] = expected_sha
        return {}

    monkeypatch.setattr(final_actual_store, "write_private_data_file", fake_write)

    updated = final_actual_store.upsert_final_actual(_record())

    assert len(updated) == 1
    assert captured["expected_sha"] is None


def test_remote_write_conflict_is_propagated(monkeypatch) -> None:
    monkeypatch.setattr(final_actual_store, "is_private_data_store_enabled", lambda: True)
    monkeypatch.setattr(final_actual_store, "read_private_data_file", lambda _path: None)

    def conflicting_write(*_args, **_kwargs) -> dict[str, object]:
        raise PrivateDataStoreConflictError("reload and retry")

    monkeypatch.setattr(final_actual_store, "write_private_data_file", conflicting_write)

    with pytest.raises(PrivateDataStoreConflictError, match="reload and retry"):
        final_actual_store.upsert_final_actual(_record())


def test_explicit_path_stays_local_when_remote_mode_is_available(
    monkeypatch,
    tmp_path: Path,
) -> None:
    path = tmp_path / "final_actuals.csv"

    def remote_mode_must_not_be_checked() -> bool:
        raise AssertionError("explicit path must bypass private-store mode")

    monkeypatch.setattr(
        final_actual_store,
        "is_private_data_store_enabled",
        remote_mode_must_not_be_checked,
    )

    final_actual_store.upsert_final_actual(_record(), path)

    loaded = final_actual_store.load_final_actuals(path)
    assert path.exists()
    assert loaded.loc[0, "final_actual"] == pytest.approx(100.0)
