import inspect
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
    assert input_source.index('"완료월 실제 실적 저장"') < input_source.index("save_actual_values(")
    assert "disabled=audit_readonly" in history_source
    assert "disabled=audit_readonly" in excel_source


def test_app_keeps_same_window_navigation_without_external_targets() -> None:
    source = Path("app.py").read_text(encoding="utf-8")

    assert 'target="_blank"' not in source
    assert "window.open" not in source
