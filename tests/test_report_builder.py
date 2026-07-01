from datetime import date

import pandas as pd

from src.report_builder import build_daily_report_text, build_model_error_summary_text


def _scenario_df(status: str = "OK") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "scenario_id": "F1_P1",
                "forecast_model": "F1_CUMULATIVE_RATE",
                "provision_strategy": "P1_ALL_REMAINING",
                "metric": "sales",
                "as_of_date": date(2026, 6, 10),
                "current_actual_cum": 70.5,
                "remaining_target": 29.5,
                "forecast_amount": 95.0,
                "forecast_rate": 0.95,
                "required_uplift": 5.0,
                "forecast_after_provision": 100.0,
                "gap_after_provision": 0.0,
                "next_close_date": date(2026, 6, 11),
                "next_close_required": 16.7,
                "risk_level": "Yellow",
                "status": status,
                "comment": "",
            },
            {
                "scenario_id": "F2_P1",
                "forecast_model": "F2_LAST_TWO_CLOSES",
                "provision_strategy": "P1_ALL_REMAINING",
                "metric": "sales",
                "as_of_date": date(2026, 6, 10),
                "current_actual_cum": 70.5,
                "remaining_target": 29.5,
                "forecast_amount": 92.0,
                "forecast_rate": 0.92,
                "required_uplift": 8.0,
                "forecast_after_provision": 100.0,
                "gap_after_provision": 0.0,
                "next_close_date": date(2026, 6, 11),
                "next_close_required": 16.7,
                "risk_level": "Red",
                "status": "OK",
                "comment": "",
            },
            {
                "scenario_id": "F3_P1",
                "forecast_model": "F3_DAY_CLOSE_WEIGHTED",
                "provision_strategy": "P1_ALL_REMAINING",
                "metric": "sales",
                "as_of_date": date(2026, 6, 10),
                "current_actual_cum": 70.5,
                "remaining_target": 29.5,
                "forecast_amount": 103.0,
                "forecast_rate": 1.03,
                "required_uplift": 0.0,
                "forecast_after_provision": 103.0,
                "gap_after_provision": 0.0,
                "next_close_date": date(2026, 6, 11),
                "next_close_required": 16.7,
                "risk_level": "Green",
                "status": "NO_GAP",
                "comment": "",
            },
        ]
    )


def _next_close_result() -> dict[str, object]:
    return {
        "next_close_date": date(2026, 6, 11),
        "required_to_recover_next_close_cum": 16.7,
    }


def _overachievement_scenario_df() -> pd.DataFrame:
    base = {
        "forecast_model": "F1_CUMULATIVE_RATE",
        "metric": "sales",
        "as_of_date": date(2026, 6, 10),
        "monthly_target": 100.0,
        "current_actual_cum": 82.0,
        "remaining_target": 30.0,
        "forecast_amount": 112.0,
        "forecast_rate": 1.12,
        "target_status": "OVER_TARGET",
        "target_variance": 12.0,
        "surplus_to_target": 12.0,
        "gap_to_target": 0.0,
        "required_uplift": 0.0,
        "forecast_after_provision": 112.0,
        "gap_after_provision": 0.0,
        "next_close_date": date(2026, 6, 11),
        "next_close_required": 16.7,
        "risk_level": "Green",
        "status": "OVER_TARGET_MANAGED",
        "strategy_type": "OVERACHIEVEMENT",
        "comment": "",
    }
    rows = []
    for scenario_id, strategy, stretch, revised, buffer, minimum, relief in [
        ("F1_O1", "O1_TARGET_HOLD_BUFFER", 0.0, 100.0, 12.0, 0.0, 0.0),
        ("F1_O2", "O2_STRETCH_TARGET_CAPTURE", 6.0, 106.0, 6.0, 0.0, 0.0),
        ("F1_O3", "O3_QUALITY_GUARD_RELIEF", 0.0, 100.0, 12.0, 18.0, 12.0),
    ]:
        row = dict(base)
        row.update(
            {
                "scenario_id": scenario_id,
                "provision_strategy": strategy,
                "overachievement_strategy": strategy,
                "stretch_uplift": stretch,
                "revised_monthly_target": revised,
                "remaining_surplus_buffer": buffer,
                "minimum_remaining_to_hit_target": minimum,
                "relief_amount": relief,
                "recommended_action": "취소, 철회, 미결제, 계약 품질 방어",
            }
        )
        rows.append(row)
    return pd.DataFrame(rows)


def test_build_daily_report_text_returns_string() -> None:
    report = build_daily_report_text(_scenario_df(), _next_close_result())

    assert isinstance(report, str)


def test_report_uses_line_breaks_by_content_section() -> None:
    report = build_daily_report_text(
        _scenario_df(),
        _next_close_result(),
        selected_scenario_id="F1_P1",
    )

    assert "[기준 현황]\n\n-" in report
    assert "\n\n[선택 시나리오]\n\n-" in report
    assert "\n\n[추천 운영전략]\n\n-" in report
    assert "\n\n[리스크 관리]\n\n-" in report
    assert "\n\n[다음 액션]\n\n-" in report
    assert "[용어 정의 - 고정 용어집]" not in report


