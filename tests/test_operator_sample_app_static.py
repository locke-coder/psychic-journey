from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_app_contains_operator_sample_management_ui_text() -> None:
    app_source = (REPO_ROOT / "app.py").read_text(encoding="utf-8")

    assert "운영 샘플 관리" in app_source
    assert "운영 기본값으로 저장" in app_source
    assert "내장 샘플로 화면 초기화" in app_source
    assert "저장된 운영 기본값 다시 불러오기" in app_source


def test_app_wires_current_and_historical_operator_sample_save_paths() -> None:
    app_source = (REPO_ROOT / "app.py").read_text(encoding="utf-8")

    assert "save_operator_sample" in app_source
    assert '"current_input"' in app_source
    assert '"historical_input"' in app_source


def test_source_has_no_close_day_auto_inference_patterns() -> None:
    patterns = [
        "weekday",
        "WEEKDAY",
        "dt.weekday",
        "date.weekday",
        "next_monday",
        "next_thursday",
        "day_name ==",
        "day_name in",
        "월요일",
        "목요일",
    ]
    source_paths = [REPO_ROOT / "app.py", *sorted((REPO_ROOT / "src").glob("*.py"))]
    hits: list[str] = []
    for path in source_paths:
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            if pattern in text:
                hits.append(f"{path.relative_to(REPO_ROOT).as_posix()}: {pattern}")

    assert hits == []
