"""Pure, reference-only insights for the HTM raw dashboard."""

from __future__ import annotations

from math import isfinite
from typing import Any

import pandas as pd


READY_STATUS = "READY"
INSUFFICIENT_DATA_STATUS = "INSUFFICIENT_DATA"
PERCENTILE_MIN_PEER_MONTHS = 3
DECOMPOSITION_TOLERANCE_EOK = 0.01

DECOMPOSITION_COLUMNS = [
    "current_month",
    "comparison_month",
    "factor",
    "current_eok",
    "comparison_eok",
    "delta_eok",
    "contribution_pct",
    "direction",
    "source",
    "is_residual",
    "final_forecast_modified",
]
ORG_ACTIVITY_COLUMNS = [
    "current_month",
    "comparison_month",
    "metric",
    "current_value",
    "comparison_value",
    "delta_value",
    "change_pct",
    "unit",
    "source",
    "relationship",
    "final_forecast_modified",
]


def build_same_bizday_percentile(
    month_df: pd.DataFrame,
    *,
    target_month_key: str | None = None,
    min_peer_months: int = PERCENTILE_MIN_PEER_MONTHS,
) -> dict[str, object]:
    """Position one exact-N month inside prior exact-N months using midrank."""
    result = _base_percentile_result()
    prepared = _prepare_month_rows(month_df)
    if prepared.empty:
        result["reason"] = "동영업일 월별 자료가 없습니다."
        return result

    all_months = _sorted_month_keys(prepared["month_key"].unique())
    target_month = str(target_month_key or all_months[-1])
    result["current_month"] = target_month
    if target_month not in all_months:
        result["reason"] = "선택한 기준월 자료가 없습니다."
        return result

    target_rows = prepared.loc[prepared["month_key"] == target_month]
    if len(target_rows) != 1:
        result["reason"] = "기준월 자료가 중복되었거나 유일하지 않습니다."
        return result

    target = target_rows.iloc[0]
    selected_idx = _to_int(target.get("selected_idx"))
    target_value = _to_float(target.get("total_cum_eok"))
    result.update(
        selected_idx=selected_idx,
        current_value_eok=target_value,
    )
    if not _is_exact_month_row(target) or target_value is None:
        result["reason"] = "기준월이 선택 영업일에 정확히 도달하지 않았습니다."
        return result

    prior = prepared.loc[
        prepared["month_key"].map(_month_sort_key) < _month_sort_key(target_month)
    ].copy()
    prior_count = int(prior["month_key"].nunique())
    counts = prior["month_key"].value_counts()
    unique_months = set(counts.loc[counts == 1].index.astype(str))
    peer_mask = prior.apply(_is_exact_month_row, axis=1)
    peer_mask &= pd.to_numeric(prior["selected_idx"], errors="coerce") == selected_idx
    peer_mask &= prior["month_key"].isin(unique_months)
    peers = prior.loc[peer_mask].copy()
    peers["total_cum_eok"] = pd.to_numeric(peers["total_cum_eok"], errors="coerce")
    peers = peers.dropna(subset=["total_cum_eok"])
    peer_values = peers["total_cum_eok"].astype(float)
    peer_count = len(peer_values)
    result.update(
        peer_count=peer_count,
        peer_months=_sorted_month_keys(peers["month_key"].astype(str).tolist()),
        excluded_month_count=max(prior_count - peer_count, 0),
    )

    minimum = max(int(min_peer_months), 1)
    if peer_count < minimum:
        result["reason"] = (
            f"정확히 도달한 과거 비교월이 {peer_count}개월입니다. "
            f"최소 {minimum}개월이 필요합니다."
        )
        return result

    below_count = int((peer_values < target_value).sum())
    tie_count = int((peer_values == target_value).sum())
    percentile = 100.0 * (below_count + 0.5 * tie_count) / peer_count
    result.update(
        status=READY_STATUS,
        percentile_pct=percentile,
        peer_median_eok=float(peer_values.median()),
        peer_min_eok=float(peer_values.min()),
        peer_max_eok=float(peer_values.max()),
        tie_count=tie_count,
        position_label=_percentile_position_label(percentile),
        reason="",
    )
    return result


