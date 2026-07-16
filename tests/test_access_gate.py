import hashlib
import ast
from pathlib import Path

from app import _is_local_url, verify_access_password


APP_SOURCE = Path("app.py").read_text(encoding="utf-8")


def _function_source(function_name: str) -> str:
    module = ast.parse(APP_SOURCE)
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == function_name:
            source = ast.get_source_segment(APP_SOURCE, node)
            assert source is not None
            return source
    raise AssertionError(f"{function_name} not found")


def test_main_requires_access_password_before_loading_app_data() -> None:
    main_source = _function_source("main")

    assert "if not _require_access_password():" in main_source
    assert main_source.index("_require_access_password()") < main_source.index(
        "base_config = load_model_config()"
    )


def test_local_preview_urls_bypass_the_external_access_gate() -> None:
    assert _is_local_url("http://localhost:8501/")
    assert _is_local_url("http://127.0.0.1:8501/?page=home")
    assert _is_local_url("http://[::1]:8501/")


def test_shared_urls_keep_the_external_access_gate() -> None:
    assert not _is_local_url("https://sales-forecast.example.com/")
    assert not _is_local_url("https://127.0.0.1.example.com/")
    assert not _is_local_url("")


def test_verify_access_password_accepts_plain_configured_password() -> None:
    assert verify_access_password(
        "invite-only",
        configured_password="invite-only",
    )


def test_verify_access_password_rejects_wrong_plain_password() -> None:
    assert not verify_access_password(
        "wrong-password",
        configured_password="invite-only",
    )


def test_verify_access_password_accepts_sha256_configured_password_hash() -> None:
    digest = hashlib.sha256("invite-only".encode("utf-8")).hexdigest()

    assert verify_access_password(
        "invite-only",
        configured_password_hash=digest,
    )


def test_verify_access_password_requires_configured_credentials() -> None:
    assert not verify_access_password("invite-only")
