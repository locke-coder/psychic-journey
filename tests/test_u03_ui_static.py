from pathlib import Path


APP_SOURCE = Path("app.py").read_text(encoding="utf-8")
VIS_SOURCE = Path("src/visualization_builder.py").read_text(encoding="utf-8")
COMBINED_SOURCE = APP_SOURCE + "\n" + VIS_SOURCE


def test_u03_a1_required_home_projection_terms_exist() -> None:
    required_terms = (
        "달성 추이 및 월말 예측 구간",
        "예상 도착 구간",
        "현재 위치",
        "다음 마감",
        "오늘의 마감 보드",
        "다음 마감 누적선 필요실적",
        "현재까지 확정 실적",
        "향후 예측 중심선",
    )

    for term in required_terms:
        assert term in COMBINED_SOURCE


def test_u03_a1_3_visual_system_terms_exist() -> None:
    required_terms = (
        "--font-sans",
        '-apple-system, BlinkMacSystemFont, "Segoe UI", "Apple SD Gothic Neo", "Malgun Gothic", "Noto Sans KR", sans-serif',
        "--font-app-title: 16px",
        "--font-page-title: 20px",
        "--font-section-title: 16px",
        "--font-card-title: 14px",
        "--font-caption: 12px",
        "--font-overline: 11px",
        "--font-metric-value: 17px",
        "word-break: keep-all",
        "overflow-wrap: anywhere",
        ".text-truncate",
        ".line-clamp-2",
        "minmax(0, 1fr) minmax(300px, 340px)",
    )

    for term in required_terms:
        assert term in APP_SOURCE


def test_u03_a1_3_report_and_history_ia_terms_exist() -> None:
    required_terms = (
        "판단 메모 · 내부 검토용",
        "복사용 보고문 · 공유용",
        "예측 이력은 과거 완료월",
        "완료월 비교",
        "같은 영업일차 Benchmark",
        "Backtest Summary",
        "ModelWeights",
        "ConfidenceBand",
        "Insights",
        "완료월 데이터가 쌓이면 예측 이력과 모델 신뢰도 비교가 표시됩니다.",
        "월마감 후 실제 실적을 저장하면 다음 달부터 비교 기준으로 사용할 수 있습니다.",
    )

    for term in required_terms:
        assert term in APP_SOURCE


def test_u03_a1_strategy_and_output_guidance_terms_are_preserved() -> None:
    required_terms = (
        "P1_ALL_REMAINING",
        "P2_CLOSE_DAY_FOCUSED",
        "P3_NON_CLOSE_DAY_FOCUSED",
        "O1 버퍼 유지",
        "O2 Stretch 전환",
        "O3 품질 방어",
        "O1_TARGET_HOLD_BUFFER",
        "O2_STRETCH_TARGET_CAPTURE",
        "O3_QUALITY_GUARD_RELIEF",
        "읽기 전용",
        "next action",
        "다음 액션",
        "outputs/latest",
        "archive_invalid",
        "현재 관리 대상",
        "strategy-card-active",
        "고정 O전략 차이 요약",
        "F예측 × O전략 전체 매트릭스",
        "O전략은 월말 예상 실적을 새로 예측하지 않습니다",
    )

    for term in required_terms:
        assert term in COMBINED_SOURCE


def test_u03_a1_5_audit_readonly_terms_exist() -> None:
    required_terms = (
        "audit_readonly",
        "AUDIT_READONLY_QUERY_PARAM",
        "읽기 전용 감리 모드",
        "완료월 실제 실적 저장",
        "disabled=audit_readonly",
        "persist_uploaded_defaults=False",
    )

    for term in required_terms:
        assert term in APP_SOURCE


def test_u03_a1_required_builder_functions_exist() -> None:
    assert "build_projection_band_data" in VIS_SOURCE
    assert "build_pace_projection_chart_data" in VIS_SOURCE
    assert "build_close_day_markers" in VIS_SOURCE


def test_u03_a1_retired_ui_terms_and_external_links_are_absent() -> None:
    forbidden_terms = (
        "Control" + " Room",
        "관" + "제실",
        "purple" + " SaaS",
        "@import" + " url(",
        "https" + "://",
        "http" + "://",
        "네비게이션 접기",
    )

    for term in forbidden_terms:
        assert term not in COMBINED_SOURCE