def resolve_latest_exact_month_key(month_df: pd.DataFrame) -> str | None:
    """Return the latest imported month that exactly reached the selected N."""
    prepared = _prepare_month_rows(month_df)
    if prepared.empty:
        return None
    eligible = prepared.loc[prepared.apply(_is_exact_month_row, axis=1)].copy()
    if eligible.empty:
        return None
    counts = eligible["month_key"].value_counts()
    unique_keys = counts.loc[counts == 1].index.astype(str)
    return _sorted_month_keys(unique_keys)[-1] if len(unique_keys) else None


def build_category_delta_decomposition(
    month_df: pd.DataFrame,
    category_df: pd.DataFrame,
    *,
    current_month_key: str | None = None,
    tolerance_eok: float = DECOMPOSITION_TOLERANCE_EOK,
) -> dict[str, object]:
    """Additively decompose the exact-N latest-vs-prior-month total delta."""
    result = _base_decomposition_result(tolerance_eok)
    pair = _exact_current_prior_pair(month_df, current_month_key=current_month_key)
    if pair["status"] != READY_STATUS:
        result["reason"] = pair["reason"]
        return result

    current = pair["current"]
    comparison = pair["comparison"]
    current_month = str(current["month_key"])
    comparison_month = str(comparison["month_key"])
    selected_idx = _to_int(current.get("selected_idx"))
    result.update(
        current_month=current_month,
        comparison_month=comparison_month,
        selected_idx=selected_idx,
    )

    required = {
        "month_key",
        "selected_idx",
        "used_idx",
        "category",
        "value_eok",
        "source",
        "fallback_used",
        "reached_selected_idx",
    }
    if category_df.empty or not required.issubset(category_df.columns):
        result["reason"] = "동영업일 상품군 누계 자료가 없습니다."
        return result

    prepared = category_df.copy()
    prepared["month_key"] = prepared["month_key"].astype(str)
    prepared["value_eok"] = pd.to_numeric(prepared["value_eok"], errors="coerce")
    exact_mask = prepared["reached_selected_idx"].map(_is_true)
    exact_mask &= ~prepared["fallback_used"].map(_is_true)
    exact_mask &= prepared["source"].astype(str) == "bizday_category_cum"
    exact_mask &= (
        pd.to_numeric(prepared["used_idx"], errors="coerce")
        == pd.to_numeric(prepared["selected_idx"], errors="coerce")
    )
    prepared = prepared.loc[
        prepared["month_key"].isin({current_month, comparison_month}) & exact_mask
    ].dropna(subset=["value_eok"])

    for month_key in (current_month, comparison_month):
        month_rows = prepared.loc[prepared["month_key"] == month_key]
        if month_rows.empty:
            result["reason"] = (
                f"{month_key} 상품군 자료가 선택 영업일 누계가 아니어서 분해에서 제외했습니다."
            )
            return result
        if month_rows["category"].astype(str).duplicated().any():
            result["reason"] = f"{month_key} 상품군 키가 중복되어 안전하게 분해할 수 없습니다."
            return result

    current_categories = prepared.loc[
        prepared["month_key"] == current_month, ["category", "value_eok"]
    ].rename(columns={"value_eok": "current_eok"})
    comparison_categories = prepared.loc[
        prepared["month_key"] == comparison_month, ["category", "value_eok"]
    ].rename(columns={"value_eok": "comparison_eok"})
    merged = current_categories.merge(
        comparison_categories,
        on="category",
        how="outer",
    ).fillna({"current_eok": 0.0, "comparison_eok": 0.0})
    merged["delta_eok"] = merged["current_eok"] - merged["comparison_eok"]

    current_total = _to_float(current.get("total_cum_eok"))
    comparison_total = _to_float(comparison.get("total_cum_eok"))
    if current_total is None or comparison_total is None:
        result["reason"] = "월 총계가 없어 상품군 합계와 정합성을 확인할 수 없습니다."
        return result
    total_delta = current_total - comparison_total
    category_delta_sum = float(merged["delta_eok"].sum())
    residual = total_delta - category_delta_sum

    rows = [
        _decomposition_row(
            current_month,
            comparison_month,
            str(row["category"]),
            _to_float(row["current_eok"]),
            _to_float(row["comparison_eok"]),
            float(row["delta_eok"]),
            total_delta,
            source="bizday_category_cum",
            is_residual=False,
        )
        for row in merged.to_dict("records")
    ]
    rows.append(
        _decomposition_row(
            current_month,
            comparison_month,
            "기타/정합 잔차",
            None,
            None,
            residual,
            total_delta,
            source="월 총계 - 상품군 증감 합계",
            is_residual=True,
        )
    )
    row_df = pd.DataFrame(rows, columns=DECOMPOSITION_COLUMNS)
    row_df["_abs_delta"] = row_df["delta_eok"].abs()
    row_df = row_df.sort_values(
        ["is_residual", "_abs_delta", "factor"],
        ascending=[True, False, True],
        kind="stable",
    ).drop(columns=["_abs_delta"]).reset_index(drop=True)
    result.update(
        status=READY_STATUS,
        total_delta_eok=total_delta,
        category_delta_sum_eok=category_delta_sum,
        reconciliation_gap_eok=residual,
        reconciled=abs(residual) <= abs(float(tolerance_eok)),
        rows=row_df,
        reason="",
    )
    return result


