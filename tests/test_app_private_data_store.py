from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pandas as pd

import app
from src.private_data_store import PrivateDataFile


def _private_file(path: str, frame: pd.DataFrame, *, sha: str = "stored-sha") -> PrivateDataFile:
    content = frame.to_csv(index=False).encode("utf-8-sig")
    return PrivateDataFile(path=path, content=content, sha=sha, size=len(content))


def _input_rows() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": ["2026-06-10", "2026-06-11"],
            "business_day_no": [7, 8],
            "sales_actual_cum": [70.5, 88.8],
            "recognized_actual_cum": [64.5, 77.7],
        }
    )


def test_saved_actuals_default_read_write_delete_use_private_store(monkeypatch) -> None:
    stored = _private_file(app.PRIVATE_SAVED_ACTUALS_PATH, _input_rows().iloc[[0]])
    captured: dict[str, object] = {}

    monkeypatch.setattr(app, "is_private_data_store_enabled", lambda: True)
    monkeypatch.setattr(app, "read_private_data_file", lambda path: stored)
    monkeypatch.setattr(
        app,
        "private_data_display_path",
        lambda path: f"github://private/{path}",
    )

    def fake_write(
        path: str,
        content: bytes,
        message: str,
        *,
        expected_sha: str | None,
    ) -> dict[str, object]:
        captured.update(
            write_path=path,
            write_content=content,
            write_message=message,
            expected_sha=expected_sha,
        )
        return {}

    def fake_delete(path: str, message: str) -> bool:
        captured.update(delete_path=path, delete_message=message)
        return True

    monkeypatch.setattr(app, "write_private_data_file", fake_write)
    monkeypatch.setattr(app, "delete_private_data_file", fake_delete)

    loaded = app.load_saved_actuals()
    location = app.save_saved_actuals(_input_rows().iloc[[1]])
    app.clear_saved_actuals()

    assert loaded.loc[0, "sales_actual_cum"] == 70.5
    assert loaded.loc[0, "recognized_actual_cum"] == 64.5
    assert location == "github://private/actuals/saved_actuals.csv"
    assert captured["write_path"] == app.PRIVATE_SAVED_ACTUALS_PATH
    assert captured["write_message"] == "Update saved actuals"
    assert captured["expected_sha"] == "stored-sha"
    written = pd.read_csv(
        io.BytesIO(captured["write_content"]),
        encoding="utf-8-sig",
    )
    assert written.loc[0, "business_day_no"] == 8
    assert written.loc[0, "sales_actual_cum"] == 88.8
    assert captured["delete_path"] == app.PRIVATE_SAVED_ACTUALS_PATH
    assert captured["delete_message"] == "Delete saved actuals"


def test_save_current_input_defaults_bundles_actuals_with_operator_commit(monkeypatch) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(app, "is_private_data_store_enabled", lambda: True)
    monkeypatch.setattr(
        app,
        "load_saved_actuals",
        lambda: pd.DataFrame(columns=app.SAVED_ACTUAL_COLUMNS),
    )
    monkeypatch.setattr(
        app,
        "private_data_display_path",
        lambda path: f"github://private/{path}",
    )

    def fake_save_operator_sample(
        kind: str,
        frame: pd.DataFrame,
        *,
        related_private_files: dict[str, bytes],
    ) -> dict[str, object]:
        captured.update(
            kind=kind,
            frame=frame.copy(),
            related_private_files=dict(related_private_files),
        )
        return {"ok": True, "path": "github://private/current_input_sample.csv"}

    def separate_write_must_not_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("saved actuals must be part of the operator atomic commit")

    monkeypatch.setattr(app, "save_operator_sample", fake_save_operator_sample)
    monkeypatch.setattr(app, "write_private_data_file", separate_write_must_not_run)

    result = app.save_current_input_defaults(_input_rows())

    assert result["ok"] is True
    assert captured["kind"] == "current_input"
    assert list(captured["related_private_files"]) == [app.PRIVATE_SAVED_ACTUALS_PATH]
    bundled = pd.read_csv(
        io.BytesIO(captured["related_private_files"][app.PRIVATE_SAVED_ACTUALS_PATH]),
        encoding="utf-8-sig",
    )
    assert bundled["business_day_no"].tolist() == [7, 8]
    assert bundled["sales_actual_cum"].tolist() == [70.5, 88.8]
    assert result["saved_actuals_path"] == "github://private/actuals/saved_actuals.csv"


