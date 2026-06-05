"""Korean text report builder for daily scenario results."""

from __future__ import annotations

from collections.abc import Mapping
from math import isfinite
from typing import Any

import pandas as pd


FORECAST_MODEL_LABELS = {
    "F1_CUMULATIVE_RATE": "F1",
    "F2_LAST_TWO_CLOSES": "F2",
    "F3_DAY_CLOSE_WEIGHTED": "F3",
    "F1": "F1",
    "F2": "F2",
    "F3": "F3",
}

RISK_LEVEL_PHRASES = {
    "Green": "목표 달성 가능성이 높음",
    "Yellow": "주의 관찰 필요",
    "Red": "강한 개선 필요",
    "Black": "고위험 또는 계산 제한",
    "N/A": "적용 불가",
}
METRIC_LABELS = {
    "sales": "판매실적",
    "recognized": "인정실적",
}
TARGET_STATUS_LABELS = {
    "UNDER_TARGET": "목표 미달",
    "ON_TARGET": "목표선 근접",
    "OVER_TARGET": "목표 초과",
    "UNKNOWN_TARGET_STATUS": "계산 불가",
}
RISK_LEVEL_LABELS = {
    "Green": "낮음",
    "Yellow": "주의",
    "Red": "높음",
    "Black": "매우 높음",
    "N/A": "해당 없음",
}
STATUS_LABELS = {
    "OK": "정상",
    "NO_GAP": "부족분 없음",
    "CAPACITY_LIMITED": "배분 한도 초과",
    "NOT_APPLICABLE": "적용 불가",
    "CALCULATION_ERROR": "계산 오류",
    "OVER_TARGET_MANAGED": "초과달성 관리",
    "ON_TARGET_MAINTAIN": "목표선 유지",
}
FORECAST_MODEL_DEFINITIONS = {
    "F1": "누적 달성률 모델. 기준일까지의 누적 실적/누적 목표 달성률을 남은 모든 일자 목표에 동일하게 적용합니다.",
    "F2": "직전 2개 완료 마감차수 모델. 기준일까지 완료된 최근 2개 마감차수의 실적/목표 비율을 남은 일자에 적용합니다.",
    "F3": "마감일/비마감일 가중 모델. 마감일과 비마감일의 과거 달성률을 분리해 남은 일자별로 적용합니다.",
}
PROVISION_STRATEGY_DEFINITIONS = {
    "P1": "전체 잔여일 배분. 예상 부족분을 기준일 이후 모든 잔여 일자에 기존 일 목표 비중대로 배분합니다.",
    "P2": "마감일 우선 배분. 예상 부족분을 기준일 이후 마감일에 우선 배분합니다.",
    "P3": "비마감일 우선 배분. 예상 부족분을 기준일 이후 비마감일에 우선 배분합니다.",
}
OVERACHIEVEMENT_STRATEGY_DEFINITIONS = {
    "O1": "목표 유지 안전버퍼. 초과 예상분을 취소, 철회, 미결제, 실적 조정 리스크 방어용 버퍼로 둡니다.",
    "O2": "상향 목표 전환. 초과 예상분 일부를 추가 성장 목표로 전환합니다.",
    "O3": "계약 품질 방어. 공식 목표는 유지하고 취소, 철회, 미결제, 결제완료율, 순계약, 상담 품질을 관리합니다.",
}
NEUTRAL_STRATEGY_DEFINITIONS = {
    "N1": "목표 유지. 공식 월 목표와 잔여 실행 계획을 유지합니다.",
    "N2": "버퍼 모니터링. 목표선 부근 변동을 매일 점검합니다.",
    "N3": "품질 점검. 계약 품질과 결제완료율을 확인합니다.",
}
RISK_LEVEL_DEFINITIONS = {
    "Green": "예상 달성률이 100% 이상이고 보정 상태가 정상이거나 부족분이 없는 상태입니다.",
    "Yellow": "예상 달성률이 95% 이상이거나 필요 상향분이 잔여 목표의 5% 이하인 상태입니다.",
    "Red": "예상 달성률이 90% 이상이거나 필요 상향분이 잔여 목표의 15% 이하인 상태입니다.",
    "Black": "계산 오류, 상한 부족, 또는 예상 달성률/필요 상향 부담이 높은 상태입니다.",
    "N/A": "해당 보정 전략을 적용할 수 없는 상태입니다.",
}
TERM_DEFINITION_SECTION_TITLE = "용어 정의 - 고정 용어집"
TERM_DEFINITION_NOTICE = (
    "고정 안내: 아래 용어 정의는 입력값이나 선택 시나리오와 무관하게 동일하게 적용되는 보고 기준입니다."
)
TERM_DEFINITION_GROUPS = (
    ("예측모델(F)", FORECAST_MODEL_DEFINITIONS),
    ("목표 보정 전략(P)", PROVISION_STRATEGY_DEFINITIONS),
    ("초과달성 운영전략(O)", OVERACHIEVEMENT_STRATEGY_DEFINITIONS),
    ("유지/모니터링 전략(N)", NEUTRAL_STRATEGY_DEFINITIONS),
    ("위험등급", RISK_LEVEL_DEFINITIONS),
)


