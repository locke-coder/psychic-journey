"""Activity-based reference cross-check for HTM raw dashboard imports."""

from __future__ import annotations

from math import isfinite
from typing import Any


ALIGNED_THRESHOLD_PCT = 3.0
NOT_AUTO_REFLECTED_NOTICE = "최종 예측에 자동 반영하지 않음"


def build_activity_crosscheck(
    raw_bundle: Any,
    main_forecast_eok: float | None = None,
) -> dict[str, Any]:
    """Build a reference-only activity estimate comparison."""
    activity_estimate_eok, estimate_source = _select_activity_estimate(raw_bundle)
    main_value = _to_float(main_forecast_eok)

    diff_eok: float | None = None
    diff_pct: float | None = None
    if activity_estimate_eok is not None and main_value is not None:
        diff_eok = activity_estimate_eok - main_value
        if main_value != 0:
            diff_pct = diff_eok / main_value * 100

    signal = _classify_signal(activity_estimate_eok, main_value, diff_pct)
    metrics = _select_validation_metrics(raw_bundle)

    return {
        "activity_estimate_eok": activity_estimate_eok,
        "main_forecast_eok": main_value,
        "diff_eok": diff_eok,
        "diff_pct": diff_pct,
        "signal": signal,
        "estimate_source": estimate_source,
        "explanation": _build_explanation(signal),
        "confidence_note": _build_confidence_note(metrics),
        "final_forecast_modified": False,
    }


def _select_activity_estimate(raw_bundle: Any) -> tuple[float | None, str | None]:
    projection = _read_attr(raw_bundle, "activity_projection")
    projection_estimate = _to_float(_read_attr(projection, "estimate_eok"))
    if projection_estimate is not None:
        return projection_estimate, "activity_projection.estimate_eok"

    method = _latest_projection_method(_read_attr(raw_bundle, "agg"))
    if method is None:
        return None, None

    for key in ("team_adopted_estimate_eok", "est_month_total_eok"):
        value = _to_float(_read_attr(method, key))
        if value is not None:
            return value, f"agg.latest.projection_method.{key}"

    low = _to_float(_read_attr(method, "field_pipeline_estimate_low_eok"))
    high = _to_float(_read_attr(method, "field_pipeline_estimate_high_eok"))
    if low is not None and high is not None:
        return (low + high) / 2, "agg.latest.projection_method.field_pipeline_estimate_midpoint_eok"
    return None, None


def _classify_signal(
    activity_estimate_eok: float | None,
    main_forecast_eok: float | None,
    diff_pct: float | None,
) -> str:
    if activity_estimate_eok is None:
        return "INSUFFICIENT_DATA"
    if main_forecast_eok is None or diff_pct is None:
        return "NO_MAIN_FORECAST"
    if abs(diff_pct) <= ALIGNED_THRESHOLD_PCT:
        return "ALIGNED"
    if diff_pct > ALIGNED_THRESHOLD_PCT:
        return "ACTIVITY_HIGHER"
    return "ACTIVITY_LOWER"


def _build_explanation(signal: str) -> str:
    suffix = f"참고/검증용이며 {NOT_AUTO_REFLECTED_NOTICE}."
    if signal == "INSUFFICIENT_DATA":
        return f"활동기반 추산값을 산출할 수 없습니다. {suffix}"
    if signal == "NO_MAIN_FORECAST":
        return (
            "[추론] 활동기반 참고 추산값은 확인되지만 기존 예측값이 연결되지 않아 "
            f"차이 판단은 제한적입니다. {suffix}"
        )
    if signal == "ALIGNED":
        return (
            f"[추론] 활동기반 참고 추산값과 기존 예측값의 차이가 "
            f"±{ALIGNED_THRESHOLD_PCT:.1f}% 이내입니다. {suffix}"
        )
    if signal == "ACTIVITY_HIGHER":
        return (
            "[추론] 활동지표상 기존 예측보다 상향 가능성을 참고할 수 있습니다. "
            f"원인 확정이 아닌 검증 신호입니다. {suffix}"
        )
    return (
        "[추론] 활동지표상 기존 예측보다 하향 가능성을 참고할 수 있습니다. "
        f"원인 확정이 아닌 검증 신호입니다. {suffix}"
    )