def build_org_activity_changes(
    month_df: pd.DataFrame,
    member_df: pd.DataFrame,
    *,
    current_month_key: str | None = None,
) -> dict[str, object]:
    """Return non-causal organization/activity changes for parallel review."""
    result = _base_org_activity_result()
    pair = _exact_current_prior_pair(month_df, current_month_key=current_month_key)
    if pair["status"] != READY_STATUS:
        result["reason"] = pair["reason"]
        return result

    current = pair["current"]
    comparison = pair["comparison"]
    current_month = str(current["month_key"])
    comparison_month = str(comparison["month_key"])
    rows: list[dict[str, object]] = []
    _append_org_activity_row(
        rows,
        current_month,
        comparison_month,
        "가동 지국수",
        current.get("active_branch_count"),
        comparison.get("active_branch_count"),
        "개",
        "bizday_rows",
    )
    for member_type, label in (
        ("총계", "구매회원 총계"),
        ("신규", "신규 구매회원"),
        ("기존", "기존 구매회원"),
    ):
        current_value = _exact_member_value(member_df, current_month, member_type)
        comparison_value = _exact_member_value(member_df, comparison_month, member_type)
        if member_type == "총계":
            current_value = (
                current_value
                if current_value is not None
                else _to_float(current.get("member_cum"))
            )
            comparison_value = (
                comparison_value
                if comparison_value is not None
                else _to_float(comparison.get("member_cum"))
            )
        _append_org_activity_row(
            rows,
            current_month,
            comparison_month,
            label,
            current_value,
            comparison_value,
            "명",
            "member_summary / bizday_rows",
        )

    if not rows:
        result["reason"] = "조직·활동 동행 자료가 부족합니다."
        return result
    result.update(
        status=READY_STATUS,
        current_month=current_month,
        comparison_month=comparison_month,
        rows=pd.DataFrame(rows, columns=ORG_ACTIVITY_COLUMNS),
        reason="",
    )
    return result


def _prepare_month_rows(month_df: pd.DataFrame) -> pd.DataFrame:
    required = {
        "month_key",
        "selected_idx",
        "used_idx",
        "total_cum_eok",
        "reached_selected_idx",
    }
    if month_df.empty or not required.issubset(month_df.columns):
        return pd.DataFrame(columns=list(required))
    prepared = month_df.copy()
    prepared["month_key"] = prepared["month_key"].astype(str)
    return prepared