def build_daily_report_text(
    scenario_df: pd.DataFrame,
    next_close_result: Mapping[str, Any] | None,
    selected_scenario_id: str | None = None,
) -> str:
    """Build a concise Korean daily report from scenario-grid output."""
    if scenario_df is None or scenario_df.empty:
        return "시나리오 결과가 없어 일일 보고서를 생성할 수 없습니다."

    result = scenario_df.copy(deep=False)
    forecast_summary = _forecast_summary_by_model(result)

    sections = [
        (
            "기준 현황",
            [
                _build_forecast_comparison_sentence(result, forecast_summary),
                _build_forecast_range_sentence(forecast_summary),
            ],
        ),
    ]

    if selected_scenario_id:
        sections.append(
            (
                "선택 시나리오",
                [_build_selected_scenario_sentence(result, selected_scenario_id)],
            )
        )

    overachievement_lines = _build_overachievement_lines(result)
    if overachievement_lines:
        sections.append(("초과달성 운영전략", overachievement_lines))

    sections.append(("다음 마감", [_build_next_close_sentence(result, next_close_result)]))

    risk_sentences = _build_risk_sentences(result)
    if risk_sentences:
        sections.append(("위험등급 및 확인 사항", risk_sentences))

    return _format_report_sections(sections)


def _format_report_sections(sections: list[tuple[str, list[str]]]) -> str:
    paragraphs: list[str] = []
    for title, lines in sections:
        cleaned_lines = [str(line).rstrip() for line in lines if str(line).strip()]
        if not cleaned_lines:
            continue

        paragraph_lines = [f"[{title}]"]
        if title == TERM_DEFINITION_SECTION_TITLE:
            paragraph_lines.extend(cleaned_lines)
        else:
            paragraph_lines.extend(f"- {line}" for line in cleaned_lines)
        paragraphs.append("\n".join(paragraph_lines))

    return "\n\n".join(paragraphs).strip()


def _build_forecast_comparison_sentence(
    scenario_df: pd.DataFrame,
    forecast_summary: dict[str, dict[str, object]],
) -> str:
    as_of_date = _format_date(_first_present(scenario_df, "as_of_date"))
    metric = _display_metric(_first_present(scenario_df, "metric") or "metric")
    current_actual = _format_amount(_first_present(scenario_df, "current_actual_cum"))

    model_parts = []
    for model_id in ("F1", "F2", "F3"):
        summary = forecast_summary.get(model_id, {})
        forecast = _format_amount(summary.get("forecast_amount"))
        rate = _format_rate(summary.get("forecast_rate"))
        model_parts.append(f"{model_id} 기준은 {forecast}(달성률 {rate})")

    return (
        f"{as_of_date} 기준 {metric} 누적 실적은 {current_actual}이며, "
        f"{', '.join(model_parts)}입니다."
    )


def _build_forecast_range_sentence(
    forecast_summary: dict[str, dict[str, object]],
) -> str:
    valid = [
        (model_id, _as_float(summary.get("forecast_amount")))
        for model_id, summary in forecast_summary.items()
    ]
    valid = [(model_id, amount) for model_id, amount in valid if _is_finite(amount)]
    if not valid:
        return "가장 보수적인 예측값과 가장 높은 예측값은 계산 불가입니다."

    conservative_model, conservative_amount = min(valid, key=lambda item: item[1])
    highest_model, highest_amount = max(valid, key=lambda item: item[1])
    return (
        f"가장 보수적인 예측값은 {conservative_model} {_format_amount(conservative_amount)}이고, "
        f"가장 높은 예측값은 {highest_model} {_format_amount(highest_amount)}입니다."
    )