def test_report_includes_f1_f2_f3_model_names() -> None:
    report = build_daily_report_text(_scenario_df(), _next_close_result())

    assert "F1" in report
    assert "F2" in report
    assert "F3" in report
    assert "판매실적 누적 실적" in report
    assert "매출 누적 실적" not in report


def test_report_includes_next_close_date_and_required_amount() -> None:
    report = build_daily_report_text(_scenario_df(), _next_close_result())

    assert "2026-06-11" in report
    assert "다음 마감 누적선 필요실적" in report
    assert "16.7억" in report


def test_report_includes_selected_scenario_phrase() -> None:
    report = build_daily_report_text(
        _scenario_df(),
        _next_close_result(),
        selected_scenario_id="F1_P1",
    )

    assert "선택 시나리오 F1_P1" in report
    assert "F1 + P1 잔여목표 균등 배분 조합" in report
    assert "F1=누적 달성률 모델" not in report
    assert "P1=전체 잔여일 배분" not in report
    assert "필요한 상향 배분" in report
    assert "전략 반영 후 예상" in report
    assert "전략 반영 후 부족분" in report
    assert "required_uplift" not in report
    assert "forecast_after_provision" not in report
    assert "gap_after_provision" not in report


def test_report_excludes_fixed_glossary_terms_from_body() -> None:
    report = build_daily_report_text(_scenario_df(), _next_close_result())

    assert "용어 정의 - 고정 용어집" not in report
    assert "고정 안내" not in report
    assert "■ 예측모델(F)" not in report
    assert "F1=누적 달성률 모델" not in report
    assert "P1=전체 잔여일 배분" not in report
    assert "Green=예상 달성률이 100% 이상" not in report


def test_report_includes_capacity_limited_warning_phrase() -> None:
    report = build_daily_report_text(
        _scenario_df(status="CAPACITY_LIMITED"),
        _next_close_result(),
        selected_scenario_id="F1_P1",
    )

    assert "배분 한도 초과" in report
    assert "CAPACITY_LIMITED" not in report
    assert "목표 달성이 불확실" in report


def test_report_explains_not_applicable_scenario() -> None:
    scenarios = _scenario_df()
    scenarios.loc[0, "status"] = "NOT_APPLICABLE"
    scenarios.loc[0, "provision_strategy"] = "P2_CLOSE_DAY_FOCUSED"

    report = build_daily_report_text(scenarios, _next_close_result())

    assert "적용 불가 시나리오(F1_P1)" in report
    assert "마감일로 표시된 잔여 입력일" in report
    assert "NOT_APPLICABLE" not in report
    assert "is_close_day=True" not in report


def test_report_includes_overachievement_strategy_language() -> None:
    report = build_daily_report_text(
        _overachievement_scenario_df(),
        _next_close_result(),
        selected_scenario_id="F1_O2",
    )

    assert "목표 초과 예상" in report
    assert "목표 상태는 초과달성 관리" in report
    assert "목표 대비 차이는 12.0억 원" in report
    assert "초과 예상분은 12.0억 원" in report
    assert "선택 전략은 O2 Stretch 전환" in report
    assert "O2 Stretch 전환분은 6.0억 원" in report
    assert "운영전략 월 목표는 106.0억 원" in report
    assert "보조 전략: O1 버퍼 유지; O3 품질 방어" in report
    assert "O1 목표 유지 안전버퍼" in report
    assert "O2 상향 목표 전환" in report
    assert "O3 계약 품질 방어" in report
    assert "취소" in report
    assert "철회" in report
    assert "미결제" in report
    assert "계약 품질" in report
    assert "NO_GAP" not in report
    assert "target_status" not in report
    assert "O1_TARGET_HOLD_BUFFER" not in report
    assert "Stretch Target" not in report


def test_report_optionally_includes_model_error_summary() -> None:
    backtest_summary = pd.DataFrame(
        {
            "forecast_model": ["F1", "F2", "F3"],
            "sample_count": [2, 2, 2],
            "error_rate": [0.08, 0.04, 0.06],
            "bias": [1.0, -0.5, 0.2],
        }
    )

    report = build_daily_report_text(
        _scenario_df(),
        _next_close_result(),
        backtest_summary_df=backtest_summary,
    )

    assert "[모델 오차율 요약]\n\n-" in report
    assert "최저 오차 모델은 F2" in report
    assert "오차율 4.0%" in report


def test_model_error_summary_is_blank_without_backtest_data() -> None:
    assert build_model_error_summary_text(pd.DataFrame()) == ""


def test_report_does_not_duplicate_sentence_endings() -> None:
    scenarios = _overachievement_scenario_df()
    scenarios.loc[
        scenarios["scenario_id"] == "F1_O2",
        "recommended_action",
    ] = "초과달성 품질을 관리합니다."

    report = build_daily_report_text(
        scenarios,
        _next_close_result(),
        selected_scenario_id="F1_O2",
    )

    assert "권장 조치는 초과달성 품질을 관리합니다." in report
    assert "입니다.입니다" not in report
    assert "합니다.입니다" not in report
    assert "관리합니다.입니다" not in report