def test_default_history_loads_delegate_to_remote_stores(monkeypatch) -> None:
    forecast = pd.DataFrame({"forecast": [1.0]})
    final = pd.DataFrame({"final": [2.0]})
    calls: dict[str, tuple[object, ...]] = {}

    monkeypatch.setattr(app, "is_private_data_store_enabled", lambda: True)

    def fake_load_forecast_history(*args: object) -> pd.DataFrame:
        calls["forecast"] = args
        return forecast

    def fake_load_final_actuals(*args: object) -> pd.DataFrame:
        calls["final"] = args
        return final

    monkeypatch.setattr(app, "load_forecast_history", fake_load_forecast_history)
    monkeypatch.setattr(app, "load_final_actuals", fake_load_final_actuals)

    tables = app.load_history_tables_for_app()

    assert tables["forecast_history"] is forecast
    assert tables["final_actuals"] is final
    assert calls == {"forecast": (), "final": ()}


def test_default_history_snapshot_delegates_none_path_to_remote_store(monkeypatch) -> None:
    rows = pd.DataFrame({"run_id": ["run-1"]})
    captured: dict[str, object] = {}

    monkeypatch.setattr(app, "is_private_data_store_enabled", lambda: True)
    monkeypatch.setattr(
        app,
        "build_forecast_history_rows",
        lambda _scenario, _context: rows,
    )

    def fake_append(frame: pd.DataFrame, path: Path | None) -> pd.DataFrame:
        captured.update(frame=frame, path=path)
        return frame

    monkeypatch.setattr(app, "append_forecast_history", fake_append)

    result = app.save_forecast_history_snapshot(
        pd.DataFrame({"scenario_id": ["F1_P1"]}),
        "2026-06-10",
        "sales",
    )

    assert result is rows
    assert captured == {"frame": rows, "path": None}


def test_excel_report_uses_temp_file_and_one_atomic_private_commit(
    monkeypatch,
    tmp_path: Path,
) -> None:
    report_bytes = b"private-xlsx-bytes"
    captured: dict[str, object] = {}
    output_dir = tmp_path / "outputs"

    monkeypatch.setattr(app, "OUTPUT_DIR", output_dir)
    monkeypatch.setattr(app, "is_private_data_store_enabled", lambda: True)
    monkeypatch.setattr(
        app,
        "load_history_tables_for_app",
        lambda: {
            "forecast_history": pd.DataFrame(),
            "final_actuals": pd.DataFrame(),
        },
    )
    monkeypatch.setattr(app, "build_backtest_dataset", lambda *_args: pd.DataFrame())
    monkeypatch.setattr(app, "summarize_by_forecast_model", lambda *_args: pd.DataFrame())

    def fake_export(path: Path, *_args: object, **_kwargs: object) -> Path:
        resolved = Path(path)
        captured["export_path"] = resolved
        resolved.write_bytes(report_bytes)
        return resolved

    def fake_atomic_write(
        files: dict[str, bytes],
        message: str,
    ) -> dict[str, object]:
        captured["files"] = dict(files)
        captured["message"] = message
        return {"commit": {"sha": "new-sha"}}

    def single_file_write_must_not_run(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("report and manifest must be committed atomically")

    monkeypatch.setattr(app, "export_daily_report", fake_export)
    monkeypatch.setattr(app, "write_private_data_files_atomic", fake_atomic_write)
    monkeypatch.setattr(app, "write_private_data_file", single_file_write_must_not_run)

    content, file_name = app.build_excel_report_bytes(
        summary_dict={},
        scenario_df=pd.DataFrame(),
        revised_targets_df=pd.DataFrame(),
        close_cycle_df=pd.DataFrame(),
        validation_result={},
        report_text="private report",
        metric="sales",
        as_of_date="2026-06-10",
    )

    report_path = f"{app.PRIVATE_REPORTS_LATEST_PATH}/{file_name}"
    manifest_path = f"{report_path}.manifest.json"
    export_path = captured["export_path"]
    files = captured["files"]

    assert content == report_bytes
    assert file_name == "daily_report_sales_20260610.xlsx"
    assert not export_path.exists()
    assert output_dir / "latest" != export_path.parent
    assert not (output_dir / "latest").exists()
    assert set(files) == {report_path, manifest_path}
    assert files[report_path] == report_bytes
    manifest = json.loads(files[manifest_path].decode("utf-8"))
    assert manifest["file_name"] == file_name
    assert manifest["as_of_date"] == "2026-06-10"
    assert manifest["metric"] == "sales"
    assert manifest["size_bytes"] == len(report_bytes)
    assert manifest["sha256"] == hashlib.sha256(report_bytes).hexdigest()
    assert captured["message"] == f"Publish {file_name}"
