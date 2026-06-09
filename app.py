"""Streamlit entry point for the input-driven sales closing forecast tool."""

from __future__ import annotations

import hashlib
import hmac
import io
import math
import os
import tempfile
from pathlib import Path
from typing import Any

import altair as alt
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - local test runtime may omit Streamlit.
    st = None

from src import history_schema
from src.backtest_engine import build_backtest_dataset, summarize_by_forecast_model
from src.close_cycle_engine import _coerce_is_close_day, build_close_cycle_summary
from src.excel_exporter import export_daily_report
from src.final_actual_store import load_final_actuals
from src.forecast_models import (
    F1_CUMULATIVE_RATE,
    F2_LAST_TWO_CLOSES,
    F3_DAY_CLOSE_WEIGHTED,
    run_forecast_model,
)
from src.loader import load_input
from src.history_store import append_forecast_history, build_forecast_history_rows
from src.next_close import calculate_next_close_required
from src.overachievement_models import (
    N1_MAINTAIN_TARGET,
    N2_MONITOR_BUFFER,
    N3_QUALITY_CHECK,
    NEUTRAL,
    O1_TARGET_HOLD_BUFFER,
    O2_STRETCH_TARGET_CAPTURE,
    O3_QUALITY_GUARD_RELIEF,
    OVERACHIEVEMENT,
    PROVISION,
    run_neutral_strategy,
    run_overachievement_strategy,
)
from src.provision_models import (
    P1_ALL_REMAINING,
    P2_CLOSE_DAY_FOCUSED,
    P3_NON_CLOSE_DAY_FOCUSED,
    run_provision_model,
)
from src.report_builder import (
    FORECAST_MODEL_DEFINITIONS as REPORT_FORECAST_MODEL_DEFINITIONS,
    NEUTRAL_STRATEGY_DEFINITIONS as REPORT_NEUTRAL_STRATEGY_DEFINITIONS,
    OVERACHIEVEMENT_STRATEGY_DEFINITIONS as REPORT_OVERACHIEVEMENT_STRATEGY_DEFINITIONS,
    PROVISION_STRATEGY_DEFINITIONS as REPORT_PROVISION_STRATEGY_DEFINITIONS,
    RISK_LEVEL_DEFINITIONS as REPORT_RISK_LEVEL_DEFINITIONS,
    build_daily_report_text,
)
from src.scenario_runner import run_scenario_grid
from src.schema import get_metric_columns, load_model_config
from src.validator import validate_input


REPO_ROOT = Path(__file__).resolve().parent
SAMPLE_INPUT_PATH = REPO_ROOT / "data" / "sample" / "input_sample.csv"
HISTORICAL_SAMPLE_INPUT_PATH = REPO_ROOT / "data" / "sample" / "historical_input_sample.csv"
OUTPUT_DIR = REPO_ROOT / "outputs"
SAVED_ACTUALS_PATH = OUTPUT_DIR / "saved_actuals.csv"
INPUT_TEMPLATE_FILENAME = "month_close_forecast_input_template.xlsx"
HISTORICAL_INPUT_TEMPLATE_FILENAME = "historical_month_close_forecast_input_template.xlsx"
SAMPLE_INPUT_SOURCE_LABEL = "샘플 데이터"
HISTORICAL_SAMPLE_INPUT_SOURCE_LABEL = "과거 샘플 데이터"
INPUT_TEMPLATE_HEADERS = (
    "date",
    "day_name",
    "business_day_no",
    "is_close_day",
    "close_type",
    "sales_target_daily",
    "recognized_target_daily",
    "sales_actual_cum",
    "recognized_actual_cum",
    "memo",
)
INPUT_TEMPLATE_SAMPLE_ROWS = (
    (
        "YYYY-MM-DD",
        "display_only",
        1,
        False,
        "",
        None,
        None,
        None,
        None,
        "",
    ),
)
HISTORICAL_INPUT_TEMPLATE_SAMPLE_ROWS = (
    ("2026-03-02", "월", 1, True, "월초특수", 35.0, 32.0, 33.0, 30.0, "과거 월 예시"),
    ("2026-03-03", "화", 2, False, "일반", 2.5, 2.3, 38.0, 34.5, "과거 월 예시"),
    ("2026-03-05", "목", 3, True, "목마감", 14.0, 12.8, 51.0, 46.3, "과거 월 예시"),
    ("2026-04-01", "수", 1, True, "월초특수", 34.0, 31.0, 31.0, 28.3, "다음 월은 1부터 다시 시작"),
    ("2026-04-02", "목", 2, False, "일반", 2.6, 2.4, 35.0, 31.8, "다음 월은 1부터 다시 시작"),
    ("2026-04-06", "월", 3, True, "월마감", 14.5, 13.3, 47.0, 42.7, "다음 월은 1부터 다시 시작"),
)
HISTORY_TAB_LABEL = "예측 이력 / Backtest"
ACCESS_SESSION_STATE_KEY = "limited_distribution_access_granted"
ACCESS_PASSWORD_SETTING_KEYS = (
    "APP_ACCESS_PASSWORD",
    "app_access_password",
    "access_password",
)
ACCESS_PASSWORD_HASH_SETTING_KEYS = (
    "APP_ACCESS_PASSWORD_SHA256",
    "app_access_password_sha256",
    "access_password_sha256",
)
COMPARE_LABEL = "전체 비교"
APP_TIMEZONE = "Asia/Seoul"
CHART_COLOR_RANGE = (
    "#2563EB",
    "#059669",
    "#D97706",
    "#7C3AED",
    "#DC2626",
    "#0F766E",
    "#9333EA",
    "#4B5563",
)
WEIGHTED_FORECAST_COLUMN_TOKENS = ("weighted_forecast", "weighted_forecast_amount")
CONFIDENCE_BAND_COLUMN_PAIRS = (
    ("confidence_lower", "confidence_upper"),
    ("forecast_lower", "forecast_upper"),
    ("lower_bound", "upper_bound"),
)

FORECAST_MODEL_OPTIONS = {
    "F1": F1_CUMULATIVE_RATE,
    "F2": F2_LAST_TWO_CLOSES,
    "F3": F3_DAY_CLOSE_WEIGHTED,
}
PROVISION_STRATEGY_OPTIONS = {
    "P1": P1_ALL_REMAINING,
    "P2": P2_CLOSE_DAY_FOCUSED,
    "P3": P3_NON_CLOSE_DAY_FOCUSED,
}
OVERACHIEVEMENT_STRATEGY_OPTIONS = {
    "O1": O1_TARGET_HOLD_BUFFER,
    "O2": O2_STRETCH_TARGET_CAPTURE,
    "O3": O3_QUALITY_GUARD_RELIEF,
}
NEUTRAL_STRATEGY_OPTIONS = {
    "N1": N1_MAINTAIN_TARGET,
    "N2": N2_MONITOR_BUFFER,
    "N3": N3_QUALITY_CHECK,
}
SCENARIO_STRATEGY_OPTIONS = {
    **PROVISION_STRATEGY_OPTIONS,
    **OVERACHIEVEMENT_STRATEGY_OPTIONS,
    **NEUTRAL_STRATEGY_OPTIONS,
}
FORECAST_MODEL_DEFINITIONS = {
    "F1": {
        "name": "누적 달성률 모델",
        "description": "기준일까지의 누적 실적/누적 목표 달성률을 남은 모든 일자 목표에 동일하게 적용합니다.",
        "formula": "forecast = current_actual_cum + remaining_target * r_cum",
    },
    "F2": {
        "name": "직전 2개 완료 마감차수 모델",
        "description": "기준일까지 완료된 최근 2개 마감차수의 실적/목표 비율을 남은 일자에 적용합니다.",
        "formula": "forecast = current_actual_cum + remaining_target * r_last2",
    },
    "F3": {
        "name": "마감일/비마감일 가중 모델",
        "description": "마감일과 비마감일의 과거 달성률을 분리해 남은 일자의 마감 여부별로 적용합니다.",
        "formula": "forecast = current_actual_cum + close_target * r_close + non_close_target * r_non_close",
    },
}
PROVISION_STRATEGY_DEFINITIONS = {
    "P1": {
        "name": "전체 잔여일 배분",
        "description": "예상 부족분을 기준일 이후 모든 잔여 일자에 기존 일 목표 비중대로 배분합니다.",
    },
    "P2": {
        "name": "마감일 우선 배분",
        "description": "예상 부족분을 기준일 이후 마감일에 우선 배분하고, 상한 초과분은 설정에 따라 재배분합니다.",
    },
    "P3": {
        "name": "비마감일 우선 배분",
        "description": "예상 부족분을 기준일 이후 비마감일에 우선 배분하고, 상한 초과분은 설정에 따라 재배분합니다.",
    },
}
OVERACHIEVEMENT_STRATEGY_DEFINITIONS = {
    "O1": {
        "name": "목표 유지 안전버퍼",
        "description": "월 목표는 유지하고 초과 예상분을 취소, 철회, 미결제, 실적 조정 리스크 방어용 버퍼로 둡니다.",
    },
    "O2": {
        "name": "상향 목표 전환",
        "description": "초과 예상분 일부를 추가 성장 목표로 전환하고 남은 초과분은 안전버퍼로 유지합니다.",
    },
    "O3": {
        "name": "계약 품질 방어",
        "description": "공식 목표는 유지하고 결제완료율, 순계약, 상담 품질, 취소/철회/미결제 리스크 관리에 집중합니다.",
    },
}
NEUTRAL_STRATEGY_DEFINITIONS = {
    "N1": {
        "name": "목표 유지",
        "description": "목표와 거의 같은 상태로 보고 공식 월 목표와 잔여 실행 계획을 유지합니다.",
    },
    "N2": {
        "name": "버퍼 모니터링",
        "description": "목표선 부근의 작은 변동이 미달로 바뀌지 않도록 취소, 철회, 미결제 변동을 점검합니다.",
    },
    "N3": {
        "name": "품질 점검",
        "description": "무리한 추가 상향보다 계약 품질, 결제완료율, 순계약 상태를 확인합니다.",
    },
}
SCENARIO_STRATEGY_DEFINITIONS = {
    **PROVISION_STRATEGY_DEFINITIONS,
    **OVERACHIEVEMENT_STRATEGY_DEFINITIONS,
    **NEUTRAL_STRATEGY_DEFINITIONS,
}
RISK_LEVEL_DEFINITIONS = {
    "Green": "예상 달성률이 100% 이상이고 보정 상태가 정상이거나 부족분이 없는 상태입니다.",
    "Yellow": "예상 달성률이 95% 이상이거나 필요 상향분이 잔여 목표의 5% 이하인 상태입니다.",
    "Red": "예상 달성률이 90% 이상이거나 필요 상향분이 잔여 목표의 15% 이하인 상태입니다.",
    "Black": "계산 오류, 상한 부족, 또는 예상 달성률/필요 상향 부담이 높은 상태입니다.",
    "N/A": "해당 보정 전략을 적용할 수 없는 상태입니다.",
}

AMOUNT_COLUMNS = {
    "monthly_target",
    "current_target_cum",
    "current_actual_cum",
    "remaining_target",
    "forecast_amount",
    "gap_to_target",
    "target_variance",
    "surplus_to_target",
    "required_uplift",
    "allocated_uplift",
    "unallocated_uplift",
    "revised_remaining_target",
    "stretch_uplift",
    "revised_monthly_target",
    "remaining_surplus_buffer",
    "minimum_remaining_to_hit_target",
    "relief_amount",
    "forecast_after_provision",
    "gap_after_provision",
    "next_close_required",
    "original_target",
    "uplift",
    "revised_target",
    "cap_target",
    "expected_after_revision",
    "final_actual",
    "cancellation_amount",
    "net_actual",
    "forecast_error",
    "abs_error",
    "mean_abs_error",
    "bias",
    "weighted_forecast",
    "weighted_forecast_amount",
    "confidence_lower",
    "confidence_upper",
    "forecast_lower",
    "forecast_upper",
    "lower_bound",
    "upper_bound",
}
RATE_COLUMNS = {
    "forecast_rate",
    "expected_rate",
    "allocation_weight",
    "final_achievement_rate",
    "error_rate",
    "signed_error_rate",
    "mean_error_rate",
    "median_error_rate",
}
DIRECT_EDITABLE_COLUMNS = (
    "sales_target_daily",
    "recognized_target_daily",
    "sales_actual_cum",
    "recognized_actual_cum",
)
ACTUAL_CUM_COLUMNS = (
    "sales_actual_cum",
    "recognized_actual_cum",
)
SAVED_ACTUAL_COLUMNS = (
    "date",
    "business_day_no",
    *ACTUAL_CUM_COLUMNS,
)
REPORT_GLOSSARY_GROUPS = (
    ("예측모델(F)", REPORT_FORECAST_MODEL_DEFINITIONS),
    ("목표 보정 전략(P)", REPORT_PROVISION_STRATEGY_DEFINITIONS),
    ("초과달성 운영전략(O)", REPORT_OVERACHIEVEMENT_STRATEGY_DEFINITIONS),
    ("유지/모니터링 전략(N)", REPORT_NEUTRAL_STRATEGY_DEFINITIONS),
    ("위험등급", REPORT_RISK_LEVEL_DEFINITIONS),
)
STRATEGY_LEVEL_COLUMNS = (
    "scenario_id",
    "target_status",
    "strategy_type",
    "provision_strategy",
    "monthly_target",
    "forecast_amount",
    "target_variance",
    "gap_to_target",
    "surplus_to_target",
    "required_uplift",
    "stretch_uplift",
    "revised_monthly_target",
    "remaining_surplus_buffer",
    "minimum_remaining_to_hit_target",
    "relief_amount",
    "revised_remaining_target",
    "forecast_after_provision",
    "gap_after_provision",
    "risk_level",
    "status",
    "recommended_action",
)
STRATEGY_LEVEL_CHART_COLUMNS = (
    "monthly_target",
    "forecast_amount",
    "revised_monthly_target",
    "target_variance",
    "gap_to_target",
    "surplus_to_target",
    "stretch_uplift",
    "remaining_surplus_buffer",
    "minimum_remaining_to_hit_target",
    "relief_amount",
)
SCENARIO_DAILY_FORECAST_COLUMNS = (
    "date",
    "date_label",
    "week_start",
    "week_end",
    "week_label",
    "week_no",
    "business_day_no",
    "is_close_day",
    "day_type",
    "close_type",
    "scenario_id",
    "series_type",
    "line_group",
    "daily_expected",
    "forecast_cum",
    "target_cum",
    "monthly_target",
    "achievement_rate",
    "target_achievement_rate",
    "achievement_label",
    "target_achievement_label",
    "forecast_label",
    "target_cum_label",
    "risk_level_label",
    "is_selected",
    "is_as_of_date",
)
SCENARIO_DAILY_DETAIL_COLUMNS = (
    "date",
    "scenario_id",
    "series_type",
    "day_type",
    "close_type",
    "daily_expected",
    "forecast_cum",
    "target_cum",
    "achievement_rate",
    "target_achievement_rate",
)
REMAINING_OPERATION_DIRECTION_COLUMNS = (
    "date",
    "date_label",
    "scenario_id",
    "strategy_type",
    "operation_mode",
    "day_type",
    "close_type",
    "original_target",
    "uplift",
    "revised_target",
    "expected_daily",
    "expected_rate",
    "direction",
    "direction_detail",
)
VALIDATION_COLUMN_LABELS = {
    "date": "날짜",
    "business_day_no": "영업일 번호",
    "is_close_day": "마감일 여부",
    "close_type": "마감 유형",
    "sales_target_daily": "판매실적 일 목표",
    "recognized_target_daily": "인정실적 일 목표",
    "sales_actual_cum": "판매실적 누적 실적",
    "recognized_actual_cum": "인정실적 누적 실적",
    "target_daily": "선택 지표의 일 목표",
    "actual_cum": "선택 지표의 누적 실적",
    "actual_daily": "일 실적",
    "monthly_target": "월 전체 목표",
    "current_target_cum": "기준일까지의 누적 목표",
    "current_actual_cum": "기준일까지의 누적 실적",
    "as_of_date": "기준일",
    "metric": "지표",
    "uplift_effective_rate": "목표 상향 반영률",
}
DISPLAY_COLUMN_LABELS = {
    **VALIDATION_COLUMN_LABELS,
    "scenario_id": "시나리오",
    "forecast_model": "예측모델",
    "provision_strategy": "운영전략",
    "forecast_rate": "예상 달성률",
    "remaining_target": "잔여 목표",
    "forecast_amount": "월말 예상 실적",
    "gap_to_target": "목표 미달 예상분",
    "target_variance": "목표 대비 차이",
    "surplus_to_target": "초과 예상분",
    "target_status": "목표 상태",
    "strategy_type": "전략 구분",
    "overachievement_strategy": "초과달성 전략",
    "required_uplift": "필요 상향",
    "allocated_uplift": "배분된 상향",
    "unallocated_uplift": "미배분 상향",
    "revised_remaining_target": "수정 잔여 목표",
    "stretch_uplift": "상향 목표 전환분",
    "revised_monthly_target": "운영전략 월 목표",
    "remaining_surplus_buffer": "잔여 안전버퍼",
    "minimum_remaining_to_hit_target": "목표 달성 최소 잔여 실적",
    "relief_amount": "품질관리 여유분",
    "forecast_after_provision": "전략 반영 후 예상",
    "gap_after_provision": "전략 반영 후 부족분",
    "next_close_date": "다음 마감일",
    "next_close_required": "다음 마감 누적선 필요실적",
    "risk_level": "위험등급",
    "status": "계산 상태",
    "recommended_action": "권장 조치",
    "comment": "설명",
    "warnings": "확인 사항",
    "date": "날짜",
    "day_name": "요일",
    "cycle_id": "마감차수",
    "cycle_start_date": "마감차수 시작일",
    "cycle_end_date": "마감차수 종료일",
    "is_completed": "완료 여부",
    "target_sum": "마감차수 목표 합계",
    "actual_sum": "마감차수 실적 합계",
    "achievement_rate": "마감차수 달성률",
    "row_count": "입력 행 수",
    "original_target": "기존 일 목표",
    "uplift": "추가 배분 목표",
    "revised_target": "수정 후 일 목표",
    "cap_target": "일별 허용 상한",
    "expected_after_revision": "수정 후 예상 일 실적",
    "expected_rate": "예상 달성률",
    "allocation_weight": "배분 비중",
    "run_id": "저장 ID",
    "run_datetime": "저장 시각",
    "target_month": "대상 월",
    "as_of_date": "기준일",
    "metric": "지표",
    "strategy_id": "전략 ID",
    "final_actual": "월마감 확정 실적",
    "final_achievement_rate": "확정 달성률",
    "final_status": "확정 목표 상태",
    "cancellation_amount": "취소/철회 금액",
    "net_actual": "순 확정 실적",
    "updated_at": "확정 저장 시각",
    "forecast_error": "예측 오차",
    "abs_error": "절대 오차",
    "error_rate": "오차율",
    "signed_error_rate": "방향성 오차율",
    "over_forecast_flag": "과대 예측 여부",
    "under_forecast_flag": "과소 예측 여부",
    "sample_count": "표본 수",
    "mean_abs_error": "평균 절대 오차",
    "mean_error_rate": "평균 오차율",
    "median_error_rate": "중앙 오차율",
    "bias": "bias",
    "best_model_by_error_rate": "최저 오차 모델",
    "weighted_forecast": "Weighted Forecast",
    "weighted_forecast_amount": "Weighted Forecast",
    "confidence_lower": "Confidence Band 하단",
    "confidence_upper": "Confidence Band 상단",
    "forecast_lower": "Confidence Band 하단",
    "forecast_upper": "Confidence Band 상단",
    "lower_bound": "Confidence Band 하단",
    "upper_bound": "Confidence Band 상단",
}
METRIC_DISPLAY_LABELS = {
    "sales": "판매실적",
    "recognized": "인정실적",
}
DISPLAY_VALUE_LABELS = {
    **METRIC_DISPLAY_LABELS,
    F1_CUMULATIVE_RATE: "F1 누적 달성률 모델",
    F2_LAST_TWO_CLOSES: "F2 직전 2개 완료 마감차수 모델",
    F3_DAY_CLOSE_WEIGHTED: "F3 마감일/비마감일 가중 모델",
    P1_ALL_REMAINING: "P1 전체 잔여일 배분",
    P2_CLOSE_DAY_FOCUSED: "P2 마감일 우선 배분",
    P3_NON_CLOSE_DAY_FOCUSED: "P3 비마감일 우선 배분",
    O1_TARGET_HOLD_BUFFER: "O1 목표 유지 안전버퍼",
    O2_STRETCH_TARGET_CAPTURE: "O2 상향 목표 전환",
    O3_QUALITY_GUARD_RELIEF: "O3 계약 품질 방어",
    N1_MAINTAIN_TARGET: "N1 목표 유지",
    N2_MONITOR_BUFFER: "N2 버퍼 모니터링",
    N3_QUALITY_CHECK: "N3 품질 점검",
    "UNDER_TARGET": "목표 미달",
    "ON_TARGET": "목표선 근접",
    "OVER_TARGET": "목표 초과",
    "UNKNOWN_TARGET_STATUS": "계산 불가",
    "PROVISION": "목표 보정",
    "OVERACHIEVEMENT": "초과달성 운영",
    "NEUTRAL": "유지/모니터링",
    "Green": "낮음",
    "Yellow": "주의",
    "Red": "높음",
    "Black": "매우 높음",
    "N/A": "해당 없음",
    "OK": "정상",
    "NO_GAP": "부족분 없음",
    "CAPACITY_LIMITED": "배분 한도 초과",
    "NOT_APPLICABLE": "적용 불가",
    "CALCULATION_ERROR": "계산 오류",
    "OVER_TARGET_MANAGED": "초과달성 관리",
    "ON_TARGET_MAINTAIN": "목표선 유지",
}
NEXT_CLOSE_REQUIRED_LABEL = "다음 마감 누적선 필요실적"
NEXT_CLOSE_REQUIRED_EXPLANATION = (
    "다음 마감 필요실적은 월 목표 부족분이 아니라, "
    "다음 마감일까지의 누적 계획선을 맞추기 위해 필요한 실적입니다."
)
KPI_HELP_TEXTS = {
    NEXT_CLOSE_REQUIRED_LABEL: NEXT_CLOSE_REQUIRED_EXPLANATION,
}
TARGET_STATUS_OPERATION_MODE_LABELS = {
    "UNDER_TARGET": "목표 보정 필요",
    "ON_TARGET": "유지/모니터링",
    "OVER_TARGET": "초과달성 관리",
}
OVERACHIEVEMENT_MATRIX_LABELS = {
    "O1": "버퍼 유지",
    "O2": "Stretch 전환",
    "O3": "품질 방어",
    O1_TARGET_HOLD_BUFFER: "버퍼 유지",
    O2_STRETCH_TARGET_CAPTURE: "Stretch 전환",
    O3_QUALITY_GUARD_RELIEF: "품질 방어",
}
VALIDATION_MESSAGE_TRANSLATIONS = {
    "business_day_no must be in ascending order.": (
        "영업일 번호가 순서대로 정렬되어 있어야 합니다. 1, 2, 3처럼 증가하는지 확인해 주세요."
    ),
    "as_of_date must exist in the input table.": (
        "선택한 기준일이 입력표 날짜에 없습니다. 입력표에 있는 날짜로 기준일을 선택해 주세요."
    ),
    "target_daily must not contain missing or invalid values.": (
        "선택한 지표의 일 목표에 빈값 또는 숫자가 아닌 값이 있습니다. 일 목표 칸을 숫자로 입력해 주세요."
    ),
    "target_daily must not be negative.": (
        "선택한 지표의 일 목표에 음수가 있습니다. 목표는 0 이상으로 입력해 주세요."
    ),
    "monthly_target must be greater than 0.": (
        "월 전체 목표 합계가 0입니다. 일 목표를 하나 이상 입력해 주세요."
    ),
    "actual_cum must be populated through as_of_date.": (
        "기준일까지의 누적 실적에 빈값이 있습니다. 기준일 이전과 기준일의 누적 실적을 모두 입력해 주세요."
    ),
    "actual_cum after as_of_date is populated.": (
        "기준일 이후 날짜에도 누적 실적이 입력되어 있습니다. 미래 날짜의 실적이 의도한 입력인지 확인해 주세요."
    ),
    "At least one is_close_day=True row is required.": (
        "마감일로 표시된 행이 없습니다. 마감일 여부 칸에 TRUE, Y, 1 중 하나로 표시된 행을 하나 이상 입력해 주세요."
    ),
    "F2 fallback warning: fewer than two completed close days exist through as_of_date.": (
        "기준일까지 완료된 마감일이 2개 미만이라 F2 방식은 F1 방식으로 대신 계산될 수 있습니다."
    ),
    "actual_cum decreases in the input table.": (
        "누적 실적이 이전 날짜보다 줄어드는 구간이 있습니다. 차감이나 환입이 의도된 값인지 확인해 주세요."
    ),
    "actual_daily calculated from actual_cum is negative.": (
        "누적 실적 차이로 계산한 일 실적이 음수입니다. 누적 실적이 중간에 감소했는지 확인해 주세요."
    ),
    "close_type is missing; blank close_type is allowed.": (
        "마감 유형 열이 없습니다. 계산은 가능하지만 마감 구분 설명은 비어 있을 수 있습니다."
    ),
    "close_type is blank for one or more close days.": (
        "마감일로 표시된 행 중 마감 유형이 비어 있습니다. 중간마감, 월마감 같은 구분값을 입력하면 해석이 쉬워집니다."
    ),
    "date contains missing or invalid values.": (
        "날짜 칸에 비어 있거나 읽을 수 없는 값이 있습니다. YYYY-MM-DD 형식으로 입력해 주세요."
    ),
    "as_of_date must be a valid date.": (
        "기준일을 날짜로 읽을 수 없습니다. 기준일을 다시 선택하거나 YYYY-MM-DD 형식으로 입력해 주세요."
    ),
    "is_close_day contains unsupported values.": (
        "마감일 여부 칸에 읽을 수 없는 값이 있습니다. TRUE/FALSE, Y/N, 1/0 중 하나로 입력해 주세요."
    ),
    "Calculation unavailable: as_of_date is not present in the input rows.": (
        "선택한 기준일을 입력표에서 찾을 수 없어 계산할 수 없습니다. 입력표에 있는 날짜로 기준일을 선택해 주세요."
    ),
    "Calculation unavailable: as_of_date is not present in input rows.": (
        "선택한 기준일을 입력표에서 찾을 수 없어 계산할 수 없습니다. 입력표에 있는 날짜로 기준일을 선택해 주세요."
    ),
    "Calculation unavailable: actual cumulative value is missing at as_of_date.": (
        "기준일의 누적 실적이 비어 있어 계산할 수 없습니다. 기준일 행의 누적 실적을 입력해 주세요."
    ),
    "Calculation unavailable: monthly_target is zero.": (
        "월 전체 목표가 0이라 계산할 수 없습니다. 일 목표를 입력해 주세요."
    ),
    "Calculation unavailable: current_target_cum is zero.": (
        "기준일까지의 누적 목표가 0이라 달성률 계산이 어렵습니다. 기준일 이전 일 목표를 확인해 주세요."
    ),
    "Calculation unavailable: uplift_effective_rate is zero.": (
        "목표 상향을 반영할 수 있는 비율이 0이라 보정 계산을 할 수 없습니다. 보정 전략이나 상한 설정을 확인해 주세요."
    ),
    "No next close day is present after as_of_date.": (
        "기준일 이후에 다음 마감일이 없습니다. 다음 마감 누적선 필요실적은 계산하지 않습니다."
    ),
    "Negative actual_daily values are present before or at as_of_date.": (
        "기준일까지의 일 실적 중 음수로 계산되는 날이 있습니다. 누적 실적 감소가 의도된 값인지 확인해 주세요."
    ),
    "F2_LAST_TWO_CLOSES fallback to F1_CUMULATIVE_RATE: fewer than two completed close cycles are available.": (
        "F2는 기준일까지 완료된 마감차수가 2개 미만이라 F1 방식으로 대신 계산했습니다."
    ),
    "F2_LAST_TWO_CLOSES fallback to F1_CUMULATIVE_RATE: last two completed close cycles have zero target.": (
        "F2는 최근 2개 완료 마감차수의 목표 합계가 0이라 F1 방식으로 대신 계산했습니다."
    ),
    "F3_DAY_CLOSE_WEIGHTED fallback: close-day and non-close-day historical targets are both required.": (
        "F3는 마감일과 비마감일의 과거 목표가 모두 필요하지만 일부가 부족해 F2 방식으로 대신 계산했습니다."
    ),
}
VALIDATION_TERM_REPLACEMENTS = {
    "F1_CUMULATIVE_RATE": "F1 누적 달성률 방식",
    "F2_LAST_TWO_CLOSES": "F2 직전 2개 마감차수 방식",
    "F3_DAY_CLOSE_WEIGHTED": "F3 마감일/비마감일 가중 방식",
    "business_day_no": "영업일 번호",
    "is_close_day": "마감일 여부",
    "close_type": "마감 유형",
    "target_daily": "일 목표",
    "actual_daily": "일 실적",
    "actual_cum": "누적 실적",
    "monthly_target": "월 전체 목표",
    "current_target_cum": "기준일까지의 누적 목표",
    "current_actual_cum": "기준일까지의 누적 실적",
    "as_of_date": "기준일",
    "uplift_effective_rate": "목표 상향 반영률",
    "fallback": "대체 계산",
}
VISUAL_METRIC_DEFINITIONS = {
    "daily_forecast_cum": {
        "label": "주간 누적 예상",
        "unit": "억원",
        "definition": "기준일까지는 확정 누적 실적, 기준일 이후는 각 시나리오의 예상 실적을 주간 말 기준으로 누적한 값입니다.",
    },
    "daily_target_cum": {
        "label": "주간 누적 목표선",
        "unit": "억원",
        "definition": "입력표의 일 목표를 날짜 순서대로 누적한 뒤 주간 말 기준으로 표시한 공식 계획선입니다.",
    },
    "daily_achievement_rate": {
        "label": "주간 월 목표 달성률",
        "unit": "%",
        "definition": "각 주의 누적 실적 또는 누적 예상 실적을 공식 월 목표로 나눈 비율입니다.",
    },
    "forecast_amount": {
        "label": "월말 예상 실적(보정 전)",
        "unit": "억원",
        "definition": "선택한 F 방식만 적용해 계산한 월말 예상 실적입니다. 잔여 목표를 다시 배분하기 전 숫자입니다.",
    },
    "forecast_after_provision": {
        "label": "월말 예상 실적(보정 후)",
        "unit": "억원",
        "definition": "F 방식의 예상에 P 보정 또는 O/N 운영전략을 반영한 뒤의 월말 예상 실적입니다.",
    },
    "gap_to_target": {
        "label": "목표 미달 예상분",
        "unit": "억원",
        "definition": "월 목표보다 예상 실적이 부족한 금액입니다. 목표 이상이면 0으로 표시합니다.",
    },
    "target_variance": {
        "label": "목표 대비 차이",
        "unit": "억원",
        "definition": "월말 예상 실적에서 월 목표를 뺀 값입니다. 양수면 초과 예상, 음수면 미달 예상입니다.",
    },
    "surplus_to_target": {
        "label": "초과 예상분",
        "unit": "억원",
        "definition": "월 목표를 넘길 것으로 예상되는 금액입니다. 미달이면 0으로 표시합니다.",
    },
    "required_uplift": {
        "label": "목표 달성에 필요한 추가 실적",
        "unit": "억원",
        "definition": "목표 미달 시 월 목표를 맞추기 위해 기준일 이후 잔여 기간에 추가로 만들어야 하는 실적 규모입니다.",
    },
    "gap_after_provision": {
        "label": "보정 후 목표 차이(+부족/-초과)",
        "unit": "억원",
        "definition": "보정 후에도 월 목표와 예상 실적 사이에 남은 부족분입니다. 초과달성 전략에서는 부족분 대신 초과 예상분과 버퍼를 함께 확인합니다.",
    },
    "monthly_target": {
        "label": "공식 월 목표",
        "unit": "억원",
        "definition": "입력표의 일 목표를 모두 더한 공식 월 목표입니다.",
    },
    "revised_monthly_target": {
        "label": "운영전략상 월 목표 수준",
        "unit": "억원",
        "definition": "선택한 운영전략에서 관리할 월 목표 수준입니다. O2는 초과 예상분 일부를 반영해 상향될 수 있습니다.",
    },
    "stretch_uplift": {
        "label": "Stretch 전환분",
        "unit": "억원",
        "definition": "O2 전략에서 초과 예상분 중 추가 성장 목표로 전환한 금액입니다.",
    },
    "remaining_surplus_buffer": {
        "label": "잔여 안전버퍼",
        "unit": "억원",
        "definition": "초과 예상분 중 취소, 철회, 미결제, 실적 조정 리스크에 대비해 남겨 두는 금액입니다.",
    },
    "minimum_remaining_to_hit_target": {
        "label": "목표 달성까지 필요한 최소 잔여 실적",
        "unit": "억원",
        "definition": "현재 누적 실적 기준으로 공식 월 목표를 맞추는 데 필요한 최소 잔여 실적입니다.",
    },
    "relief_amount": {
        "label": "품질관리 여유분",
        "unit": "억원",
        "definition": "O3 전략에서 무리한 추가 압박 대신 계약 품질과 결제완료율 관리에 활용할 수 있는 여유분입니다.",
    },
    "original_target": {
        "label": "기존 일 목표",
        "unit": "억원",
        "definition": "입력표에 원래 들어 있던 해당 날짜의 목표입니다.",
    },
    "uplift": {
        "label": "추가 배분 목표",
        "unit": "억원",
        "definition": "목표 달성을 위해 해당 날짜에 새로 더 배분한 목표입니다.",
    },
    "revised_target": {
        "label": "수정 후 일 목표",
        "unit": "억원",
        "definition": "기존 일 목표에 추가 배분 목표를 더한 값입니다.",
    },
    "cap_target": {
        "label": "일별 허용 상한",
        "unit": "억원",
        "definition": "설정한 cap rate를 반영했을 때 해당 날짜에 배분할 수 있는 최대 목표입니다.",
    },
    "expected_after_revision": {
        "label": "수정 후 예상 일 실적",
        "unit": "억원",
        "definition": "수정 후 일 목표와 예상 달성률을 바탕으로 계산한 해당 날짜의 예상 실적입니다.",
    },
    "target_sum": {
        "label": "마감차수 목표 합계",
        "unit": "억원",
        "definition": "해당 마감차수 기간에 포함된 일 목표를 모두 더한 값입니다.",
    },
    "actual_sum": {
        "label": "마감차수 실적 합계",
        "unit": "억원",
        "definition": "해당 마감차수 기간에 실제로 발생한 실적을 모두 더한 값입니다.",
    },
    "achievement_rate": {
        "label": "마감차수 달성률",
        "unit": "%",
        "definition": "마감차수 실적 합계를 마감차수 목표 합계로 나눈 비율입니다.",
    },
}
VISUAL_READING_GUIDES = {
    "scenario_daily_progress": {
        "title": "주간 목표 달성률 전망",
        "steps": (
            "100% 기준선을 중심으로 기준일까지의 확정 달성률과 이후 주간 시나리오 달성률을 비교합니다.",
            "마우스 휠과 드래그로 특정 주간 구간을 확대/축소해 마감 전후 변화를 봅니다.",
            "선 끝 라벨의 최종 달성률과 목표 대비 차이를 보고 우위 시나리오를 고릅니다.",
        ),
        "decision": "100% 위로 안정적으로 올라서고, 같은 주차에서 더 높은 달성률을 보이는 조합이 시각적으로 우위입니다.",
    },
    "scenario_amount": {
        "title": "월말 예상 실적 비교",
        "steps": (
            "먼저 공식 월 목표를 기준선으로 잡습니다.",
            "월말 예상 실적(보정 전)이 목표보다 낮은지, 높은지 확인합니다.",
            "전략 반영 후 예상이 목표선을 회복하는지 보고 선택 전략의 효과를 판단합니다.",
        ),
        "decision": "전략 반영 후 예상이 목표보다 낮으면 보정 강도가 부족하고, 목표보다 높으면 초과분 관리 전략을 함께 봅니다.",
    },
    "scenario_target_position": {
        "title": "목표선 대비 예상 실적",
        "steps": (
            "빨간 기준선은 공식 월 목표입니다.",
            "막대 끝이 기준선 오른쪽이면 목표 초과, 왼쪽이면 목표 미달입니다.",
            "선택 시나리오는 진한 테두리로 표시해 다른 조합과 바로 비교합니다.",
        ),
        "decision": "기준선을 넘기는 조합 중 위험등급과 운영 부담이 낮은 조합을 우선 검토합니다.",
    },
    "scenario_gap_position": {
        "title": "부족/초과 금액",
        "steps": (
            "0선을 기준으로 오른쪽은 초과 예상, 왼쪽은 미달 예상입니다.",
            "막대 길이가 길수록 목표선에서 더 멀리 떨어진 조합입니다.",
            "미달 막대는 보정 필요 규모, 초과 막대는 버퍼 또는 Stretch 후보 규모로 봅니다.",
        ),
        "decision": "미달 폭이 큰 조합은 실행 부담이 크고, 초과 폭이 큰 조합은 초과분 관리 전략이 중요합니다.",
    },
    "scenario_heatmap": {
        "title": "시나리오 조합 지도",
        "steps": (
            "행은 예측모델(F1~F3), 열은 운영전략(P/O/N)을 뜻합니다.",
            "붉은 칸은 목표 미달, 초록 칸은 목표 초과 방향입니다.",
            "칸 안 숫자는 월 목표 대비 부족/초과 금액입니다.",
        ),
        "decision": "같은 색이 반복되면 모델보다 시장 흐름 영향이 크고, 행마다 색이 달라지면 예측모델 선택 민감도가 큽니다.",
    },
    "scenario_status": {
        "title": "목표 상태 확인",
        "steps": (
            "목표 대비 차이는 양수면 초과 예상, 음수면 미달 예상으로 읽습니다.",
            "미달 구간은 목표 미달 예상분과 목표 달성에 필요한 추가 실적을 함께 봅니다.",
            "초과 구간은 초과 예상분이 운영상 버퍼인지, 상향 목표로 전환할 수 있는지 확인합니다.",
        ),
        "decision": "부족분이 큰 시나리오는 실행 부담이 높고, 초과분이 큰 시나리오는 품질 리스크와 Stretch 전환 가능성을 검토합니다.",
    },
    "scenario_matrix": {
        "title": "시나리오 숫자표",
        "steps": (
            "행은 예측모델(F1~F3), 열은 운영전략(P/O/N)을 뜻합니다.",
            "먼저 같은 행 안에서 전략별 월말 예상 실적 차이를 비교합니다.",
            "그다음 같은 열 안에서 예측모델별 민감도를 비교해 보수적/공격적 전망 차이를 봅니다.",
        ),
        "decision": "숫자가 가장 큰 조합보다, KPI 위험등급과 실행 가능한 보정 전략까지 같이 맞는 조합을 선택합니다.",
    },
    "target_allocation": {
        "title": "일자별 목표 변화",
        "steps": (
            "기존 일 목표를 해당 날짜의 원래 계획선으로 봅니다.",
            "추가 배분 목표는 부족분을 메우기 위해 새로 얹은 부담입니다.",
            "수정 후 일 목표는 기존 목표와 추가 배분이 반영된 최종 관리 목표입니다.",
        ),
        "decision": "수정 후 일 목표가 특정 날짜에 과도하게 몰리면 배분 전략이나 상한 설정을 재검토합니다.",
    },
    "target_uplift": {
        "title": "일자별 추가 부담",
        "steps": (
            "막대는 목표 달성을 위해 해당 날짜에 추가로 얹힌 목표입니다.",
            "마감일에 막대가 몰리면 마감 당일 의존도가 높은 계획입니다.",
            "일반일에도 막대가 넓게 퍼지면 남은 기간 전체에 부담을 분산한 계획입니다.",
        ),
        "decision": "특정 날짜의 추가 부담이 과도하면 P2/P3 같은 배분 전략을 바꿔 비교합니다.",
    },
    "target_stack": {
        "title": "기존 목표와 추가 배분",
        "steps": (
            "회색은 기존 일 목표, 주황색은 새로 더한 추가 배분 목표입니다.",
            "막대 전체 높이가 수정 후 일 목표입니다.",
            "상한선에 가까운 날짜가 많을수록 실행 여력이 부족하다는 신호입니다.",
        ),
        "decision": "추가 배분이 상한선 근처에 반복되면 목표 상향 강도나 잔여 기간 운영 계획을 재검토합니다.",
    },
    "target_cap": {
        "title": "상한과 예상 실적",
        "steps": (
            "일별 허용 상한은 해당 날짜에 배분 가능한 최대 목표선입니다.",
            "수정 후 예상 일 실적이 상한보다 낮은지 확인해 목표가 현실적인지 봅니다.",
            "상한에 계속 붙어 있으면 잔여 기간 전체의 실행 여력이 부족하다는 신호입니다.",
        ),
        "decision": "상한을 자주 넘거나 근접하면 마감일/비마감일 배분 방식 또는 월 목표 상향 부담을 다시 봅니다.",
    },
    "close_cycle_amount": {
        "title": "마감차수별 목표와 실적",
        "steps": (
            "각 마감차수의 목표 합계를 기준으로 잡습니다.",
            "실적 합계가 목표 합계보다 높으면 해당 차수는 초과 달성, 낮으면 미달입니다.",
            "미달 차수가 반복되는지, 특정 마감차수에서만 흔들리는지 흐름을 봅니다.",
        ),
        "decision": "최근 마감차수에서 미달이 커질수록 남은 기간 보정 필요성이 높아집니다.",
    },
    "close_cycle_rate": {
        "title": "마감차수별 달성률",
        "steps": (
            "100%를 기준선으로 두고 각 마감차수가 목표를 넘겼는지 확인합니다.",
            "달성률이 상승 중인지 하락 중인지 방향을 봅니다.",
            "최근 2개 마감차수의 흐름은 F2 예측모델의 근거가 되므로 특히 따로 봅니다.",
        ),
        "decision": "최근 달성률이 100% 아래로 내려가면 월말 예상보다 실제 마감 리스크를 더 보수적으로 봅니다.",
    },
    "strategy_amount": {
        "title": "전략별 월 목표 수준",
        "steps": (
            "공식 월 목표와 월말 예상 실적의 간격을 먼저 봅니다.",
            "운영전략상 월 목표 수준이 공식 목표와 같은지, 상향됐는지 확인합니다.",
            "상향된 목표가 예상 실적 안에서 감당되는지 비교합니다.",
        ),
        "decision": "상향 목표가 예상 실적보다 높으면 공격적인 전략이고, 공식 목표를 유지하면 방어적인 전략입니다.",
    },
    "strategy_buffer": {
        "title": "전략별 초과/완화 수준",
        "steps": (
            "초과 예상분이 있다면 안전버퍼, Stretch 전환분, 품질관리 여유분으로 나뉘는 구조를 봅니다.",
            "목표 미달이면 목표 달성에 필요한 추가 실적이 얼마나 남는지 봅니다.",
            "각 전략이 숫자를 키우는 전략인지, 리스크를 줄이는 전략인지 구분합니다.",
        ),
        "decision": "초과분이 크면 성장 전환과 버퍼 유지의 균형을, 부족분이 크면 실제 추가 실행 가능성을 우선 판단합니다.",
    },
}


