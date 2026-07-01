from src.ui_components import (
    operation_mode_description,
    render_kpi_card,
    render_report_card,
    scenario_display_name,
    scenario_is_emphasis,
    status_label,
)
from src.ui_styles import get_global_styles


def test_status_label_maps_target_status_to_business_copy() -> None:
    assert status_label("UNDER_TARGET") == "목표 보정 필요"
    assert status_label("ON_TARGET") == "유지/모니터링"
    assert status_label("OVER_TARGET") == "초과달성 관리"


def test_scenario_display_name_maps_core_strategies() -> None:
    assert scenario_display_name("O1_TARGET_HOLD_BUFFER") == "버퍼 유지"
    assert scenario_display_name("O2_STRETCH_TARGET_CAPTURE") == "Stretch 전환"
    assert scenario_display_name("O3_QUALITY_GUARD_RELIEF") == "품질 방어"
    assert scenario_display_name("P1_ALL_REMAINING") == "잔여목표 균등 배분"
    assert scenario_display_name("P2_CLOSE_DAY_FOCUSED") == "마감일 집중 보정"
    assert scenario_display_name("P3_NON_CLOSE_DAY_FOCUSED") == "비마감일 분산 보정"


def test_scenario_emphasis_only_applies_to_overachievement_strategies() -> None:
    assert scenario_is_emphasis("O1_TARGET_HOLD_BUFFER") is True
    assert scenario_is_emphasis("O2_STRETCH_TARGET_CAPTURE") is True
    assert scenario_is_emphasis("O3_QUALITY_GUARD_RELIEF") is True
    assert scenario_is_emphasis("P1_ALL_REMAINING") is False


def test_scenario_display_name_uses_safe_fallback_for_unknown_id() -> None:
    assert scenario_display_name("CUSTOM_STRATEGY") == "CUSTOM_STRATEGY"


def test_operation_mode_description_uses_status_specific_language() -> None:
    assert any(
        token in operation_mode_description("OVER_TARGET")
        for token in ("초과분", "버퍼")
    )
    assert "보정" in operation_mode_description("UNDER_TARGET")


def test_render_report_card_escapes_report_text() -> None:
    html = render_report_card("<script>alert('x')</script>")

    assert "&lt;script&gt;" in html
    assert "<script>" not in html


def test_render_report_card_formats_sections_as_report_blocks() -> None:
    html = render_report_card(
        "[기준 현황]\n\n- F1 기준은 157.0억 원입니다.\n\n"
        "[선택 시나리오]\n\n- F1_O1을 선택했습니다."
    )

    assert "<pre" not in html
    assert 'class="report-card__section-title">기준 현황</h3>' in html
    assert 'class="report-card__section-title">선택 시나리오</h3>' in html
    assert "<li>F1 기준은 157.0억 원입니다.</li>" in html
    assert "[기준 현황]" not in html


def test_render_kpi_card_keeps_placeholder_text_safe() -> None:
    html = render_kpi_card("월마감 예상 실적", "입력 후 계산됩니다", sub="계산 전")

    assert "kpi-card" in html
    assert "입력 후 계산됩니다" in html
    assert "계산 전" in html


def test_global_styles_expose_required_status_tokens() -> None:
    css = get_global_styles()

    for token in (
        "--status-under",
        "--status-on",
        "--status-over",
        "--surface-card",
        "--surface-hero",
        "--line-soft",
        "--text-main",
        "--text-muted",
        "forecast-strategy-board",
        "unified-decision-strip",
        "unified-model-grid",
        "unified-scenario-panel",
        "unified-detail-expander",
        "strategy-recommendation-pulse",
    ):
        assert token in css