def test_u03_a1_6_visual_polish_terms_exist() -> None:
    required_terms = (
        "--line-body: 1.62",
        "--line-card: 1.56",
        "padding-top: 2.35rem",
        "overflow-wrap: anywhere",
        "word-break: keep-all",
        "F1/F2/F3 mini chart data rows",
        "누적 목표선",
        "누적 실적",
        "누적 달성률",
        "build_forecast_model_mini_chart_source",
        "build_close_cycle_cumulative_source",
        "build_strategy_arrival_compare_source",
    )

    for term in required_terms:
        assert term in COMBINED_SOURCE


def test_u03_a1_strategy_management_highlight_is_subtle() -> None:
    required_terms = (
        "is-recommended-badge",
        "border-top: 3px solid rgba(20, 117, 111, 0.55)",
        ".strategy-section .status-badge",
        "box-shadow: none !important",
    )
    forbidden_terms = (
        "권장 · 현재 관리 대상",
        "border-left: 5px solid var(--teal) !important",
    )

    for term in required_terms:
        assert term in APP_SOURCE

    for term in forbidden_terms:
        assert term not in APP_SOURCE


def test_u03_a1_page_header_padding_is_preserved_after_final_overrides() -> None:
    assert "padding: 14px 16px 15px !important" in APP_SOURCE
    assert ".page-header > *:first-child" in APP_SOURCE
    assert ".page-header,\n        .page-header-compact {\n            margin: 0 0 10px !important;\n            padding: 0 !important;" not in APP_SOURCE


def test_u03_a1_operation_mode_card_is_compact_and_status_colored() -> None:
    for required in (
        "grid-template-columns: minmax(0, 1fr) minmax(260px, 0.86fr);",
        ".pace-mode-card.status-over-target",
        "border-left-color: #2d8b67;",
        "font-size: 24px !important;",
        "padding: 12px 14px !important;",
    ):
        assert required in APP_SOURCE


def test_u03_a1_kpi_grid_uses_single_row_for_seven_cards() -> None:
    for required in (
        "grid-template-columns: repeat(7, minmax(0, 1fr)) !important;",
        "gap: 8px !important;",
        "padding: 10px 11px !important;",
    ):
        assert required in APP_SOURCE


def test_u03_a1_home_chart_and_decision_panel_layout_is_aligned() -> None:
    for required in (
        ".workbench-shell.top-status-bar",
        "margin: 0 0 16px !important;",
        "align-items: stretch !important;",
        "margin-top: 14px !important;",
        "background: var(--chart-bg) !important;",
        "grid-template-columns: 96px minmax(0, 1fr);",
        ".decision-panel__row:last-child",
    ):
        assert required in APP_SOURCE


def test_u03_a1_streamlit_metric_cards_keep_equal_height() -> None:
    for required in (
        'height: 100px !important;',
        'min-height: 100px !important;',
        'display: flex !important;',
        'flex-direction: column !important;',
        'justify-content: flex-start !important;',
        '[data-testid="stMetric"] > div',
        '[data-testid="stMetricDelta"]',
        'margin-top: 6px !important;',
    ):
        assert required in APP_SOURCE

    metric_block = APP_SOURCE.split('[data-testid="stMetric"] {\n', 2)[2].split("\n        }", 1)[0]
    assert "height: auto" not in metric_block


def test_u03_a1_projection_chart_uses_card_colored_background() -> None:
    for required in (
        '--chart-bg: #f7f9fb;',
        '.properties(height=320, background="#f7f9fb")',
        '.configure(background="#f7f9fb")',
        '.configure_view(strokeWidth=0, fill="#f7f9fb")',
        'div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) .projection-chart-card',
        'div[data-testid="stVerticalBlockBorderWrapper"]:has(.projection-chart-card__head) details',
    ):
        assert required in APP_SOURCE


def test_u03_a1_scenario_inline_title_does_not_overlap_info_box() -> None:
    for required in (
        'div[data-testid="stMarkdownContainer"]:has(.scenario-inline-chart-title)',
        "margin: 10px 0 12px !important;",
        "min-height: 28px;",
        "padding: 0 0 4px;",
        'div[data-testid="stAlert"]',
        "clear: both;",
    ):
        assert required in APP_SOURCE


def test_u03_a1_no_close_day_inference_terms_are_added_to_app_or_builder() -> None:
    forbidden_terms = (
        "week" + "day",
        "WEEK" + "DAY",
        "dt." + "week" + "day",
        "date." + "week" + "day",
        "next_" + "monday",
        "next_" + "thursday",
        "day_name " + "==",
        "day_name " + "in",
        "월" + "요일",
        "목" + "요일",
    )

    for term in forbidden_terms:
        assert term not in COMBINED_SOURCE
