from pathlib import Path

from src.ui_styles import get_linear_bento_css


def test_pace_bar_sticks_by_its_streamlit_container() -> None:
    css = get_linear_bento_css()

    assert 'div[data-testid="stElementContainer"]:has(.same-window-top-status)' in css
    assert "position: sticky !important;" in css
    assert ".same-window-top-status {\n        position: relative !important;" in css


def test_deploy_header_hides_on_scroll_and_returns_at_top_hover_zone() -> None:
    css = get_linear_bento_css()
    app_source = Path("app.py").read_text(encoding="utf-8")

    assert "scroll-timeline-name: --pace-main-scroll;" in css
    assert "@keyframes deploy-header-auto-hide" in css
    assert "animation-duration: auto;" in css
    assert "animation-range: 0 72px;" in css
    assert ".stApp:has(.deploy-hover-zone:hover)" in css
    assert 'background: #f6f7f9 !important;' in css
    assert 'opacity: 1 !important;' in css
    assert 'class="deploy-hover-zone"' in app_source
