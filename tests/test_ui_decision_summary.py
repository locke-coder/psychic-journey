from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from app import build_visual_decision_summary, build_visual_headline
from src import ui_decision_summary as decision_summary_module


POSITIVE_NEXT_CLOSE = {
    "next_close_date": "2026-06-15",
    "required_to_recover_next_close_cum": 6.0,
}
POSITIVE_NEXT_CLOSE_SENTENCE = (
    "2026-06-15까지 누적 기준으로 최소 6.0억 원을 더 확보해야 합니다."
)


def _headline_prefix(kind: str, amount: str | None = None) -> str:
    if kind == "under":
        return (
            f"결론: 목표선보다 {amount}억 원 부족할 가능성이 큽니다. "
            "먼저 전략 반영 후 예상이 공식 월 목표선까지 회복되는지 보고, "
            "그다음 잔여 일자별 추가 배분이 감당 가능한지 확인하세요. "
        )
    if kind == "over":
        return (
            f"결론: 목표선보다 {amount}억 원 여유가 예상됩니다. "
            "초과분을 안전버퍼로 남길지, Stretch 목표로 전환할지 차트에서 확인하세요. "
        )
    if kind == "neutral":
        return (
            "결론: 목표선 근처의 유지/모니터링 구간입니다. "
            "시각화에서는 예측모델별 흔들림과 다음 마감 누적선을 함께 확인하세요. "
        )
    raise AssertionError(f"unexpected headline kind: {kind}")


@pytest.mark.parametrize(
    (
        "target_status",
        "target_variance",
        "gap_to_target",
        "surplus_to_target",
        "expected_kind",
        "expected_amount",
    ),
    [
        pytest.param("UNDER_TARGET", -8.0, 99.0, 0.0, "under", "8.0", id="under-consistent"),
        pytest.param("OVER_TARGET", 8.0, 0.0, 7.5, "over", "7.5", id="over-consistent"),
        pytest.param("ON_TARGET", 0.0, 0.0, 0.0, "neutral", None, id="on-zero"),
        pytest.param(
            "UNKNOWN_TARGET_STATUS",
            None,
            None,
            None,
            "neutral",
            None,
            id="unknown-missing",
        ),
        pytest.param(
            "OVER_TARGET",
            -8.0,
            8.0,
            7.5,
            "under",
            "8.0",
            id="negative-variance-precedes-over-status",
        ),
        pytest.param(
            "UNDER_TARGET",
            8.0,
            0.0,
            7.5,
            "under",
            "8.0",
            id="under-status-precedes-positive-variance",
        ),
        pytest.param(
            "ON_TARGET",
            8.0,
            0.0,
            7.5,
            "over",
            "7.5",
            id="positive-variance-overrides-on-status",
        ),
        pytest.param(
            "UNDER_TARGET",
            None,
            5.0,
            0.0,
            "under",
            "5.0",
            id="under-gap-fallback",
        ),
        pytest.param(
            "OVER_TARGET",
            8.0,
            0.0,
            0.0,
            "over",
            "8.0",
            id="over-variance-fallback",
        ),
        pytest.param(
            "UNKNOWN_TARGET_STATUS",
            -4.0,
            4.0,
            0.0,
            "under",
            "4.0",
            id="negative-variance-overrides-unknown-status",
        ),
    ],
)
def test_visual_headline_preserves_status_variance_precedence_and_fallbacks(
    target_status: str,
    target_variance: object,
    gap_to_target: object,
    surplus_to_target: object,
    expected_kind: str,
    expected_amount: str | None,
) -> None:
    selected_row = pd.Series(
        {
            "target_status": target_status,
            "target_variance": target_variance,
            "gap_to_target": gap_to_target,
            "surplus_to_target": surplus_to_target,
        },
        dtype=object,
    )

    result = build_visual_headline(selected_row, {}, POSITIVE_NEXT_CLOSE)

    assert result == (
        _headline_prefix(expected_kind, expected_amount) + POSITIVE_NEXT_CLOSE_SENTENCE
    )


def test_visual_headline_preserves_unused_validation_result_compatibility() -> None:
    selected_row = pd.Series(
        {
            "target_status": "ON_TARGET",
            "target_variance": 0.0,
            "gap_to_target": 0.0,
            "surplus_to_target": 0.0,
        },
        dtype=object,
    )

    empty_validation = build_visual_headline(selected_row, {}, POSITIVE_NEXT_CLOSE)
    populated_validation = build_visual_headline(
        selected_row,
        {"monthly_target": 999.0, "errors": ["ignored"]},
        POSITIVE_NEXT_CLOSE,
    )

    assert populated_validation == empty_validation