def _build_selected_scenario_sentence(
    scenario_df: pd.DataFrame,
    selected_scenario_id: str,
) -> str:
    selected_rows = scenario_df.loc[
        scenario_df.get("scenario_id", pd.Series(dtype=object)).astype(str) == selected_scenario_id
    ]
    if selected_rows.empty:
        return f"선택 시나리오 {selected_scenario_id}는 결과표에서 찾을 수 없습니다."

    row = selected_rows.iloc[0]
    target_status = str(row.get("target_status", ""))
    strategy_type = str(row.get("strategy_type", ""))
    if target_status == "OVER_TARGET" or strategy_type == "OVERACHIEVEMENT":
        return _build_selected_overachievement_sentence(row, selected_scenario_id)
    if target_status == "ON_TARGET" or strategy_type == "NEUTRAL":
        return _build_selected_neutral_sentence(row, selected_scenario_id)

    required_uplift = _format_amount(row.get("required_uplift"))
    forecast_after = _format_amount(row.get("forecast_after_provision"))
    gap_after = _format_amount(row.get("gap_after_provision"))
    remaining_target = _format_amount(row.get("remaining_target"))
    forecast_key, provision_key = _split_scenario_id(selected_scenario_id)
    scenario_definition = _selected_scenario_definition(forecast_key, provision_key)

    sentence = (
        f"선택 시나리오 {selected_scenario_id}({scenario_definition}) 기준 월 목표 달성을 위해 "
        f"잔여 목표 {remaining_target} 중 필요한 상향 배분은 {required_uplift}이며, "
        f"전략 반영 후 예상은 {forecast_after}, "
        f"전략 반영 후 부족분은 {gap_after}입니다."
    )
    if str(row.get("status", "")) == "CAPACITY_LIMITED":
        sentence += " 배분 한도 제한으로 목표 달성이 불확실합니다."
    if str(row.get("status", "")) == "NOT_APPLICABLE":
        sentence += f" 적용 불가 사유는 {_not_applicable_reason(row)}입니다."
    return sentence


def _build_selected_overachievement_sentence(
    row: pd.Series,
    selected_scenario_id: str,
) -> str:
    forecast_key, strategy_key = _split_scenario_id(selected_scenario_id)
    scenario_definition = _selected_scenario_definition(forecast_key, strategy_key)
    target_status = _display_target_status(row.get("target_status"))
    return (
        f"선택 시나리오 {selected_scenario_id}({scenario_definition})는 목표 초과 예상입니다. "
        f"목표 상태는 {target_status}이며, "
        f"목표 대비 차이는 {_format_amount(row.get('target_variance'))}, "
        f"초과 예상분은 {_format_amount(row.get('surplus_to_target'))}입니다. "
        f"{_recommended_action_sentence(row, '초과달성 운영전략을 확인합니다')}"
    )


def _build_selected_neutral_sentence(
    row: pd.Series,
    selected_scenario_id: str,
) -> str:
    forecast_key, strategy_key = _split_scenario_id(selected_scenario_id)
    scenario_definition = _selected_scenario_definition(forecast_key, strategy_key)
    target_status = _display_target_status(row.get("target_status"))
    return (
        f"선택 시나리오 {selected_scenario_id}({scenario_definition})는 목표선에 근접한 상태입니다. "
        f"목표 상태는 {target_status}이며, "
        f"목표 대비 차이는 {_format_amount(row.get('target_variance'))}입니다. "
        f"{_recommended_action_sentence(row, '유지관리 전략을 적용합니다')}"
    )


def _recommended_action_sentence(row: pd.Series, default: str) -> str:
    action = row.get("recommended_action", default)
    if _is_missing(action) or not str(action).strip():
        action = default

    action_text = str(action).strip()
    if action_text.endswith((".", "!", "?")):
        return f"권장 조치는 {action_text}"
    if action_text.endswith(("다", "요")):
        return f"권장 조치는 {action_text}."
    return f"권장 조치는 {action_text}입니다."


def _build_term_definition_sentence() -> str:
    return " ".join(_build_term_definition_lines())


def _build_term_definition_lines() -> list[str]:
    lines = [TERM_DEFINITION_NOTICE]
    for group_title, definitions in TERM_DEFINITION_GROUPS:
        lines.append(f"■ {group_title}")
        lines.extend(f"  - {term}={definition}" for term, definition in definitions.items())
    return lines


