from __future__ import annotations

from copy import deepcopy

import pandas as pd
import pytest

from src.ui_metadata_builders import (
    build_forecast_definition_df,
    build_neutral_definition_df,
    build_overachievement_definition_df,
    build_provision_definition_df,
    build_report_glossary_df,
    build_risk_definition_df,
    build_visual_metric_definition_df,
    build_visual_reading_guide,
)


def test_visual_metric_definitions_preserve_requested_order_and_fallback() -> None:
    definitions = {
        "metric_a": {
            "label": "지표 A",
            "unit": "억원",
            "definition": "지표 A의 고정 정의입니다.",
        },
        "metric_b": {
            "label": "지표 B",
            "unit": "%",
            "definition": "지표 B의 고정 정의입니다.",
        },
    }
    original = deepcopy(definitions)

    result = build_visual_metric_definition_df(
        ("metric_b", "unknown_metric", "metric_a"),
        definitions=definitions,
    )

    assert definitions == original
    assert result.to_dict("records") == [
        {"범례": "지표 B", "단위": "%", "수치 의미": "지표 B의 고정 정의입니다."},
        {
            "범례": "unknown_metric",
            "단위": "",
            "수치 의미": "정의가 등록되지 않은 수치입니다.",
        },
        {"범례": "지표 A", "단위": "억원", "수치 의미": "지표 A의 고정 정의입니다."},
    ]


def test_visual_reading_guide_preserves_wording_order_and_source() -> None:
    guides = {
        "guide_a": {
            "title": "목표선 비교",
            "steps": ["목표선을 확인합니다.", "예상 실적을 비교합니다."],
            "decision": "목표선을 넘는지 판단합니다.",
        }
    }
    original = deepcopy(guides)

    result = build_visual_reading_guide("guide_a", guides=guides)

    assert guides == original
    assert result == {
        "title": "목표선 비교",
        "steps": ("목표선을 확인합니다.", "예상 실적을 비교합니다."),
        "decision": "목표선을 넘는지 판단합니다.",
    }
    assert result is not guides["guide_a"]


def test_visual_reading_guide_preserves_missing_guide_and_field_fallbacks() -> None:
    guides = {"partial": {"title": "부분 가이드"}}

    assert build_visual_reading_guide("partial", guides=guides) == {
        "title": "부분 가이드",
        "steps": (),
        "decision": "",
    }
    assert build_visual_reading_guide("unknown", guides=guides) == {
        "title": "",
        "steps": (),
        "decision": "",
    }


def test_forecast_definitions_preserve_wording_formula_and_row_order() -> None:
    definitions = {
        "F2": {
            "name": "직전 마감 모델",
            "description": "완료 마감차수만 사용합니다.",
            "formula": "forecast = actual + remaining * rate",
        },
        "F1": {
            "name": "누적 모델",
            "description": "누적 달성률을 적용합니다.",
            "formula": "forecast = actual + remaining * cumulative_rate",
        },
    }
    original = deepcopy(definitions)

    result = build_forecast_definition_df(definitions=definitions)

    assert definitions == original
    assert result.to_dict("records") == [
        {
            "model": "F2",
            "name": "직전 마감 모델",
            "description": "완료 마감차수만 사용합니다.",
            "formula": "forecast = actual + remaining * rate",
        },
        {
            "model": "F1",
            "name": "누적 모델",
            "description": "누적 달성률을 적용합니다.",
            "formula": "forecast = actual + remaining * cumulative_rate",
        },
    ]


@pytest.mark.parametrize(
    ("builder", "prefix"),
    [
        (build_provision_definition_df, "P"),
        (build_overachievement_definition_df, "O"),
        (build_neutral_definition_df, "N"),
    ],
)
def test_strategy_definitions_preserve_wording_and_row_order(builder, prefix: str) -> None:
    definitions = {
        f"{prefix}2": {"name": "두 번째", "description": "두 번째 고정 설명"},
        f"{prefix}1": {"name": "첫 번째", "description": "첫 번째 고정 설명"},
    }
    original = deepcopy(definitions)

    result = builder(definitions=definitions)

    assert definitions == original
    assert result.to_dict("records") == [
        {
            "strategy": f"{prefix}2",
            "name": "두 번째",
            "description": "두 번째 고정 설명",
        },
        {
            "strategy": f"{prefix}1",
            "name": "첫 번째",
            "description": "첫 번째 고정 설명",
        },
    ]


def test_report_glossary_preserves_group_code_order_and_source() -> None:
    groups = (
        ("예측모델(F)", {"F2": "F2 고정 정의", "F1": "F1 고정 정의"}),
        ("위험등급", {2: "두 번째 위험", 1: "첫 번째 위험"}),
    )
    original = deepcopy(groups)

    result = build_report_glossary_df(groups=groups)

    assert groups == original
    assert result.to_dict("records") == [
        {"구분": "예측모델(F)", "코드": "F2", "정의": "F2 고정 정의"},
        {"구분": "예측모델(F)", "코드": "F1", "정의": "F1 고정 정의"},
        {"구분": "위험등급", "코드": "2", "정의": "두 번째 위험"},
        {"구분": "위험등급", "코드": "1", "정의": "첫 번째 위험"},
    ]


def test_risk_definitions_preserve_wording_and_row_order() -> None:
    definitions = {"Black": "매우 높음 고정 정의", "Green": "낮음 고정 정의"}
    original = deepcopy(definitions)

    result = build_risk_definition_df(definitions=definitions)

    assert definitions == original
    assert result.to_dict("records") == [
        {"risk_level": "Black", "definition": "매우 높음 고정 정의"},
        {"risk_level": "Green", "definition": "낮음 고정 정의"},
    ]


@pytest.mark.parametrize(
    ("builder", "definitions", "missing_key"),
    [
        (
            build_forecast_definition_df,
            {"F1": {"name": "이름", "description": "설명"}},
            "formula",
        ),
        (
            build_provision_definition_df,
            {"P1": {"name": "이름"}},
            "description",
        ),
    ],
)
def test_definition_builders_preserve_missing_required_field_failure(
    builder,
    definitions: dict[str, dict[str, str]],
    missing_key: str,
) -> None:
    with pytest.raises(KeyError, match=missing_key):
        builder(definitions=definitions)


@pytest.mark.parametrize(
    "builder_call",
    [
        lambda: build_visual_metric_definition_df((), definitions={}),
        lambda: build_forecast_definition_df(definitions={}),
        lambda: build_provision_definition_df(definitions={}),
        lambda: build_report_glossary_df(groups=()),
        lambda: build_risk_definition_df(definitions={}),
    ],
)
def test_metadata_builders_preserve_empty_frame_shape(builder_call) -> None:
    result = builder_call()

    assert isinstance(result, pd.DataFrame)
    assert result.empty
    assert list(result.columns) == []
