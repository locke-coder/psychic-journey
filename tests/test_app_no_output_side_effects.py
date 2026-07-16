import inspect
import os
from pathlib import Path

import pandas as pd

import app
from src import history_schema


class FakeStreamlit:
    def __init__(self) -> None:
        self.button_labels: list[str] = []
        self.downloads: list[str] = []
        self.messages: list[str] = []

    def markdown(self, body: object, **_: object) -> None:
        self.messages.append(str(body))

    def dataframe(self, *_: object, **__: object) -> None:
        return None

    def info(self, body: object, **_: object) -> None:
        self.messages.append(str(body))

    def caption(self, body: object, **_: object) -> None:
        self.messages.append(str(body))

    def button(self, label: str, **_: object) -> bool:
        self.button_labels.append(label)
        return False

    def download_button(self, label: str, **_: object) -> None:
        self.downloads.append(label)

    def success(self, body: object, **_: object) -> None:
        self.messages.append(str(body))

    def warning(self, body: object, **_: object) -> None:
        self.messages.append(str(body))

    def subheader(self, body: object, **_: object) -> None:
        self.messages.append(str(body))

    def write(self, body: object, **_: object) -> None:
        self.messages.append(str(body))

    def columns(self, spec: object, **_: object) -> list["FakeStreamlit"]:
        count = spec if isinstance(spec, int) else len(spec)
        return [self for _ in range(count)]


def _excel_context() -> dict[str, object]:
    return {
        "scenario_df": pd.DataFrame(
            [
                {
                    "scenario_id": "F1_P1",
                    "target_status": "UNDER_TARGET",
                    "monthly_target": 100.0,
                }
            ]
        ),
        "revised_targets_df": pd.DataFrame(),
        "summary_dict": {"metric": "sales"},
        "close_cycle_df": pd.DataFrame(),
        "validation_result": {"errors": [], "warnings": []},
        "report_text": "테스트 보고 메모",
        "metric": "sales",
        "as_of_date": "2026-06-12",
    }


def test_latest_excel_snapshot_reads_metadata_without_writing(tmp_path: Path) -> None:
    latest_dir = tmp_path / "latest"
    latest_dir.mkdir()
    report_path = latest_dir / "daily_report_sales_20260612_v2.xlsx"
    report_path.write_bytes(b"existing workbook bytes")
    before_stat = report_path.stat()

    snapshot = app.list_latest_excel_outputs(latest_dir)

    after_stat = report_path.stat()
    assert snapshot["파일명"].tolist() == ["daily_report_sales_20260612_v2.xlsx"]
    assert before_stat.st_mtime_ns == after_stat.st_mtime_ns
    assert before_stat.st_size == after_stat.st_size


def test_latest_excel_artifact_status_uses_actual_newest_daily_report(tmp_path: Path) -> None:
    latest_dir = tmp_path / "latest"
    latest_dir.mkdir()
    older_report = latest_dir / "daily_report_sales_20260610_v2.xlsx"
    newer_report = latest_dir / "daily_report_sales_20260611_v2.xlsx"
    reference = latest_dir / "reference_only.xlsx"
    older_report.write_bytes(b"older")
    newer_report.write_bytes(b"newer report")
    reference.write_bytes(b"reference")
    older_report.touch()
    newer_report.touch()

    status = app.get_latest_excel_artifact_status(latest_dir)

    assert status["exists"] is True
    assert status["file_name"] == "daily_report_sales_20260611_v2.xlsx"
    assert status["size_bytes"] == len(b"newer report")


def test_latest_audit_logs_select_newest_file_per_category(tmp_path: Path) -> None:
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    old_pytest = log_dir / "old_pytest.txt"
    old_pytest.write_text("old", encoding="utf-8")
    newest_pytest = log_dir / "latest_tests_before.txt"
    newest_pytest.write_text("new", encoding="utf-8")
    old_stat = old_pytest.stat()
    os.utime(old_pytest, (old_stat.st_atime, old_stat.st_mtime - 60))
    (log_dir / "latest_gate_before.json").write_text("{}", encoding="utf-8")
    (log_dir / "latest_forbidden_scan.txt").write_text("0", encoding="utf-8")

    logs = app.list_latest_audit_logs(log_dir, now=pd.Timestamp.now())

    by_label = logs.set_index("검증 항목")
    assert by_label.loc["pytest", "최근 저장 로그"] == newest_pytest.name
    assert by_label.loc["Gate Runner", "최근 저장 로그"] == "latest_gate_before.json"
    assert by_label.loc["금지 패턴", "최근 저장 로그"] == "latest_forbidden_scan.txt"
    assert by_label.loc["outputs mtime", "상태"] == "확인 필요"


