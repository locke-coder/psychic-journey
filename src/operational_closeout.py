"""Pure readiness summary for the report -> Excel -> audit closeout flow."""

from __future__ import annotations

from math import isfinite
from typing import Mapping

import pandas as pd


PASS = "PASS"
BLOCKED = "BLOCKED"
REFRESH = "REFRESH"
MANUAL = "MANUAL"

CLOSEOUT_COLUMNS = [
    "단계",
    "상태",
    "판정",
    "근거",
    "확인 화면",
    "code",
]


def build_operational_closeout_summary(
    *,
    validation_result: Mapping[str, object] | None,
    selected_row: Mapping[str, object] | None,
    report_text: object,
    expected_report_name: object,
    latest_excel_status: Mapping[str, object] | None,
    audit_logs: pd.DataFrame | None,
) -> dict[str, object]:
    """Return one read-only readiness contract shared by report and audit pages."""
    validation = dict(validation_result or {})
    selection = dict(selected_row or {})
    excel = dict(latest_excel_status or {})
    expected_name = str(expected_report_name or "").strip()
    report_body = str(report_text or "").strip()
    errors = list(validation.get("errors") or [])
    warnings = list(validation.get("warnings") or [])
    rows: list[dict[str, object]] = []

    if errors:
        _append_row(
            rows,
            "입력 검증",
            BLOCKED,
            f"오류 {len(errors)}건",
            "입력 오류를 해소해야 공유 절차를 진행할 수 있습니다.",
            "입력 · 데이터",
        )
    else:
        _append_row(
            rows,
            "입력 검증",
            PASS,
            "통과",
            f"오류 0건 · 주의 {len(warnings)}건",
            "입력 · 데이터",
        )

    selection_ready = (
        _has_text(selection.get("scenario_id"))
        and _has_text(selection.get("target_status"))
        and _to_float(selection.get("forecast_after_provision")) is not None
    )
    _append_row(
        rows,
        "예측·전략 확정",
        PASS if selection_ready else BLOCKED,
        "확정" if selection_ready else "선택 필요",
        (
            f"{selection.get('scenario_id')} · {selection.get('target_status')}"
            if selection_ready
            else "선택 시나리오와 월말 예상값이 완성되지 않았습니다."
        ),
        "예측 · 전략 통합",
    )

    report_ready = bool(report_body) and report_body != "입력 후 계산됩니다."
    _append_row(
        rows,
        "보고문",
        PASS if report_ready else BLOCKED,
        "작성됨" if report_ready else "생성 필요",
        (
            f"복사용 보고문 {len(report_body):,}자"
            if report_ready
            else "계산 완료 후 복사용 보고문을 확인해야 합니다."
        ),
        "보고 메모",
    )

    latest_exists = bool(excel.get("exists"))
    latest_name = str(excel.get("file_name") or "").strip()
    expected_is_file = expected_name.lower().endswith(".xlsx")
    excel_current = (
        latest_exists
        and expected_is_file
        and latest_name.lower() == expected_name.lower()
    )
    if excel_current:
        excel_code = PASS
        excel_label = "최신"
        excel_evidence = f"{latest_name} · {excel.get('modified_at') or '시각 확인 필요'}"
    elif latest_exists:
        excel_code = REFRESH
        excel_label = "갱신 필요"
        excel_evidence = (
            f"실제 {latest_name} / 현재 생성 예정 "
            f"{expected_name or '파일명 확인 필요'}"
        )
    else:
        excel_code = REFRESH
        excel_label = "생성 필요"
        excel_evidence = f"현재 생성 예정 {expected_name or '파일명 확인 필요'}"
    _append_row(
        rows,
        "Excel 공유본",
        excel_code,
        excel_label,
        excel_evidence,
        "Excel 공유",
    )

    audit_state = _audit_log_state(audit_logs)
    _append_row(
        rows,
        "저장 검증 로그",
        audit_state["code"],
        audit_state["label"],
        audit_state["evidence"],
        "검증 · 운영관리",
    )

    _append_row(
        rows,
        "공유 보안",
        MANUAL,
        "수동 확인",
        "공유 채널 권한과 PII·계약 식별정보 포함 여부를 공유 직전에 확인합니다.",
        "검증 · 운영관리",
    )

    items = pd.DataFrame(rows, columns=CLOSEOUT_COLUMNS)
    blocked_count = int((items["code"] == BLOCKED).sum())
    refresh_count = int((items["code"] == REFRESH).sum())
    pass_count = int((items["code"] == PASS).sum())
    if blocked_count:
        overall_code = BLOCKED
        overall_label = "공유 차단"
    elif refresh_count:
        overall_code = REFRESH
        overall_label = "갱신 필요"
    else:
        overall_code = MANUAL
        overall_label = "수동 확인 후 공유 가능"

    next_action = _next_action(items, overall_code)
    return {
        "overall_code": overall_code,
        "overall_label": overall_label,
        "pass_count": pass_count,
        "blocked_count": blocked_count,
        "refresh_count": refresh_count,
        "manual_count": int((items["code"] == MANUAL).sum()),
        "items": items,
        "next_action": next_action,
        "final_forecast_modified": False,
        "outputs_modified": False,
    }


def _audit_log_state(audit_logs: pd.DataFrame | None) -> dict[str, str]:
    if audit_logs is None or audit_logs.empty:
        return {
            "code": REFRESH,
            "label": "확인 필요",
            "evidence": "저장된 검증 로그가 없습니다.",
        }
    required = {"검증 항목", "상태"}
    if not required.issubset(audit_logs.columns):
        return {
            "code": REFRESH,
            "label": "확인 필요",
            "evidence": "검증 로그 상태 컬럼을 확인할 수 없습니다.",
        }
    stale = audit_logs.loc[
        ~audit_logs["상태"].astype(str).isin({"24시간 이내", "7일 이내"}),
        "검증 항목",
    ].astype(str).tolist()
    if stale:
        return {
            "code": REFRESH,
            "label": "갱신 필요",
            "evidence": "갱신 대상: " + ", ".join(stale),
        }
    return {
        "code": PASS,
        "label": "통과",
        "evidence": f"저장 로그 {len(audit_logs)}개 항목이 7일 이내입니다.",
    }


def _next_action(items: pd.DataFrame, overall_code: str) -> str:
    if overall_code == MANUAL:
        return "공유 채널 권한과 민감정보 포함 여부를 확인한 뒤 공유합니다."
    candidates = items.loc[items["code"] == overall_code]
    if candidates.empty:
        return "운영 마감 항목을 다시 확인합니다."
    first = candidates.iloc[0]
    if overall_code == BLOCKED:
        return f"{first['확인 화면']}에서 {first['단계']} 항목을 먼저 해소합니다."
    return f"{first['확인 화면']}에서 {first['단계']} 항목을 갱신합니다."


def _append_row(
    rows: list[dict[str, object]],
    step: str,
    code: str,
    label: str,
    evidence: str,
    page: str,
) -> None:
    rows.append(
        {
            "단계": step,
            "상태": label,
            "판정": _code_label(code),
            "근거": evidence,
            "확인 화면": page,
            "code": code,
        }
    )


def _code_label(code: str) -> str:
    return {
        PASS: "자동 확인",
        BLOCKED: "차단",
        REFRESH: "갱신",
        MANUAL: "수동",
    }.get(code, code)


def _has_text(value: object) -> bool:
    if value is None:
        return False
    try:
        if pd.isna(value):
            return False
    except (TypeError, ValueError):
        pass
    return bool(str(value).strip())


def _to_float(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None
