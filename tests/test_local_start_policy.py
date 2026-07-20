from pathlib import Path


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "tools" / "start_streamlit_server.ps1"
)
RUNBOOK_PATH = Path(__file__).resolve().parents[1] / "docs" / "local_preview_runbook.md"


def test_local_start_defaults_to_loopback_demo_mode() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert '[string]$Address = "127.0.0.1"' in source
    assert '[ValidateSet("private", "local_demo")]' in source
    assert '[string]$DataMode = "local_demo"' in source
    assert '$env:PRIVATE_DATA_MODE = $DataMode' in source
    assert '[switch]$UseSavedLocalData' in source
    assert '$env:LOCAL_DEMO_FRESH_START' in source


def test_local_demo_mode_is_rejected_for_non_loopback_addresses() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert '$LoopbackAddresses = @("127.0.0.1", "localhost", "::1")' in source
    assert 'if ($DataMode -eq "local_demo" -and -not $IsLoopback)' in source
    assert "local_demo mode is restricted to a loopback address" in source


def test_shared_start_still_requires_access_control_configuration() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "if (-not $IsLoopback" in source
    assert "$env:APP_ACCESS_PASSWORD" in source
    assert "$env:APP_ACCESS_PASSWORD_SHA256" in source


def test_local_preview_runbook_documents_safe_modes() -> None:
    source = RUNBOOK_PATH.read_text(encoding="utf-8")

    assert "start_streamlit_server.ps1" in source
    assert "PRIVATE_DATA_MODE=local_demo" in source
    assert "-DataMode private" in source
    assert "-UseSavedLocalData" in source
    assert "is_close_day" in source