def _build_overachievement_lines(scenario_df: pd.DataFrame) -> list[str]:
    if "target_status" not in scenario_df:
        return []

    over_rows = scenario_df.loc[scenario_df["target_status"].astype(str) == "OVER_TARGET"]
    if over_rows.empty:
        return []

    first_row = over_rows.iloc[0]
    lines = [
        (
            "목표 초과 예상: "
            f"목표 상태는 {_display_target_status(first_row.get('target_status'))}, "
            f"목표 대비 차이는 {_format_amount(first_row.get('target_variance'))}, "
            f"초과 예상분은 {_format_amount(first_row.get('surplus_to_target'))}입니다."
        )
    ]

    for strategy_key in ("O1", "O2", "O3"):
        strategy_rows = over_rows.loc[
            over_rows["scenario_id"].astype(str).str.endswith(f"_{strategy_key}")
        ]
        if strategy_rows.empty:
            continue
        row = strategy_rows.iloc[0]
        if strategy_key == "O1":
            lines.append(
                "O1 목표 유지 안전버퍼: 공식 목표는 유지하고 "
                f"{_format_amount(row.get('remaining_surplus_buffer'))}를 안전버퍼로 둡니다. "
                "취소, 철회, 미결제, 실적 조정 리스크 방어용입니다."
            )
        elif strategy_key == "O2":
            lines.append(
                "O2 상향 목표 전환: 초과분 일부를 추가 성장 목표로 전환합니다. "
                f"상향 목표 전환분={_format_amount(row.get('stretch_uplift'))}, "
                f"운영전략 월 목표={_format_amount(row.get('revised_monthly_target'))}, "
                f"잔여 안전버퍼={_format_amount(row.get('remaining_surplus_buffer'))}입니다."
            )
        elif strategy_key == "O3":
            lines.append(
                "O3 계약 품질 방어: 공식 목표는 유지하고 계약 품질을 방어합니다. "
                f"목표 달성 최소 잔여 실적={_format_amount(row.get('minimum_remaining_to_hit_target'))}, "
                f"품질관리 여유분={_format_amount(row.get('relief_amount'))}입니다. "
                "취소, 철회, 미결제, 결제완료율, 순계약, 상담 품질 관리를 우선합니다."
            )

    return lines


def _build_next_close_sentence(
    scenario_df: pd.DataFrame,
    next_close_result: Mapping[str, Any] | None,
) -> str:
    next_close_result = next_close_result or {}
    next_close_date = next_close_result.get("next_close_date")
    required = _next_close_required(next_close_result)

    if next_close_date is None:
        next_close_date = _first_present(scenario_df, "next_close_date")
    if required is None:
        required = _first_present(scenario_df, "next_close_required")

    if _is_missing(next_close_date):
        return "다음 마감일은 입력표에 없으며, 다음 마감 누적선 필요실적은 계산 불가입니다."

    return (
        f"다음 마감일은 {_format_date(next_close_date)}이며, "
        f"다음 마감 누적선 필요실적은 {_format_amount(required)}입니다. "
        "다음 마감 필요실적은 월 목표 부족분이 아니라, "
        "다음 마감일까지의 누적 계획선을 맞추기 위해 필요한 실적입니다."
    )


def _build_risk_sentences(scenario_df: pd.DataFrame) -> list[str]:
    sentences: list[str] = []

    if "risk_level" in scenario_df:
        counts = _risk_level_counts(scenario_df["risk_level"])
        if counts:
            parts = [
                f"{_display_risk_level(risk_level)} {count}건({RISK_LEVEL_PHRASES.get(risk_level, '별도 확인 필요')})"
                for risk_level, count in counts
            ]
            sentences.append(f"위험등급별로 {', '.join(parts)}입니다.")

    if "status" in scenario_df:
        capacity_rows = scenario_df.loc[scenario_df["status"].astype(str) == "CAPACITY_LIMITED"]
        if not capacity_rows.empty:
            scenarios = _scenario_list(capacity_rows)
            sentences.append(
                f"배분 한도 초과 시나리오({scenarios})는 배분 한도 제한으로 "
                "목표 달성이 불확실합니다."
            )

        not_applicable_rows = scenario_df.loc[scenario_df["status"].astype(str) == "NOT_APPLICABLE"]
        for _, row in not_applicable_rows.iterrows():
            sentences.append(
                f"적용 불가 시나리오({_scenario_name(row)})는 "
                f"{_not_applicable_reason(row)}입니다."
            )

    return sentences


def _forecast_summary_by_model(scenario_df: pd.DataFrame) -> dict[str, dict[str, object]]:
    summary: dict[str, dict[str, object]] = {}
    for _, row in scenario_df.iterrows():
        model_id = _forecast_model_label(row)
        if model_id not in {"F1", "F2", "F3"} or model_id in summary:
            continue
        summary[model_id] = {
            "forecast_amount": row.get("forecast_amount"),
            "forecast_rate": row.get("forecast_rate"),
        }
    return summary