def _build_confidence_note(metrics: dict[str, float]) -> str:
    if not metrics:
        return "검증 지표가 없어 신뢰구간 해석은 제한적입니다."

    parts = [f"{name}={value:.3g}" for name, value in metrics.items()]
    return "ACTV/projection_method 검증 지표 참고: " + ", ".join(parts) + "."


def _select_validation_metrics(raw_bundle: Any) -> dict[str, float]:
    projection = _read_attr(raw_bundle, "activity_projection")
    candidates = (
        ("r2", _read_attr(projection, "r2")),
        ("r2", _read_attr(projection, "insample_r2")),
        ("loo_r2", _read_attr(projection, "loo_r2")),
        ("mape", _read_attr(projection, "mape")),
        ("mape", _read_attr(projection, "loo_mape_pct")),
    )
    metrics = _first_metrics(candidates)
    if metrics:
        return metrics

    method = _latest_projection_method(_read_attr(raw_bundle, "agg"))
    return _first_metrics(
        (
            ("r2", _read_attr(method, "r2")),
            ("r2", _read_attr(method, "activity_model_insample_r2")),
            ("loo_r2", _read_attr(method, "loo_r2")),
            ("loo_r2", _read_attr(method, "activity_model_loo_r2")),
            ("mape", _read_attr(method, "mape")),
            ("mape", _read_attr(method, "activity_model_loo_mape_pct")),
        )
    )


def _first_metrics(candidates: tuple[tuple[str, Any], ...]) -> dict[str, float]:
    metrics: dict[str, float] = {}
    for name, raw_value in candidates:
        if name in metrics:
            continue
        value = _to_float(raw_value)
        if value is not None:
            metrics[name] = value
    return metrics


def _latest_projection_method(agg: Any) -> Any | None:
    month_items = _iter_month_items(agg)
    if not month_items:
        return None

    for _month_key, month_data in sorted(month_items, key=lambda item: _month_sort_key(item[0]), reverse=True):
        method = _read_attr(month_data, "projection_method")
        if isinstance(method, dict) or method is not None:
            return method
    return None


def _iter_month_items(agg: Any) -> list[tuple[str, Any]]:
    if not isinstance(agg, dict):
        return []

    months = agg.get("months")
    if isinstance(months, dict):
        return [(str(key), value) for key, value in months.items() if isinstance(value, dict)]
    if isinstance(months, list):
        items: list[tuple[str, Any]] = []
        for index, value in enumerate(months, start=1):
            if isinstance(value, dict):
                key = value.get("month_key") or value.get("key") or index
                items.append((str(key), value))
        return items

    keyed_items = [
        (str(key), value)
        for key, value in agg.items()
        if isinstance(value, dict) and _looks_like_month_key(str(key))
    ]
    if keyed_items:
        return keyed_items

    if "projection_method" in agg:
        return [(str(agg.get("month_key") or "unknown"), agg)]
    return []


def _looks_like_month_key(value: str) -> bool:
    normalized = value.replace("-", ".").replace("/", ".")
    parts = normalized.split(".")
    if len(parts) < 2:
        return False
    return _to_float(parts[0]) is not None and _to_float(parts[1]) is not None


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


def _read_attr(value: Any, key: str) -> Any:
    if value is None:
        return None
    if isinstance(value, dict):
        return value.get(key)
    return getattr(value, key, None)


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return number if isfinite(number) else None


def _to_int(value: Any) -> int | None:
    number = _to_float(value)
    if number is None:
        return None
    return int(number)