def _exact_current_prior_pair(
    month_df: pd.DataFrame,
    *,
    current_month_key: str | None = None,
) -> dict[str, object]:
    prepared = _prepare_month_rows(month_df)
    if prepared.empty:
        return {"status": INSUFFICIENT_DATA_STATUS, "reason": "월별 자료가 없습니다."}
    month_keys = _sorted_month_keys(prepared["month_key"].unique())
    target_month = str(current_month_key or month_keys[-1])
    if target_month not in month_keys:
        return {
            "status": INSUFFICIENT_DATA_STATUS,
            "reason": "선택한 분석월 자료가 없습니다.",
        }
    prior_months = [
        key for key in month_keys if _month_sort_key(key) < _month_sort_key(target_month)
    ]
    if not prior_months:
        return {"status": INSUFFICIENT_DATA_STATUS, "reason": "전월 비교 자료가 없습니다."}
    current_month, comparison_month = target_month, prior_months[-1]
    if not _are_adjacent_months(comparison_month, current_month):
        return {
            "status": INSUFFICIENT_DATA_STATUS,
            "reason": "최신월과 전월이 연속되지 않아 분해하지 않았습니다.",
        }
    current_rows = prepared.loc[prepared["month_key"] == current_month]
    comparison_rows = prepared.loc[prepared["month_key"] == comparison_month]
    if len(current_rows) != 1 or len(comparison_rows) != 1:
        return {
            "status": INSUFFICIENT_DATA_STATUS,
            "reason": "비교 월 총계가 중복되었거나 유일하지 않습니다.",
        }
    current = current_rows.iloc[0]
    comparison = comparison_rows.iloc[0]
    if not _is_exact_month_row(current) or not _is_exact_month_row(comparison):
        return {
            "status": INSUFFICIENT_DATA_STATUS,
            "reason": "최신월 또는 전월이 선택 영업일에 정확히 도달하지 않았습니다.",
        }
    current_idx = _to_int(current.get("selected_idx"))
    comparison_idx = _to_int(comparison.get("selected_idx"))
    if current_idx is None or current_idx != comparison_idx:
        return {
            "status": INSUFFICIENT_DATA_STATUS,
            "reason": "최신월과 전월의 비교 영업일차가 다릅니다.",
        }
    return {
        "status": READY_STATUS,
        "reason": "",
        "current": current,
        "comparison": comparison,
    }


def _is_exact_month_row(row: pd.Series) -> bool:
    selected_idx = _to_int(row.get("selected_idx"))
    used_idx = _to_int(row.get("used_idx"))
    return (
        _is_true(row.get("reached_selected_idx"))
        and selected_idx is not None
        and used_idx == selected_idx
        and _to_float(row.get("total_cum_eok")) is not None
    )


def _exact_member_value(
    member_df: pd.DataFrame,
    month_key: str,
    member_type: str,
) -> float | None:
    required = {"month_key", "selected_idx", "used_idx", "member_type", "member_cnt"}
    if member_df.empty or not required.issubset(member_df.columns):
        return None
    rows = member_df.loc[
        (member_df["month_key"].astype(str) == month_key)
        & (member_df["member_type"].astype(str) == member_type)
        & (
            pd.to_numeric(member_df["used_idx"], errors="coerce")
            == pd.to_numeric(member_df["selected_idx"], errors="coerce")
        )
    ]
    if len(rows) != 1:
        return None
    return _to_float(rows.iloc[0].get("member_cnt"))


def _append_org_activity_row(
    rows: list[dict[str, object]],
    current_month: str,
    comparison_month: str,
    metric: str,
    current_value: object,
    comparison_value: object,
    unit: str,
    source: str,
) -> None:
    current_number = _to_float(current_value)
    comparison_number = _to_float(comparison_value)
    if current_number is None or comparison_number is None:
        return
    delta = current_number - comparison_number
    change_pct = delta / comparison_number if comparison_number > 0 else None
    rows.append(
        {
            "current_month": current_month,
            "comparison_month": comparison_month,
            "metric": metric,
            "current_value": current_number,
            "comparison_value": comparison_number,
            "delta_value": delta,
            "change_pct": change_pct,
            "unit": unit,
            "source": source,
            "relationship": "동행 지표(인과 아님)",
            "final_forecast_modified": False,
        }
    )