def _forecast_model_label(row: pd.Series) -> str:
    forecast_model = str(row.get("forecast_model", ""))
    label = FORECAST_MODEL_LABELS.get(forecast_model)
    if label:
        return label

    scenario_id = str(row.get("scenario_id", ""))
    scenario_prefix = scenario_id.split("_", maxsplit=1)[0]
    return FORECAST_MODEL_LABELS.get(scenario_prefix, forecast_model)


def _risk_level_counts(risk_values: pd.Series) -> list[tuple[str, int]]:
    cleaned = [
        str(value)
        for value in risk_values
        if not _is_missing(value) and str(value).strip()
    ]
    if not cleaned:
        return []

    ordered_levels = ["Green", "Yellow", "Red", "Black", "N/A"]
    counts = {level: cleaned.count(level) for level in ordered_levels}
    result = [(level, count) for level, count in counts.items() if count > 0]

    extra_levels = sorted(set(cleaned) - set(ordered_levels))
    result.extend((level, cleaned.count(level)) for level in extra_levels)
    return result


def _not_applicable_reason(row: pd.Series) -> str:
    comment = row.get("comment")
    if isinstance(comment, str) and comment.strip():
        return comment.strip()

    provision_strategy = str(row.get("provision_strategy", ""))
    if provision_strategy == "P2_CLOSE_DAY_FOCUSED":
        return "기준일 이후 마감일로 표시된 잔여 입력일이 없어 적용 불가"
    if provision_strategy == "P3_NON_CLOSE_DAY_FOCUSED":
        return "기준일 이후 비마감일로 표시된 잔여 입력일이 없어 적용 불가"
    return "기준일 이후 배분 가능한 잔여 입력일이 없어 적용 불가"


def _next_close_required(next_close_result: Mapping[str, Any]) -> object | None:
    for key in (
        "next_close_required",
        "required_to_recover_next_close_cum",
        "required_to_hit_current_cycle",
    ):
        value = next_close_result.get(key)
        if not _is_missing(value):
            return value
    return None


def _scenario_list(rows: pd.DataFrame) -> str:
    return ", ".join(_scenario_name(row) for _, row in rows.iterrows())


def _scenario_name(row: pd.Series) -> str:
    scenario_id = row.get("scenario_id")
    if not _is_missing(scenario_id) and str(scenario_id):
        return str(scenario_id)
    return f"{_forecast_model_label(row)}_{row.get('provision_strategy', 'UNKNOWN')}"


def _split_scenario_id(scenario_id: str) -> tuple[str, str]:
    if "_" not in scenario_id:
        return scenario_id, ""
    return scenario_id.split("_", maxsplit=1)


def _selected_scenario_definition(forecast_key: str, provision_key: str) -> str:
    return f"{forecast_key} + {provision_key} 조합"


def _display_metric(value: object) -> str:
    text = "" if _is_missing(value) else str(value)
    return METRIC_LABELS.get(text, text or "지표")


def _display_target_status(value: object) -> str:
    text = "" if _is_missing(value) else str(value)
    return TARGET_STATUS_LABELS.get(text, text or "계산 불가")


def _display_risk_level(value: object) -> str:
    text = "" if _is_missing(value) else str(value)
    return RISK_LEVEL_LABELS.get(text, text or "계산 불가")


def _first_present(scenario_df: pd.DataFrame, column: str) -> object | None:
    if column not in scenario_df:
        return None
    values = scenario_df[column].dropna()
    if values.empty:
        return None
    return values.iloc[0]


def _format_amount(value: object) -> str:
    number = _as_float(value)
    if not _is_finite(number):
        return "계산 불가"
    return f"{number:.1f}억 원"


def _format_rate(value: object) -> str:
    number = _as_float(value)
    if not _is_finite(number):
        return "계산 불가"
    return f"{number * 100:.1f}%"


def _format_date(value: object) -> str:
    if _is_missing(value):
        return "계산 불가"
    try:
        return str(pd.Timestamp(value).date())
    except Exception:  # noqa: BLE001 - report should tolerate display-only values.
        return str(value)


def _as_float(value: object) -> float:
    if _is_missing(value):
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _is_finite(value: object) -> bool:
    try:
        return isfinite(float(value))
    except (TypeError, ValueError):
        return False


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False