@pytest.mark.parametrize(
    ("target_status", "operation_mode", "expected"),
    [
        (
            "UNDER_TARGET",
            "목표 보정 필요",
            "목표 보정 필요 상태입니다. 시나리오별 예상 탭에서 어떤 F/P 조합이 부족분을 줄이는지 보세요.",
        ),
        (
            "ON_TARGET",
            "유지/모니터링",
            "유지/모니터링 상태입니다. 목표선은 맞지만 마감차수 흐름이 흔들리는지 함께 확인하세요.",
        ),
        (
            "OVER_TARGET",
            "초과달성 관리",
            "초과달성 관리 상태입니다. 초과분을 버퍼로 둘지, 상향 목표로 전환할지 전략 수준 탭에서 보세요.",
        ),
        (
            "UNKNOWN_TARGET_STATUS",
            "계산 불가",
            "목표 판정에 필요한 값이 부족합니다. 입력값 점검 결과를 먼저 확인하세요.",
        ),
        (
            None,
            "계산 불가",
            "목표 판정에 필요한 값이 부족합니다. 입력값 점검 결과를 먼저 확인하세요.",
        ),
    ],
)
def test_visual_status_sentence_preserves_exact_branch_wording(
    target_status: object,
    operation_mode: object,
    expected: str,
) -> None:
    assert decision_summary_module._visual_status_sentence(target_status, operation_mode) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (-8.0, "월말 기준 8.0억 원를 더 채워야 목표선에 도달합니다."),
        (0.0, "월말 예상이 공식 월 목표와 거의 같습니다. 남은 기간의 변동 리스크를 봅니다."),
        (8.0, "월말 기준 8.0억 원가 목표선 위에 있어 버퍼 또는 Stretch 후보입니다."),
        (
            None,
            "목표 대비 차이를 계산할 수 없습니다. 선택 시나리오 상세 값을 확인하세요.",
        ),
        (
            "bad",
            "목표 대비 차이를 계산할 수 없습니다. 선택 시나리오 상세 값을 확인하세요.",
        ),
        (
            float("inf"),
            "목표 대비 차이를 계산할 수 없습니다. 선택 시나리오 상세 값을 확인하세요.",
        ),
    ],
)
def test_visual_variance_sentence_preserves_sign_missing_and_current_particles(
    value: object,
    expected: str,
) -> None:
    assert decision_summary_module._visual_variance_sentence(value) == expected


@pytest.mark.parametrize(
    ("next_close_result", "expected"),
    [
        (
            {"next_close_date": "2026-06-15", "required_to_recover_next_close_cum": 6.0},
            POSITIVE_NEXT_CLOSE_SENTENCE,
        ),
        (
            {"next_close_date": "2026-06-15", "required_to_recover_next_close_cum": 0.0},
            "2026-06-15까지 다음 마감 기준선에 대한 추가 회복 부담은 없습니다.",
        ),
        (
            {"next_close_date": "2026-06-15", "required_to_recover_next_close_cum": -1.0},
            "2026-06-15까지 다음 마감 기준선에 대한 추가 회복 부담은 없습니다.",
        ),
        (
            {"next_close_date": None, "required_to_recover_next_close_cum": 6.0},
            "다음 마감 기준선은 계산 가능한 데이터가 있을 때 표시됩니다.",
        ),
        (
            {"next_close_date": "2026-06-15", "required_to_recover_next_close_cum": None},
            "다음 마감 기준선은 계산 가능한 데이터가 있을 때 표시됩니다.",
        ),
        (
            {"next_close_date": "2026-06-15", "required_to_recover_next_close_cum": "bad"},
            "다음 마감 기준선은 계산 가능한 데이터가 있을 때 표시됩니다.",
        ),
        (
            {"next_close_date": "not-a-date", "required_to_recover_next_close_cum": 2.0},
            "not-a-date까지 누적 기준으로 최소 2.0억 원을 더 확보해야 합니다.",
        ),
    ],
)
def test_visual_next_close_sentence_preserves_missing_and_signed_boundaries(
    next_close_result: dict[str, object],
    expected: str,
) -> None:
    original = deepcopy(next_close_result)

    result = decision_summary_module._visual_next_close_sentence(next_close_result)

    assert result == expected
    assert next_close_result == original


