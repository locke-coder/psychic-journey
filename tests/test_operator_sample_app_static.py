from __future__ import annotations

import ast
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


def test_operator_sample_private_store_errors_are_rendered_without_page_failure() -> None:
    app_source = (REPO_ROOT / "app.py").read_text(encoding="utf-8")

    assert "_try_save_operator_sample_for_ui" in app_source
    assert "except PrivateDataStoreError as exc:" in app_source
    assert "_render_operator_sample_store_error" in app_source
    assert "Contents: Read and write" in app_source


def test_rate_limit_error_import_tolerates_streamlit_deploy_cache_skew() -> None:
    app_source = (REPO_ROOT / "app.py").read_text(encoding="utf-8")
    module = ast.parse(app_source)
    private_store_imports = {
        alias.name
        for node in module.body
        if isinstance(node, ast.ImportFrom) and node.module == "src.private_data_store"
        for alias in node.names
    }

    assert "PrivateDataStoreRateLimitError" not in private_store_imports
    assert 'exc.__class__.__name__ == "PrivateDataStoreRateLimitError"' in app_source


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