def _decomposition_row(
    current_month: str,
    comparison_month: str,
    factor: str,
    current_eok: float | None,
    comparison_eok: float | None,
    delta_eok: float,
    total_delta_eok: float,
    *,
    source: str,
    is_residual: bool,
) -> dict[str, object]:
    contribution_pct = delta_eok / total_delta_eok if total_delta_eok != 0 else None
    direction = "증가" if delta_eok > 0 else "감소" if delta_eok < 0 else "변동 없음"
    return {
        "current_month": current_month,
        "comparison_month": comparison_month,
        "factor": factor,
        "current_eok": current_eok,
        "comparison_eok": comparison_eok,
        "delta_eok": delta_eok,
        "contribution_pct": contribution_pct,
        "direction": direction,
        "source": source,
        "is_residual": is_residual,
        "final_forecast_modified": False,
    }


def _base_percentile_result() -> dict[str, object]:
    return {
        "status": INSUFFICIENT_DATA_STATUS,
        "current_month": None,
        "selected_idx": None,
        "current_value_eok": None,
        "peer_count": 0,
        "peer_months": [],
        "excluded_month_count": 0,
        "percentile_pct": None,
        "peer_median_eok": None,
        "peer_min_eok": None,
        "peer_max_eok": None,
        "tie_count": 0,
        "position_label": "자료 부족",
        "formula": "empirical_midrank_prior_exact_n",
        "reason": "",
        "final_forecast_modified": False,
    }


def _base_decomposition_result(tolerance_eok: float) -> dict[str, object]:
    return {
        "status": INSUFFICIENT_DATA_STATUS,
        "current_month": None,
        "comparison_month": None,
        "selected_idx": None,
        "total_delta_eok": None,
        "category_delta_sum_eok": None,
        "reconciliation_gap_eok": None,
        "reconciled": False,
        "tolerance_eok": abs(float(tolerance_eok)),
        "rows": pd.DataFrame(columns=DECOMPOSITION_COLUMNS),
        "reason": "",
        "final_forecast_modified": False,
    }


def _base_org_activity_result() -> dict[str, object]:
    return {
        "status": INSUFFICIENT_DATA_STATUS,
        "current_month": None,
        "comparison_month": None,
        "rows": pd.DataFrame(columns=ORG_ACTIVITY_COLUMNS),
        "reason": "",
        "final_forecast_modified": False,
    }


def _percentile_position_label(percentile: float) -> str:
    if percentile >= 75:
        return "과거 분포 상단"
    if percentile >= 25:
        return "과거 분포 중간"
    return "과거 분포 하단"


def _sorted_month_keys(values: Any) -> list[str]:
    return sorted((str(value) for value in values), key=_month_sort_key)


def _month_sort_key(value: object) -> tuple[int, int, str]:
    text = str(value)
    normalized = text.replace("-", ".").replace("/", ".")
    parts = normalized.split(".")
    if len(parts) >= 2:
        year = _to_int(parts[0])
        month = _to_int(parts[1])
        if year is not None and month is not None:
            if year < 100:
                year += 2000
            return (year, month, text)
    return (9999, 99, text)


def _are_adjacent_months(previous: object, current: object) -> bool:
    previous_key = _month_sort_key(previous)
    current_key = _month_sort_key(current)
    if previous_key[0] == 9999 or current_key[0] == 9999:
        return False
    previous_number = previous_key[0] * 12 + previous_key[1]
    current_number = current_key[0] * 12 + current_key[1]
    return current_number - previous_number == 1


def _is_true(value: object) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    return str(value).strip().upper() in {"1", "TRUE", "Y"}


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


def _to_int(value: object) -> int | None:
    number = _to_float(value)
    return int(number) if number is not None else None