def main() -> None:
    """Render the Streamlit app."""
    if st is None:
        raise RuntimeError("Streamlit is required to run app.py. Install requirements.txt first.")

    st.set_page_config(page_title="월마감 영업실적 예측툴", layout="wide")
    _inject_app_styles()
    if not _require_access_password():
        st.stop()

    st.title("월마감 영업실적 예측툴")

    config = load_model_config()
    df, source_label = _render_file_upload()
    if df is None:
        st.stop()
    historical_df, historical_source_label = _render_historical_upload()

    st.caption(f"입력 소스: {source_label}")
    df = _render_input_editor(df, source_label)
    metric, as_of_date, forecast_choice, provision_choice, config = _render_settings(
        df,
        config,
    )

    results = calculate_validated_results(df, as_of_date, metric, config)
    validation_result = results["validation"]

    st.header("4. 입력값 점검")
    st.caption("입력표가 계산 가능한 상태인지 확인하고, 문제가 있으면 쉬운 문장으로 안내합니다.")
    _render_validation(validation_result)
    if validation_result["errors"]:
        st.info("입력값에 고쳐야 할 항목이 있어 계산을 중단했습니다. 위 메시지를 확인한 뒤 입력표를 수정해 주세요.")
        return

    scenario_df = results["scenario_df"]
    next_close_result = results["next_close_result"]
    close_cycle_df = results["close_cycle_df"]
    selected_scenario_id = _render_selected_scenario_picker(
        scenario_df,
        forecast_choice,
        provision_choice,
    )
    selected_row = _selected_scenario_row(scenario_df, selected_scenario_id)
    forecast_result, provision_result = run_selected_scenario_detail(
        df,
        as_of_date,
        metric,
        selected_scenario_id,
        config,
    )
    revised_targets_df = provision_result.get("allocation_by_day", pd.DataFrame())
    historical_context = build_historical_context(
        historical_df,
        df,
        as_of_date,
        metric,
        validation_result,
        historical_source_label,
    )

    st.header("5. KPI")
    _render_kpis(
        validation_result,
        scenario_df,
        next_close_result,
        selected_row,
    )

    st.header("6. 본문")
    _render_body(
        scenario_df,
        selected_scenario_id,
        selected_row,
        forecast_result,
        provision_result,
        revised_targets_df,
        close_cycle_df,
        next_close_result,
        validation_result,
        historical_context,
        metric,
        as_of_date,
        df,
        config,
    )

    st.header("7. 다운로드")
    report_text = build_daily_report_text(
        scenario_df,
        next_close_result,
        selected_scenario_id=selected_scenario_id,
    )
    summary_dict = build_summary_dict(
        validation_result,
        selected_row,
        next_close_result,
        metric,
        as_of_date,
    )
    report_bytes, report_name = build_excel_report_bytes(
        summary_dict,
        scenario_df,
        _as_dataframe(revised_targets_df),
        close_cycle_df,
        build_display_validation_result(validation_result),
        report_text,
        metric,
        as_of_date,
    )
    st.download_button(
        "엑셀 리포트 다운로드",
        data=report_bytes,
        file_name=report_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _require_access_password() -> bool:
    configured_password, configured_password_hash = _configured_access_credentials()
    is_configured = bool(configured_password or configured_password_hash)
    if st.session_state.get(ACCESS_SESSION_STATE_KEY) and is_configured:
        _render_access_logout()
        return True

    st.title("월마감 영업실적 예측툴")
    st.caption("링크를 받은 대상자에게만 제공되는 제한 배포 화면입니다.")

    if not is_configured:
        st.warning("접속 비밀번호가 설정되지 않아 앱을 열 수 없습니다.")
        st.code(
            "APP_ACCESS_PASSWORD=공유할_접속_비밀번호",
            language="text",
        )
        st.caption("배포 환경의 Secrets 또는 환경변수에 위 값을 설정한 뒤 앱을 다시 시작하세요.")
        return False

    with st.form("access_password_form", clear_on_submit=True):
        password = st.text_input("접속 비밀번호", type="password")
        submitted = st.form_submit_button("입장")

    if submitted:
        if verify_access_password(
            password,
            configured_password=configured_password,
            configured_password_hash=configured_password_hash,
        ):
            st.session_state[ACCESS_SESSION_STATE_KEY] = True
            _rerun_app()
            return False
        st.error("비밀번호가 일치하지 않습니다.")

    return False


def _render_access_logout() -> None:
    with st.sidebar:
        st.caption("제한 배포 모드")
        if st.button("로그아웃"):
            st.session_state.pop(ACCESS_SESSION_STATE_KEY, None)
            _rerun_app()


def _rerun_app() -> None:
    if hasattr(st, "rerun"):
        st.rerun()
    else:  # pragma: no cover - compatibility for older Streamlit runtimes.
        st.experimental_rerun()


def _configured_access_credentials() -> tuple[str | None, str | None]:
    return (
        _read_configured_setting(ACCESS_PASSWORD_SETTING_KEYS),
        _read_configured_setting(ACCESS_PASSWORD_HASH_SETTING_KEYS),
    )


def _read_configured_setting(setting_keys: tuple[str, ...]) -> str | None:
    for key in setting_keys:
        value = _clean_optional_secret(os.environ.get(key))
        if value:
            return value

    if st is None:
        return None

    for key in setting_keys:
        try:
            value = _clean_optional_secret(st.secrets.get(key))
        except Exception:  # noqa: BLE001 - Streamlit raises different errors when secrets are absent.
            continue
        if value:
            return value
    return None


def _clean_optional_secret(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def verify_access_password(
    candidate_password: str,
    *,
    configured_password: str | None = None,
    configured_password_hash: str | None = None,
) -> bool:
    """Verify an access password against plain or SHA-256 configured credentials."""
    candidate = str(candidate_password or "")
    expected_password = _clean_optional_secret(configured_password)
    expected_hash = _clean_optional_secret(configured_password_hash)

    if expected_password and hmac.compare_digest(candidate, expected_password):
        return True

    if expected_hash:
        candidate_hash = hashlib.sha256(candidate.encode("utf-8")).hexdigest()
        return hmac.compare_digest(candidate_hash, expected_hash.lower())

    return False


def _inject_app_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --app-bg: #f6f8fb;
            --panel-bg: #ffffff;
            --line-soft: #d9e2ec;
            --line-strong: #b8c6d6;
            --text-main: #18212f;
            --text-muted: #667085;
            --accent: #1f6f78;
            --accent-soft: #e7f3f4;
            --font-title: 1.72rem;
            --font-section: 1.12rem;
            --font-subsection: 0.98rem;
            --font-body: 0.88rem;
            --font-control: 0.86rem;
            --font-caption: 0.78rem;
            --font-small: 0.72rem;
            --font-kpi-value: 1.02rem;
            --metric-card-height: 100px;
            --line-body: 1.48;
            --line-tight: 1.22;
        }

        .stApp {
            background: var(--app-bg);
            color: var(--text-main);
            font-size: var(--font-body);
            line-height: var(--line-body);
        }

        [data-testid="stHeader"] {
            background: rgba(246, 248, 251, 0.92);
            border-bottom: 1px solid rgba(217, 226, 236, 0.72);
        }

        footer {
            display: none !important;
            visibility: hidden !important;
        }

        .block-container {
            max-width: 1480px;
            padding-top: 1.5rem;
            padding-bottom: 4rem;
        }

        h1 {
            color: var(--text-main);
            font-size: var(--font-title) !important;
            font-weight: 720 !important;
            line-height: var(--line-tight) !important;
            letter-spacing: 0 !important;
            margin-bottom: 1.1rem !important;
        }

        h2 {
            color: var(--text-main);
            font-size: var(--font-section) !important;
            font-weight: 680 !important;
            line-height: var(--line-tight) !important;
            letter-spacing: 0 !important;
            margin-top: 1.6rem !important;
            padding-top: 1.05rem !important;
            border-top: 1px solid var(--line-soft);
        }

        h3 {
            color: var(--text-main);
            font-size: var(--font-subsection) !important;
            font-weight: 650 !important;
            line-height: var(--line-tight) !important;
            letter-spacing: 0 !important;
            margin-top: 1rem !important;
            margin-bottom: 0.45rem !important;
        }

        p, li, label, div[data-testid="stMarkdownContainer"] {
            color: var(--text-main);
            font-size: var(--font-body) !important;
            line-height: var(--line-body) !important;
            letter-spacing: 0 !important;
        }

        div[data-testid="stCaptionContainer"],
        div[data-testid="stCaptionContainer"] p,
        small {
            color: var(--text-muted) !important;
            font-size: var(--font-caption) !important;
            line-height: 1.38 !important;
            letter-spacing: 0 !important;
        }

        [data-testid="stMetric"] {
            height: var(--metric-card-height);
            min-height: var(--metric-card-height);
            box-sizing: border-box;
            padding: 0.58rem 0.72rem;
            background: var(--panel-bg);
            border: 1px solid var(--line-soft);
            border-left: 3px solid var(--accent);
            border-radius: 8px;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
        }

        [data-testid="stMetricLabel"],
        [data-testid="stMetricLabel"] p {
            color: var(--text-muted) !important;
            font-size: var(--font-small) !important;
            font-weight: 620 !important;
            line-height: var(--line-tight) !important;
            margin-bottom: 0.2rem !important;
        }

        [data-testid="stMetricValue"] {
            color: var(--text-main) !important;
            font-size: var(--font-kpi-value) !important;
            font-weight: 700 !important;
            line-height: var(--line-tight) !important;
            letter-spacing: 0 !important;
        }

        [data-testid="stMetricDelta"] {
            font-size: var(--font-small) !important;
            line-height: 1.15 !important;
        }

        div[data-testid="stAlert"] {
            border-radius: 8px;
            border: 1px solid var(--line-soft);
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        }

        div[data-testid="stDataFrame"],
        div[data-testid="stTable"] {
            border: 1px solid var(--line-soft);
            border-radius: 8px;
            overflow: hidden;
            background: var(--panel-bg);
        }

        div[data-testid="stDataFrame"] *,
        div[data-testid="stTable"] *,
        [data-testid="stDataEditor"] * {
            font-size: var(--font-control) !important;
            line-height: 1.36 !important;
        }

        div[data-testid="stTabs"] [role="tablist"] {
            gap: 0.2rem;
            border-bottom: 1px solid var(--line-soft);
        }

        button[data-baseweb="tab"] {
            border-radius: 6px 6px 0 0;
            padding: 0.42rem 0.76rem;
            color: var(--text-muted);
            font-size: var(--font-control) !important;
            font-weight: 620;
            line-height: var(--line-tight) !important;
        }

        button[data-baseweb="tab"][aria-selected="true"] {
            background: var(--accent-soft);
            color: var(--accent);
        }

        div[data-testid="stFileUploader"] section,
        div[data-testid="stExpander"] details {
            border: 1px solid var(--line-soft);
            border-radius: 8px;
            background: var(--panel-bg);
        }

        [data-testid="stFileUploaderDropzone"] button [data-testid="stIconMaterial"],
        [data-testid="stFileUploaderDropzone"] button [data-testid="stMarkdownContainer"],
        [data-testid="stFileUploaderDropzoneInstructions"] {
            display: none !important;
        }

        [data-testid="stFileUploaderDropzone"] button::after {
            content: "파일 선택";
            font-size: var(--font-control);
            font-weight: 650;
            color: var(--text-main);
        }

        [data-testid="stFileUploaderDropzone"]::after {
            content: "CSV 또는 XLSX 파일을 업로드할 수 있습니다.";
            color: var(--text-muted);
            font-size: var(--font-caption);
            line-height: 1.35;
        }

        div[data-testid="stExpander"] summary {
            font-size: var(--font-control) !important;
            font-weight: 650;
            color: var(--text-main);
            line-height: var(--line-tight) !important;
        }

        div[data-testid="stButton"] button,
        div[data-testid="stDownloadButton"] button {
            border-radius: 6px;
            border: 1px solid var(--line-strong);
            font-size: var(--font-control) !important;
            font-weight: 650;
            line-height: var(--line-tight) !important;
            box-shadow: 0 1px 2px rgba(16, 24, 40, 0.05);
        }

        div[data-testid="stSelectbox"] label,
        div[data-testid="stDateInput"] label,
        div[data-testid="stNumberInput"] label,
        div[data-testid="stTextInput"] label,
        div[data-testid="stFileUploader"] label {
            font-size: var(--font-control) !important;
            font-weight: 620 !important;
            line-height: var(--line-tight) !important;
        }

        div[data-baseweb="select"] *,
        div[data-baseweb="input"] *,
        div[data-baseweb="base-input"] *,
        div[data-testid="stDateInput"] * {
            font-size: var(--font-control) !important;
            line-height: 1.34 !important;
        }

        textarea,
        input {
            border-radius: 6px !important;
            font-size: var(--font-control) !important;
            line-height: 1.42 !important;
        }

        textarea[aria-label="자동 보고문"] {
            font-size: var(--font-body) !important;
            line-height: 1.58 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def calculate_validated_results(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Validate input and run calculations only when no errors exist."""
    validation_result = validate_input(df, as_of_date, metric, config)
    if validation_result["errors"]:
        return {"validation": validation_result}

    return {
        "validation": validation_result,
        "scenario_df": run_scenario_grid(df, as_of_date, metric, config),
        "next_close_result": calculate_next_close_required(
            df,
            as_of_date,
            metric,
            config,
        ),
        "close_cycle_df": build_close_cycle_summary(df, metric, as_of_date),
    }


def default_as_of_date(
    df: pd.DataFrame,
    metric: str,
    today: object | None = None,
) -> pd.Timestamp:
    """Return the latest input business date before today."""
    _ = metric
    dates = pd.to_datetime(df["date"], errors="raise").dt.normalize()
    current_date = _current_app_date(today)
    previous_business_dates = dates.loc[dates.dt.date < current_date]
    if not previous_business_dates.empty:
        return previous_business_dates.iloc[-1]
    return dates.iloc[0]


def _current_app_date(today: object | None = None) -> object:
    if today is not None:
        return pd.Timestamp(today).date()
    return pd.Timestamp.now(tz=APP_TIMEZONE).date()


def normalize_direct_input_edits(df: pd.DataFrame) -> pd.DataFrame:
    """Return editor data with target and actual columns converted for calculation."""
    normalized = df.copy()
    for column in DIRECT_EDITABLE_COLUMNS:
        if column not in normalized.columns:
            continue
        values = normalized[column].replace(r"^\s*$", pd.NA, regex=True)
        normalized[column] = pd.to_numeric(values, errors="coerce").astype(float)
    return normalized


def load_saved_actuals(path: str | Path = SAVED_ACTUALS_PATH) -> pd.DataFrame:
    """Load locally saved cumulative actual values."""
    saved_path = Path(path)
    if not saved_path.exists():
        return pd.DataFrame(columns=SAVED_ACTUAL_COLUMNS)
    return _normalize_saved_actuals(pd.read_csv(saved_path, encoding="utf-8-sig"))


def save_actual_values(
    df: pd.DataFrame,
    path: str | Path = SAVED_ACTUALS_PATH,
) -> Path:
    """Persist cumulative actual values for future app defaults."""
    saved_path = Path(path)
    saved_path.parent.mkdir(parents=True, exist_ok=True)
    saved_actuals = _build_saved_actuals(df)
    saved_actuals.to_csv(saved_path, index=False, encoding="utf-8-sig")
    return saved_path


def apply_saved_actuals(
    df: pd.DataFrame,
    saved_actuals: pd.DataFrame,
) -> pd.DataFrame:
    """Apply saved actual values to matching date and business-day rows."""
    saved = _normalize_saved_actuals(saved_actuals)
    if saved.empty:
        return df.copy()

    result = df.copy()
    result["_date_key"] = pd.to_datetime(result["date"], errors="coerce").dt.normalize()
    result["_business_day_key"] = pd.to_numeric(
        result["business_day_no"],
        errors="coerce",
    ).astype("Int64")

    saved = saved.rename(
        columns={
            "date": "_date_key",
            "business_day_no": "_business_day_key",
            **{column: f"{column}_saved" for column in ACTUAL_CUM_COLUMNS},
        }
    )
    saved["_saved_actual_row"] = True
    merged = result.merge(
        saved,
        on=["_date_key", "_business_day_key"],
        how="left",
        sort=False,
    )
    matched = merged["_saved_actual_row"].fillna(False).astype(bool)
    for column in ACTUAL_CUM_COLUMNS:
        saved_column = f"{column}_saved"
        if column in result.columns and saved_column in merged.columns:
            result.loc[matched, column] = merged.loc[matched, saved_column].to_numpy()

    return result.drop(columns=["_date_key", "_business_day_key"])


def clear_saved_actuals(path: str | Path = SAVED_ACTUALS_PATH) -> None:
    """Delete locally saved actual defaults when the user asks to reset them."""
    saved_path = Path(path)
    if saved_path.exists():
        saved_path.unlink()


def _build_saved_actuals(df: pd.DataFrame) -> pd.DataFrame:
    result = pd.DataFrame(columns=SAVED_ACTUAL_COLUMNS)
    if "date" not in df.columns or "business_day_no" not in df.columns:
        return result

    result["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    result["business_day_no"] = pd.to_numeric(
        df["business_day_no"],
        errors="coerce",
    ).astype("Int64")
    for column in ACTUAL_CUM_COLUMNS:
        if column not in df.columns:
            result[column] = pd.NA
            continue
        values = df[column].replace(r"^\s*$", pd.NA, regex=True)
        result[column] = pd.to_numeric(values, errors="coerce")

    valid_rows = result["date"].notna() & result["business_day_no"].notna()
    return result.loc[valid_rows, list(SAVED_ACTUAL_COLUMNS)].reset_index(drop=True)


def _normalize_saved_actuals(saved_actuals: pd.DataFrame) -> pd.DataFrame:
    result = saved_actuals.copy()
    for column in SAVED_ACTUAL_COLUMNS:
        if column not in result.columns:
            result[column] = pd.NA

    result = result.loc[:, list(SAVED_ACTUAL_COLUMNS)]
    result["date"] = pd.to_datetime(result["date"], errors="coerce").dt.normalize()
    result["business_day_no"] = pd.to_numeric(
        result["business_day_no"],
        errors="coerce",
    ).astype("Int64")
    for column in ACTUAL_CUM_COLUMNS:
        values = result[column].replace(r"^\s*$", pd.NA, regex=True)
        result[column] = pd.to_numeric(values, errors="coerce")

    result = result.dropna(subset=["date", "business_day_no"])
    result = result.drop_duplicates(["date", "business_day_no"], keep="last")
    return result.reset_index(drop=True)


def build_runtime_config(
    base_config: dict[str, Any],
    close_day_cap_rate: float,
    non_close_day_cap_rate: float,
) -> dict[str, Any]:
    """Return a calculation config without mutating the loaded YAML config."""
    runtime_config = dict(base_config)
    runtime_config["close_day_cap_rate"] = float(close_day_cap_rate)
    runtime_config["non_close_day_cap_rate"] = float(non_close_day_cap_rate)
    return runtime_config


def run_selected_scenario_detail(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    scenario_id: str,
    config: dict[str, Any],
) -> tuple[dict[str, object], dict[str, object]]:
    """Run the selected scenario pair and return detailed forecast and strategy data."""
    forecast_key, strategy_key = scenario_id.split("_", maxsplit=1)
    forecast_model = FORECAST_MODEL_OPTIONS[forecast_key]
    forecast_result = run_forecast_model(
        df,
        metric,
        as_of_date,
        forecast_model,
        config,
    )
    if strategy_key in PROVISION_STRATEGY_OPTIONS:
        strategy_result = run_provision_model(
            df,
            forecast_result,
            as_of_date,
            metric,
            PROVISION_STRATEGY_OPTIONS[strategy_key],
            config,
        )
    elif strategy_key in OVERACHIEVEMENT_STRATEGY_OPTIONS:
        strategy_result = run_overachievement_strategy(
            forecast_result,
            OVERACHIEVEMENT_STRATEGY_OPTIONS[strategy_key],
            config,
        )
    elif strategy_key in NEUTRAL_STRATEGY_OPTIONS:
        strategy_result = run_neutral_strategy(
            forecast_result,
            NEUTRAL_STRATEGY_OPTIONS[strategy_key],
        )
    else:
        raise ValueError(f"지원하지 않는 시나리오 전략입니다: {strategy_key}")
    return forecast_result, strategy_result


def build_scenario_matrix(scenario_df: pd.DataFrame) -> pd.DataFrame:
    """Return a 3x3 display matrix for forecast/strategy scenarios."""
    matrix = pd.DataFrame(
        index=["F1", "F2", "F3"],
        columns=_ordered_strategy_keys(scenario_df),
    )
    for _, row in scenario_df.iterrows():
        scenario_id = str(row.get("scenario_id", ""))
        if "_" not in scenario_id:
            continue
        forecast_key, strategy_key = scenario_id.split("_", maxsplit=1)
        matrix.loc[forecast_key, strategy_key] = (
            f"{format_amount(row.get('forecast_after_provision'))} / "
            f"{_localize_display_value(row.get('risk_level', ''))} / "
            f"{_scenario_matrix_mode_label(row, strategy_key)}"
        )
    return matrix


def _scenario_matrix_mode_label(row: pd.Series, strategy_key: str) -> object:
    strategy_type = str(row.get("strategy_type", ""))
    if strategy_type == OVERACHIEVEMENT or strategy_key in {"O1", "O2", "O3"}:
        strategy_value = row.get("overachievement_strategy")
        return OVERACHIEVEMENT_MATRIX_LABELS.get(
            str(strategy_value),
            OVERACHIEVEMENT_MATRIX_LABELS.get(
                strategy_key,
                _operation_mode_label(row.get("target_status")),
            ),
        )
    return _localize_display_value(row.get("status", ""))


def build_scenario_value_matrix(
    scenario_df: pd.DataFrame,
    value_column: str = "forecast_after_provision",
) -> pd.DataFrame:
    """Return a numeric 3x3 scenario matrix for quick visual comparison."""
    matrix = pd.DataFrame(
        index=["F1", "F2", "F3"],
        columns=_ordered_strategy_keys(scenario_df),
        dtype="float64",
    )
    if value_column not in scenario_df.columns:
        return matrix

    for _, row in scenario_df.iterrows():
        scenario_id = str(row.get("scenario_id", ""))
        if "_" not in scenario_id:
            continue
        forecast_key, strategy_key = scenario_id.split("_", maxsplit=1)
        if forecast_key in matrix.index and strategy_key in matrix.columns:
            matrix.loc[forecast_key, strategy_key] = _as_float(row.get(value_column))
    return matrix


def _ordered_strategy_keys(scenario_df: pd.DataFrame) -> list[str]:
    default_order = ["P1", "P2", "P3", "O1", "O2", "O3", "N1", "N2", "N3"]
    suffixes: set[str] = set()
    if "scenario_id" in scenario_df:
        for scenario_id in scenario_df["scenario_id"].astype(str):
            if "_" in scenario_id:
                suffixes.add(scenario_id.split("_", maxsplit=1)[1])
    ordered = [suffix for suffix in default_order if suffix in suffixes]
    return ordered or ["P1", "P2", "P3"]


def build_scenario_chart_data(scenario_df: pd.DataFrame) -> pd.DataFrame:
    """Return scenario-level values ready for Streamlit charts."""
    return _build_indexed_numeric_chart_data(
        scenario_df,
        "scenario_id",
        (
            "monthly_target",
            "forecast_amount",
            "forecast_after_provision",
            "revised_monthly_target",
            "target_variance",
            "gap_to_target",
            "surplus_to_target",
            "required_uplift",
            "gap_after_provision",
        ),
    )


def build_scenario_daily_forecast_source(
    df: pd.DataFrame,
    scenario_df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    config: dict[str, Any],
    selected_scenario_id: str | None = None,
) -> pd.DataFrame:
    """Return cumulative daily actuals and scenario forecasts for progress charts."""
    columns = get_metric_columns(metric)
    required_columns = {"date", "is_close_day", columns["target_daily"], columns["actual_cum"]}
    if df.empty or scenario_df.empty or not required_columns.issubset(df.columns):
        return pd.DataFrame(columns=SCENARIO_DAILY_FORECAST_COLUMNS)
    if "scenario_id" not in scenario_df.columns:
        return pd.DataFrame(columns=SCENARIO_DAILY_FORECAST_COLUMNS)

    working = df.copy()
    try:
        working["date"] = pd.to_datetime(working["date"], errors="raise").dt.normalize()
        working = working.sort_values(["date"], kind="mergesort").reset_index(drop=True)
        working["target_daily_numeric"] = pd.to_numeric(
            working[columns["target_daily"]],
            errors="raise",
        ).astype("float64")
        actual_values = working[columns["actual_cum"]].replace(r"^\s*$", pd.NA, regex=True)
        working["actual_cum_numeric"] = pd.to_numeric(actual_values, errors="coerce")
        working["is_close_day_bool"] = _coerce_is_close_day(working["is_close_day"])
    except Exception:  # noqa: BLE001 - visual source should fail closed.
        return pd.DataFrame(columns=SCENARIO_DAILY_FORECAST_COLUMNS)

    working["target_cum"] = working["target_daily_numeric"].cumsum()
    monthly_target = float(working["target_daily_numeric"].sum())
    as_of_timestamp = pd.Timestamp(as_of_date).normalize()
    selected_id = str(selected_scenario_id or "")

    rows: list[dict[str, object]] = []
    actual_rows = working.loc[
        (working["date"] <= as_of_timestamp) & working["actual_cum_numeric"].notna()
    ]
    for _, day_row in actual_rows.iterrows():
        rows.append(
            _build_daily_forecast_row(
                day_row=day_row,
                scenario_id="확정 실적",
                series_type="확정 실적",
                line_group="actual",
                daily_expected=float("nan"),
                forecast_cum=day_row["actual_cum_numeric"],
                monthly_target=monthly_target,
                selected_id=selected_id,
                as_of_timestamp=as_of_timestamp,
                risk_level_label="",
            )
        )

    scenario_lookup = scenario_df.set_index(scenario_df["scenario_id"].astype(str), drop=False)
    for scenario_id in scenario_df["scenario_id"].astype(str).tolist():
        forecast_result, strategy_result = run_selected_scenario_detail(
            df,
            as_of_date,
            metric,
            scenario_id,
            config,
        )
        current_actual_cum = _as_float(forecast_result.get("current_actual_cum"))
        if not math.isfinite(current_actual_cum):
            continue

        as_of_rows = working.loc[working["date"] == as_of_timestamp]
        if not as_of_rows.empty:
            rows.append(
                _build_daily_forecast_row(
                    day_row=as_of_rows.iloc[-1],
                    scenario_id=scenario_id,
                    series_type="시나리오 예상",
                    line_group=scenario_id,
                    daily_expected=0.0,
                    forecast_cum=current_actual_cum,
                    monthly_target=monthly_target,
                    selected_id=selected_id,
                    as_of_timestamp=as_of_timestamp,
                    risk_level_label=_scenario_daily_risk_label(
                        scenario_lookup,
                        scenario_id,
                    ),
                )
            )

        expected_by_day = _build_scenario_expected_daily_map(
            working,
            forecast_result,
            strategy_result,
            as_of_timestamp,
        )
        cumulative = current_actual_cum
        for _, day_row in working.loc[working["date"] > as_of_timestamp].iterrows():
            day = pd.Timestamp(day_row["date"]).normalize()
            daily_expected = expected_by_day.get(day, float("nan"))
            if not math.isfinite(_as_float(daily_expected)):
                continue
            cumulative += float(daily_expected)
            rows.append(
                _build_daily_forecast_row(
                    day_row=day_row,
                    scenario_id=scenario_id,
                    series_type="시나리오 예상",
                    line_group=scenario_id,
                    daily_expected=daily_expected,
                    forecast_cum=cumulative,
                    monthly_target=monthly_target,
                    selected_id=selected_id,
                    as_of_timestamp=as_of_timestamp,
                    risk_level_label=_scenario_daily_risk_label(
                        scenario_lookup,
                        scenario_id,
                    ),
                )
            )

    if not rows:
        return pd.DataFrame(columns=SCENARIO_DAILY_FORECAST_COLUMNS)
    return pd.DataFrame(rows, columns=SCENARIO_DAILY_FORECAST_COLUMNS)


def build_scenario_weekly_forecast_source(daily_source: pd.DataFrame) -> pd.DataFrame:
    """Return weekly endpoint rows from the daily cumulative scenario source."""
    if daily_source.empty:
        return pd.DataFrame(columns=SCENARIO_DAILY_FORECAST_COLUMNS)

    working = daily_source.copy()
    working["date"] = pd.to_datetime(working["date"], errors="coerce")
    working = working.dropna(subset=["date", "forecast_cum"])
    if working.empty:
        return pd.DataFrame(columns=SCENARIO_DAILY_FORECAST_COLUMNS)

    working = working.sort_values(["line_group", "date"], kind="mergesort")
    group_columns = [
        "line_group",
        "scenario_id",
        "series_type",
        "week_start",
        "week_end",
        "week_label",
        "week_no",
    ]
    weekly = (
        working.groupby(group_columns, dropna=False, sort=False)
        .tail(1)
        .sort_values(["date", "line_group"], kind="mergesort")
        .reset_index(drop=True)
    )
    return weekly.loc[:, list(SCENARIO_DAILY_FORECAST_COLUMNS)]


def build_selected_scenario_daily_detail_source(
    daily_source: pd.DataFrame,
    selected_scenario_id: str | None,
) -> pd.DataFrame:
    """Return actual and selected scenario daily rows for the integrated detail table."""
    if daily_source.empty:
        return pd.DataFrame(columns=SCENARIO_DAILY_DETAIL_COLUMNS)

    selected_id = str(selected_scenario_id or "")
    source = daily_source.loc[
        (daily_source["series_type"] == "확정 실적")
        | (daily_source["scenario_id"].astype(str) == selected_id)
    ].copy()
    if source.empty:
        return pd.DataFrame(columns=SCENARIO_DAILY_DETAIL_COLUMNS)

    source["date"] = pd.to_datetime(source["date"], errors="coerce").dt.date
    for column in (
        "daily_expected",
        "forecast_cum",
        "target_cum",
        "achievement_rate",
        "target_achievement_rate",
    ):
        source[column] = pd.to_numeric(source[column], errors="coerce")
    return source.loc[:, list(SCENARIO_DAILY_DETAIL_COLUMNS)].reset_index(drop=True)


def build_remaining_operation_direction_source(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    scenario_id: str,
    forecast_result: dict[str, object],
    strategy_result: dict[str, object],
) -> pd.DataFrame:
    """Return remaining-day operating direction rows for one selected scenario."""
    allocation_by_day = _as_dataframe(strategy_result.get("allocation_by_day"))
    if not allocation_by_day.empty:
        return _build_allocation_operation_direction_source(
            allocation_by_day,
            scenario_id,
            strategy_result,
        )

    return _build_maintenance_operation_direction_source(
        df,
        as_of_date,
        metric,
        scenario_id,
        forecast_result,
        strategy_result,
    )


def _build_allocation_operation_direction_source(
    allocation_by_day: pd.DataFrame,
    scenario_id: str,
    strategy_result: dict[str, object],
) -> pd.DataFrame:
    available_columns = [
        column
        for column in (
            "date",
            "is_close_day",
            "close_type",
            "original_target",
            "uplift",
            "revised_target",
            "expected_after_revision",
            "expected_rate",
            "cap_exceeded",
        )
        if column in allocation_by_day.columns
    ]
    source = allocation_by_day.loc[:, available_columns].copy()
    source["date"] = pd.to_datetime(source["date"], errors="coerce").dt.normalize()
    for column in (
        "original_target",
        "uplift",
        "revised_target",
        "expected_after_revision",
        "expected_rate",
    ):
        if column not in source.columns:
            source[column] = 0.0
        source[column] = pd.to_numeric(source[column], errors="coerce").fillna(0.0)
    if "cap_exceeded" not in source.columns:
        source["cap_exceeded"] = False
    if "is_close_day" not in source.columns:
        source["is_close_day"] = False
    if "close_type" not in source.columns:
        source["close_type"] = ""

    source["scenario_id"] = scenario_id
    source["strategy_type"] = str(strategy_result.get("strategy_type", PROVISION))
    source["operation_mode"] = "업리프트 배분"
    source["expected_daily"] = source["expected_after_revision"]
    source["day_type"] = source["is_close_day"].map(
        lambda value: "마감일" if not _is_missing(value) and bool(value) else "일반일"
    )
    source["direction"] = source.apply(_allocation_direction_label, axis=1)
    source["direction_detail"] = source.apply(_allocation_direction_detail, axis=1)
    source["date_label"] = source["date"].map(_format_chart_index)
    return source.loc[:, list(REMAINING_OPERATION_DIRECTION_COLUMNS)].dropna(
        subset=["date"]
    ).reset_index(drop=True)


def _build_maintenance_operation_direction_source(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    scenario_id: str,
    forecast_result: dict[str, object],
    strategy_result: dict[str, object],
) -> pd.DataFrame:
    columns = get_metric_columns(metric)
    required_columns = {"date", "is_close_day", columns["target_daily"]}
    if df.empty or not required_columns.issubset(df.columns):
        return pd.DataFrame(columns=REMAINING_OPERATION_DIRECTION_COLUMNS)

    working = df.copy()
    try:
        working["date"] = pd.to_datetime(working["date"], errors="raise").dt.normalize()
        working["is_close_day_bool"] = _coerce_is_close_day(working["is_close_day"])
        working["original_target"] = pd.to_numeric(
            working[columns["target_daily"]],
            errors="raise",
        ).astype("float64")
    except Exception:  # noqa: BLE001 - visual source should fail closed.
        return pd.DataFrame(columns=REMAINING_OPERATION_DIRECTION_COLUMNS)

    remaining = working.loc[working["date"] > pd.Timestamp(as_of_date).normalize()].copy()
    if remaining.empty:
        return pd.DataFrame(columns=REMAINING_OPERATION_DIRECTION_COLUMNS)

    expected_rates = _expected_rate_map(forecast_result)
    remaining["expected_rate"] = remaining["date"].map(
        lambda value: expected_rates.get(pd.Timestamp(value).normalize(), float("nan"))
    )
    remaining["expected_daily"] = remaining["original_target"] * remaining["expected_rate"]
    remaining["uplift"] = 0.0
    remaining["revised_target"] = remaining["original_target"]
    remaining["scenario_id"] = scenario_id
    remaining["strategy_type"] = str(strategy_result.get("strategy_type", NEUTRAL))
    remaining["operation_mode"] = _maintenance_operation_mode(strategy_result)
    remaining["day_type"] = remaining["is_close_day_bool"].map(
        lambda value: "마감일" if bool(value) else "일반일"
    )
    remaining["close_type"] = remaining["close_type"] if "close_type" in remaining else ""
    remaining["direction"] = _maintenance_direction_label(strategy_result)
    remaining["direction_detail"] = remaining.apply(
        lambda row: _maintenance_direction_detail(row, strategy_result),
        axis=1,
    )
    remaining["date_label"] = remaining["date"].map(_format_chart_index)
    return remaining.loc[:, list(REMAINING_OPERATION_DIRECTION_COLUMNS)].dropna(
        subset=["date"]
    ).reset_index(drop=True)


def _expected_rate_map(forecast_result: dict[str, object]) -> dict[pd.Timestamp, float]:
    expected_rate_by_day = forecast_result.get("expected_rate_by_day", {})
    if not isinstance(expected_rate_by_day, dict):
        return {}
    return {
        pd.Timestamp(day).normalize(): _as_float(rate)
        for day, rate in expected_rate_by_day.items()
    }


def _allocation_direction_label(row: pd.Series) -> str:
    if bool(row.get("cap_exceeded", False)):
        return "상한 점검"
    if _as_float(row.get("uplift")) > 0:
        return "추가 배분"
    return "기존 목표 유지"


def _allocation_direction_detail(row: pd.Series) -> str:
    if bool(row.get("cap_exceeded", False)):
        return "배분 요청이 일별 상한에 근접하거나 초과합니다. 목표 조정 가능성을 먼저 확인합니다."
    uplift = _as_float(row.get("uplift"))
    if math.isfinite(uplift) and uplift > 0:
        return f"기존 일 목표에 {format_amount(uplift)}를 추가 배분해 잔여 부족분을 회복합니다."
    return "추가 상향 없이 기존 일 목표를 유지합니다."


def _maintenance_operation_mode(strategy_result: dict[str, object]) -> str:
    strategy_type = str(strategy_result.get("strategy_type", NEUTRAL))
    if strategy_type == OVERACHIEVEMENT:
        return "목표 유지/버퍼 관리"
    return "목표 유지/모니터링"


def _maintenance_direction_label(strategy_result: dict[str, object]) -> str:
    strategy_type = str(strategy_result.get("strategy_type", NEUTRAL))
    strategy_id = str(strategy_result.get("strategy_id", ""))
    if strategy_type == OVERACHIEVEMENT and "STRETCH" in strategy_id:
        return "Stretch 후보"
    if strategy_type == OVERACHIEVEMENT:
        return "버퍼 방어"
    return "유지 모니터링"


def _maintenance_direction_detail(
    row: pd.Series,
    strategy_result: dict[str, object],
) -> str:
    direction = _maintenance_direction_label(strategy_result)
    expected_daily = format_amount(row.get("expected_daily"))
    if direction == "Stretch 후보":
        return f"기존 일 목표는 유지하되 예상 일실적 {expected_daily}를 기준으로 초과분 전환 여지를 봅니다."
    if direction == "버퍼 방어":
        return f"기존 일 목표를 유지하고 예상 일실적 {expected_daily} 대비 취소/철회/미결제 리스크를 점검합니다."
    return f"기존 일 목표를 유지하며 예상 일실적 {expected_daily} 흐름이 계획선에서 이탈하는지 봅니다."


def _build_scenario_expected_daily_map(
    working: pd.DataFrame,
    forecast_result: dict[str, object],
    strategy_result: dict[str, object],
    as_of_timestamp: pd.Timestamp,
) -> dict[pd.Timestamp, float]:
    allocation_by_day = _as_dataframe(strategy_result.get("allocation_by_day"))
    if not allocation_by_day.empty and {"date", "expected_after_revision"}.issubset(
        allocation_by_day.columns
    ):
        allocation = allocation_by_day.loc[:, ["date", "expected_after_revision"]].copy()
        allocation["date"] = pd.to_datetime(allocation["date"], errors="coerce").dt.normalize()
        allocation["expected_after_revision"] = pd.to_numeric(
            allocation["expected_after_revision"],
            errors="coerce",
        )
        allocation = allocation.dropna(subset=["date", "expected_after_revision"])
        return {
            pd.Timestamp(day).normalize(): float(value)
            for day, value in allocation.groupby("date")["expected_after_revision"].sum().items()
        }

    expected_rate_by_day = forecast_result.get("expected_rate_by_day", {})
    if not isinstance(expected_rate_by_day, dict):
        return {}
    normalized_rates = {
        pd.Timestamp(day).normalize(): _as_float(rate)
        for day, rate in expected_rate_by_day.items()
    }
    result: dict[pd.Timestamp, float] = {}
    remaining_rows = working.loc[working["date"] > as_of_timestamp]
    for _, day_row in remaining_rows.iterrows():
        day = pd.Timestamp(day_row["date"]).normalize()
        rate = normalized_rates.get(day, float("nan"))
        target = _as_float(day_row.get("target_daily_numeric"))
        if math.isfinite(rate) and math.isfinite(target):
            result[day] = target * rate
    return result


def _build_daily_forecast_row(
    *,
    day_row: pd.Series,
    scenario_id: str,
    series_type: str,
    line_group: str,
    daily_expected: object,
    forecast_cum: object,
    monthly_target: float,
    selected_id: str,
    as_of_timestamp: pd.Timestamp,
    risk_level_label: str,
) -> dict[str, object]:
    forecast_value = _as_float(forecast_cum)
    target_cum = _as_float(day_row.get("target_cum"))
    achievement_rate = safe_divide(forecast_value, monthly_target)
    target_achievement_rate = safe_divide(target_cum, monthly_target)
    date_value = pd.Timestamp(day_row.get("date")).normalize()
    week_start, week_end, week_no, week_label = _week_bucket_values(date_value)
    is_close_day = bool(day_row.get("is_close_day_bool", False))

    return {
        "date": date_value,
        "date_label": _format_chart_index(date_value),
        "week_start": week_start,
        "week_end": week_end,
        "week_label": week_label,
        "week_no": week_no,
        "business_day_no": day_row.get("business_day_no", pd.NA),
        "is_close_day": is_close_day,
        "day_type": "마감일" if bool(is_close_day) else "일반일",
        "close_type": day_row.get("close_type", ""),
        "scenario_id": scenario_id,
        "series_type": series_type,
        "line_group": line_group,
        "daily_expected": _as_float(daily_expected),
        "forecast_cum": forecast_value,
        "target_cum": target_cum,
        "monthly_target": monthly_target,
        "achievement_rate": achievement_rate,
        "target_achievement_rate": target_achievement_rate,
        "achievement_label": format_rate(achievement_rate),
        "target_achievement_label": format_rate(target_achievement_rate),
        "forecast_label": format_amount(forecast_value),
        "target_cum_label": format_amount(target_cum),
        "risk_level_label": risk_level_label,
        "is_selected": series_type == "시나리오 예상" and scenario_id == selected_id,
        "is_as_of_date": date_value == as_of_timestamp,
    }


def _week_bucket_values(date_value: pd.Timestamp) -> tuple[pd.Timestamp, pd.Timestamp, int, str]:
    week_start = (date_value - pd.Timedelta(days=int(date_value.dayofweek))).normalize()
    week_end = week_start + pd.Timedelta(days=6)
    iso = date_value.isocalendar()
    week_no = int(iso.week)
    week_label = f"{week_start.strftime('%m/%d')}~{week_end.strftime('%m/%d')}"
    return week_start, week_end, week_no, week_label


def _scenario_daily_risk_label(
    scenario_lookup: pd.DataFrame,
    scenario_id: str,
) -> str:
    if scenario_id not in scenario_lookup.index:
        return ""
    return str(_localize_display_value(scenario_lookup.loc[scenario_id].get("risk_level", "")))


def build_scenario_target_position_source(
    scenario_df: pd.DataFrame,
    selected_scenario_id: str | None = None,
) -> pd.DataFrame:
    """Return scenario rows focused on target-line comparison."""
    required = ("scenario_id", "monthly_target")
    if scenario_df.empty or not set(required).issubset(scenario_df.columns):
        return pd.DataFrame(
            columns=[
                "scenario_id",
                "monthly_target",
                "forecast_after_provision",
                "target_variance",
                "target_status_label",
                "risk_level_label",
                "is_selected",
                "forecast_label",
                "variance_label",
            ]
        )

    value_column = (
        "forecast_after_provision"
        if "forecast_after_provision" in scenario_df.columns
        else "forecast_amount"
    )
    available_columns = [
        column
        for column in (
            "scenario_id",
            "monthly_target",
            value_column,
            "target_variance",
            "target_status",
            "risk_level",
        )
        if column in scenario_df.columns
    ]
    source = scenario_df.loc[:, available_columns].copy()
    if value_column != "forecast_after_provision":
        source["forecast_after_provision"] = source[value_column]

    for column in ("monthly_target", "forecast_after_provision", "target_variance"):
        if column in source.columns:
            source[column] = pd.to_numeric(source[column], errors="coerce")
    if "target_variance" not in source.columns:
        source["target_variance"] = (
            source["forecast_after_provision"] - source["monthly_target"]
        )

    source["scenario_id"] = source["scenario_id"].astype(str)
    source["target_status_label"] = source.get(
        "target_status",
        pd.Series(["UNKNOWN_TARGET_STATUS"] * len(source), index=source.index),
    ).map(_localize_display_value)
    source["risk_level_label"] = source.get(
        "risk_level",
        pd.Series(["N/A"] * len(source), index=source.index),
    ).map(_localize_display_value)
    source["is_selected"] = source["scenario_id"] == str(selected_scenario_id or "")
    source["forecast_label"] = source["forecast_after_provision"].map(format_amount)
    source["variance_label"] = source["target_variance"].map(_format_signed_amount)
    source = source.dropna(subset=["forecast_after_provision", "monthly_target"])
    return source.reset_index(drop=True)


def build_scenario_heatmap_source(
    scenario_df: pd.DataFrame,
    selected_scenario_id: str | None = None,
) -> pd.DataFrame:
    """Return scenario matrix rows with signed target variance."""
    source = build_scenario_target_position_source(scenario_df, selected_scenario_id)
    if source.empty:
        return pd.DataFrame(
            columns=[
                "scenario_id",
                "forecast_key",
                "strategy_key",
                "target_variance",
                "variance_label",
                "target_status_label",
                "is_selected",
            ]
        )

    rows: list[dict[str, object]] = []
    for row in source.to_dict("records"):
        scenario_id = str(row.get("scenario_id", ""))
        forecast_key, strategy_key = _split_scenario_id(scenario_id)
        rows.append(
            {
                "scenario_id": scenario_id,
                "forecast_key": forecast_key,
                "strategy_key": strategy_key,
                "target_variance": row.get("target_variance"),
                "variance_label": row.get("variance_label"),
                "target_status_label": row.get("target_status_label"),
                "is_selected": row.get("is_selected"),
            }
        )
    return pd.DataFrame(rows)


def build_remaining_target_chart_data(revised_targets_df: pd.DataFrame) -> pd.DataFrame:
    """Return remaining daily target values ready for Streamlit charts."""
    return _build_indexed_numeric_chart_data(
        revised_targets_df,
        "date",
        (
            "original_target",
            "uplift",
            "revised_target",
            "cap_target",
            "expected_after_revision",
        ),
    )


def build_remaining_target_daily_source(revised_targets_df: pd.DataFrame) -> pd.DataFrame:
    """Return remaining-day rows with labels for intuitive target allocation charts."""
    if revised_targets_df.empty or "date" not in revised_targets_df.columns:
        return pd.DataFrame(
            columns=[
                "date",
                "date_label",
                "day_type",
                "close_type",
                "original_target",
                "uplift",
                "revised_target",
                "cap_target",
                "expected_after_revision",
                "cap_exceeded",
            ]
        )

    available_columns = [
        column
        for column in (
            "date",
            "day_name",
            "is_close_day",
            "close_type",
            "original_target",
            "uplift",
            "revised_target",
            "cap_target",
            "expected_after_revision",
            "cap_exceeded",
        )
        if column in revised_targets_df.columns
    ]
    source = revised_targets_df.loc[:, available_columns].copy()
    for column in (
        "original_target",
        "uplift",
        "revised_target",
        "cap_target",
        "expected_after_revision",
    ):
        if column in source.columns:
            source[column] = pd.to_numeric(source[column], errors="coerce")
        else:
            source[column] = pd.NA
    if "cap_exceeded" not in source.columns:
        source["cap_exceeded"] = False
    if "close_type" not in source.columns:
        source["close_type"] = ""

    source["date_label"] = source["date"].map(_format_chart_index)
    if "is_close_day" in source.columns:
        source["day_type"] = source["is_close_day"].map(
            lambda value: "마감일" if not _is_missing(value) and bool(value) else "일반일"
        )
    else:
        source["day_type"] = "잔여일"
    return source.reset_index(drop=True)


def build_remaining_target_stack_source(revised_targets_df: pd.DataFrame) -> pd.DataFrame:
    """Return long-form existing target and uplift rows for stacked bars."""
    daily = build_remaining_target_daily_source(revised_targets_df)
    if daily.empty:
        return pd.DataFrame(columns=["date_label", "target_part", "value"])

    stack_source = daily.melt(
        id_vars=[
            "date",
            "date_label",
            "day_type",
            "close_type",
            "revised_target",
            "cap_target",
            "expected_after_revision",
            "cap_exceeded",
        ],
        value_vars=["original_target", "uplift"],
        var_name="target_part",
        value_name="value",
    )
    stack_source["target_part"] = stack_source["target_part"].map(
        {
            "original_target": "기존 일 목표",
            "uplift": "추가 배분 목표",
        }
    )
    return stack_source.dropna(subset=["value"]).reset_index(drop=True)


def build_strategy_level_table(
    scenario_df: pd.DataFrame,
    selected_scenario_id: str | None = None,
) -> pd.DataFrame:
    """Return strategy-level target values when no daily reallocation is produced."""
    if scenario_df.empty:
        return pd.DataFrame(columns=STRATEGY_LEVEL_COLUMNS)

    result = scenario_df.copy(deep=False)
    forecast_key = _selected_forecast_key(selected_scenario_id)
    if forecast_key and "scenario_id" in result.columns:
        result = result.loc[
            result["scenario_id"].astype(str).str.startswith(f"{forecast_key}_")
        ]

    available_columns = [
        column for column in STRATEGY_LEVEL_COLUMNS if column in result.columns
    ]
    if not available_columns:
        return pd.DataFrame(columns=STRATEGY_LEVEL_COLUMNS)
    return result.loc[:, available_columns].reset_index(drop=True)


def build_strategy_level_chart_data(
    scenario_df: pd.DataFrame,
    selected_scenario_id: str | None = None,
) -> pd.DataFrame:
    """Return strategy-level values ready for Streamlit charts."""
    strategy_table = build_strategy_level_table(scenario_df, selected_scenario_id)
    chart_data = _build_indexed_numeric_chart_data(
        strategy_table,
        "scenario_id",
        STRATEGY_LEVEL_CHART_COLUMNS,
    )
    if chart_data.empty:
        return chart_data
    return chart_data.dropna(axis=1, how="all")


def build_grouped_bar_chart_source(
    chart_data: pd.DataFrame,
    metric_columns: tuple[str, ...],
) -> pd.DataFrame:
    """Return long-form chart data so bars are compared side-by-side, not stacked."""
    available_columns = _available_chart_columns(chart_data, metric_columns)
    if chart_data.empty or not available_columns:
        return pd.DataFrame(columns=["category", "metric", "범례", "value"])

    source = chart_data.loc[:, list(available_columns)].reset_index()
    index_column = str(source.columns[0])
    source = source.rename(columns={index_column: "category"})
    long_source = source.melt(
        id_vars="category",
        value_vars=list(available_columns),
        var_name="metric",
        value_name="value",
    )
    labels = _chart_labels(available_columns)
    long_source["범례"] = long_source["metric"].map(labels)
    long_source["value"] = pd.to_numeric(long_source["value"], errors="coerce")
    return long_source.dropna(subset=["value"]).reset_index(drop=True)


def build_auto_axis_domain(values: pd.Series) -> list[float] | None:
    """Return a padded value-axis domain that emphasizes chart differences."""
    numeric_values = pd.to_numeric(values, errors="coerce").dropna()
    numeric_values = numeric_values.loc[numeric_values.map(math.isfinite)]
    if numeric_values.empty:
        return None

    value_min = float(numeric_values.min())
    value_max = float(numeric_values.max())
    magnitude = max(abs(value_min), abs(value_max), 1.0)
    if math.isclose(value_min, value_max, rel_tol=0.0, abs_tol=1e-9):
        padding = max(magnitude * 0.05, 0.1)
        return [value_min - padding, value_max + padding]

    span = value_max - value_min
    padding = max(span * 0.12, magnitude * 0.02, 0.1)
    lower = value_min - padding
    upper = value_max + padding

    if value_min < 0 < value_max:
        return [min(lower, 0.0), max(upper, 0.0)]
    if value_min >= 0:
        return [max(0.0, lower), upper]
    return [lower, min(0.0, upper)]


def chart_value_format(unit: str) -> str:
    """Return an Altair number format for values already stored in display units."""
    _ = unit
    return ",.1f"


def build_close_cycle_chart_data(close_cycle_df: pd.DataFrame) -> pd.DataFrame:
    """Return close-cycle values ready for Streamlit charts."""
    return _build_indexed_numeric_chart_data(
        close_cycle_df,
        "cycle_end_date",
        (
            "target_sum",
            "actual_sum",
            "achievement_rate",
        ),
    )


def build_visual_metric_definition_df(metric_columns: tuple[str, ...]) -> pd.DataFrame:
    """Return user-facing definitions for chart series."""
    rows = []
    for column in metric_columns:
        definition = VISUAL_METRIC_DEFINITIONS.get(column, {})
        rows.append(
            {
                "범례": definition.get("label", column),
                "단위": definition.get("unit", ""),
                "수치 의미": definition.get("definition", "정의가 등록되지 않은 수치입니다."),
            }
        )
    return pd.DataFrame(rows)


def build_visual_reading_guide(guide_key: str) -> dict[str, object]:
    """Return the reading logic for a visual block."""
    guide = VISUAL_READING_GUIDES.get(guide_key, {})
    return {
        "title": guide.get("title", ""),
        "steps": tuple(guide.get("steps", ())),
        "decision": guide.get("decision", ""),
    }


def build_visual_headline(
    selected_row: pd.Series,
    validation_result: dict[str, Any],
    next_close_result: dict[str, Any],
) -> str:
    """Return the first sentence users should read before the charts."""
    _ = validation_result
    target_status = str(selected_row.get("target_status", "UNKNOWN_TARGET_STATUS"))
    target_variance = _as_float(selected_row.get("target_variance"))
    surplus = _as_float(selected_row.get("surplus_to_target"))
    next_close_sentence = _visual_next_close_sentence(next_close_result)

    if target_status == "UNDER_TARGET" or (
        math.isfinite(target_variance) and target_variance < 0
    ):
        shortage = abs(target_variance) if math.isfinite(target_variance) else selected_row.get("gap_to_target")
        return (
            f"결론: 목표선보다 {format_amount(shortage)} 부족할 가능성이 큽니다. "
            "먼저 전략 반영 후 예상이 공식 월 목표선까지 회복되는지 보고, "
            f"그다음 잔여 일자별 추가 배분이 감당 가능한지 확인하세요. {next_close_sentence}"
        )

    if target_status == "OVER_TARGET" or (
        math.isfinite(target_variance) and target_variance > 0
    ):
        surplus_amount = surplus if math.isfinite(surplus) and surplus > 0 else target_variance
        return (
            f"결론: 목표선보다 {format_amount(surplus_amount)} 여유가 예상됩니다. "
            "초과분을 안전버퍼로 남길지, Stretch 목표로 전환할지 차트에서 확인하세요. "
            f"{next_close_sentence}"
        )

    return (
        "결론: 목표선 근처의 유지/모니터링 구간입니다. "
        "시각화에서는 예측모델별 흔들림과 다음 마감 누적선을 함께 확인하세요. "
        f"{next_close_sentence}"
    )


def build_visual_decision_summary(
    selected_row: pd.Series,
    validation_result: dict[str, Any],
    next_close_result: dict[str, Any],
) -> pd.DataFrame:
    """Return chart interpretation rows in a fixed reading order."""
    target_status = selected_row.get("target_status", "UNKNOWN_TARGET_STATUS")
    risk_level = selected_row.get("risk_level", "N/A")
    operation_mode = _operation_mode_label(target_status)
    monthly_target = validation_result.get("monthly_target")
    forecast_after = selected_row.get("forecast_after_provision")
    target_variance = selected_row.get("target_variance")
    next_close_date = next_close_result.get("next_close_date")
    next_close_required = next_close_result.get("required_to_recover_next_close_cum")

    return pd.DataFrame(
        [
            {
                "확인 순서": "1",
                "볼 것": "목표 판정",
                "현재 값": (
                    f"{_localize_display_value(target_status)} / "
                    f"위험 {_localize_display_value(risk_level)}"
                ),
                "해석": _visual_status_sentence(target_status, operation_mode),
            },
            {
                "확인 순서": "2",
                "볼 것": "목표선 대비 예상 실적",
                "현재 값": (
                    f"{format_amount(forecast_after)} / "
                    f"목표 {format_amount(monthly_target)}"
                ),
                "해석": "막대가 목표선보다 낮으면 잔여 목표 보정이 필요하고, 높으면 초과분 관리가 핵심입니다.",
            },
            {
                "확인 순서": "3",
                "볼 것": "목표 대비 차이",
                "현재 값": _format_signed_amount(target_variance),
                "해석": _visual_variance_sentence(target_variance),
            },
            {
                "확인 순서": "4",
                "볼 것": "다음 마감선",
                "현재 값": (
                    f"{_format_date(next_close_date)} / "
                    f"{format_amount(next_close_required)}"
                ),
                "해석": _visual_next_close_sentence(next_close_result),
            },
        ]
    )


def _visual_status_sentence(target_status: object, operation_mode: object) -> str:
    status = str(target_status)
    mode = str(operation_mode)
    if status == "UNDER_TARGET":
        return f"{mode} 상태입니다. 시나리오별 예상 탭에서 어떤 F/P 조합이 부족분을 줄이는지 보세요."
    if status == "OVER_TARGET":
        return f"{mode} 상태입니다. 초과분을 버퍼로 둘지, 상향 목표로 전환할지 전략 수준 탭에서 보세요."
    if status == "ON_TARGET":
        return f"{mode} 상태입니다. 목표선은 맞지만 마감차수 흐름이 흔들리는지 함께 확인하세요."
    return "목표 판정에 필요한 값이 부족합니다. 입력값 점검 결과를 먼저 확인하세요."


def _visual_variance_sentence(value: object) -> str:
    number = _as_float(value)
    if not math.isfinite(number):
        return "목표 대비 차이를 계산할 수 없습니다. 선택 시나리오 상세 값을 확인하세요."
    if number < 0:
        return f"월말 기준 {format_amount(abs(number))}를 더 채워야 목표선에 도달합니다."
    if number > 0:
        return f"월말 기준 {format_amount(number)}가 목표선 위에 있어 버퍼 또는 Stretch 후보입니다."
    return "월말 예상이 공식 월 목표와 거의 같습니다. 남은 기간의 변동 리스크를 봅니다."


def _visual_next_close_sentence(next_close_result: dict[str, Any]) -> str:
    next_close_date = next_close_result.get("next_close_date")
    required = _as_float(next_close_result.get("required_to_recover_next_close_cum"))
    if _is_missing(next_close_date) or not math.isfinite(required):
        return "다음 마감 기준선은 계산 가능한 데이터가 있을 때 표시됩니다."
    if required <= 0:
        return f"{_format_date(next_close_date)}까지 다음 마감 기준선에 대한 추가 회복 부담은 없습니다."
    return f"{_format_date(next_close_date)}까지 누적 기준으로 최소 {format_amount(required)}을 더 확보해야 합니다."


def _format_signed_amount(value: object) -> str:
    number = _as_float(value)
    if not math.isfinite(number):
        return "계산 불가"
    sign = "+" if number > 0 else ""
    return f"{sign}{number:.1f}억 원"


def build_forecast_definition_df() -> pd.DataFrame:
    """Return display definitions for F1/F2/F3 forecast models."""
    return pd.DataFrame(
        [
            {
                "model": model_id,
                "name": definition["name"],
                "description": definition["description"],
                "formula": definition["formula"],
            }
            for model_id, definition in FORECAST_MODEL_DEFINITIONS.items()
        ]
    )


def build_provision_definition_df() -> pd.DataFrame:
    """Return display definitions for P1/P2/P3 provision strategies."""
    return pd.DataFrame(
        [
            {
                "strategy": strategy_id,
                "name": definition["name"],
                "description": definition["description"],
            }
            for strategy_id, definition in PROVISION_STRATEGY_DEFINITIONS.items()
        ]
    )


def build_overachievement_definition_df() -> pd.DataFrame:
    """Return display definitions for O1/O2/O3 overachievement strategies."""
    return pd.DataFrame(
        [
            {
                "strategy": strategy_id,
                "name": definition["name"],
                "description": definition["description"],
            }
            for strategy_id, definition in OVERACHIEVEMENT_STRATEGY_DEFINITIONS.items()
        ]
    )


def build_neutral_definition_df() -> pd.DataFrame:
    """Return display definitions for N1/N2/N3 neutral strategies."""
    return pd.DataFrame(
        [
            {
                "strategy": strategy_id,
                "name": definition["name"],
                "description": definition["description"],
            }
            for strategy_id, definition in NEUTRAL_STRATEGY_DEFINITIONS.items()
        ]
    )


def build_report_glossary_df() -> pd.DataFrame:
    """Return the fixed glossary used by the generated report."""
    rows: list[dict[str, str]] = []
    for group, definitions in REPORT_GLOSSARY_GROUPS:
        for code, definition in definitions.items():
            rows.append(
                {
                    "구분": group,
                    "코드": _localize_display_value(code),
                    "정의": definition,
                }
            )
    return pd.DataFrame(rows)


def build_risk_definition_df() -> pd.DataFrame:
    """Return display definitions for scenario risk levels."""
    return pd.DataFrame(
        [
            {
                "risk_level": risk_level,
                "definition": definition,
            }
            for risk_level, definition in RISK_LEVEL_DEFINITIONS.items()
        ]
    )


def build_selected_scenario_explanation(
    scenario_id: str,
    selected_row: pd.Series,
) -> pd.DataFrame:
    """Return a concise, non-duplicative summary for the selected scenario."""
    forecast_key, strategy_key = _split_scenario_id(scenario_id)
    forecast_name = FORECAST_MODEL_DEFINITIONS.get(forecast_key, {}).get("name", forecast_key)
    strategy_name = SCENARIO_STRATEGY_DEFINITIONS.get(strategy_key, {}).get(
        "name",
        strategy_key,
    )
    risk_level = str(selected_row.get("risk_level", "계산 불가"))
    status = str(selected_row.get("status", "계산 불가"))
    strategy_type = str(selected_row.get("strategy_type", PROVISION))
    target_status = str(selected_row.get("target_status", "계산 불가"))
    display_risk_level = _localize_display_value(risk_level)
    display_status = _localize_display_value(status)
    display_strategy_type = _localize_display_value(strategy_type)
    display_target_status = _localize_display_value(target_status)
    display_operation_mode = _operation_mode_label(target_status)

    return pd.DataFrame(
        [
            {
                "item": "선택 조합",
                "value": scenario_id,
            },
            {
                "item": "예측 모델",
                "value": f"{forecast_key} {forecast_name}",
            },
            {
                "item": "운영 전략",
                "value": f"{strategy_key} {strategy_name}",
            },
            {
                "item": "전략 구분",
                "value": display_strategy_type,
            },
            {
                "item": "조합 의미",
                "value": _selected_strategy_meaning(
                    forecast_key,
                    strategy_key,
                    strategy_type,
                    display_target_status,
                ),
            },
            {
                "item": "목표 상태",
                "value": display_target_status,
            },
            {
                "item": "위험등급 / 운영모드",
                "value": f"{display_risk_level} / {display_operation_mode}",
            },
            {
                "item": "계산 상태",
                "value": display_status,
            },
            {
                "item": "월말 예상 실적",
                "value": format_amount(selected_row.get("forecast_amount")),
            },
            {
                "item": "전략 반영 후 예상",
                "value": format_amount(selected_row.get("forecast_after_provision")),
            },
            {
                "item": "목표 대비 차이",
                "value": format_amount(selected_row.get("target_variance")),
            },
            {
                "item": "필요 상향",
                "value": format_amount(selected_row.get("required_uplift")),
            },
            {
                "item": "초과 예상분",
                "value": format_amount(selected_row.get("surplus_to_target")),
            },
            {
                "item": "권장 조치",
                "value": selected_row.get("recommended_action", "계산 결과를 확인합니다."),
            },
        ]
    )


def _selected_strategy_meaning(
    forecast_key: str,
    strategy_key: str,
    strategy_type: str,
    target_status: str,
) -> str:
    if strategy_type == OVERACHIEVEMENT:
        return (
            f"{forecast_key}로 월말 예상 실적을 산출한 결과 {target_status}로 판단되어, "
            f"{strategy_key} 초과달성 운영전략을 적용합니다."
        )
    if strategy_type == NEUTRAL:
        return (
            f"{forecast_key}로 월말 예상 실적을 산출한 결과 {target_status}로 판단되어, "
            f"{strategy_key} 유지/모니터링 전략을 적용합니다."
        )
    return (
        f"{forecast_key}로 월말 예상 실적을 산출한 뒤, "
        f"{strategy_key} 방식으로 목표 상향분을 잔여 일자에 배분합니다."
    )


def format_scenario_option_label(scenario_id: str) -> str:
    """Return a scenario option label with F/P definitions for the selectbox."""
    forecast_key, strategy_key = _split_scenario_id(scenario_id)
    forecast_name = FORECAST_MODEL_DEFINITIONS.get(forecast_key, {}).get(
        "name",
        "정의 없음",
    )
    strategy_name = SCENARIO_STRATEGY_DEFINITIONS.get(strategy_key, {}).get(
        "name",
        "정의 없음",
    )
    return f"{scenario_id} - {forecast_key} {forecast_name} / {strategy_key} {strategy_name}"


def format_validation_messages(messages: list[object]) -> list[str]:
    """Return user-facing Korean validation messages."""
    return [format_validation_message(message) for message in messages]


def format_validation_message(message: object) -> str:
    """Translate validation and warning messages for non-technical users."""
    text = str(message)
    if text in VALIDATION_MESSAGE_TRANSLATIONS:
        return VALIDATION_MESSAGE_TRANSLATIONS[text]

    if text.startswith("Missing required input column: "):
        column = _strip_sentence_end(text.removeprefix("Missing required input column: "))
        return f"{_format_column_label(column)} 열이 없습니다. 입력표에 해당 열을 추가해 주세요."

    if text.startswith("Missing required input columns: "):
        columns = _split_column_list(
            _strip_sentence_end(text.removeprefix("Missing required input columns: "))
        )
        column_text = ", ".join(_format_column_label(column) for column in columns)
        return f"{column_text} 열이 없습니다. 입력표에 해당 열을 추가해 주세요."

    if text.startswith("metric must be one of: "):
        return "지표 선택값을 확인해 주세요. 판매실적(sales) 또는 인정실적(recognized) 중 하나를 선택해야 합니다."

    if text.endswith(" contains invalid numeric values."):
        column = text.removesuffix(" contains invalid numeric values.")
        return f"{_format_column_label(column)} 칸에 숫자로 읽을 수 없는 값이 있습니다. 숫자만 입력해 주세요."

    if text.endswith(" contains duplicate values."):
        column = text.removesuffix(" contains duplicate values.")
        return f"{_format_column_label(column)} 값이 중복되어 있습니다. 같은 값이 두 번 들어간 행을 확인해 주세요."

    if text.startswith("Actual daily calculation failed: "):
        detail = _replace_validation_terms(text.removeprefix("Actual daily calculation failed: "))
        return f"일 실적 계산 중 문제가 발생했습니다. {detail}"

    if text.startswith("Close-cycle summary failed: "):
        detail = _replace_validation_terms(text.removeprefix("Close-cycle summary failed: "))
        return f"마감차수 요약 계산 중 문제가 발생했습니다. {detail}"

    if text.startswith("Next close calculation failed: "):
        detail = _replace_validation_terms(text.removeprefix("Next close calculation failed: "))
        return f"다음 마감 누적선 필요실적 계산 중 문제가 발생했습니다. {detail}"

    if text.startswith("Calculation error: "):
        detail = _replace_validation_terms(text.removeprefix("Calculation error: "))
        return f"계산 중 문제가 발생했습니다. {detail}"

    return f"확인 필요: {_replace_validation_terms(text)}"


def build_display_validation_result(validation_result: dict[str, Any]) -> dict[str, Any]:
    """Return a validation result with user-facing messages and original metrics."""
    display_result = dict(validation_result)
    display_result["errors"] = format_validation_messages(
        list(validation_result.get("errors", []))
    )
    display_result["warnings"] = format_validation_messages(
        list(validation_result.get("warnings", []))
    )
    return display_result


def _format_column_label(column: str) -> str:
    column = column.strip()
    label = VALIDATION_COLUMN_LABELS.get(column)
    if label is None:
        return column
    return f"{label}({column})"


def _replace_validation_terms(text: str) -> str:
    replaced = text
    for term in sorted(VALIDATION_TERM_REPLACEMENTS, key=len, reverse=True):
        replaced = replaced.replace(term, VALIDATION_TERM_REPLACEMENTS[term])
    return replaced


def _strip_sentence_end(text: str) -> str:
    return text.strip().removesuffix(".").strip()


def _split_column_list(text: str) -> list[str]:
    return [column.strip() for column in text.split(",") if column.strip()]


def build_summary_dict(
    validation_result: dict[str, Any],
    selected_row: pd.Series,
    next_close_result: dict[str, Any],
    metric: str,
    as_of_date: object,
) -> dict[str, Any]:
    """Build summary values for the KPI area and Excel export."""
    achievement_rate = safe_divide(
        validation_result.get("current_actual_cum"),
        validation_result.get("current_target_cum"),
    )
    return {
        "metric": metric,
        "as_of_date": pd.Timestamp(as_of_date).date(),
        "monthly_target": validation_result.get("monthly_target"),
        "current_target_cum": validation_result.get("current_target_cum"),
        "current_actual_cum": validation_result.get("current_actual_cum"),
        "cumulative_achievement_rate": achievement_rate,
        "selected_scenario_id": selected_row.get("scenario_id"),
        "forecast_after_provision": selected_row.get("forecast_after_provision"),
        "target_status": selected_row.get("target_status"),
        "target_variance": selected_row.get("target_variance"),
        "surplus_to_target": selected_row.get("surplus_to_target"),
        "strategy_type": selected_row.get("strategy_type"),
        "risk_level": selected_row.get("risk_level"),
        "status": selected_row.get("status"),
        "next_close_date": next_close_result.get("next_close_date"),
        "next_close_required": next_close_result.get(
            "required_to_recover_next_close_cum"
        ),
        "validation_errors": format_validation_messages(
            list(validation_result.get("errors", []))
        ),
        "validation_warnings": format_validation_messages(
            list(validation_result.get("warnings", []))
        ),
    }


def build_excel_report_bytes(
    summary_dict: dict[str, Any],
    scenario_df: pd.DataFrame,
    revised_targets_df: pd.DataFrame,
    close_cycle_df: pd.DataFrame,
    validation_result: dict[str, Any],
    report_text: str,
    metric: str,
    as_of_date: object,
) -> tuple[bytes, str]:
    """Export the calculated report to outputs and return bytes for download."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    date_token = pd.Timestamp(as_of_date).strftime("%Y%m%d")
    report_name = f"daily_report_{metric}_{date_token}.xlsx"
    output_path = OUTPUT_DIR / report_name
    saved_path = export_daily_report(
        output_path,
        summary_dict,
        scenario_df,
        revised_targets_df,
        close_cycle_df,
        validation_result,
        report_text,
        overwrite=True,
    )
    return saved_path.read_bytes(), report_name


def load_forecast_history_for_app(path: str | Path | None = None) -> pd.DataFrame:
    """Load forecast history for the UI, preserving optional future columns."""
    history_path = (
        Path(path)
        if path is not None
        else _history_storage_path(history_schema.FORECAST_HISTORY)
    )
    columns = list(history_schema.FORECAST_HISTORY_COLUMNS)
    if not history_path.exists() or history_path.stat().st_size == 0:
        return pd.DataFrame(columns=columns)

    loaded = pd.read_csv(history_path, encoding="utf-8-sig")
    history_schema.validate_required_columns(loaded.columns, history_schema.FORECAST_HISTORY)
    optional_columns = [column for column in loaded.columns if column not in columns]
    return loaded.loc[:, [*columns, *optional_columns]].copy()


def load_history_tables_for_app(
    forecast_history_path: str | Path | None = None,
    final_actuals_path: str | Path | None = None,
) -> dict[str, pd.DataFrame]:
    """Load history tables without failing when either storage file is absent."""
    final_path = (
        Path(final_actuals_path)
        if final_actuals_path is not None
        else _history_storage_path(history_schema.FINAL_ACTUALS)
    )
    return {
        "forecast_history": load_forecast_history_for_app(forecast_history_path),
        "final_actuals": load_final_actuals(final_path),
    }


def save_forecast_history_snapshot(
    scenario_df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    path: str | Path | None = None,
) -> pd.DataFrame:
    """Save the current scenario grid as one forecast history snapshot."""
    target_path = (
        Path(path)
        if path is not None
        else _history_storage_path(history_schema.FORECAST_HISTORY)
    )
    run_context = {
        "run_id": None,
        "run_datetime": pd.Timestamp.now(tz=APP_TIMEZONE),
        "target_month": pd.Timestamp(as_of_date).strftime("%Y-%m"),
        "as_of_date": pd.Timestamp(as_of_date).date().isoformat(),
        "metric": metric,
    }
    rows = build_forecast_history_rows(scenario_df, run_context)
    return append_forecast_history(rows, target_path)


def build_backtest_insights(
    forecast_history: pd.DataFrame,
    final_actuals: pd.DataFrame,
    model_summary: pd.DataFrame,
) -> list[str]:
    """Return concise interpretation messages for the Backtest tab."""
    if forecast_history.empty:
        return ["저장된 forecast_history가 아직 없습니다. 계산 후 예측 이력 저장을 누르면 Backtest 표본이 쌓입니다."]
    if final_actuals.empty:
        return ["final_actuals가 아직 없어 예측값과 확정 실적의 오차율은 계산하지 않았습니다."]
    if model_summary.empty:
        return ["forecast_history와 final_actuals의 target_month/metric이 아직 매칭되지 않아 Backtest 요약을 만들 수 없습니다."]

    ranked = model_summary.copy()
    ranked["mean_error_rate"] = pd.to_numeric(ranked["mean_error_rate"], errors="coerce")
    ranked = ranked.loc[ranked["mean_error_rate"].notna()].sort_values(
        ["mean_error_rate", "forecast_model"],
        kind="mergesort",
    )
    if ranked.empty:
        return ["Backtest 표본은 있지만 유효한 평균 오차율이 없어 모델 우열을 판단하지 않았습니다."]

    best = ranked.iloc[0]
    bias = _as_float(best.get("bias"))
    bias_message = "bias는 거의 중립입니다."
    if math.isfinite(bias) and bias > 0:
        bias_message = "bias가 양수라 평균적으로 과대 예측 경향이 있습니다."
    elif math.isfinite(bias) and bias < 0:
        bias_message = "bias가 음수라 평균적으로 과소 예측 경향이 있습니다."

    return [
        f"현재 표본 기준 최저 평균 오차율 모델은 {best.get('forecast_model')}이며 평균 오차율은 {format_rate(best.get('mean_error_rate'))}입니다.",
        bias_message,
        "동적 가중 예측은 이 모델별 오차율과 bias가 충분히 누적된 뒤 적용 후보로 판단할 수 있습니다.",
    ]


def _history_storage_path(schema_name: str) -> Path:
    return history_schema.get_storage_paths(repo_root=REPO_ROOT)[schema_name]


def format_amount(value: object) -> str:
    """Format an amount in hundred-million KRW."""
    number = _as_float(value)
    if not math.isfinite(number):
        return "계산 불가"
    return f"{number:.1f}억 원"


def format_rate(value: object) -> str:
    """Format a decimal ratio as a percentage."""
    number = _as_float(value)
    if not math.isfinite(number):
        return "계산 불가"
    return f"{number * 100:.1f}%"


def safe_divide(numerator: object, denominator: object) -> float:
    """Return numerator / denominator or NaN for unavailable ratios."""
    numerator_value = _as_float(numerator)
    denominator_value = _as_float(denominator)
    if not math.isfinite(numerator_value) or not math.isfinite(denominator_value):
        return float("nan")
    if denominator_value == 0:
        return float("nan")
    return numerator_value / denominator_value


def build_historical_monthly_summary(
    historical_df: pd.DataFrame,
    metric: str,
) -> pd.DataFrame:
    """Return month-level final target and achievement summaries."""
    prepared = _prepare_historical_metric_frame(historical_df, metric)
    if prepared.empty:
        return pd.DataFrame(
            columns=[
                "month",
                "row_count",
                "completed_actual_days",
                "final_business_day_no",
                "monthly_target",
                "final_actual_cum",
                "final_achievement_rate",
                "close_day_count",
            ]
        )

    rows: list[dict[str, object]] = []
    for month, month_df in prepared.groupby("_month", sort=True):
        completed = month_df.dropna(subset=["_actual_cum"])
        final_business_day_no = (
            completed["_business_day_no"].max()
            if not completed.empty
            else month_df["_business_day_no"].max()
        )
        final_actual_cum = (
            completed.sort_values(["_business_day_no", "_date"])["_actual_cum"].iloc[-1]
            if not completed.empty
            else float("nan")
        )
        monthly_target = month_df["_target_daily"].sum()
        rows.append(
            {
                "month": str(month),
                "row_count": int(len(month_df)),
                "completed_actual_days": int(len(completed)),
                "final_business_day_no": int(final_business_day_no),
                "monthly_target": float(monthly_target),
                "final_actual_cum": float(final_actual_cum),
                "final_achievement_rate": safe_divide(final_actual_cum, monthly_target),
                "close_day_count": int(month_df["_is_close_day"].sum()),
            }
        )
    return pd.DataFrame(rows)


def build_historical_stage_benchmark(
    historical_df: pd.DataFrame,
    current_df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    validation_result: dict[str, Any] | None = None,
) -> dict[str, object]:
    """Compare the current month with historical months at the same business-day stage."""
    stage_df = build_historical_stage_comparison(
        historical_df,
        current_df,
        as_of_date,
        metric,
    )
    current_business_day_no = _current_business_day_no(current_df, as_of_date)
    current_monthly_target = _historical_context_value(
        validation_result,
        "monthly_target",
        _current_monthly_target(current_df, metric),
    )
    current_target_cum = _historical_context_value(
        validation_result,
        "current_target_cum",
        _current_target_cum(current_df, as_of_date, metric),
    )
    current_actual_cum = _historical_context_value(
        validation_result,
        "current_actual_cum",
        _current_actual_cum(current_df, as_of_date, metric),
    )
    current_rate = safe_divide(current_actual_cum, current_target_cum)

    result: dict[str, object] = {
        "month_count": int(len(stage_df)),
        "current_business_day_no": current_business_day_no,
        "current_monthly_target": current_monthly_target,
        "current_target_cum": current_target_cum,
        "current_actual_cum": current_actual_cum,
        "current_achievement_rate": current_rate,
        "historical_stage_median_rate": float("nan"),
        "historical_stage_p25_rate": float("nan"),
        "historical_stage_p75_rate": float("nan"),
        "historical_final_median_rate": float("nan"),
        "historical_forecast_lower": float("nan"),
        "historical_forecast_median": float("nan"),
        "historical_forecast_upper": float("nan"),
        "current_stage_percentile": float("nan"),
        "stage_df": stage_df,
    }
    if stage_df.empty:
        return result

    stage_rates = pd.to_numeric(
        stage_df["as_of_achievement_rate"],
        errors="coerce",
    ).dropna()
    final_rates = pd.to_numeric(
        stage_df["final_achievement_rate"],
        errors="coerce",
    ).dropna()
    if not stage_rates.empty:
        result["historical_stage_median_rate"] = float(stage_rates.median())
        result["historical_stage_p25_rate"] = float(stage_rates.quantile(0.25))
        result["historical_stage_p75_rate"] = float(stage_rates.quantile(0.75))
        if math.isfinite(current_rate):
            result["current_stage_percentile"] = float((stage_rates <= current_rate).mean())
    if not final_rates.empty:
        result["historical_final_median_rate"] = float(final_rates.median())

    multiplier_source = stage_df.copy()
    multiplier_source["stage_to_final_multiplier"] = [
        safe_divide(final_rate, stage_rate)
        for final_rate, stage_rate in zip(
            multiplier_source["final_achievement_rate"],
            multiplier_source["as_of_achievement_rate"],
        )
    ]
    multipliers = pd.to_numeric(
        multiplier_source["stage_to_final_multiplier"],
        errors="coerce",
    ).dropna()
    multipliers = multipliers.loc[multipliers.map(math.isfinite)]
    multipliers = multipliers.loc[multipliers > 0]
    if not multipliers.empty and math.isfinite(current_rate):
        result["historical_forecast_lower"] = float(
            current_monthly_target * current_rate * multipliers.quantile(0.25)
        )
        result["historical_forecast_median"] = float(
            current_monthly_target * current_rate * multipliers.median()
        )
        result["historical_forecast_upper"] = float(
            current_monthly_target * current_rate * multipliers.quantile(0.75)
        )
    return result


def build_historical_stage_comparison(
    historical_df: pd.DataFrame,
    current_df: pd.DataFrame,
    as_of_date: object,
    metric: str,
) -> pd.DataFrame:
    """Return historical month rows matched to the current business-day stage."""
    prepared = _prepare_historical_metric_frame(historical_df, metric)
    if prepared.empty:
        return pd.DataFrame()

    current_business_day_no = _current_business_day_no(current_df, as_of_date)
    if not math.isfinite(current_business_day_no):
        return pd.DataFrame()

    monthly_summary = build_historical_monthly_summary(historical_df, metric)
    monthly_summary = monthly_summary.set_index("month", drop=False)
    rows: list[dict[str, object]] = []
    for month, month_df in prepared.groupby("_month", sort=True):
        candidates = month_df.loc[
            (month_df["_business_day_no"] <= current_business_day_no)
            & month_df["_actual_cum"].notna()
            & (month_df["_target_cum"] > 0)
        ]
        if candidates.empty or str(month) not in monthly_summary.index:
            continue

        stage_row = candidates.sort_values(["_business_day_no", "_date"]).iloc[-1]
        final_row = monthly_summary.loc[str(month)]
        rows.append(
            {
                "month": str(month),
                "matched_business_day_no": int(stage_row["_business_day_no"]),
                "as_of_target_cum": float(stage_row["_target_cum"]),
                "as_of_actual_cum": float(stage_row["_actual_cum"]),
                "as_of_achievement_rate": safe_divide(
                    stage_row["_actual_cum"],
                    stage_row["_target_cum"],
                ),
                "monthly_target": float(final_row["monthly_target"]),
                "final_actual_cum": float(final_row["final_actual_cum"]),
                "final_achievement_rate": float(final_row["final_achievement_rate"]),
                "remaining_actual_growth": float(
                    final_row["final_actual_cum"] - stage_row["_actual_cum"]
                ),
            }
        )
    return pd.DataFrame(rows)


def build_historical_progress_profile(
    historical_df: pd.DataFrame,
    metric: str,
) -> pd.DataFrame:
    """Return historical cumulative achievement bands by business day."""
    prepared = _prepare_historical_metric_frame(historical_df, metric)
    if prepared.empty:
        return pd.DataFrame()

    valid = prepared.dropna(subset=["_achievement_rate"])
    if valid.empty:
        return pd.DataFrame()

    grouped = valid.groupby("_business_day_no")["_achievement_rate"]
    profile = pd.DataFrame(
        {
            "business_day_no": grouped.median().index.astype(int),
            "historical_p25_rate": grouped.quantile(0.25).to_numpy(),
            "historical_median_rate": grouped.median().to_numpy(),
            "historical_p75_rate": grouped.quantile(0.75).to_numpy(),
            "month_count": grouped.count().to_numpy(),
        }
    )
    return profile.reset_index(drop=True)


def build_historical_progress_chart_data(
    historical_df: pd.DataFrame,
    current_df: pd.DataFrame,
    as_of_date: object,
    metric: str,
) -> pd.DataFrame:
    """Return long-form current and historical progress data for charting."""
    profile = build_historical_progress_profile(historical_df, metric)
    current_progress = _build_current_progress_series(current_df, as_of_date, metric)
    rows: list[dict[str, object]] = []

    for _, row in profile.iterrows():
        business_day_no = int(row["business_day_no"])
        for column, label in (
            ("historical_p25_rate", "과거 하위 25%"),
            ("historical_median_rate", "과거 중앙값"),
            ("historical_p75_rate", "과거 상위 25%"),
        ):
            rows.append(
                {
                    "business_day_no": business_day_no,
                    "series": label,
                    "achievement_rate": float(row[column]),
                }
            )

    for _, row in current_progress.iterrows():
        rows.append(
            {
                "business_day_no": int(row["business_day_no"]),
                "series": "현재 월",
                "achievement_rate": float(row["achievement_rate"]),
            }
        )
    return pd.DataFrame(rows)


def build_historical_context(
    historical_df: pd.DataFrame,
    current_df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    validation_result: dict[str, Any],
    source_label: str = "",
) -> dict[str, object]:
    """Return all historical analysis artifacts used by the UI."""
    history = _as_dataframe(historical_df)
    if history.empty:
        return {"has_data": False, "source_label": source_label}

    monthly_summary = build_historical_monthly_summary(history, metric)
    benchmark = build_historical_stage_benchmark(
        history,
        current_df,
        as_of_date,
        metric,
        validation_result,
    )
    chart_data = build_historical_progress_chart_data(
        history,
        current_df,
        as_of_date,
        metric,
    )
    return {
        "has_data": True,
        "source_label": source_label,
        "row_count": int(len(history)),
        "monthly_summary": monthly_summary,
        "benchmark": benchmark,
        "progress_chart_data": chart_data,
        "interpretation": build_historical_interpretation(benchmark),
    }


def build_historical_interpretation(benchmark: dict[str, object]) -> list[str]:
    """Return business-readable interpretation sentences for historical context."""
    month_count = int(benchmark.get("month_count") or 0)
    if month_count == 0:
        return [
            "현재 기준 영업일차와 비교할 수 있는 과거 월 데이터가 아직 부족합니다.",
            "과거 파일에는 같은 영업일차까지 누적 실적이 입력된 완료 월을 포함해 주세요.",
        ]

    current_rate = _as_float(benchmark.get("current_achievement_rate"))
    median_rate = _as_float(benchmark.get("historical_stage_median_rate"))
    p25_rate = _as_float(benchmark.get("historical_stage_p25_rate"))
    p75_rate = _as_float(benchmark.get("historical_stage_p75_rate"))
    current_business_day_no = benchmark.get("current_business_day_no")

    messages = [
        f"현재 월은 {current_business_day_no}영업일차 기준으로 과거 {month_count}개 월과 비교합니다.",
    ]
    if math.isfinite(current_rate) and math.isfinite(median_rate):
        diff = current_rate - median_rate
        messages.append(
            f"현재 누적 달성률은 {format_rate(current_rate)}이고, 같은 영업일차 과거 중앙값은 {format_rate(median_rate)}입니다."
        )
        if math.isfinite(p25_rate) and current_rate < p25_rate:
            messages.append("현재 흐름은 과거 하위 25%보다 낮아 월말 리스크를 보수적으로 보는 편이 좋습니다.")
        elif math.isfinite(p75_rate) and current_rate > p75_rate:
            messages.append("현재 흐름은 과거 상위 25%보다 높아 초과분 관리와 품질 리스크를 함께 볼 구간입니다.")
        else:
            messages.append("현재 흐름은 과거 일반 범위 안에 있어 기존 예측모델과 함께 균형 있게 해석할 수 있습니다.")
        if abs(diff) >= 0.01:
            messages.append(f"과거 중앙값 대비 차이는 {diff * 100:+.1f}%p입니다.")

    lower = _as_float(benchmark.get("historical_forecast_lower"))
    median = _as_float(benchmark.get("historical_forecast_median"))
    upper = _as_float(benchmark.get("historical_forecast_upper"))
    if all(math.isfinite(value) for value in (lower, median, upper)):
        messages.append(
            "과거의 같은 시점 이후 월말 전환 흐름을 적용하면 "
            f"{format_amount(lower)} ~ {format_amount(upper)} 범위, 중앙값 {format_amount(median)} 수준으로 읽을 수 있습니다."
        )
    return messages


def _prepare_historical_metric_frame(
    df: pd.DataFrame,
    metric: str,
) -> pd.DataFrame:
    metric_columns = get_metric_columns(metric)
    target_column = metric_columns["target_daily"]
    actual_column = metric_columns["actual_cum"]
    required_columns = {"date", "business_day_no", "is_close_day", target_column, actual_column}
    if df.empty or not required_columns.issubset(df.columns):
        return pd.DataFrame()

    result = df.copy()
    result["_date"] = pd.to_datetime(result["date"], errors="coerce")
    result["_month"] = result["_date"].dt.to_period("M").astype(str)
    result["_business_day_no"] = pd.to_numeric(
        result["business_day_no"],
        errors="coerce",
    )
    result["_target_daily"] = pd.to_numeric(result[target_column], errors="coerce")
    result["_actual_cum"] = pd.to_numeric(result[actual_column], errors="coerce")
    result["_is_close_day"] = result["is_close_day"].astype(bool)
    result = result.dropna(subset=["_date", "_business_day_no", "_target_daily"])
    if result.empty:
        return pd.DataFrame()

    result = result.sort_values(["_month", "_business_day_no", "_date"]).reset_index(drop=True)
    result["_target_cum"] = result.groupby("_month")["_target_daily"].cumsum()
    result["_achievement_rate"] = [
        safe_divide(actual, target)
        for actual, target in zip(result["_actual_cum"], result["_target_cum"])
    ]
    return result


def _build_current_progress_series(
    current_df: pd.DataFrame,
    as_of_date: object,
    metric: str,
) -> pd.DataFrame:
    prepared = _prepare_historical_metric_frame(current_df, metric)
    if prepared.empty:
        return pd.DataFrame(columns=["business_day_no", "achievement_rate"])

    as_of_timestamp = pd.Timestamp(as_of_date).normalize()
    current = prepared.loc[
        (prepared["_date"].dt.normalize() <= as_of_timestamp)
        & prepared["_actual_cum"].notna()
        & prepared["_achievement_rate"].notna()
    ].copy()
    if current.empty:
        return pd.DataFrame(columns=["business_day_no", "achievement_rate"])
    return pd.DataFrame(
        {
            "business_day_no": current["_business_day_no"].astype(int),
            "achievement_rate": current["_achievement_rate"].astype(float),
        }
    )


def _current_business_day_no(df: pd.DataFrame, as_of_date: object) -> float:
    if df.empty or "date" not in df.columns or "business_day_no" not in df.columns:
        return float("nan")

    dates = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    as_of_timestamp = pd.Timestamp(as_of_date).normalize()
    rows = df.loc[dates == as_of_timestamp]
    if rows.empty:
        return float("nan")
    return float(pd.to_numeric(rows.iloc[0]["business_day_no"], errors="coerce"))


def _current_monthly_target(df: pd.DataFrame, metric: str) -> float:
    metric_columns = get_metric_columns(metric)
    target_column = metric_columns["target_daily"]
    if df.empty or target_column not in df.columns:
        return float("nan")
    return float(pd.to_numeric(df[target_column], errors="coerce").sum())


def _current_target_cum(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
) -> float:
    metric_columns = get_metric_columns(metric)
    target_column = metric_columns["target_daily"]
    if df.empty or "date" not in df.columns or target_column not in df.columns:
        return float("nan")

    dates = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    as_of_timestamp = pd.Timestamp(as_of_date).normalize()
    values = pd.to_numeric(df.loc[dates <= as_of_timestamp, target_column], errors="coerce")
    if values.empty:
        return float("nan")
    return float(values.sum())


def _current_actual_cum(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
) -> float:
    metric_columns = get_metric_columns(metric)
    actual_column = metric_columns["actual_cum"]
    if df.empty or "date" not in df.columns or actual_column not in df.columns:
        return float("nan")

    dates = pd.to_datetime(df["date"], errors="coerce").dt.normalize()
    as_of_timestamp = pd.Timestamp(as_of_date).normalize()
    rows = df.loc[dates == as_of_timestamp]
    if rows.empty:
        return float("nan")
    return float(pd.to_numeric(pd.Series([rows.iloc[0][actual_column]]), errors="coerce").iloc[0])


def _historical_context_value(
    validation_result: dict[str, Any] | None,
    key: str,
    fallback: float,
) -> float:
    if validation_result is None:
        return fallback
    value = _as_float(validation_result.get(key))
    if math.isfinite(value):
        return value
    return fallback


def _build_template_workbook_bytes(
    sheet_title: str,
    sample_rows: tuple[tuple[object, ...], ...],
) -> bytes:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_title
    worksheet.append(list(INPUT_TEMPLATE_HEADERS))
    for row in sample_rows:
        worksheet.append(list(row))

    header_fill = PatternFill(fill_type="solid", fgColor="44546A")
    header_font = Font(bold=True, color="FFFFFF")
    for cell in worksheet[1]:
        cell.fill = header_fill
        cell.font = header_font

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = f"A1:J{worksheet.max_row}"
    for cell in worksheet[1]:
        cell_width = max(12, min(28, len(str(cell.value)) + 4))
        worksheet.column_dimensions[cell.column_letter].width = cell_width

    buffer = io.BytesIO()
    workbook.save(buffer)
    workbook.close()
    return buffer.getvalue()


def build_input_template_bytes() -> bytes:
    return _build_template_workbook_bytes("InputTemplate", INPUT_TEMPLATE_SAMPLE_ROWS)


def build_historical_input_template_bytes() -> bytes:
    return _build_template_workbook_bytes(
        "HistoricalInputTemplate",
        _load_historical_input_template_sample_rows(),
    )


def _load_historical_input_template_sample_rows() -> tuple[tuple[object, ...], ...]:
    try:
        sample_df = pd.read_csv(HISTORICAL_SAMPLE_INPUT_PATH, encoding="utf-8-sig")
    except (OSError, UnicodeDecodeError, pd.errors.ParserError):
        return HISTORICAL_INPUT_TEMPLATE_SAMPLE_ROWS

    missing_columns = [
        column for column in INPUT_TEMPLATE_HEADERS if column not in sample_df.columns
    ]
    if missing_columns:
        return HISTORICAL_INPUT_TEMPLATE_SAMPLE_ROWS

    rows: list[tuple[object, ...]] = []
    for row in sample_df.loc[:, list(INPUT_TEMPLATE_HEADERS)].itertuples(
        index=False,
        name=None,
    ):
        rows.append(tuple(None if pd.isna(value) else value for value in row))

    return tuple(rows) or HISTORICAL_INPUT_TEMPLATE_SAMPLE_ROWS


def _render_input_template_download() -> None:
    st.download_button(
        "엑셀 업로드 양식 다운로드",
        data=build_input_template_bytes(),
        file_name=INPUT_TEMPLATE_FILENAME,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _render_historical_input_template_download() -> None:
    st.download_button(
        "과거 월 누적 업로드 양식 다운로드",
        data=build_historical_input_template_bytes(),
        file_name=HISTORICAL_INPUT_TEMPLATE_FILENAME,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )


def _render_file_upload() -> tuple[pd.DataFrame | None, str]:
    st.header("1. 파일 업로드")
    _render_input_template_download()
    st.caption("새로 업로드한 입력 파일의 누적 실적은 최신 기본값으로 등록됩니다.")
    uploaded_file = st.file_uploader("입력 파일 업로드", type=["csv", "xlsx"])
    uploaded_name = getattr(uploaded_file, "name", None)
    if uploaded_name != st.session_state.get("uploaded_file_name"):
        st.session_state["uploaded_file_name"] = uploaded_name
        st.session_state["force_sample_input"] = False
    if st.button("샘플 데이터 로딩"):
        st.session_state["force_sample_input"] = True

    try:
        if uploaded_file is not None and not st.session_state.get("force_sample_input", False):
            return _load_uploaded_input(uploaded_file), uploaded_file.name
        return load_input(SAMPLE_INPUT_PATH), SAMPLE_INPUT_SOURCE_LABEL
    except Exception as exc:  # noqa: BLE001 - surface load errors in the UI.
        st.error(f"입력 파일을 로딩할 수 없습니다: {exc}")
        return None, ""


def _render_historical_upload() -> tuple[pd.DataFrame, str]:
    st.header("1-1. 과거 월 누적 데이터")
    with st.expander("과거 월 데이터 업로드(선택)", expanded=False):
        st.caption(
            "현재 입력 파일과 같은 컬럼 구조의 CSV/XLSX를 여러 월 누적 형태로 업로드합니다. "
            "과거 월 파일은 비교 계산에만 사용하고 최신 기본값 저장 대상에서는 제외합니다."
        )
        _render_historical_input_template_download()
        uploaded_file = st.file_uploader(
            "과거 월 누적 파일 업로드",
            type=["csv", "xlsx"],
            key="historical_month_upload",
        )
        sample_col, clear_col = st.columns(2)
        if sample_col.button("과거 샘플 데이터 로딩", key="load_historical_sample"):
            st.session_state["use_historical_sample_input"] = True
        if clear_col.button("과거 데이터 비우기", key="clear_historical_sample"):
            st.session_state["use_historical_sample_input"] = False
            return pd.DataFrame(), ""

        try:
            if uploaded_file is not None:
                st.session_state["use_historical_sample_input"] = False
                historical_df = _load_uploaded_input(
                    uploaded_file,
                    sort_by="date",
                    strict_business_day_no=False,
                )
                st.success(f"과거 월 데이터 {len(historical_df)}행을 불러왔습니다.")
                return historical_df, uploaded_file.name

            if st.session_state.get("use_historical_sample_input", False):
                historical_df = load_input(
                    HISTORICAL_SAMPLE_INPUT_PATH,
                    sort_by="date",
                    strict_business_day_no=False,
                )
                st.success(f"과거 샘플 데이터 {len(historical_df)}행을 불러왔습니다.")
                return historical_df, HISTORICAL_SAMPLE_INPUT_SOURCE_LABEL
        except Exception as exc:  # noqa: BLE001 - surface load errors in the UI.
            st.error(f"과거 월 데이터를 로딩할 수 없습니다: {exc}")
            return pd.DataFrame(), ""

        st.info("과거 월 데이터를 업로드하면 현재 월을 같은 영업일차의 과거 흐름과 비교합니다.")
    return pd.DataFrame(), ""


def _render_input_editor(df: pd.DataFrame, source_label: str) -> pd.DataFrame:
    st.header("2. 입력 수정")
    saved_actuals = _load_saved_actuals_for_ui()
    df, default_source = apply_latest_upload_policy(df, source_label, saved_actuals)
    if default_source == "uploaded":
        st.caption("업로드 입력값을 최신 실적 기본값으로 등록했습니다.")
    elif default_source == "saved":
        st.caption(f"저장된 실적 기본값 {len(saved_actuals)}건을 불러왔습니다.")

    editor_key = "direct_input_editor"
    source_key = "direct_input_editor_source"
    source_token = _input_source_token(df, source_label)
    if st.session_state.get(source_key) != source_token:
        st.session_state[source_key] = source_token
        st.session_state.pop(editor_key, None)

    reset_col, clear_col = st.columns(2)
    if reset_col.button("입력값 초기화", key="reset_direct_input_editor"):
        st.session_state.pop(editor_key, None)
    if clear_col.button("저장된 실적값 삭제", key="clear_saved_actuals"):
        clear_saved_actuals()
        st.session_state.pop(editor_key, None)
        st.session_state.pop(source_key, None)
        st.rerun()

    edited_df = st.data_editor(
        df,
        column_config=_input_editor_column_config(),
        disabled=_non_editable_input_columns(df),
        hide_index=True,
        key=editor_key,
        num_rows="fixed",
        use_container_width=True,
    )
    normalized = normalize_direct_input_edits(_as_dataframe(edited_df))
    save_actual_values(normalized)
    return normalized


def apply_latest_upload_policy(
    df: pd.DataFrame,
    source_label: str,
    saved_actuals: pd.DataFrame,
    path: str | Path = SAVED_ACTUALS_PATH,
) -> tuple[pd.DataFrame, str]:
    """Apply the latest-value policy for uploaded current-month inputs."""
    if _is_current_upload_source(source_label):
        normalized = normalize_direct_input_edits(df)
        save_actual_values(normalized, path)
        return normalized, "uploaded"

    if not saved_actuals.empty:
        return apply_saved_actuals(df, saved_actuals), "saved"

    return df.copy(), "none"


def _is_current_upload_source(source_label: str) -> bool:
    return bool(source_label) and source_label != SAMPLE_INPUT_SOURCE_LABEL


def _load_saved_actuals_for_ui() -> pd.DataFrame:
    try:
        return load_saved_actuals()
    except Exception as exc:  # noqa: BLE001 - keep the app usable if the store is corrupt.
        st.warning(f"저장된 실적값을 불러올 수 없습니다: {exc}")
        return pd.DataFrame(columns=SAVED_ACTUAL_COLUMNS)


def _input_source_token(df: pd.DataFrame, source_label: str) -> str:
    parts = [source_label, str(len(df))]
    for column in ("date", "business_day_no", "is_close_day", "close_type"):
        if column in df.columns:
            parts.append(f"{column}:{','.join(df[column].astype(str).tolist())}")
    return "|".join(parts)


def _input_editor_column_config() -> dict[str, object]:
    if st is None:
        return {}

    return {
        "date": st.column_config.DateColumn("날짜", format="YYYY-MM-DD"),
        "day_name": st.column_config.TextColumn("요일(표시용)"),
        "business_day_no": st.column_config.NumberColumn("영업일 번호", format="%d"),
        "is_close_day": st.column_config.CheckboxColumn("마감일 여부"),
        "close_type": st.column_config.TextColumn("마감 유형"),
        "sales_target_daily": st.column_config.NumberColumn(
            "판매실적 일 목표",
            min_value=0.0,
            step=0.1,
            format="%.1f",
        ),
        "recognized_target_daily": st.column_config.NumberColumn(
            "인정실적 일 목표",
            min_value=0.0,
            step=0.1,
            format="%.1f",
        ),
        "sales_actual_cum": st.column_config.NumberColumn(
            "판매실적 누적 실적",
            min_value=0.0,
            step=0.1,
            format="%.1f",
        ),
        "recognized_actual_cum": st.column_config.NumberColumn(
            "인정실적 누적 실적",
            min_value=0.0,
            step=0.1,
            format="%.1f",
        ),
        "memo": st.column_config.TextColumn("메모"),
    }


def _non_editable_input_columns(df: pd.DataFrame) -> list[str]:
    return [column for column in df.columns if column not in DIRECT_EDITABLE_COLUMNS]


def _render_settings(
    df: pd.DataFrame,
    base_config: dict[str, Any],
) -> tuple[str, pd.Timestamp, str, str, dict[str, Any]]:
    st.header("3. 기준 설정")
    metric = st.selectbox(
        "지표 선택",
        ["sales", "recognized"],
        index=0,
        format_func=lambda value: METRIC_DISPLAY_LABELS.get(value, value),
    )
    dates = pd.to_datetime(df["date"], errors="raise")
    date_values = [timestamp.date() for timestamp in dates]
    default_date = default_as_of_date(df, metric).date()
    default_index = date_values.index(default_date) if default_date in date_values else 0
    as_of_date = st.selectbox(
        "기준일 선택",
        date_values,
        index=default_index,
        key=f"as_of_date_{metric}_{default_date.isoformat()}",
    )
    forecast_choice = st.selectbox(
        "예측모델 선택",
        ["F1", "F2", "F3", COMPARE_LABEL],
        index=3,
    )
    provision_choice = st.selectbox(
        "운영 전략 선택",
        ["P1", "P2", "P3", "O1", "O2", "O3", "N1", "N2", "N3", COMPARE_LABEL],
        index=9,
    )

    col1, col2 = st.columns(2)
    close_day_cap_rate = col1.number_input(
        "마감일 목표 상한 배율",
        min_value=0.0,
        value=float(base_config.get("close_day_cap_rate", 1.30)),
        step=0.05,
        format="%.2f",
    )
    non_close_day_cap_rate = col2.number_input(
        "비마감일 목표 상한 배율",
        min_value=0.0,
        value=float(base_config.get("non_close_day_cap_rate", 1.50)),
        step=0.05,
        format="%.2f",
    )
    config = build_runtime_config(
        base_config,
        close_day_cap_rate,
        non_close_day_cap_rate,
    )
    return metric, pd.Timestamp(as_of_date), forecast_choice, provision_choice, config


def _render_validation(validation_result: dict[str, Any]) -> None:
    errors = format_validation_messages(list(validation_result.get("errors", [])))
    warnings = format_validation_messages(list(validation_result.get("warnings", [])))
    if errors:
        st.error("수정이 필요한 항목")
        for message in errors:
            st.write(f"- {message}")
    else:
        st.success("계산을 막는 입력 문제 없음")

    if warnings:
        st.warning("확인하면 좋은 항목")
        for message in warnings:
            st.write(f"- {message}")
    else:
        st.info("추가로 확인할 주의 사항 없음")


def _render_selected_scenario_picker(
    scenario_df: pd.DataFrame,
    forecast_choice: str,
    provision_choice: str,
) -> str:
    candidates = _filter_scenarios(scenario_df, forecast_choice, provision_choice)
    scenario_ids = candidates["scenario_id"].astype(str).tolist()
    if len(scenario_ids) == 1:
        st.caption(f"선택 시나리오: {format_scenario_option_label(scenario_ids[0])}")
        return scenario_ids[0]
    return st.selectbox(
        "선택 시나리오 상세",
        scenario_ids,
        format_func=format_scenario_option_label,
        index=0,
    )


def _render_kpis(
    validation_result: dict[str, Any],
    scenario_df: pd.DataFrame,
    next_close_result: dict[str, Any],
    selected_row: pd.Series,
) -> None:
    for row in build_kpi_rows(
        validation_result,
        scenario_df,
        next_close_result,
        selected_row,
    ):
        cols = st.columns(len(row))
        for col, (label, value) in zip(cols, row):
            help_text = KPI_HELP_TEXTS.get(label)
            if help_text:
                col.metric(label, value, help=help_text)
            else:
                col.metric(label, value)


def build_kpi_rows(
    validation_result: dict[str, Any],
    scenario_df: pd.DataFrame,
    next_close_result: dict[str, Any],
    selected_row: pd.Series,
) -> tuple[tuple[tuple[str, object], ...], ...]:
    achievement_rate = safe_divide(
        validation_result.get("current_actual_cum"),
        validation_result.get("current_target_cum"),
    )
    forecast_summary = _forecast_summary(scenario_df)
    next_close_date = next_close_result.get("next_close_date")
    next_close_required = next_close_result.get("required_to_recover_next_close_cum")
    target_status = selected_row.get("target_status", "계산 불가")

    return (
        (
            ("월 목표", format_amount(validation_result.get("monthly_target"))),
            ("기준일 누적 목표", format_amount(validation_result.get("current_target_cum"))),
            ("기준일 누적 실적", format_amount(validation_result.get("current_actual_cum"))),
            ("누적 달성률", format_rate(achievement_rate)),
        ),
        (
            ("F1예상", format_amount(forecast_summary.get("F1"))),
            ("F2예상", format_amount(forecast_summary.get("F2"))),
            ("F3예상", format_amount(forecast_summary.get("F3"))),
        ),
        (
            ("다음 마감일", _format_date(next_close_date)),
            (NEXT_CLOSE_REQUIRED_LABEL, format_amount(next_close_required)),
        ),
        (
            ("목표상태", _localize_display_value(target_status)),
            ("목표대비 차이", format_amount(selected_row.get("target_variance"))),
            ("초과 예상분", format_amount(selected_row.get("surplus_to_target"))),
            ("위험등급", _localize_display_value(selected_row.get("risk_level", "계산 불가"))),
            ("운영모드", _operation_mode_label(target_status)),
        ),
    )


def _render_body(
    scenario_df: pd.DataFrame,
    selected_scenario_id: str,
    selected_row: pd.Series,
    forecast_result: dict[str, object],
    provision_result: dict[str, object],
    revised_targets_df: Any,
    close_cycle_df: pd.DataFrame,
    next_close_result: dict[str, Any],
    validation_result: dict[str, Any],
    historical_context: dict[str, object],
    metric: str,
    as_of_date: object,
    df: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    _render_visuals(
        scenario_df,
        selected_scenario_id,
        selected_row,
        _as_dataframe(revised_targets_df),
        close_cycle_df,
        next_close_result,
        validation_result,
        metric,
        as_of_date,
        df,
        config,
    )
    _render_historical_context_panel(historical_context)

    st.subheader("시나리오 매트릭스")
    st.dataframe(build_scenario_matrix(scenario_df), use_container_width=True)

    _render_selected_scenario_summary(selected_scenario_id, selected_row)

    with st.expander("선택 시나리오 상세", expanded=False):
        detail_df = selected_row.to_frame(name="value").reset_index()
        detail_df.columns = ["item", "value"]
        st.dataframe(_format_display_df(detail_df), use_container_width=True)

    warnings = [
        *list(forecast_result.get("warnings", [])),
        *list(provision_result.get("warnings", [])),
    ]
    if warnings:
        st.warning("선택 시나리오 확인 사항")
        for message in dict.fromkeys(str(warning) for warning in warnings):
            st.write(f"- {format_validation_message(message)}")

    _render_target_or_strategy_table(
        scenario_df,
        selected_scenario_id,
        revised_targets_df,
    )

    st.subheader("자동 보고문")
    report_text = build_daily_report_text(
        scenario_df,
        next_close_result,
        selected_scenario_id=selected_scenario_id,
    )
    _render_report_glossary_panel()
    report_key = hashlib.sha1(report_text.encode("utf-8")).hexdigest()[:12]
    st.text_area("자동 보고문", value=report_text, height=320, key=f"auto_report_{report_key}")

    st.subheader("입력값 점검 결과")
    _render_validation(validation_result)


def _render_report_glossary_panel() -> None:
    glossary_df = build_report_glossary_df()
    with st.expander("자동 보고문 고정 용어 정의", expanded=False):
        st.caption("보고문 본문과 분리해 별도로 운영하는 고정 기준값입니다.")
        tabs = st.tabs([group for group, _ in REPORT_GLOSSARY_GROUPS])
        for tab, (group, _) in zip(tabs, REPORT_GLOSSARY_GROUPS):
            with tab:
                group_df = glossary_df.loc[glossary_df["구분"] == group, ["코드", "정의"]]
                st.dataframe(group_df, hide_index=True, use_container_width=True)


def _render_selected_scenario_summary(
    selected_scenario_id: str,
    selected_row: pd.Series,
) -> None:
    st.subheader("선택 시나리오 요약")
    st.dataframe(
        build_selected_scenario_explanation(selected_scenario_id, selected_row),
        hide_index=True,
        use_container_width=True,
    )


def _render_target_or_strategy_table(
    scenario_df: pd.DataFrame,
    selected_scenario_id: str,
    revised_targets_df: Any,
) -> None:
    revised_targets = _as_dataframe(revised_targets_df)
    if not revised_targets.empty:
        st.subheader("잔여 일자별 수정 목표표")
        st.caption("목표 미달 보정전략(P1~P3)에서 입력표에 있는 잔여 일자별 목표를 어떻게 수정하는지 표시합니다.")
        st.dataframe(
            _format_display_df(revised_targets),
            use_container_width=True,
        )
        return

    strategy_table = build_strategy_level_table(scenario_df, selected_scenario_id)
    st.subheader("운영전략별 목표 수준표")
    st.caption(
        "초과달성/유지 전략은 입력표 밖 날짜를 만들거나 잔여 일자 목표를 강제로 재배분하지 않습니다. "
        "대신 선택한 예측모델의 운영전략별 월 목표, 초과 예상분, 안전버퍼, 품질관리 여유분을 표시합니다."
    )
    if strategy_table.empty:
        st.info("운영전략별 목표 수준 데이터 없음")
        return
    st.dataframe(
        _format_display_df(strategy_table),
        use_container_width=True,
    )


def _render_visuals(
    scenario_df: pd.DataFrame,
    selected_scenario_id: str,
    selected_row: pd.Series,
    revised_targets_df: pd.DataFrame,
    close_cycle_df: pd.DataFrame,
    next_close_result: dict[str, Any],
    validation_result: dict[str, Any],
    metric: str,
    as_of_date: object,
    df: pd.DataFrame,
    config: dict[str, Any],
) -> None:
    st.subheader("시각화")
    st.caption("각 탭은 결론 확인 → 기준선 확인 → 차이 확인 → 실행 판단 순서로 읽습니다.")
    _render_visual_decision_panel(
        selected_scenario_id,
        selected_row,
        validation_result,
        next_close_result,
    )
    scenario_tab, target_tab, close_cycle_tab, history_tab = st.tabs(
        ["시나리오별 예상", "잔여 목표/전략 수준", "마감차수 흐름", HISTORY_TAB_LABEL]
    )

    with scenario_tab:
        scenario_chart_data = build_scenario_chart_data(scenario_df)
        if scenario_chart_data.empty:
            st.info("시나리오 차트 데이터 없음")
        else:
            _render_visual_metric_definitions(
                ("daily_forecast_cum", "daily_target_cum", "daily_achievement_rate")
            )
            _render_chart_reading_guide("scenario_daily_progress")
            _render_forecast_model_scenario_tabs(
                df,
                scenario_df,
                as_of_date,
                metric,
                config,
                selected_scenario_id,
            )

            with st.expander("시나리오 숫자표", expanded=False):
                value_matrix = build_scenario_value_matrix(scenario_df)
                st.dataframe(value_matrix.map(format_amount), use_container_width=True)

    with target_tab:
        st.caption(f"선택 시나리오: {selected_scenario_id}")
        target_chart_data = build_remaining_target_chart_data(revised_targets_df)
        if target_chart_data.empty:
            _render_strategy_level_visuals(scenario_df, selected_scenario_id)
        else:
            _render_visual_metric_definitions(
                ("original_target", "uplift", "revised_target", "cap_target")
            )
            _render_chart_reading_guide("target_stack")
            _render_remaining_target_stack_chart(revised_targets_df)

    with close_cycle_tab:
        close_cycle_bar_columns = ("target_sum", "actual_sum")
        close_cycle_rate_columns = ("achievement_rate",)
        _render_visual_metric_definitions(
            (*close_cycle_bar_columns, *close_cycle_rate_columns)
        )
        close_cycle_chart_data = build_close_cycle_chart_data(close_cycle_df)
        if close_cycle_chart_data.empty:
            st.info("마감 사이클 차트 데이터 없음")
        else:
            _render_chart_reading_guide("close_cycle_amount")
            _render_grouped_bar_chart(close_cycle_chart_data, close_cycle_bar_columns)
            _render_chart_reading_guide("close_cycle_rate")
            _render_line_chart(close_cycle_chart_data, close_cycle_rate_columns)

    with history_tab:
        _render_forecast_history_backtest_tab(scenario_df, metric, as_of_date)


def _render_visual_decision_panel(
    selected_scenario_id: str,
    selected_row: pd.Series,
    validation_result: dict[str, Any],
    next_close_result: dict[str, Any],
) -> None:
    st.markdown("**결론 먼저 보기**")
    st.info(build_visual_headline(selected_row, validation_result, next_close_result))

    cols = st.columns(4)
    cols[0].metric("선택 시나리오", selected_scenario_id)
    cols[1].metric(
        "전략 반영 후 예상",
        format_amount(selected_row.get("forecast_after_provision")),
        delta=_format_signed_amount(selected_row.get("target_variance")),
        help="delta는 공식 월 목표 대비 차이입니다.",
    )
    cols[2].metric("목표 상태", _localize_display_value(selected_row.get("target_status")))
    cols[3].metric("위험등급", _localize_display_value(selected_row.get("risk_level", "N/A")))

    with st.expander("차트 해석 순서", expanded=True):
        st.dataframe(
            build_visual_decision_summary(
                selected_row,
                validation_result,
                next_close_result,
            ),
            hide_index=True,
            use_container_width=True,
        )


def _render_forecast_history_backtest_tab(
    scenario_df: pd.DataFrame,
    metric: str,
    as_of_date: object,
) -> None:
    st.subheader(HISTORY_TAB_LABEL)
    st.caption("현재 계산 결과를 저장하고, 월마감 확정 실적과 매칭되는 이력은 Backtest로 비교합니다.")

    save_col, path_col = st.columns([1, 3])
    if save_col.button("예측 이력 저장", key=f"save_forecast_history_{metric}_{pd.Timestamp(as_of_date).date()}"):
        try:
            saved_history = save_forecast_history_snapshot(scenario_df, as_of_date, metric)
            st.success(f"예측 이력을 저장했습니다. forecast_history {len(saved_history)}건")
        except Exception as exc:  # noqa: BLE001 - Streamlit should stay usable.
            st.warning(f"예측 이력을 저장하지 못했습니다: {exc}")

    path_col.caption(
        f"forecast_history: {_history_storage_path(history_schema.FORECAST_HISTORY)} | "
        f"final_actuals: {_history_storage_path(history_schema.FINAL_ACTUALS)}"
    )

    tables = _load_history_tables_for_ui()
    forecast_history = tables["forecast_history"]
    final_actuals = tables["final_actuals"]
    focused_history = _focus_history_for_current_context(
        forecast_history,
        metric,
        as_of_date,
    )

    st.markdown("**forecast_history 테이블**")
    if forecast_history.empty:
        st.info("forecast_history 파일이 없거나 저장된 예측 이력이 없습니다. 예측 이력 저장 후 이 표에 누적됩니다.")
    else:
        st.dataframe(
            _format_display_df(forecast_history.tail(200)),
            hide_index=True,
            use_container_width=True,
        )

    st.markdown("**final_actuals 테이블**")
    if final_actuals.empty:
        st.info("final_actuals가 아직 없습니다. 월마감 확정 실적이 저장되면 Backtest 오차율을 계산합니다.")
    else:
        st.dataframe(
            _format_display_df(final_actuals.tail(200)),
            hide_index=True,
            use_container_width=True,
        )

    backtest_df = build_backtest_dataset(forecast_history, final_actuals)
    model_summary = summarize_by_forecast_model(backtest_df)

    st.markdown("**모델별 평균 오차율 / bias**")
    if model_summary.empty:
        st.info("예측 이력과 확정 실적의 대상 월/지표가 아직 매칭되지 않아 모델별 평균 오차율과 bias를 표시할 수 없습니다.")
    else:
        st.dataframe(
            _format_display_df(model_summary),
            hide_index=True,
            use_container_width=True,
        )

    _render_forecast_history_trend_chart(focused_history)
    _render_target_status_distribution(focused_history)
    _render_gap_surplus_trend_chart(focused_history)
    _render_optional_weighted_forecast(focused_history)
    _render_optional_confidence_band(focused_history)

    st.markdown("**Insight**")
    for message in build_backtest_insights(forecast_history, final_actuals, model_summary):
        st.write(f"- {message}")


def _load_history_tables_for_ui() -> dict[str, pd.DataFrame]:
    try:
        return load_history_tables_for_app()
    except Exception as exc:  # noqa: BLE001 - keep the app usable if storage is corrupt.
        st.warning(f"예측 이력/Backtest 저장소를 불러오지 못했습니다: {exc}")
        return {
            "forecast_history": pd.DataFrame(columns=history_schema.FORECAST_HISTORY_COLUMNS),
            "final_actuals": pd.DataFrame(columns=history_schema.FINAL_ACTUALS_COLUMNS),
        }


def _focus_history_for_current_context(
    forecast_history: pd.DataFrame,
    metric: str,
    as_of_date: object,
) -> pd.DataFrame:
    if forecast_history.empty:
        return forecast_history

    focused = forecast_history.copy()
    if "metric" in focused.columns:
        metric_rows = focused.loc[focused["metric"].astype(str) == str(metric)]
        if not metric_rows.empty:
            focused = metric_rows

    if "target_month" in focused.columns:
        target_month = pd.Timestamp(as_of_date).strftime("%Y-%m")
        month_rows = focused.loc[focused["target_month"].astype(str) == target_month]
        if not month_rows.empty:
            focused = month_rows
    return focused.reset_index(drop=True)


def _render_forecast_history_trend_chart(forecast_history: pd.DataFrame) -> None:
    st.markdown("**예측 추이 그래프**")
    source = _history_long_metric_source(forecast_history, ("forecast_amount",))
    if source.empty:
        st.info("예측 추이 그래프를 만들 forecast_amount 이력이 없습니다.")
        return

    chart = (
        alt.Chart(source)
        .mark_line(point=True, strokeWidth=2.4)
        .encode(
            x=alt.X("as_of_date:T", title="기준일"),
            y=alt.Y(
                "value:Q",
                title="예측값",
                scale=_auto_value_scale(source),
                axis=alt.Axis(format=chart_value_format("억원")),
            ),
            color=alt.Color("forecast_model:N", title="예측 모델"),
            tooltip=[
                alt.Tooltip("as_of_date:T", title="기준일"),
                alt.Tooltip("forecast_model:N", title="예측 모델"),
                alt.Tooltip("value:Q", title="예측값", format=chart_value_format("억원")),
            ],
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_target_status_distribution(forecast_history: pd.DataFrame) -> None:
    st.markdown("**target_status 분포**")
    if forecast_history.empty or "target_status" not in forecast_history.columns:
        st.info("target_status 분포를 만들 예측 이력이 없습니다.")
        return

    source = (
        forecast_history["target_status"]
        .fillna("UNKNOWN")
        .astype(str)
        .value_counts()
        .rename_axis("target_status")
        .reset_index(name="count")
    )
    source["target_status_label"] = source["target_status"].map(_localize_display_value)
    chart = (
        alt.Chart(source)
        .mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            x=alt.X("target_status_label:N", title="목표 상태", sort=None),
            y=alt.Y("count:Q", title="건수", axis=alt.Axis(format="d")),
            color=alt.Color("target_status_label:N", title="목표 상태"),
            tooltip=[
                alt.Tooltip("target_status_label:N", title="목표 상태"),
                alt.Tooltip("count:Q", title="건수", format="d"),
            ],
        )
        .properties(height=260)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_gap_surplus_trend_chart(forecast_history: pd.DataFrame) -> None:
    st.markdown("**gap_to_target / surplus_to_target 추이**")
    source = _history_long_metric_source(
        forecast_history,
        ("gap_to_target", "surplus_to_target"),
    )
    if source.empty:
        st.info("gap_to_target / surplus_to_target 추이를 만들 이력이 없습니다.")
        return

    chart = (
        alt.Chart(source)
        .mark_line(point=True, strokeWidth=2.3)
        .encode(
            x=alt.X("as_of_date:T", title="기준일"),
            y=alt.Y(
                "value:Q",
                title="금액",
                scale=_auto_value_scale(source),
                axis=alt.Axis(format=chart_value_format("억원")),
            ),
            color=alt.Color("metric_label:N", title="항목"),
            strokeDash=alt.StrokeDash("forecast_model:N", title="예측 모델"),
            tooltip=[
                alt.Tooltip("as_of_date:T", title="기준일"),
                alt.Tooltip("forecast_model:N", title="예측 모델"),
                alt.Tooltip("metric_label:N", title="항목"),
                alt.Tooltip("value:Q", title="금액", format=chart_value_format("억원")),
            ],
        )
        .properties(height=300)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_optional_weighted_forecast(forecast_history: pd.DataFrame) -> None:
    st.markdown("**Weighted Forecast**")
    weighted_columns = _optional_columns_by_token(
        forecast_history,
        WEIGHTED_FORECAST_COLUMN_TOKENS,
    )
    if not weighted_columns:
        st.caption("Weighted Forecast 데이터가 아직 없습니다.")
        return

    display_columns = _available_columns(
        forecast_history,
        ("target_month", "as_of_date", "metric", *weighted_columns),
    )
    weighted_rows = forecast_history.loc[:, display_columns].dropna(
        how="all",
        subset=weighted_columns,
    )
    if weighted_rows.empty:
        st.caption("Weighted Forecast 컬럼은 있지만 표시할 값이 없습니다.")
        return
    st.dataframe(_format_display_df(weighted_rows.tail(100)), hide_index=True, use_container_width=True)


def _render_optional_confidence_band(forecast_history: pd.DataFrame) -> None:
    st.markdown("**Confidence Band**")
    band_pair = _confidence_band_pair(forecast_history)
    if band_pair is None:
        st.caption("Confidence Band 데이터가 아직 없습니다.")
        return

    lower_column, upper_column = band_pair
    display_columns = _available_columns(
        forecast_history,
        ("target_month", "as_of_date", "metric", "forecast_model", "forecast_amount", lower_column, upper_column),
    )
    band_rows = forecast_history.loc[:, display_columns].dropna(
        how="all",
        subset=[lower_column, upper_column],
    )
    if band_rows.empty:
        st.caption("Confidence Band 컬럼은 있지만 표시할 값이 없습니다.")
        return
    st.dataframe(_format_display_df(band_rows.tail(100)), hide_index=True, use_container_width=True)


def _history_long_metric_source(
    forecast_history: pd.DataFrame,
    value_columns: tuple[str, ...],
) -> pd.DataFrame:
    if forecast_history.empty or "as_of_date" not in forecast_history.columns:
        return pd.DataFrame()

    available_value_columns = [
        column
        for column in value_columns
        if column in forecast_history.columns
    ]
    if not available_value_columns:
        return pd.DataFrame()

    working = forecast_history.copy()
    working["as_of_date"] = pd.to_datetime(working["as_of_date"], errors="coerce")
    if "forecast_model" not in working.columns:
        working["forecast_model"] = "ALL"
    for column in available_value_columns:
        working[column] = pd.to_numeric(working[column], errors="coerce")

    grouped = (
        working.dropna(subset=["as_of_date"])
        .groupby(["as_of_date", "forecast_model"], dropna=False)[available_value_columns]
        .mean()
        .reset_index()
    )
    source = grouped.melt(
        id_vars=["as_of_date", "forecast_model"],
        value_vars=available_value_columns,
        var_name="metric",
        value_name="value",
    ).dropna(subset=["value"])
    source["metric_label"] = source["metric"].map(_display_column_label)
    return source.reset_index(drop=True)


def _optional_columns_by_token(
    df: pd.DataFrame,
    tokens: tuple[str, ...],
) -> list[str]:
    if df.empty:
        return []
    lower_tokens = tuple(token.lower() for token in tokens)
    return [
        column
        for column in df.columns
        if any(token in str(column).lower() for token in lower_tokens)
    ]


def _confidence_band_pair(df: pd.DataFrame) -> tuple[str, str] | None:
    if df.empty:
        return None
    columns = set(df.columns)
    for lower_column, upper_column in CONFIDENCE_BAND_COLUMN_PAIRS:
        if lower_column in columns and upper_column in columns:
            return lower_column, upper_column
    return None


def _available_columns(
    df: pd.DataFrame,
    preferred_columns: tuple[str, ...],
) -> list[str]:
    return [column for column in preferred_columns if column in df.columns]


def _render_historical_context_panel(historical_context: dict[str, object]) -> None:
    if not historical_context.get("has_data"):
        return

    benchmark = dict(historical_context.get("benchmark") or {})
    source_label = str(historical_context.get("source_label") or "과거 월 데이터")
    row_count = int(historical_context.get("row_count") or 0)
    month_count = int(benchmark.get("month_count") or 0)

    st.subheader("과거 월 누적 기준 해석")
    st.caption(
        f"과거 데이터: {source_label} | {row_count}행 | 같은 영업일차 비교 가능 월 {month_count}개"
    )

    lower = benchmark.get("historical_forecast_lower")
    median = benchmark.get("historical_forecast_median")
    upper = benchmark.get("historical_forecast_upper")
    forecast_range = (
        f"{format_amount(lower)} ~ {format_amount(upper)}"
        if math.isfinite(_as_float(lower)) and math.isfinite(_as_float(upper))
        else "계산 불가"
    )

    cols = st.columns(4)
    cols[0].metric("현재 누적 달성률", format_rate(benchmark.get("current_achievement_rate")))
    cols[1].metric("과거 중앙값", format_rate(benchmark.get("historical_stage_median_rate")))
    cols[2].metric("과거 보정 예상 범위", forecast_range)
    cols[3].metric("과거 보정 중앙값", format_amount(median))

    for message in historical_context.get("interpretation", []):
        st.write(f"- {message}")

    progress_chart_data = _as_dataframe(historical_context.get("progress_chart_data"))
    _render_historical_progress_chart(progress_chart_data)

    stage_df = _as_dataframe(benchmark.get("stage_df"))
    if not stage_df.empty:
        with st.expander("같은 영업일차 과거 월 비교표", expanded=False):
            st.dataframe(
                _format_historical_stage_df(stage_df),
                hide_index=True,
                use_container_width=True,
            )

    monthly_summary = _as_dataframe(historical_context.get("monthly_summary"))
    if not monthly_summary.empty:
        with st.expander("과거 월별 최종 요약", expanded=False):
            st.dataframe(
                _format_historical_monthly_summary_df(monthly_summary),
                hide_index=True,
                use_container_width=True,
            )


def _render_historical_progress_chart(chart_data: pd.DataFrame) -> None:
    if chart_data.empty:
        st.info("과거 누적 흐름 차트 데이터 없음")
        return

    chart = (
        alt.Chart(chart_data)
        .mark_line(point=True, strokeWidth=2.3)
        .encode(
            x=alt.X(
                "business_day_no:O",
                title="영업일차",
                sort=None,
                axis=alt.Axis(labelAngle=0),
            ),
            y=alt.Y(
                "achievement_rate:Q",
                title="누적 달성률",
                axis=alt.Axis(format=".0%"),
                scale=alt.Scale(zero=False, nice=True),
            ),
            color=alt.Color(
                "series:N",
                title="범례",
                scale=alt.Scale(
                    domain=["현재 월", "과거 중앙값", "과거 하위 25%", "과거 상위 25%"],
                    range=["#DC2626", "#2563EB", "#94A3B8", "#64748B"],
                ),
            ),
            tooltip=[
                alt.Tooltip("business_day_no:O", title="영업일차"),
                alt.Tooltip("series:N", title="범례"),
                alt.Tooltip("achievement_rate:Q", title="누적 달성률", format=".1%"),
            ],
        )
        .properties(height=320)
        .configure_axis(labelFontSize=11, titleFontSize=12)
        .configure_legend(labelFontSize=11, titleFontSize=12)
    )
    st.altair_chart(chart, use_container_width=True)


def _format_historical_stage_df(stage_df: pd.DataFrame) -> pd.DataFrame:
    result = stage_df.copy()
    columns = [
        "month",
        "matched_business_day_no",
        "as_of_target_cum",
        "as_of_actual_cum",
        "as_of_achievement_rate",
        "monthly_target",
        "final_actual_cum",
        "final_achievement_rate",
        "remaining_actual_growth",
    ]
    result = result.loc[:, [column for column in columns if column in result.columns]]
    for column in (
        "as_of_target_cum",
        "as_of_actual_cum",
        "monthly_target",
        "final_actual_cum",
        "remaining_actual_growth",
    ):
        if column in result.columns:
            result[column] = result[column].map(format_amount)
    for column in ("as_of_achievement_rate", "final_achievement_rate"):
        if column in result.columns:
            result[column] = result[column].map(format_rate)
    return result.rename(
        columns={
            "month": "월",
            "matched_business_day_no": "비교 영업일차",
            "as_of_target_cum": "당시 누적 목표",
            "as_of_actual_cum": "당시 누적 실적",
            "as_of_achievement_rate": "당시 누적 달성률",
            "monthly_target": "월 목표",
            "final_actual_cum": "최종 누적 실적",
            "final_achievement_rate": "최종 달성률",
            "remaining_actual_growth": "비교일 이후 증가 실적",
        }
    )


def _format_historical_monthly_summary_df(monthly_summary: pd.DataFrame) -> pd.DataFrame:
    result = monthly_summary.copy()
    columns = [
        "month",
        "row_count",
        "completed_actual_days",
        "final_business_day_no",
        "monthly_target",
        "final_actual_cum",
        "final_achievement_rate",
        "close_day_count",
    ]
    result = result.loc[:, [column for column in columns if column in result.columns]]
    for column in ("monthly_target", "final_actual_cum"):
        if column in result.columns:
            result[column] = result[column].map(format_amount)
    if "final_achievement_rate" in result.columns:
        result["final_achievement_rate"] = result["final_achievement_rate"].map(format_rate)
    return result.rename(
        columns={
            "month": "월",
            "row_count": "행 수",
            "completed_actual_days": "실적 입력일 수",
            "final_business_day_no": "최종 영업일차",
            "monthly_target": "월 목표",
            "final_actual_cum": "최종 누적 실적",
            "final_achievement_rate": "최종 달성률",
            "close_day_count": "마감일 수",
        }
    )


def _render_strategy_level_visuals(
    scenario_df: pd.DataFrame,
    selected_scenario_id: str,
) -> None:
    strategy_table = build_strategy_level_table(scenario_df, selected_scenario_id)
    if strategy_table.empty:
        st.info("운영전략별 목표 수준 데이터 없음")
        return

    _render_visual_metric_definitions(
        ("monthly_target", "forecast_after_provision", "target_variance")
    )
    _render_chart_reading_guide("scenario_target_position")
    _render_scenario_target_position_chart(strategy_table, selected_scenario_id)

    st.dataframe(_format_display_df(strategy_table), use_container_width=True)


def _render_forecast_model_scenario_tabs(
    df: pd.DataFrame,
    scenario_df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    config: dict[str, Any],
    selected_scenario_id: str | None,
) -> None:
    forecast_keys = [
        forecast_key
        for forecast_key in ("F1", "F2", "F3")
        if not _scenario_df_for_forecast_key(scenario_df, forecast_key).empty
    ]
    if not forecast_keys:
        st.info("예측모델별 시나리오 데이터 없음")
        return

    tabs = st.tabs([f"{forecast_key} 예측" for forecast_key in forecast_keys])
    for tab, forecast_key in zip(tabs, forecast_keys):
        with tab:
            model_scenario_df = _scenario_df_for_forecast_key(scenario_df, forecast_key)
            model_selected_id = _default_scenario_for_forecast_key(
                model_scenario_df,
                forecast_key,
                selected_scenario_id,
            )
            st.caption(
                f"{forecast_key} 기준으로 운영전략만 비교합니다. "
                "그래프는 해당 예측모델의 전략선만 표시합니다."
            )
            strategy_scenario_id = _render_model_strategy_selector(
                model_scenario_df,
                forecast_key,
                model_selected_id,
            )
            daily_forecast_source = build_scenario_daily_forecast_source(
                df,
                model_scenario_df,
                as_of_date,
                metric,
                config,
                strategy_scenario_id,
            )
            _render_scenario_daily_forecast_chart(
                daily_forecast_source,
                model_scenario_df,
                strategy_scenario_id,
            )
            _render_remaining_operation_direction_panel(
                df,
                as_of_date,
                metric,
                config,
                strategy_scenario_id,
            )
            _render_selected_scenario_daily_detail_table(
                daily_forecast_source,
                strategy_scenario_id,
            )


def _scenario_df_for_forecast_key(
    scenario_df: pd.DataFrame,
    forecast_key: str,
) -> pd.DataFrame:
    if scenario_df.empty or "scenario_id" not in scenario_df.columns:
        return pd.DataFrame(columns=scenario_df.columns)
    return scenario_df.loc[
        scenario_df["scenario_id"].astype(str).str.startswith(f"{forecast_key}_")
    ].reset_index(drop=True)


def _default_scenario_for_forecast_key(
    model_scenario_df: pd.DataFrame,
    forecast_key: str,
    selected_scenario_id: str | None,
) -> str:
    scenario_ids = model_scenario_df["scenario_id"].astype(str).tolist()
    selected_id = str(selected_scenario_id or "")
    if selected_id.startswith(f"{forecast_key}_") and selected_id in scenario_ids:
        return selected_id
    if scenario_ids:
        return scenario_ids[0]
    return ""


def _render_model_strategy_selector(
    model_scenario_df: pd.DataFrame,
    forecast_key: str,
    selected_scenario_id: str,
) -> str:
    scenario_ids = model_scenario_df["scenario_id"].astype(str).tolist()
    if not scenario_ids:
        return ""

    default_index = (
        scenario_ids.index(selected_scenario_id)
        if selected_scenario_id in scenario_ids
        else 0
    )
    return st.selectbox(
        "잔여기간 운영전략",
        scenario_ids,
        format_func=format_scenario_option_label,
        index=default_index,
        key=f"remaining_strategy_{forecast_key}_{'_'.join(scenario_ids)}",
    )


def _render_remaining_operation_direction_panel(
    df: pd.DataFrame,
    as_of_date: object,
    metric: str,
    config: dict[str, Any],
    scenario_id: str,
) -> None:
    if not scenario_id:
        st.info("잔여기간 운영전략을 선택할 수 없습니다.")
        return

    forecast_result, strategy_result = run_selected_scenario_detail(
        df,
        as_of_date,
        metric,
        scenario_id,
        config,
    )
    direction_source = build_remaining_operation_direction_source(
        df,
        as_of_date,
        metric,
        scenario_id,
        forecast_result,
        strategy_result,
    )
    if direction_source.empty:
        st.info("잔여기간 일자별 운영 방향 데이터 없음")
        return

    st.markdown("**잔여기간 일자별 운영 방향**")
    _render_remaining_operation_direction_chart(direction_source)
    with st.expander("잔여기간 운영 방향표", expanded=False):
        st.dataframe(
            _format_remaining_operation_direction_df(direction_source),
            hide_index=True,
            use_container_width=True,
        )


def _render_remaining_operation_direction_chart(source: pd.DataFrame) -> None:
    chart_source = source.copy()
    chart_source["date"] = pd.to_datetime(chart_source["date"], errors="coerce")
    chart_source = chart_source.dropna(subset=["date"])
    if chart_source.empty:
        st.info("잔여기간 운영 방향 차트 데이터 없음")
        return

    for column in ("original_target", "uplift", "revised_target", "expected_daily"):
        chart_source[column] = pd.to_numeric(chart_source[column], errors="coerce")

    date_order = chart_source["date_label"].tolist()
    bar = (
        alt.Chart(chart_source)
        .mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            x=alt.X(
                "date_label:N",
                title=None,
                sort=date_order,
                axis=alt.Axis(labelAngle=-30, labelLimit=110),
            ),
            y=alt.Y(
                "revised_target:Q",
                title="일자별 관리 목표(억원)",
                axis=alt.Axis(format=chart_value_format("억원")),
            ),
            color=alt.Color(
                "direction:N",
                title="운영 방향",
                scale=alt.Scale(
                    domain=[
                        "추가 배분",
                        "상한 점검",
                        "기존 목표 유지",
                        "버퍼 방어",
                        "Stretch 후보",
                        "유지 모니터링",
                    ],
                    range=[
                        "#2563EB",
                        "#DC2626",
                        "#94A3B8",
                        "#059669",
                        "#7C3AED",
                        "#0F766E",
                    ],
                ),
            ),
            tooltip=[
                alt.Tooltip("date_label:N", title="날짜"),
                alt.Tooltip("day_type:N", title="일자 구분"),
                alt.Tooltip("operation_mode:N", title="운영 모드"),
                alt.Tooltip("direction:N", title="운영 방향"),
                alt.Tooltip("original_target:Q", title="기존 일 목표", format=chart_value_format("억원")),
                alt.Tooltip("uplift:Q", title="업리프트", format=chart_value_format("억원")),
                alt.Tooltip("revised_target:Q", title="관리 목표", format=chart_value_format("억원")),
                alt.Tooltip("expected_daily:Q", title="예상 일실적", format=chart_value_format("억원")),
                alt.Tooltip("direction_detail:N", title="해석"),
            ],
        )
    )
    expected_line = (
        alt.Chart(chart_source)
        .mark_line(point=True, color="#111827", strokeWidth=2)
        .encode(
            x=alt.X("date_label:N", sort=date_order),
            y=alt.Y("expected_daily:Q"),
            tooltip=[
                alt.Tooltip("date_label:N", title="날짜"),
                alt.Tooltip("expected_daily:Q", title="예상 일실적", format=chart_value_format("억원")),
            ],
        )
    )
    chart = (
        (bar + expected_line)
        .properties(height=280)
        .configure_axis(labelFontSize=11, titleFontSize=12)
        .configure_legend(labelFontSize=11, titleFontSize=12)
    )
    st.altair_chart(chart, use_container_width=True)


def _format_remaining_operation_direction_df(source: pd.DataFrame) -> pd.DataFrame:
    result = source.copy()
    result = result.loc[:, list(REMAINING_OPERATION_DIRECTION_COLUMNS)]
    result["date"] = result["date"].map(_format_date)
    for column in ("original_target", "uplift", "revised_target", "expected_daily"):
        result[column] = result[column].map(format_amount)
    result["expected_rate"] = result["expected_rate"].map(format_rate)
    return result.rename(
        columns={
            "date": "날짜",
            "date_label": "날짜 라벨",
            "scenario_id": "시나리오",
            "strategy_type": "전략 구분",
            "operation_mode": "운영 모드",
            "day_type": "일자 구분",
            "close_type": "마감 유형",
            "original_target": "기존 일 목표",
            "uplift": "업리프트",
            "revised_target": "관리 목표",
            "expected_daily": "예상 일실적",
            "expected_rate": "예상 달성률",
            "direction": "운영 방향",
            "direction_detail": "방향 해석",
        }
    )


def _render_scenario_daily_forecast_chart(
    source: pd.DataFrame,
    scenario_df: pd.DataFrame,
    selected_scenario_id: str | None = None,
) -> None:
    if source.empty:
        st.info("주간 시나리오 누적 전망 데이터 없음")
        return

    chart_source = source.copy()
    chart_source["date"] = pd.to_datetime(chart_source["date"], errors="coerce")
    chart_source["week_start"] = pd.to_datetime(chart_source["week_start"], errors="coerce")
    chart_source["week_end"] = pd.to_datetime(chart_source["week_end"], errors="coerce")
    chart_source = chart_source.dropna(subset=["date", "forecast_cum"])
    if chart_source.empty:
        st.info("주간 시나리오 누적 전망 데이터 없음")
        return

    target_source = (
        chart_source.loc[
            :,
            [
                "date",
                "week_end",
                "week_label",
                "target_cum",
                "monthly_target",
                "target_achievement_rate",
                "target_achievement_label",
            ],
        ]
        .drop_duplicates("date")
        .sort_values("date")
    )
    week_marker_source = (
        chart_source.loc[:, ["week_start", "week_label"]]
        .dropna(subset=["week_start"])
        .drop_duplicates("week_start")
        .sort_values("week_start")
    )
    actual_source = chart_source.loc[chart_source["series_type"] == "확정 실적"]
    forecast_source = chart_source.loc[chart_source["series_type"] == "시나리오 예상"]
    position_source = build_scenario_target_position_source(scenario_df, selected_scenario_id)
    forecast_source = _attach_scenario_position_fields(forecast_source, position_source)
    close_day_source = source.loc[
        source["is_close_day"],
        ["date", "date_label", "close_type"],
    ].drop_duplicates("date")
    close_day_source["date"] = pd.to_datetime(close_day_source["date"], errors="coerce")
    close_day_source = close_day_source.dropna(subset=["date"])
    close_day_source["band_start"] = close_day_source["date"] - pd.Timedelta(hours=12)
    close_day_source["band_end"] = close_day_source["date"] + pd.Timedelta(hours=12)

    y_max = max(
        _finite_max(chart_source["achievement_rate"]),
        _finite_max(target_source["target_achievement_rate"]),
        1.0,
    )
    scenario_order = forecast_source["scenario_id"].drop_duplicates().tolist()
    selected_id = str(selected_scenario_id or "")
    final_label_source = _selected_daily_final_label_source(forecast_source, selected_id)
    as_of_dates = source.loc[source["is_as_of_date"], "date"].drop_duplicates()
    as_of_source = pd.DataFrame({"as_of_date": as_of_dates.tolist()[:1]})
    zoom = alt.selection_interval(bind="scales", encodings=["x"], name="weekly_zoom")
    x_axis = alt.Axis(
        format="%m/%d",
        labelAngle=0,
        tickCount=alt.TimeIntervalStep("week", 1),
    )

    close_day_band = (
        alt.Chart(close_day_source)
        .mark_rect(color="#FEF3C7", opacity=0.55)
        .encode(
            x=alt.X("band_start:T", title=None),
            x2="band_end:T",
            tooltip=[
                alt.Tooltip("date_label:N", title="마감일"),
                alt.Tooltip("close_type:N", title="마감 유형"),
            ],
        )
    )
    week_markers = (
        alt.Chart(week_marker_source)
        .mark_rule(color="#E2E8F0", strokeWidth=1)
        .encode(
            x=alt.X("week_start:T", title=None),
            tooltip=[alt.Tooltip("week_label:N", title="주간")],
        )
    )
    target_line = (
        alt.Chart(target_source)
        .mark_line(color="#94A3B8", strokeDash=[6, 5], strokeWidth=1.8, interpolate="linear")
        .encode(
            x=alt.X(
                "date:T",
                title=None,
                axis=x_axis,
            ),
            y=alt.Y(
                "target_achievement_rate:Q",
                title="월 목표 달성률",
                scale=alt.Scale(domain=[0, y_max * 1.08], nice=True),
                axis=alt.Axis(format=".0%"),
            ),
            tooltip=[
                alt.Tooltip("week_label:N", title="주간"),
                alt.Tooltip("target_cum:Q", title="누적 목표선", format=chart_value_format("억원")),
                alt.Tooltip("target_achievement_rate:Q", title="누적 목표 달성률", format=".1%"),
            ],
        )
    )
    actual_line = (
        alt.Chart(actual_source)
        .mark_line(color="#1D4ED8", strokeWidth=3, interpolate="linear")
        .encode(
            x=alt.X(
                "date:T",
                title=None,
                axis=x_axis,
            ),
            y=alt.Y("achievement_rate:Q"),
            tooltip=_daily_forecast_tooltips("확정 누적 실적", include_variance=False),
        )
    )
    forecast_lines = (
        alt.Chart(forecast_source)
        .mark_line(interpolate="linear")
        .encode(
            x=alt.X(
                "date:T",
                title=None,
                axis=x_axis,
            ),
            y=alt.Y("achievement_rate:Q"),
            color=alt.Color(
                "scenario_id:N",
                title="시나리오",
                sort=scenario_order,
                scale=alt.Scale(range=list(CHART_COLOR_RANGE)),
            ),
            detail="line_group:N",
            opacity=alt.condition("datum.is_selected", alt.value(1.0), alt.value(0.38)),
            strokeWidth=alt.condition("datum.is_selected", alt.value(3.2), alt.value(1.5)),
            tooltip=_daily_forecast_tooltips("누적 예상"),
        )
    )
    monthly_rule = (
        alt.Chart(pd.DataFrame({"goal_rate": [1.0]}))
        .mark_rule(color="#DC2626", strokeDash=[7, 5], strokeWidth=2)
        .encode(
            y="goal_rate:Q",
            tooltip=[
                alt.Tooltip(
                    "goal_rate:Q",
                    title="공식 월 목표선",
                    format=".0%",
                )
            ],
        )
    )
    as_of_rule = (
        alt.Chart(as_of_source)
        .mark_rule(color="#64748B", strokeDash=[2, 3], strokeWidth=1.4)
        .encode(
            x="as_of_date:T",
            tooltip=[alt.Tooltip("as_of_date:T", title="기준일", format="%Y-%m-%d")],
        )
    )
    final_label = (
        alt.Chart(final_label_source)
        .mark_text(align="right", baseline="middle", dx=-7, dy=-8, fontSize=11, fontWeight="bold")
        .encode(
            x="date:T",
            y="achievement_rate:Q",
            text="final_label:N",
            color=alt.value("#111827"),
        )
    )
    progress_chart = (
        (
            close_day_band
            + week_markers
            + target_line
            + actual_line
            + forecast_lines
            + monthly_rule
            + as_of_rule
            + final_label
        )
        .properties(height=330)
        .add_params(zoom)
    )

    chart = (
        progress_chart
        .configure_axis(labelFontSize=11, titleFontSize=12)
        .configure_legend(labelFontSize=11, titleFontSize=12)
    )
    st.caption("차트 위에서 마우스 휠 또는 드래그로 주간 구간을 확대/축소할 수 있습니다.")
    st.altair_chart(chart, use_container_width=True)


def _render_selected_scenario_daily_detail_table(
    daily_source: pd.DataFrame,
    selected_scenario_id: str | None,
) -> None:
    detail = build_selected_scenario_daily_detail_source(daily_source, selected_scenario_id)
    if detail.empty:
        return

    with st.expander("선택 시나리오 일자별 추정 내역", expanded=False):
        st.dataframe(
            _format_daily_forecast_detail_df(detail),
            hide_index=True,
            use_container_width=True,
        )


def _format_daily_forecast_detail_df(detail: pd.DataFrame) -> pd.DataFrame:
    result = detail.copy()
    result["date"] = result["date"].map(_format_date)
    result["daily_expected"] = result["daily_expected"].map(_format_optional_amount)
    result["forecast_cum"] = result["forecast_cum"].map(format_amount)
    result["target_cum"] = result["target_cum"].map(format_amount)
    result["achievement_rate"] = result["achievement_rate"].map(format_rate)
    result["target_achievement_rate"] = result["target_achievement_rate"].map(format_rate)
    return result.rename(
        columns={
            "date": "날짜",
            "scenario_id": "시나리오",
            "series_type": "구분",
            "day_type": "일자 구분",
            "close_type": "마감 유형",
            "daily_expected": "당일 추정",
            "forecast_cum": "누적 실적/예상",
            "target_cum": "누적 목표선",
            "achievement_rate": "월 목표 달성률",
            "target_achievement_rate": "계획선 달성률",
        }
    )


def _format_optional_amount(value: object) -> str:
    number = _as_float(value)
    if not math.isfinite(number):
        return "-"
    return format_amount(number)


def _daily_forecast_tooltips(
    value_title: str,
    *,
    include_variance: bool = True,
) -> list[alt.Tooltip]:
    tooltips = [
        alt.Tooltip("week_label:N", title="주간"),
        alt.Tooltip("date_label:N", title="대표일"),
        alt.Tooltip("scenario_id:N", title="시나리오"),
        alt.Tooltip("day_type:N", title="일자 구분"),
        alt.Tooltip("close_type:N", title="마감 유형"),
        alt.Tooltip("daily_expected:Q", title="당일 예상", format=chart_value_format("억원")),
        alt.Tooltip("forecast_cum:Q", title=value_title, format=chart_value_format("억원")),
        alt.Tooltip("target_cum:Q", title="누적 목표선", format=chart_value_format("억원")),
        alt.Tooltip("achievement_rate:Q", title="월 목표 달성률", format=".1%"),
        alt.Tooltip("target_achievement_rate:Q", title="계획선 달성률", format=".1%"),
        alt.Tooltip("risk_level_label:N", title="위험등급"),
    ]
    if include_variance:
        tooltips.insert(-1, alt.Tooltip("variance_label:N", title="월말 목표 대비 차이"))
    return tooltips


def _finite_max(values: pd.Series) -> float:
    numeric_values = pd.to_numeric(values, errors="coerce")
    numeric_values = numeric_values.loc[numeric_values.map(math.isfinite)]
    if numeric_values.empty:
        return 0.0
    return float(numeric_values.max())


def _selected_daily_final_label_source(
    forecast_source: pd.DataFrame,
    selected_scenario_id: str,
) -> pd.DataFrame:
    if forecast_source.empty:
        return pd.DataFrame(columns=[*SCENARIO_DAILY_FORECAST_COLUMNS, "final_label"])
    selected = forecast_source.loc[forecast_source["scenario_id"] == selected_scenario_id]
    if selected.empty:
        selected = forecast_source
    last_rows = (
        selected.sort_values(["scenario_id", "date"])
        .groupby("scenario_id", as_index=False)
        .tail(1)
        .copy()
    )
    if selected_scenario_id and selected_scenario_id in set(last_rows["scenario_id"].astype(str)):
        last_rows = last_rows.loc[last_rows["scenario_id"].astype(str) == selected_scenario_id]
    variance_label = last_rows.get(
        "variance_label",
        pd.Series([""] * len(last_rows), index=last_rows.index),
    ).fillna("")
    last_rows["final_label"] = (
        last_rows["scenario_id"].astype(str)
        + " "
        + last_rows["achievement_label"].astype(str)
        + " / "
        + variance_label.astype(str)
    )
    return last_rows


def _attach_scenario_position_fields(
    forecast_source: pd.DataFrame,
    position_source: pd.DataFrame,
) -> pd.DataFrame:
    if forecast_source.empty or position_source.empty:
        return forecast_source

    fields = [
        column
        for column in (
            "scenario_id",
            "target_variance",
            "variance_label",
            "target_status_label",
            "forecast_after_provision",
        )
        if column in position_source.columns
    ]
    if len(fields) <= 1:
        return forecast_source
    return forecast_source.merge(
        position_source.loc[:, fields].drop_duplicates("scenario_id"),
        on="scenario_id",
        how="left",
    )


def _render_scenario_target_position_chart(
    scenario_df: pd.DataFrame,
    selected_scenario_id: str | None = None,
) -> None:
    source = build_scenario_target_position_source(scenario_df, selected_scenario_id)
    if source.empty:
        st.info("목표선 대비 예상 실적 차트 데이터 없음")
        return

    scenario_order = source["scenario_id"].tolist()
    target_value = source["monthly_target"].dropna().iloc[0]
    x_max = max(
        float(source["forecast_after_provision"].max()),
        float(source["monthly_target"].max()),
        1.0,
    )
    bar = (
        alt.Chart(source)
        .mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3)
        .encode(
            y=alt.Y(
                "scenario_id:N",
                title=None,
                sort=scenario_order,
                axis=alt.Axis(labelLimit=120),
            ),
            x=alt.X(
                "forecast_after_provision:Q",
                title="전략 반영 후 예상(억원)",
                scale=alt.Scale(domain=[0, x_max * 1.08], nice=True),
                axis=alt.Axis(format=chart_value_format("억원")),
            ),
            color=alt.Color(
                "target_status_label:N",
                title="목표 상태",
                scale=alt.Scale(
                    domain=["목표 미달", "목표 달성", "목표 초과", "계산 불가"],
                    range=["#DC2626", "#2563EB", "#059669", "#6B7280"],
                ),
            ),
            opacity=alt.condition("datum.is_selected", alt.value(1.0), alt.value(0.68)),
            stroke=alt.condition("datum.is_selected", alt.value("#111827"), alt.value("#ffffff")),
            strokeWidth=alt.condition("datum.is_selected", alt.value(2.2), alt.value(0.4)),
            tooltip=[
                alt.Tooltip("scenario_id:N", title="시나리오"),
                alt.Tooltip("target_status_label:N", title="목표 상태"),
                alt.Tooltip("risk_level_label:N", title="위험등급"),
                alt.Tooltip(
                    "forecast_after_provision:Q",
                    title="전략 반영 후 예상",
                    format=chart_value_format("억원"),
                ),
                alt.Tooltip(
                    "monthly_target:Q",
                    title="공식 월 목표",
                    format=chart_value_format("억원"),
                ),
                alt.Tooltip("variance_label:N", title="목표 대비 차이"),
            ],
        )
    )
    target_rule = (
        alt.Chart(pd.DataFrame({"monthly_target": [target_value]}))
        .mark_rule(color="#DC2626", strokeDash=[6, 4], strokeWidth=2)
        .encode(
            x="monthly_target:Q",
            tooltip=[
                alt.Tooltip(
                    "monthly_target:Q",
                    title="공식 월 목표",
                    format=chart_value_format("억원"),
                )
            ],
        )
    )
    labels = (
        alt.Chart(source)
        .mark_text(align="left", baseline="middle", dx=5, fontSize=11)
        .encode(
            y=alt.Y("scenario_id:N", sort=scenario_order),
            x="forecast_after_provision:Q",
            text="forecast_label:N",
        )
    )
    chart = (
        (bar + target_rule + labels)
        .properties(height=max(260, len(source) * 30))
        .configure_axis(labelFontSize=11, titleFontSize=12)
        .configure_legend(labelFontSize=11, titleFontSize=12)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_scenario_gap_chart(
    scenario_df: pd.DataFrame,
    selected_scenario_id: str | None = None,
) -> None:
    source = build_scenario_target_position_source(scenario_df, selected_scenario_id)
    if source.empty:
        st.info("부족/초과 금액 차트 데이터 없음")
        return

    scenario_order = source["scenario_id"].tolist()
    magnitude = max(
        float(source["target_variance"].abs().max(skipna=True) or 0.0),
        1.0,
    )
    x_domain = [-magnitude * 1.2, magnitude * 1.2]
    bar = (
        alt.Chart(source)
        .mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3)
        .encode(
            y=alt.Y(
                "scenario_id:N",
                title=None,
                sort=scenario_order,
                axis=alt.Axis(labelLimit=120),
            ),
            x=alt.X(
                "target_variance:Q",
                title="목표 대비 차이(억원)",
                scale=alt.Scale(domain=x_domain, nice=True),
                axis=alt.Axis(format=chart_value_format("억원")),
            ),
            color=alt.condition(
                "datum.target_variance >= 0",
                alt.value("#059669"),
                alt.value("#DC2626"),
            ),
            opacity=alt.condition("datum.is_selected", alt.value(1.0), alt.value(0.7)),
            tooltip=[
                alt.Tooltip("scenario_id:N", title="시나리오"),
                alt.Tooltip("target_status_label:N", title="목표 상태"),
                alt.Tooltip("variance_label:N", title="목표 대비 차이"),
            ],
        )
    )
    zero_rule = alt.Chart(pd.DataFrame({"zero": [0]})).mark_rule(
        color="#111827",
        strokeWidth=1.4,
    ).encode(x="zero:Q")
    positive_text = (
        alt.Chart(source.loc[source["target_variance"] >= 0])
        .mark_text(align="left", baseline="middle", dx=4, fontSize=11)
        .encode(
            y=alt.Y("scenario_id:N", sort=scenario_order),
            x="target_variance:Q",
            text="variance_label:N",
        )
    )
    negative_text = (
        alt.Chart(source.loc[source["target_variance"] < 0])
        .mark_text(align="right", baseline="middle", dx=-4, fontSize=11)
        .encode(
            y=alt.Y("scenario_id:N", sort=scenario_order),
            x="target_variance:Q",
            text="variance_label:N",
        )
    )
    chart = (
        (bar + zero_rule + positive_text + negative_text)
        .properties(height=max(260, len(source) * 30))
        .configure_axis(labelFontSize=11, titleFontSize=12)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_scenario_heatmap(
    scenario_df: pd.DataFrame,
    selected_scenario_id: str | None = None,
) -> None:
    source = build_scenario_heatmap_source(scenario_df, selected_scenario_id)
    if source.empty:
        st.info("시나리오 조합 지도 데이터 없음")
        return

    strategy_order = _ordered_strategy_keys(scenario_df)
    magnitude = max(
        float(pd.to_numeric(source["target_variance"], errors="coerce").abs().max() or 0.0),
        1.0,
    )
    heatmap = (
        alt.Chart(source)
        .mark_rect(cornerRadius=2)
        .encode(
            x=alt.X("strategy_key:N", title="운영전략", sort=strategy_order),
            y=alt.Y("forecast_key:N", title="예측모델", sort=["F1", "F2", "F3"]),
            color=alt.Color(
                "target_variance:Q",
                title="목표 대비 차이",
                scale=alt.Scale(
                    domain=[-magnitude, 0, magnitude],
                    range=["#DC2626", "#F8FAFC", "#059669"],
                ),
            ),
            stroke=alt.condition("datum.is_selected", alt.value("#111827"), alt.value("#ffffff")),
            strokeWidth=alt.condition("datum.is_selected", alt.value(2.4), alt.value(0.8)),
            tooltip=[
                alt.Tooltip("scenario_id:N", title="시나리오"),
                alt.Tooltip("target_status_label:N", title="목표 상태"),
                alt.Tooltip("variance_label:N", title="목표 대비 차이"),
            ],
        )
    )
    text = (
        alt.Chart(source)
        .mark_text(fontSize=12, fontWeight="bold")
        .encode(
            x=alt.X("strategy_key:N", sort=strategy_order),
            y=alt.Y("forecast_key:N", sort=["F1", "F2", "F3"]),
            text="variance_label:N",
            color=alt.value("#111827"),
        )
    )
    chart = (
        (heatmap + text)
        .properties(height=210)
        .configure_axis(labelFontSize=12, titleFontSize=12)
        .configure_legend(labelFontSize=11, titleFontSize=12)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_remaining_uplift_chart(revised_targets_df: pd.DataFrame) -> None:
    source = build_remaining_target_daily_source(revised_targets_df)
    if source.empty:
        st.info("일자별 추가 부담 차트 데이터 없음")
        return

    date_order = source["date_label"].tolist()
    chart = (
        alt.Chart(source)
        .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
        .encode(
            x=alt.X(
                "date_label:N",
                title=None,
                sort=date_order,
                axis=alt.Axis(labelAngle=-30, labelLimit=120),
            ),
            y=alt.Y(
                "uplift:Q",
                title="추가 배분 목표(억원)",
                axis=alt.Axis(format=chart_value_format("억원")),
            ),
            color=alt.Color(
                "day_type:N",
                title="일자 구분",
                scale=alt.Scale(
                    domain=["마감일", "일반일", "잔여일"],
                    range=["#D97706", "#2563EB", "#6B7280"],
                ),
            ),
            tooltip=[
                alt.Tooltip("date_label:N", title="날짜"),
                alt.Tooltip("day_type:N", title="일자 구분"),
                alt.Tooltip("close_type:N", title="마감 유형"),
                alt.Tooltip("original_target:Q", title="기존 일 목표", format=chart_value_format("억원")),
                alt.Tooltip("uplift:Q", title="추가 배분 목표", format=chart_value_format("억원")),
                alt.Tooltip("revised_target:Q", title="수정 후 일 목표", format=chart_value_format("억원")),
            ],
        )
        .properties(height=300)
        .configure_axis(labelFontSize=11, titleFontSize=12)
        .configure_legend(labelFontSize=11, titleFontSize=12)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_remaining_target_stack_chart(revised_targets_df: pd.DataFrame) -> None:
    daily = build_remaining_target_daily_source(revised_targets_df)
    stack_source = build_remaining_target_stack_source(revised_targets_df)
    if daily.empty or stack_source.empty:
        st.info("기존 목표와 추가 배분 차트 데이터 없음")
        return

    date_order = daily["date_label"].tolist()
    bars = (
        alt.Chart(stack_source)
        .mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            x=alt.X(
                "date_label:N",
                title=None,
                sort=date_order,
                axis=alt.Axis(labelAngle=-30, labelLimit=120),
            ),
            y=alt.Y(
                "value:Q",
                title="수정 후 일 목표(억원)",
                stack="zero",
                axis=alt.Axis(format=chart_value_format("억원")),
            ),
            color=alt.Color(
                "target_part:N",
                title="목표 구성",
                scale=alt.Scale(
                    domain=["기존 일 목표", "추가 배분 목표"],
                    range=["#CBD5E1", "#D97706"],
                ),
            ),
            tooltip=[
                alt.Tooltip("date_label:N", title="날짜"),
                alt.Tooltip("target_part:N", title="구성"),
                alt.Tooltip("value:Q", title="금액", format=chart_value_format("억원")),
                alt.Tooltip("revised_target:Q", title="수정 후 일 목표", format=chart_value_format("억원")),
                alt.Tooltip("cap_target:Q", title="일별 허용 상한", format=chart_value_format("억원")),
            ],
        )
    )
    cap_line = (
        alt.Chart(daily)
        .mark_line(point=True, color="#DC2626", strokeDash=[5, 4], strokeWidth=2)
        .encode(
            x=alt.X("date_label:N", sort=date_order),
            y=alt.Y("cap_target:Q"),
            tooltip=[
                alt.Tooltip("date_label:N", title="날짜"),
                alt.Tooltip("cap_target:Q", title="일별 허용 상한", format=chart_value_format("억원")),
            ],
        )
    )
    expected_line = (
        alt.Chart(daily)
        .mark_line(point=True, color="#0F766E", strokeWidth=2)
        .encode(
            x=alt.X("date_label:N", sort=date_order),
            y=alt.Y("expected_after_revision:Q"),
            tooltip=[
                alt.Tooltip("date_label:N", title="날짜"),
                alt.Tooltip(
                    "expected_after_revision:Q",
                    title="수정 후 예상 일 실적",
                    format=chart_value_format("억원"),
                ),
            ],
        )
    )
    chart = (
        (bars + cap_line + expected_line)
        .properties(height=320)
        .configure_axis(labelFontSize=11, titleFontSize=12)
        .configure_legend(labelFontSize=11, titleFontSize=12)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_grouped_bar_chart(
    chart_data: pd.DataFrame,
    metric_columns: tuple[str, ...],
) -> None:
    source = build_grouped_bar_chart_source(chart_data, metric_columns)
    if source.empty:
        st.info("막대 차트 데이터 없음")
        return

    label_order = [
        _chart_labels(metric_columns)[column]
        for column in metric_columns
        if column in set(source["metric"])
    ]
    value_format = chart_value_format(_chart_unit(metric_columns))
    chart = (
        alt.Chart(source)
        .mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            x=alt.X(
                "category:N",
                title=None,
                sort=None,
                axis=alt.Axis(labelAngle=-30, labelLimit=120),
            ),
            xOffset=alt.XOffset("범례:N", sort=label_order),
            y=alt.Y(
                "value:Q",
                title=_chart_unit(metric_columns) or "값",
                stack=None,
                scale=_auto_value_scale(source),
                axis=alt.Axis(format=value_format),
            ),
            color=alt.Color(
                "범례:N",
                title="범례",
                sort=label_order,
                scale=alt.Scale(range=list(CHART_COLOR_RANGE)),
            ),
            tooltip=[
                alt.Tooltip("category:N", title="항목"),
                alt.Tooltip("범례:N", title="수치"),
                alt.Tooltip("value:Q", title=_chart_tooltip_value_title(metric_columns), format=value_format),
            ],
        )
        .properties(height=320)
        .configure_axis(labelFontSize=11, titleFontSize=12)
        .configure_legend(labelFontSize=11, titleFontSize=12)
    )
    st.altair_chart(chart, use_container_width=True)


def _render_line_chart(
    chart_data: pd.DataFrame,
    metric_columns: tuple[str, ...],
) -> None:
    source = build_grouped_bar_chart_source(chart_data, metric_columns)
    if source.empty:
        st.info("선 차트 데이터 없음")
        return

    label_order = [
        _chart_labels(metric_columns)[column]
        for column in metric_columns
        if column in set(source["metric"])
    ]
    unit = _chart_unit(metric_columns)
    value_format = chart_value_format(unit)
    tooltip_title = _chart_tooltip_value_title(metric_columns)
    chart = (
        alt.Chart(source)
        .mark_line(point=True, strokeWidth=2.5)
        .encode(
            x=alt.X(
                "category:N",
                title=None,
                sort=None,
                axis=alt.Axis(labelAngle=-30, labelLimit=120),
            ),
            y=alt.Y(
                "value:Q",
                title=unit or "값",
                scale=_auto_value_scale(source),
                axis=alt.Axis(format=value_format),
            ),
            color=alt.Color(
                "범례:N",
                title="범례",
                sort=label_order,
                scale=alt.Scale(range=list(CHART_COLOR_RANGE)),
            ),
            tooltip=[
                alt.Tooltip("category:N", title="항목"),
                alt.Tooltip("범례:N", title="수치"),
                alt.Tooltip("value:Q", title=tooltip_title, format=value_format),
            ],
        )
        .properties(height=300)
        .configure_axis(labelFontSize=11, titleFontSize=12)
        .configure_legend(labelFontSize=11, titleFontSize=12)
    )
    st.altair_chart(chart, use_container_width=True)


def _auto_value_scale(source: pd.DataFrame) -> alt.Scale:
    axis_domain = build_auto_axis_domain(source["value"])
    if axis_domain is None:
        return alt.Scale(zero=False)
    return alt.Scale(domain=axis_domain, zero=False, nice=True)


def _chart_unit(metric_columns: tuple[str, ...]) -> str:
    units = {
        VISUAL_METRIC_DEFINITIONS.get(column, {}).get("unit", "")
        for column in metric_columns
    }
    units.discard("")
    if len(units) == 1:
        return next(iter(units))
    return ""


def _chart_tooltip_value_title(metric_columns: tuple[str, ...]) -> str:
    unit = _chart_unit(metric_columns)
    if unit:
        return f"값({unit})"
    return "값"


def _render_chart_reading_guide(guide_key: str) -> None:
    guide = build_visual_reading_guide(guide_key)
    title = str(guide.get("title") or "").strip()
    steps = tuple(guide.get("steps") or ())
    decision = str(guide.get("decision") or "").strip()
    if not title or not steps:
        return

    st.markdown(f"**{title} 읽는 법**")
    for index, step in enumerate(steps, start=1):
        st.markdown(f"{index}. {step}")
    if decision:
        st.caption(f"판단 기준: {decision}")


def _render_visual_metric_definitions(metric_columns: tuple[str, ...]) -> None:
    definition_df = build_visual_metric_definition_df(metric_columns)
    if definition_df.empty:
        return

    with st.expander("범례와 수치 정의", expanded=False):
        for row in definition_df.to_dict("records"):
            st.markdown(f"- **{row['범례']} ({row['단위']})**: {row['수치 의미']}")


def _load_uploaded_input(
    uploaded_file: Any,
    sort_by: str = "business_day_no",
    strict_business_day_no: bool = True,
) -> pd.DataFrame:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix not in {".csv", ".xlsx"}:
        raise ValueError("Unsupported input file type. Use CSV or XLSX.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = Path(tmp_dir) / f"uploaded{suffix}"
        temp_path.write_bytes(uploaded_file.getvalue())
        if sort_by not in {"business_day_no", "date"}:
            raise ValueError("sort_by must be either 'business_day_no' or 'date'.")
        return load_input(
            temp_path,
            sort_by=sort_by,
            strict_business_day_no=strict_business_day_no,
        )


def _filter_scenarios(
    scenario_df: pd.DataFrame,
    forecast_choice: str,
    provision_choice: str,
) -> pd.DataFrame:
    result = scenario_df.copy(deep=False)
    if forecast_choice != COMPARE_LABEL:
        result = result.loc[result["scenario_id"].astype(str).str.startswith(forecast_choice)]
    if provision_choice != COMPARE_LABEL:
        strategy_filtered = result.loc[
            result["scenario_id"].astype(str).str.endswith(provision_choice)
        ]
        if not strategy_filtered.empty:
            result = strategy_filtered
    return result.reset_index(drop=True)


def _split_scenario_id(scenario_id: str) -> tuple[str, str]:
    if "_" not in scenario_id:
        return scenario_id, ""
    return scenario_id.split("_", maxsplit=1)


def _selected_forecast_key(selected_scenario_id: str | None) -> str:
    if not selected_scenario_id:
        return ""
    forecast_key, _ = _split_scenario_id(str(selected_scenario_id))
    if forecast_key in FORECAST_MODEL_OPTIONS:
        return forecast_key
    return ""


def _selected_scenario_row(scenario_df: pd.DataFrame, scenario_id: str) -> pd.Series:
    rows = scenario_df.loc[scenario_df["scenario_id"].astype(str) == scenario_id]
    if rows.empty:
        return scenario_df.iloc[0]
    return rows.iloc[0]


def _forecast_summary(scenario_df: pd.DataFrame) -> dict[str, object]:
    summary: dict[str, object] = {}
    for _, row in scenario_df.iterrows():
        scenario_id = str(row.get("scenario_id", ""))
        forecast_key = scenario_id.split("_", maxsplit=1)[0]
        if forecast_key in {"F1", "F2", "F3"} and forecast_key not in summary:
            summary[forecast_key] = row.get("forecast_amount")
    return summary


def _build_indexed_numeric_chart_data(
    df: pd.DataFrame,
    index_column: str,
    value_columns: tuple[str, ...],
) -> pd.DataFrame:
    if df.empty or index_column not in df.columns:
        return pd.DataFrame()

    available_columns = [column for column in value_columns if column in df.columns]
    if not available_columns:
        return pd.DataFrame()

    result = df.loc[:, [index_column, *available_columns]].copy()
    result[index_column] = result[index_column].map(_format_chart_index)
    for column in available_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce")
    return result.set_index(index_column)


def _available_chart_columns(
    chart_data: pd.DataFrame,
    preferred_columns: tuple[str, ...],
) -> tuple[str, ...]:
    if chart_data.empty:
        return ()
    return tuple(
        column
        for column in preferred_columns
        if column in chart_data.columns and not chart_data[column].isna().all()
    )


def _rename_chart_columns(
    df: pd.DataFrame,
    labels: dict[str, str],
) -> pd.DataFrame:
    return df.rename(columns=labels)


def _chart_labels(metric_columns: tuple[str, ...]) -> dict[str, str]:
    return {
        column: VISUAL_METRIC_DEFINITIONS.get(column, {}).get("label", column)
        for column in metric_columns
    }


def _format_chart_index(value: object) -> str:
    if _is_missing(value):
        return ""
    if isinstance(value, pd.Timestamp):
        return str(value.date())
    return str(value)


def _format_display_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()
    if {"item", "value"}.issubset(result.columns):
        original_items = result["item"].astype(str)
        result["value"] = [
            _format_named_value(item, value)
            for item, value in zip(result["item"], result["value"])
        ]
        result["value"] = result["value"].map(_localize_display_value)
        result["item"] = original_items.map(_display_column_label)
        return result

    for column in result.columns:
        if column in AMOUNT_COLUMNS:
            result[column] = result[column].map(format_amount)
        elif column in RATE_COLUMNS:
            result[column] = result[column].map(format_rate)
        elif "date" in str(column).lower():
            result[column] = result[column].map(_format_date)
        else:
            result[column] = result[column].map(_localize_display_value)
    return result.rename(columns={column: _display_column_label(column) for column in result.columns})


def _format_named_value(name: object, value: object) -> object:
    column_name = str(name)
    if column_name in AMOUNT_COLUMNS:
        return format_amount(value)
    if column_name in RATE_COLUMNS:
        return format_rate(value)
    if "date" in column_name.lower():
        return _format_date(value)
    return value


def _display_column_label(column: object) -> str:
    return DISPLAY_COLUMN_LABELS.get(str(column), str(column))


def _localize_display_value(value: object) -> object:
    if _is_missing(value):
        return value
    if isinstance(value, bool):
        return "예" if value else "아니오"
    if isinstance(value, (list, tuple, set)):
        localized = [format_validation_message(item) for item in value]
        return ", ".join(str(item) for item in localized if str(item))
    text = str(value)
    return DISPLAY_VALUE_LABELS.get(text, value)


def _operation_mode_label(target_status: object) -> object:
    if _is_missing(target_status):
        return "계산 불가"
    text = str(target_status)
    return TARGET_STATUS_OPERATION_MODE_LABELS.get(text, _localize_display_value(text))


def _format_date(value: object) -> str:
    if _is_missing(value):
        return "계산 불가"
    try:
        return str(pd.Timestamp(value).date())
    except Exception:  # noqa: BLE001 - display only.
        return str(value)


def _as_dataframe(value: Any) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value
    if value is None:
        return pd.DataFrame()
    return pd.DataFrame(value)


def _as_float(value: object) -> float:
    if _is_missing(value):
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


if __name__ == "__main__":
    main()