def test_visual_decision_summary_preserves_exact_four_row_contract() -> None:
    selected_row = pd.Series(
        {
            "target_status": "UNDER_TARGET",
            "risk_level": "Yellow",
            "forecast_after_provision": 92.0,
            "target_variance": -8.0,
        },
        dtype=object,
    )

    result = build_visual_decision_summary(
        selected_row,
        {"monthly_target": 100.0},
        POSITIVE_NEXT_CLOSE,
    )

    assert list(result.columns) == ["확인 순서", "볼 것", "현재 값", "해석"]
    assert result.to_dict("records") == [
        {
            "확인 순서": "1",
            "볼 것": "목표 판정",
            "현재 값": "목표 보정 필요 / 위험 주의",
            "해석": "목표 보정 필요 상태입니다. 시나리오별 예상 탭에서 어떤 F/P 조합이 부족분을 줄이는지 보세요.",
        },
        {
            "확인 순서": "2",
            "볼 것": "목표선 대비 예상 실적",
            "현재 값": "92.0억 원 / 목표 100.0억 원",
            "해석": "막대가 목표선보다 낮으면 잔여 목표 보정이 필요하고, 높으면 초과분 관리가 핵심입니다.",
        },
        {
            "확인 순서": "3",
            "볼 것": "목표 대비 차이",
            "현재 값": "-8.0억 원",
            "해석": "월말 기준 8.0억 원를 더 채워야 목표선에 도달합니다.",
        },
        {
            "확인 순서": "4",
            "볼 것": "다음 마감선",
            "현재 값": "2026-06-15 / 6.0억 원",
            "해석": POSITIVE_NEXT_CLOSE_SENTENCE,
        },
    ]


@pytest.mark.parametrize(
    ("risk_level", "risk_label"),
    [
        ("Green", "낮음"),
        ("Yellow", "주의"),
        ("Red", "높음"),
        ("Black", "매우 높음"),
    ],
)
def test_visual_decision_summary_preserves_status_and_risk_localization(
    risk_level: str,
    risk_label: str,
) -> None:
    selected_row = pd.Series(
        {
            "target_status": "ON_TARGET",
            "risk_level": risk_level,
            "forecast_after_provision": 100.0,
            "target_variance": 0.0,
        },
        dtype=object,
    )

    result = build_visual_decision_summary(
        selected_row,
        {"monthly_target": 100.0},
        {"next_close_date": "2026-06-15", "required_to_recover_next_close_cum": 0.0},
    )

    assert result.loc[0, "현재 값"] == f"유지/모니터링 / 위험 {risk_label}"


def test_visual_decision_summary_preserves_missing_value_display_contract() -> None:
    selected_row = pd.Series(
        {
            "target_status": "UNKNOWN_TARGET_STATUS",
            "risk_level": float("nan"),
            "forecast_after_provision": None,
            "target_variance": None,
        },
        dtype=object,
    )

    result = build_visual_decision_summary(selected_row, {}, {})

    assert result.to_dict("records") == [
        {
            "확인 순서": "1",
            "볼 것": "목표 판정",
            "현재 값": "계산 불가 / 위험 nan",
            "해석": "목표 판정에 필요한 값이 부족합니다. 입력값 점검 결과를 먼저 확인하세요.",
        },
        {
            "확인 순서": "2",
            "볼 것": "목표선 대비 예상 실적",
            "현재 값": "계산 불가 / 목표 계산 불가",
            "해석": "막대가 목표선보다 낮으면 잔여 목표 보정이 필요하고, 높으면 초과분 관리가 핵심입니다.",
        },
        {
            "확인 순서": "3",
            "볼 것": "목표 대비 차이",
            "현재 값": "계산 불가",
            "해석": "목표 대비 차이를 계산할 수 없습니다. 선택 시나리오 상세 값을 확인하세요.",
        },
        {
            "확인 순서": "4",
            "볼 것": "다음 마감선",
            "현재 값": "계산 불가 / 계산 불가",
            "해석": "다음 마감 기준선은 계산 가능한 데이터가 있을 때 표시됩니다.",
        },
    ]


def test_visual_decision_builders_do_not_mutate_inputs() -> None:
    selected_row = pd.Series(
        {
            "target_status": "UNDER_TARGET",
            "risk_level": "Yellow",
            "forecast_after_provision": 92.0,
            "target_variance": -8.0,
            "gap_to_target": 8.0,
            "surplus_to_target": 0.0,
        },
        dtype=object,
    )
    validation_result = {"monthly_target": 100.0, "errors": []}
    next_close_result = deepcopy(POSITIVE_NEXT_CLOSE)
    original_selected_row = selected_row.copy(deep=True)
    original_validation_result = deepcopy(validation_result)
    original_next_close_result = deepcopy(next_close_result)

    build_visual_headline(selected_row, validation_result, next_close_result)
    build_visual_decision_summary(selected_row, validation_result, next_close_result)

    pd.testing.assert_series_equal(selected_row, original_selected_row)
    assert validation_result == original_validation_result
    assert next_close_result == original_next_close_result