def test_excel_detail_default_render_does_not_call_export(monkeypatch, tmp_path: Path) -> None:
    latest_dir = tmp_path / "latest"
    latest_dir.mkdir()
    report_path = latest_dir / "daily_report_sales_20260612_v2.xlsx"
    report_path.write_bytes(b"existing workbook bytes")
    before_mtime = report_path.stat().st_mtime_ns
    fake_st = FakeStreamlit()

    def fail_export(*_: object, **__: object) -> tuple[bytes, str]:
        raise AssertionError("Excel export must be behind an explicit button action")

    monkeypatch.setattr(app, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(app, "build_excel_report_bytes", fail_export)

    app._render_excel_detail_page(_excel_context())

    assert fake_st.button_labels == ["최신 리포트 재생성"]
    assert fake_st.downloads == ["기존 Excel 리포트 다운로드"]
    assert report_path.stat().st_mtime_ns == before_mtime


def test_excel_export_call_is_inside_explicit_button_condition() -> None:
    source = inspect.getsource(app._render_excel_detail_page)

    button_index = source.index('"최신 리포트 재생성"')
    export_index = source.index("build_excel_report_bytes(")

    assert "읽기 전용" in source
    assert button_index < export_index


def test_history_default_render_does_not_touch_saved_actuals(monkeypatch, tmp_path: Path) -> None:
    saved_path = tmp_path / "saved_actuals.csv"
    saved_path.write_text("date,business_day_no,sales_actual_cum\n2026-06-10,8,88.8\n", encoding="utf-8")
    before_stat = saved_path.stat()
    fake_st = FakeStreamlit()

    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(
        app,
        "_load_history_tables_for_ui",
        lambda: {
            "forecast_history": pd.DataFrame(columns=history_schema.FORECAST_HISTORY_COLUMNS),
            "final_actuals": pd.DataFrame(columns=history_schema.FINAL_ACTUALS_COLUMNS),
        },
    )

    app._render_forecast_history_backtest_tab(pd.DataFrame(), "sales", "2026-06-12")

    after_stat = saved_path.stat()
    assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
    assert after_stat.st_size == before_stat.st_size


def test_audit_page_default_render_does_not_touch_saved_actuals(monkeypatch, tmp_path: Path) -> None:
    saved_path = tmp_path / "saved_actuals.csv"
    saved_path.write_text("date,business_day_no,sales_actual_cum\n2026-06-10,8,88.8\n", encoding="utf-8")
    before_stat = saved_path.stat()
    fake_st = FakeStreamlit()

    monkeypatch.setattr(app, "st", fake_st)

    app._render_audit_detail_page({"validation_result": {"errors": [], "warnings": []}})

    after_stat = saved_path.stat()
    assert after_stat.st_mtime_ns == before_stat.st_mtime_ns
    assert after_stat.st_size == before_stat.st_size


def test_audit_readonly_mode_keeps_write_helpers_behind_disabled_buttons() -> None:
    input_source = inspect.getsource(app._render_input_editor)
    history_source = inspect.getsource(app._render_forecast_history_backtest_tab)
    excel_source = inspect.getsource(app._render_excel_detail_page)

    assert "audit_readonly" in input_source
    assert "완료월 실제 실적 저장" in input_source
    assert "disabled=audit_readonly" in input_source
    assert input_source.index('"완료월 실제 실적 저장"') < input_source.index(
        "save_current_input_defaults("
    )
    assert "disabled=audit_readonly" in history_source
    assert "disabled=audit_readonly" in excel_source


def test_app_keeps_same_window_navigation_without_external_targets() -> None:
    source = Path("app.py").read_text(encoding="utf-8")

    assert 'target="_blank"' not in source
    assert "window.open" not in source
