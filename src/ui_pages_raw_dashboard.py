"""Streamlit page and pure helpers for HTM raw dashboard comparisons."""

from __future__ import annotations

import os
from math import isfinite
from pathlib import Path
from typing import Any, Mapping

import altair as alt
import pandas as pd

try:
    import streamlit as st
except ModuleNotFoundError:  # pragma: no cover - local test runtime may omit Streamlit.
    st = None

from src.activity_crosscheck import build_activity_crosscheck
from src.raw_dashboard_insights import (
    READY_STATUS as INSIGHT_READY_STATUS,
    build_category_delta_decomposition,
    build_org_activity_changes,
    build_same_bizday_percentile,
    resolve_latest_exact_month_key,
)
from src.raw_dashboard_importer import (
    RawDashboardParseError,
    bundle_to_frames,
    extract_large_raw_table,
    parse_raw_dashboard_file,
    parse_raw_dashboard_html,
)
from src.ui_components import render_kpi_card, render_section_header
from src.ui_navigation import render_page_header_html


RAW_DASHBOARD_PAGE_TITLE = "N영업일 Raw 비교"
RAW_DASHBOARD_AUTOLOAD_ENV = "RAW_DASHBOARD_AUTOLOAD_PATH"
RAW_DASHBOARD_AUTOLOAD_SECRET = "raw_dashboard_autoload_path"
RAW_DASHBOARD_SELECTED_BUSINESS_DAY_CONTEXT = "raw_dashboard_selected_business_day_no"
RAW_DASHBOARD_SELECTED_IDX_SESSION_KEY = "raw_dashboard_linked_business_day_no"
RAW_DASHBOARD_HTML_SUFFIXES = {".htm", ".html"}
REFERENCE_HISTORY_NOTICE = (
    "HTM Raw Dashboard는 forecast input을 대체하지 않는 reference/history 데이터입니다."
)
IS_CLOSE_DAY_GUARDRAIL_NOTICE = (
    "마감일 판단은 기존 forecast input의 is_close_day 컬럼만 사용합니다."
)
NO_AUTO_FORECAST_NOTICE = "이 화면은 예측 산식에 자동 반영되지 않습니다."
ACTIVITY_CROSSCHECK_NOTICE = "이 값은 최종 forecast에 자동 반영되지 않습니다."
P3_REFERENCE_NOTICE = (
    "백분위·상품군 요인분해·조직활동 동행지표는 reference/history 전용이며 "
    "최종 forecast에 자동 반영되지 않습니다."
)
ACTIVITY_CROSSCHECK_OPTIONAL_MISSING = (
    "optional object 없음: ACTV/projection_method 데이터가 없어 제한적으로 표시합니다."
)
SAMPLE_GUIDANCE_TEXT = (
    "업로드 테스트는 data/sample/raw_dashboard_sample_minimal.htm 파일로 확인할 수 있습니다."
)
NOT_REACHED_STATUS = "미도달"
REACHED_STATUS = "도달"
NO_DATA_STATUS = "데이터 없음"
OPTIONAL_MISSING_STATUS = "optional object 없음"


MONTH_COMPARISON_COLUMNS = [
    "month_key",
    "selected_idx",
    "used_idx",
    "total_cum_manwon",
    "total_cum_eok",
    "active_branch_count",
    "member_cum",
    "reached_selected_idx",
    "status",
    "prev_month_delta_eok",
    "prev_month_delta_pct",
]
CATEGORY_COMPARISON_COLUMNS = [
    "month_key",
    "selected_idx",
    "used_idx",
    "category",
    "value_manwon",
    "value_eok",
    "share_pct",
    "source",
    "fallback_used",
    "reached_selected_idx",
    "status",
]
GROUP_COMPARISON_COLUMNS = [
    "month_key",
    "selected_idx",
    "used_idx",
    "group",
    "count",
    "revenue_manwon",
    "revenue_eok",
    "share_pct",
    "source",
    "status",
]
MEMBER_COMPARISON_COLUMNS = [
    "month_key",
    "selected_idx",
    "used_idx",
    "member_type",
    "member_cnt",
    "member_amt_manwon",
    "member_amt_eok",
    "source",
    "status",
]
BRANCH_COMPARISON_COLUMNS = [
    "month_key",
    "selected_idx",
    "used_idx",
    "active_branch_count",
    "branch_bin",
    "branch_count",
    "source",
    "status",
]


def decode_uploaded_html(uploaded_file: Any) -> str:
    """Decode an uploaded HTM/HTML file with utf-8 first, then cp949."""
    raw_bytes = uploaded_file.getvalue()
    decode_errors: list[UnicodeDecodeError] = []
    for encoding in ("utf-8", "cp949"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError as exc:
            decode_errors.append(exc)
    raise RawDashboardParseError(
        "Could not decode uploaded raw dashboard file with utf-8 or cp949."
    ) from decode_errors[-1]


def resolve_raw_dashboard_autoload_path(
    context: Mapping[str, Any] | None = None,
) -> Path | None:
    """Return a validated read-only server path for automatic HTM loading."""
    configured_value: object | None = None
    if isinstance(context, Mapping):
        configured_value = context.get(RAW_DASHBOARD_AUTOLOAD_SECRET)
    if not configured_value:
        configured_value = os.getenv(RAW_DASHBOARD_AUTOLOAD_ENV)
    if not configured_value and st is not None:
        try:
            configured_value = st.secrets.get(RAW_DASHBOARD_AUTOLOAD_SECRET)
        except (FileNotFoundError, KeyError, AttributeError):
            configured_value = None

    configured_text = str(configured_value or "").strip()
    if not configured_text:
        return None

    path = Path(configured_text).expanduser()
    if path.suffix.lower() not in RAW_DASHBOARD_HTML_SUFFIXES:
        raise RawDashboardParseError("Automatic raw dashboard source must be an HTM/HTML file.")
    if not path.is_file():
        raise RawDashboardParseError("Configured automatic raw dashboard file was not found.")
    return path


def _load_raw_dashboard_server_file_uncached(
    path_text: str,
    _modified_ns: int,
    _size_bytes: int,
) -> tuple[Any, dict[str, pd.DataFrame]]:
    bundle = parse_raw_dashboard_file(path_text)
    return bundle, bundle_to_frames(bundle)


def _load_large_raw_table_server_file_uncached(
    path_text: str,
    _modified_ns: int,
    _size_bytes: int,
    table_key: str,
) -> pd.DataFrame:
    html_text = _read_raw_dashboard_text(Path(path_text))
    return extract_large_raw_table(html_text, table_key)


if st is not None:
    _load_raw_dashboard_server_file_cached = st.cache_data(show_spinner=False)(
        _load_raw_dashboard_server_file_uncached
    )
    _extract_large_raw_table_cached = st.cache_data(show_spinner=False)(
        extract_large_raw_table
    )
    _load_large_raw_table_server_file_cached = st.cache_data(show_spinner=False)(
        _load_large_raw_table_server_file_uncached
    )
else:  # pragma: no cover - exercised only when Streamlit is unavailable.
    _load_raw_dashboard_server_file_cached = _load_raw_dashboard_server_file_uncached
    _extract_large_raw_table_cached = extract_large_raw_table
    _load_large_raw_table_server_file_cached = _load_large_raw_table_server_file_uncached


def load_raw_dashboard_server_file(
    path: str | Path,
) -> tuple[Any, dict[str, pd.DataFrame]]:
    """Load an automatic HTM source, refreshing the cache when the file changes."""
    source_path = Path(path)
    stat = source_path.stat()
    return _load_raw_dashboard_server_file_cached(
        str(source_path),
        stat.st_mtime_ns,
        stat.st_size,
    )


def load_large_raw_table_server_file(
    path: str | Path,
    table_key: str,
) -> pd.DataFrame:
    """Materialize one large raw table and refresh it when the HTM changes."""
    source_path = Path(path)
    stat = source_path.stat()
    return _load_large_raw_table_server_file_cached(
        str(source_path),
        stat.st_mtime_ns,
        stat.st_size,
        table_key,
    )


def _read_raw_dashboard_text(path: Path) -> str:
    decode_errors: list[UnicodeDecodeError] = []
    for encoding in ("utf-8", "cp949"):
        try:
            return path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            decode_errors.append(exc)
    raise RawDashboardParseError(
        f"Could not decode raw dashboard file {path.name} with utf-8 or cp949."
    ) from decode_errors[-1]


def get_available_bizday_range(frames: dict[str, pd.DataFrame]) -> tuple[int, int]:
    """Return the min/max imported business index from importer frames."""
    bizday_rows = _frame(frames, "bizday_rows")
    if bizday_rows.empty or "idx" not in bizday_rows.columns:
        return (0, 0)

    idx_values = pd.to_numeric(bizday_rows["idx"], errors="coerce").dropna()
    if idx_values.empty:
        return (0, 0)
    return (int(idx_values.min()), int(idx_values.max()))


def build_month_bizday_comparison(
    frames: dict[str, pd.DataFrame],
    selected_idx: int,
) -> pd.DataFrame:
    """Build month-level cumulative comparison at the selected imported index."""
    bizday_rows = _frame(frames, "bizday_rows")
    if bizday_rows.empty or not {"month_key", "idx"}.issubset(bizday_rows.columns):
        return pd.DataFrame(columns=MONTH_COMPARISON_COLUMNS)

    rows: list[dict[str, object]] = []
    prepared = bizday_rows.copy()
    prepared["idx"] = pd.to_numeric(prepared["idx"], errors="coerce")
    prepared = prepared.dropna(subset=["idx"])
    for month_key in _month_keys(frames):
        month_rows = prepared.loc[prepared["month_key"].astype(str) == str(month_key)].copy()
        if month_rows.empty:
            rows.append(_empty_month_row(str(month_key), selected_idx))
            continue

        month_rows = month_rows.sort_values("idx", kind="stable")
        exact_rows = month_rows.loc[month_rows["idx"] == selected_idx]
        reached = not exact_rows.empty
        if reached:
            used = exact_rows.iloc[-1]
        else:
            previous_rows = month_rows.loc[month_rows["idx"] <= selected_idx]
            used = previous_rows.iloc[-1] if not previous_rows.empty else month_rows.iloc[0]

        used_idx = _to_int(used.get("idx"))
        total_cum_manwon = _to_float(used.get("total_cum_manwon"))
        total_cum_eok = _to_float(used.get("total_cum_eok"))
        if total_cum_eok is None and total_cum_manwon is not None:
            total_cum_eok = _manwon_to_eok(total_cum_manwon)

        rows.append(
            {
                "month_key": str(month_key),
                "selected_idx": int(selected_idx),
                "used_idx": used_idx,
                "total_cum_manwon": total_cum_manwon,
                "total_cum_eok": total_cum_eok,
                "active_branch_count": _to_int(used.get("active_branch_count")),
                "member_cum": _to_int(used.get("member_cum")),
                "reached_selected_idx": bool(reached),
                "status": REACHED_STATUS if reached else NOT_REACHED_STATUS,
                "prev_month_delta_eok": None,
                "prev_month_delta_pct": None,
            }
        )

    result = pd.DataFrame(rows, columns=MONTH_COMPARISON_COLUMNS)
    result = _sort_by_month_key(result)
    previous_values = result["total_cum_eok"].shift(1)
    previous_reached = result["reached_selected_idx"].shift(1, fill_value=False)
    comparable_pair = result["reached_selected_idx"] & previous_reached
    result["prev_month_delta_eok"] = (
        result["total_cum_eok"] - previous_values
    ).where(comparable_pair)
    result["prev_month_delta_pct"] = [
        _safe_ratio(delta, previous) if is_comparable else None
        for delta, previous, is_comparable in zip(
            result["prev_month_delta_eok"],
            previous_values,
            comparable_pair,
        )
    ]
    return result.reset_index(drop=True)


def build_category_comparison(
    frames: dict[str, pd.DataFrame],
    selected_idx: int,
) -> pd.DataFrame:
    """Build product-category comparison, preferring selected-index cumulative rows."""
    month_comparison = build_month_bizday_comparison(frames, selected_idx)
    if month_comparison.empty:
        return pd.DataFrame(columns=CATEGORY_COMPARISON_COLUMNS)

    bizday_category = _frame(frames, "bizday_category_cum")
    category_totals = _frame(frames, "category_totals")
    rows: list[dict[str, object]] = []

    for month in month_comparison.to_dict("records"):
        month_key = str(month["month_key"])
        used_idx = _to_int(month.get("used_idx"))
        source = "bizday_category_cum"
        fallback_used = False
        category_rows = pd.DataFrame()
        if used_idx is not None and not bizday_category.empty:
            category_rows = bizday_category.loc[
                (bizday_category.get("month_key", pd.Series(dtype=object)).astype(str) == month_key)
                & (pd.to_numeric(bizday_category.get("idx"), errors="coerce") == used_idx)
            ].copy()

        if category_rows.empty and not category_totals.empty:
            category_rows = category_totals.loc[
                category_totals.get("month_key", pd.Series(dtype=object)).astype(str) == month_key
            ].copy()
            source = "category_totals"
            fallback_used = True

        if category_rows.empty:
            rows.append(
                {
                    "month_key": month_key,
                    "selected_idx": int(selected_idx),
                    "used_idx": used_idx,
                    "category": NO_DATA_STATUS,
                    "value_manwon": None,
                    "value_eok": None,
                    "share_pct": None,
                    "source": OPTIONAL_MISSING_STATUS,
                    "fallback_used": False,
                    "reached_selected_idx": bool(month.get("reached_selected_idx")),
                    "status": NO_DATA_STATUS,
                }
            )
            continue

        value_column = "cum_manwon" if "cum_manwon" in category_rows.columns else "total_manwon"
        total_value = pd.to_numeric(category_rows[value_column], errors="coerce").sum()
        for row in category_rows.to_dict("records"):
            value_manwon = _to_float(row.get(value_column))
            rows.append(
                {
                    "month_key": month_key,
                    "selected_idx": int(selected_idx),
                    "used_idx": used_idx,
                    "category": str(row.get("category") or NO_DATA_STATUS),
                    "value_manwon": value_manwon,
                    "value_eok": _manwon_to_eok(value_manwon),
                    "share_pct": _safe_ratio(value_manwon, total_value),
                    "source": source,
                    "fallback_used": fallback_used,
                    "reached_selected_idx": bool(month.get("reached_selected_idx")),
                    "status": str(month.get("status") or NO_DATA_STATUS),
                }
            )

    return pd.DataFrame(rows, columns=CATEGORY_COMPARISON_COLUMNS)


def build_group_comparison(
    frames: dict[str, pd.DataFrame],
    selected_idx: int,
) -> pd.DataFrame:
    """Build comparison by imported monthly group stats."""
    group_stats = _frame(frames, "group_stats")
    if group_stats.empty:
        return pd.DataFrame(columns=GROUP_COMPARISON_COLUMNS)

    month_comparison = build_month_bizday_comparison(frames, selected_idx)
    used_by_month = {
        str(row["month_key"]): row
        for row in month_comparison.to_dict("records")
    }
    rows: list[dict[str, object]] = []
    for month_key in _month_keys(frames):
        month_key_text = str(month_key)
        month_rows = group_stats.loc[
            group_stats.get("month_key", pd.Series(dtype=object)).astype(str) == month_key_text
        ].copy()
        month_meta = used_by_month.get(month_key_text, {})
        used_idx = _to_int(month_meta.get("used_idx"))
        if "idx" in month_rows.columns and used_idx is not None:
            month_rows = month_rows.loc[
                pd.to_numeric(month_rows["idx"], errors="coerce") == used_idx
            ].copy()
        if month_rows.empty:
            rows.append(_empty_group_row(month_key_text, selected_idx, used_idx))
            continue

        revenue_values = _first_numeric_series(
            month_rows,
            ("revenue_manwon", "total_manwon", "amount_manwon", "value_manwon", "value"),
        )
        total_revenue = revenue_values.sum()
        for index, row in enumerate(month_rows.to_dict("records")):
            revenue_manwon = _to_float(revenue_values.iloc[index])
            rows.append(
                {
                    "month_key": month_key_text,
                    "selected_idx": int(selected_idx),
                    "used_idx": used_idx,
                    "group": _pick_text(
                        row,
                        ("group", "group_name", "name", "label", "category"),
                        NO_DATA_STATUS,
                    ),
                    "count": _pick_number(
                        row,
                        ("count", "branch_count", "member_count", "member_cnt"),
                        prefer_int=True,
                    ),
                    "revenue_manwon": revenue_manwon,
                    "revenue_eok": _manwon_to_eok(revenue_manwon),
                    "share_pct": _safe_ratio(revenue_manwon, total_revenue),
                    "source": "group_stats",
                    "status": str(month_meta.get("status") or REACHED_STATUS),
                }
            )
    return pd.DataFrame(rows, columns=GROUP_COMPARISON_COLUMNS)


def build_member_comparison(
    frames: dict[str, pd.DataFrame],
    selected_idx: int,
) -> pd.DataFrame:
    """Build purchasing member comparison with safe fallbacks for optional details."""
    member_summary = _frame(frames, "member_summary")
    month_comparison = build_month_bizday_comparison(frames, selected_idx)
    if month_comparison.empty and member_summary.empty:
        return pd.DataFrame(columns=MEMBER_COMPARISON_COLUMNS)

    rows: list[dict[str, object]] = []
    for month in month_comparison.to_dict("records"):
        month_key = str(month["month_key"])
        summary_rows = member_summary.loc[
            member_summary.get("month_key", pd.Series(dtype=object)).astype(str) == month_key
        ] if not member_summary.empty else pd.DataFrame()
        used_idx = _to_int(month.get("used_idx"))
        if "idx" in summary_rows.columns and used_idx is not None:
            summary_rows = summary_rows.loc[
                pd.to_numeric(summary_rows["idx"], errors="coerce") == used_idx
            ].copy()
        if "member_type" in summary_rows.columns:
            for member_type in ("총계", "신규", "기존"):
                type_rows = summary_rows.loc[
                    summary_rows["member_type"].astype(str) == member_type
                ]
                summary = type_rows.iloc[-1].to_dict() if not type_rows.empty else {}
                rows.append(
                    _member_row(
                        month_key,
                        selected_idx,
                        used_idx,
                        member_type,
                        _pick_number(summary, ("member_cnt", "member_count", "count"), True),
                        _pick_number(
                            summary,
                            ("member_amt_manwon", "member_amount_manwon", "amount_manwon"),
                            False,
                        ),
                        "bizday_member" if "idx" in summary else "member_summary",
                        str(month.get("status") or NO_DATA_STATUS)
                        if summary
                        else OPTIONAL_MISSING_STATUS,
                    )
                )
            continue

        summary = summary_rows.iloc[-1].to_dict() if not summary_rows.empty else {}
        total_count = (
            _pick_number(summary, ("total_purchasing_members", "member_cnt", "member_count"), True)
            or _to_int(month.get("member_cum"))
        )
        total_amount = _pick_number(
            summary,
            ("member_amt_manwon", "member_amount_manwon", "amount_manwon"),
            False,
        )
        rows.append(
            _member_row(
                month_key,
                selected_idx,
                used_idx,
                "총계",
                total_count,
                total_amount,
                "member_summary" if summary else "bizday_rows",
                str(month.get("status") or NO_DATA_STATUS),
            )
        )
        rows.append(
            _member_row(
                month_key,
                selected_idx,
                used_idx,
                "신규",
                _pick_number(summary, ("new_member_cnt", "new_member_count"), True),
                _pick_number(summary, ("new_member_amt_manwon", "new_member_amount_manwon"), False),
                "member_summary",
                OPTIONAL_MISSING_STATUS,
            )
        )
        rows.append(
            _member_row(
                month_key,
                selected_idx,
                used_idx,
                "기존",
                _pick_number(summary, ("existing_member_cnt", "existing_member_count"), True),
                _pick_number(
                    summary,
                    ("existing_member_amt_manwon", "existing_member_amount_manwon"),
                    False,
                ),
                "member_summary",
                OPTIONAL_MISSING_STATUS,
            )
        )
    return pd.DataFrame(rows, columns=MEMBER_COMPARISON_COLUMNS)


def build_branch_comparison(
    frames: dict[str, pd.DataFrame],
    selected_idx: int,
) -> pd.DataFrame:
    """Build active branch and branch-bin comparison."""
    month_comparison = build_month_bizday_comparison(frames, selected_idx)
    if month_comparison.empty:
        return pd.DataFrame(columns=BRANCH_COMPARISON_COLUMNS)

    branch_bins = _frame(frames, "branch_bins")
    rows: list[dict[str, object]] = []
    for month in month_comparison.to_dict("records"):
        month_key = str(month["month_key"])
        month_bins = branch_bins.loc[
            branch_bins.get("month_key", pd.Series(dtype=object)).astype(str) == month_key
        ] if not branch_bins.empty else pd.DataFrame()
        used_idx = _to_int(month.get("used_idx"))
        if "idx" in month_bins.columns and used_idx is not None:
            month_bins = month_bins.loc[
                pd.to_numeric(month_bins["idx"], errors="coerce") == used_idx
            ].copy()
        if month_bins.empty:
            rows.append(
                {
                    "month_key": month_key,
                    "selected_idx": int(selected_idx),
                    "used_idx": used_idx,
                    "active_branch_count": _to_int(month.get("active_branch_count")),
                    "branch_bin": OPTIONAL_MISSING_STATUS,
                    "branch_count": None,
                    "source": OPTIONAL_MISSING_STATUS,
                    "status": str(month.get("status") or NO_DATA_STATUS),
                }
            )
            continue

        for row in month_bins.to_dict("records"):
            rows.append(
                {
                    "month_key": month_key,
                    "selected_idx": int(selected_idx),
                    "used_idx": used_idx,
                    "active_branch_count": _to_int(month.get("active_branch_count")),
                    "branch_bin": _pick_text(row, ("bin", "label", "name"), NO_DATA_STATUS),
                    "branch_count": _pick_number(
                        row,
                        ("branch_count", "count", "value"),
                        prefer_int=True,
                    ),
                    "source": "branch_bins",
                    "status": str(month.get("status") or NO_DATA_STATUS),
                }
            )
    return pd.DataFrame(rows, columns=BRANCH_COMPARISON_COLUMNS)


def render_raw_dashboard_page(context: Mapping[str, Any] | None = None) -> None:
    """Render the Streamlit reference/history raw dashboard comparison page."""
    _require_streamlit()
    st.markdown(
        render_page_header_html("raw_dashboard"),
        unsafe_allow_html=True,
    )
    _render_required_notices()

    uploaded_file = st.file_uploader(
        "HTM Raw Dashboard 업로드",
        type=["htm", "html"],
        help=(
            "수동 업로드가 서버 자동 로딩보다 우선합니다. 원문 HTM은 화면에 출력하지 않고 "
            "필요한 JavaScript 집계 객체만 파싱합니다."
        ),
    )
    raw_html_text: str | None = None
    raw_source_path: Path | None = None

    try:
        if uploaded_file is not None:
            raw_html_text = decode_uploaded_html(uploaded_file)
            bundle = parse_raw_dashboard_html(
                raw_html_text,
                source_name=str(getattr(uploaded_file, "name", "uploaded.htm")),
            )
            frames = bundle_to_frames(bundle)
            st.caption(f"데이터 소스: 수동 업로드 · {bundle.source_name}")
        else:
            autoload_path = resolve_raw_dashboard_autoload_path(context)
            if autoload_path is None:
                st.info("업로드 또는 자동 로딩 설정이 없습니다. " + SAMPLE_GUIDANCE_TEXT)
                return
            raw_source_path = autoload_path
            bundle, frames = load_raw_dashboard_server_file(autoload_path)
            st.success(f"서버 자동 로딩 · {autoload_path.name}")
    except RawDashboardParseError as exc:
        st.error(f"Raw Dashboard 파싱 오류: {exc}")
        return

    _render_import_summary(bundle, frames)
    min_idx, max_idx = get_available_bizday_range(frames)
    if min_idx == 0 and max_idx == 0:
        st.warning("bizday_rows 데이터가 없어 N영업일 비교를 만들 수 없습니다.")
        _render_raw_table_browser(
            frames,
            raw_html_text=raw_html_text,
            raw_source_path=raw_source_path,
        )
        return

    main_forecast_eok = _main_forecast_eok_from_context(context)
    selected_idx_default, linked_to_as_of_date = resolve_raw_dashboard_selected_idx(
        context,
        frames,
        min_idx,
        max_idx,
    )
    if linked_to_as_of_date:
        st.session_state[RAW_DASHBOARD_SELECTED_IDX_SESSION_KEY] = selected_idx_default
    else:
        stored_idx = st.session_state.get(RAW_DASHBOARD_SELECTED_IDX_SESSION_KEY)
        try:
            stored_idx_value = int(stored_idx)
        except (TypeError, ValueError):
            stored_idx_value = selected_idx_default
        if not min_idx <= stored_idx_value <= max_idx:
            stored_idx_value = selected_idx_default
        st.session_state[RAW_DASHBOARD_SELECTED_IDX_SESSION_KEY] = stored_idx_value
    selected_idx = st.slider(
        "기준 영업일차",
        min_value=min_idx,
        max_value=max_idx,
        step=1,
        key=RAW_DASHBOARD_SELECTED_IDX_SESSION_KEY,
        disabled=linked_to_as_of_date,
    )
    if linked_to_as_of_date:
        as_of_date = context.get("as_of_date") if isinstance(context, Mapping) else None
        try:
            as_of_date_text = pd.Timestamp(as_of_date).date().isoformat()
        except (TypeError, ValueError):
            as_of_date_text = "기준일"
        st.caption(
            f"{as_of_date_text} 기준일의 입력표 {selected_idx}영업일차와 자동 연동되었습니다."
        )
    _render_comparison_sections(
        bundle,
        frames,
        int(selected_idx),
        main_forecast_eok=main_forecast_eok,
    )
    _render_raw_table_browser(
        frames,
        raw_html_text=raw_html_text,
        raw_source_path=raw_source_path,
    )


def _render_required_notices() -> None:
    st.info(REFERENCE_HISTORY_NOTICE)
    st.warning(IS_CLOSE_DAY_GUARDRAIL_NOTICE)
    st.caption(NO_AUTO_FORECAST_NOTICE)


def _render_import_summary(bundle: Any, frames: dict[str, pd.DataFrame]) -> None:
    warnings = _frame(frames, "warnings")
    found = ", ".join(bundle.objects_found)
    st.caption(f"파싱 객체: {found}")
    if not warnings.empty:
        display_columns = [column for column in ("code", "object_name", "message") if column in warnings]
        st.dataframe(warnings[display_columns], hide_index=True, use_container_width=True)


def _render_raw_table_browser(
    frames: dict[str, pd.DataFrame],
    *,
    raw_html_text: str | None,
    raw_source_path: Path | None,
) -> None:
    inventory = _frame(frames, "raw_table_inventory")
    if inventory.empty:
        return

    st.markdown("### HTML RAW TABLE 전체 추출")
    st.caption(
        "HTML의 원천 객체를 표 단위로 보존합니다. 기본 표는 즉시 표시하고, "
        "개인·회원 금액 상세는 선택할 때만 지연 로딩합니다."
    )
    _render_raw_inventory_visual(inventory)
    with st.expander("RAW TABLE 인벤토리", expanded=True):
        inventory_display = inventory.rename(
            columns={
                "table_name": "표 이름",
                "source_object": "원천 객체",
                "row_count": "행 수",
                "column_count": "열 수",
                "loading_mode": "로딩 방식",
                "status": "상태",
            }
        )
        display_columns = [
            column
            for column in ("표 이름", "원천 객체", "행 수", "열 수", "로딩 방식", "상태")
            if column in inventory_display.columns
        ]
        st.dataframe(
            inventory_display[display_columns],
            hide_index=True,
            use_container_width=True,
        )

    available = inventory.loc[inventory["status"] != "원천 객체 없음"].copy()
    if available.empty:
        st.info("표로 변환할 수 있는 원천 객체가 없습니다.")
        return
    labels = dict(zip(available["table_key"], available["table_name"]))
    selected_key = st.selectbox(
        "RAW TABLE 선택",
        options=available["table_key"].tolist(),
        format_func=lambda key: labels.get(key, key),
        key="raw_dashboard_table_selector",
    )
    selected_meta = available.loc[available["table_key"] == selected_key].iloc[0]
    is_large = selected_meta["loading_mode"] == "선택 시 지연 로딩"

    try:
        if is_large:
            st.warning(
                "대용량 상세표입니다. 선택한 표만 메모리에 불러오며 예측 입력에는 반영하지 않습니다."
            )
            with st.spinner("선택한 대용량 RAW TABLE을 불러오는 중입니다..."):
                if raw_html_text is not None:
                    selected_frame = _extract_large_raw_table_cached(
                        raw_html_text,
                        str(selected_key),
                    )
                elif raw_source_path is not None:
                    selected_frame = load_large_raw_table_server_file(
                        raw_source_path,
                        str(selected_key),
                    )
                else:
                    selected_frame = pd.DataFrame()
        else:
            selected_frame = _frame(frames, str(selected_key))
    except (KeyError, RawDashboardParseError) as exc:
        st.error(f"RAW TABLE 추출 오류: {exc}")
        return

    st.caption(
        f"{labels.get(selected_key, selected_key)} · "
        f"{selected_frame.shape[0]:,}행 × {selected_frame.shape[1]:,}열"
    )
    if selected_frame.empty:
        st.info("선택한 표의 원천 행이 없습니다.")
        return
    st.dataframe(selected_frame, hide_index=True, use_container_width=True, height=440)
    st.download_button(
        "선택 표 CSV 내려받기",
        data=selected_frame.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"{selected_key}.csv",
        mime="text/csv",
        key=f"raw_dashboard_download_{selected_key}",
    )


def _render_raw_inventory_visual(inventory: pd.DataFrame) -> None:
    """Show table scale and loading mode before the user selects raw data."""
    required = {"table_name", "row_count", "loading_mode", "status"}
    if inventory.empty or not required.issubset(inventory.columns):
        return
    source = inventory.copy()
    source["row_count"] = pd.to_numeric(source["row_count"], errors="coerce").fillna(0)
    source["row_label"] = source["row_count"].map(lambda value: f"{int(value):,}행")
    chart = (
        alt.Chart(source)
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("row_count:Q", title="데이터 행 수", axis=alt.Axis(grid=False)),
            y=alt.Y(
                "table_name:N",
                title=None,
                sort="-x",
                axis=alt.Axis(labelLimit=220),
            ),
            color=alt.condition(
                "datum.loading_mode == '선택 시 지연 로딩'",
                alt.value("#7e99e5"),
                alt.value("#2f65e8"),
            ),
            tooltip=[
                alt.Tooltip("table_name:N", title="데이터 표"),
                alt.Tooltip("row_count:Q", title="행 수", format=","),
                alt.Tooltip("loading_mode:N", title="로딩 방식"),
                alt.Tooltip("status:N", title="상태"),
            ],
        )
        .properties(height=max(220, min(560, len(source) * 30)))
    )
    labels = chart.mark_text(align="left", dx=5, color="#14213d").encode(
        text="row_label:N"
    )
    with st.container(border=True):
        st.markdown("**원천 데이터 규모와 로딩 방식**")
        st.altair_chart(
            (chart + labels)
            .configure_view(stroke=None)
            .configure_axis(labelFontSize=10, titleFontSize=11),
            use_container_width=True,
        )
        st.caption("진한 블루는 즉시 표시, 연한 블루는 선택 시 불러오는 대용량 표입니다.")


def _main_forecast_eok_from_context(context: Mapping[str, Any] | None) -> float | None:
    if not isinstance(context, Mapping):
        return None
    return _to_float(context.get("raw_dashboard_main_forecast_eok"))


def _render_comparison_sections(
    bundle: Any,
    frames: dict[str, pd.DataFrame],
    selected_idx: int,
    *,
    main_forecast_eok: float | None,
) -> None:
    month_df = build_month_bizday_comparison(frames, selected_idx)
    category_df = build_category_comparison(frames, selected_idx)
    group_df = build_group_comparison(frames, selected_idx)
    branch_df = build_branch_comparison(frames, selected_idx)
    member_df = build_member_comparison(frames, selected_idx)

    _render_kpis(month_df, member_df, selected_idx)
    _render_same_bizday_percentile(month_df, selected_idx)
    _render_factor_decomposition(month_df, category_df, member_df)
    _render_interpretation_cards(month_df, category_df, branch_df, member_df)
    _render_activity_crosscheck(bundle, main_forecast_eok)
    _render_table_and_chart(
        "월별 누적 실적 비교",
        month_df,
        value_column="total_cum_eok",
        color_column="status",
    )
    _render_table_and_chart(
        "상품군별 누적 비교",
        category_df,
        value_column="value_eok",
        color_column="category",
    )
    _render_table_and_chart(
        "차월그룹별 가동/실적 비교",
        group_df,
        value_column="revenue_eok",
        color_column="group",
    )
    _render_table_and_chart(
        "가동지국/급간 비교",
        branch_df,
        value_column="branch_count",
        color_column="branch_bin",
    )
    _render_table_and_chart(
        "구매회원 신규/기존 비교",
        member_df,
        value_column="member_cnt",
        color_column="member_type",
    )


def _render_kpis(
    month_df: pd.DataFrame,
    member_df: pd.DataFrame,
    selected_idx: int,
) -> None:
    latest = _latest_row(month_df)
    previous = _previous_row(month_df)
    member_total = _latest_member_value(member_df, "총계", "member_cnt")
    member_new = _latest_member_value(member_df, "신규", "member_cnt")
    member_existing = _latest_member_value(member_df, "기존", "member_cnt")
    missing_month_count = (
        int((month_df["reached_selected_idx"] == False).sum()) if not month_df.empty else 0
    )

    delta_eok = latest.get("prev_month_delta_eok") if latest else None
    previous_eok = previous.get("total_cum_eok") if previous else None
    latest_reached = bool(latest.get("reached_selected_idx")) if latest else False
    latest_used_idx = _to_int(latest.get("used_idx")) if latest else None
    total_label = (
        f"{selected_idx}영업일 누적 판매실적"
        if latest_reached
        else f"최신월 도달 {latest_used_idx or 0}영업일 누적"
    )
    delta_label = (
        _format_delta(delta_eok, previous_eok)
        if latest_reached
        else "비교 제외"
    )
    cards = (
        render_kpi_card(
            total_label,
            _format_eok(latest.get("total_cum_eok") if latest else None),
            sub=(
                f"{latest.get('month_key')} · {latest.get('status')}"
                if latest
                else NO_DATA_STATUS
            ),
            focus=True,
        ),
        render_kpi_card(
            "전월 동영업일 대비",
            delta_label,
            sub="증감 eok / %" if latest_reached else "최신월 미도달",
        ),
        render_kpi_card(
            "가동 지국수",
            _format_count(latest.get("active_branch_count") if latest else None),
            sub=str(latest.get("status") or NO_DATA_STATUS) if latest else NO_DATA_STATUS,
        ),
        render_kpi_card("구매회원 총계", _format_count(member_total), sub="총계"),
        render_kpi_card("신규 구매회원", _format_count(member_new), sub=OPTIONAL_MISSING_STATUS),
        render_kpi_card("기존 구매회원", _format_count(member_existing), sub=OPTIONAL_MISSING_STATUS),
        render_kpi_card("데이터 미도달 월 수", f"{missing_month_count}개월", sub=NOT_REACHED_STATUS),
    )
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def _render_same_bizday_percentile(
    month_df: pd.DataFrame,
    selected_idx: int,
) -> None:
    analysis_month = resolve_latest_exact_month_key(month_df)
    result = build_same_bizday_percentile(
        month_df,
        target_month_key=analysis_month,
    )
    latest = _latest_row(month_df)
    latest_month = str(latest.get("month_key") or "") if latest else ""
    st.markdown(
        render_section_header(
            "동영업일 백분위",
            f"{selected_idx}영업일에 정확히 도달한 월만으로 분석월의 위치를 계산합니다.",
        ),
        unsafe_allow_html=True,
    )
    if analysis_month and latest_month and analysis_month != latest_month:
        st.warning(
            f"최신월 {latest_month}은 {selected_idx}영업일 미도달"
            f"(도달 {latest.get('used_idx')}영업일)이라 백분위·요인분해에서 제외했습니다. "
            f"최신 정확 도달월 {analysis_month}을 분석월로 사용합니다."
        )
    if result["status"] != INSIGHT_READY_STATUS:
        st.info(f"백분위 자료 부족: {result['reason']}")
        st.caption(P3_REFERENCE_NOTICE)
        return

    percentile = _to_float(result.get("percentile_pct"))
    peer_count = _to_int(result.get("peer_count")) or 0
    excluded_count = _to_int(result.get("excluded_month_count")) or 0
    cards = (
        render_kpi_card(
            "분석월 분포 위치",
            f"{percentile:,.1f} 백분위" if percentile is not None else NO_DATA_STATUS,
            sub=(
                f"{result.get('current_month')} · "
                f"{result.get('position_label') or NO_DATA_STATUS}"
            ),
            focus=True,
        ),
        render_kpi_card(
            "과거 동영업일 중앙값",
            _format_eok(result.get("peer_median_eok")),
            sub=f"적격 과거 {peer_count}개월",
        ),
        render_kpi_card(
            "과거 비교 범위",
            _format_eok_range(
                result.get("peer_min_eok"),
                result.get("peer_max_eok"),
            ),
            sub=f"미도달·중복 제외 {excluded_count}개월",
        ),
    )
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)
    st.caption(
        "산식: 과거 적격월 중 현재보다 낮은 월 + 동률 월의 0.5를 적격월 수로 나눈 "
        "중간순위 백분위입니다. 최신월은 기준분포에 포함하지 않습니다."
    )
    st.caption(P3_REFERENCE_NOTICE)


def _render_factor_decomposition(
    month_df: pd.DataFrame,
    category_df: pd.DataFrame,
    member_df: pd.DataFrame,
) -> None:
    analysis_month = resolve_latest_exact_month_key(month_df)
    decomposition = build_category_delta_decomposition(
        month_df,
        category_df,
        current_month_key=analysis_month,
    )
    st.markdown(
        render_section_header(
            "동영업일 실적 차이 요인분해",
            "상품군 증감은 합산 기여로, 조직·활동은 인과가 아닌 동행 변화로 분리합니다.",
        ),
        unsafe_allow_html=True,
    )
    if decomposition["status"] != INSIGHT_READY_STATUS:
        st.info(f"상품군 요인분해 자료 부족: {decomposition['reason']}")
    else:
        rows = decomposition["rows"]
        non_residual = rows.loc[rows["is_residual"] == False].copy()
        top_factor = (
            non_residual.iloc[non_residual["delta_eok"].abs().argmax()]
            if not non_residual.empty
            else None
        )
        cards = (
            render_kpi_card(
                "총 실적 차이",
                _format_signed_eok(decomposition.get("total_delta_eok")),
                sub=(
                    f"{decomposition['comparison_month']} → "
                    f"{decomposition['current_month']}"
                ),
                focus=True,
            ),
            render_kpi_card(
                "최대 상품군 변화",
                str(top_factor.get("factor")) if top_factor is not None else NO_DATA_STATUS,
                sub=(
                    _format_signed_eok(top_factor.get("delta_eok"))
                    if top_factor is not None
                    else NO_DATA_STATUS
                ),
            ),
            render_kpi_card(
                "상품군 합계 정합",
                "일치" if decomposition.get("reconciled") else "잔차 확인",
                sub=(
                    "잔차 "
                    f"{_format_signed_eok(decomposition.get('reconciliation_gap_eok'))}"
                ),
            ),
        )
        st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)

        chart = (
            alt.Chart(rows)
            .mark_bar(cornerRadiusEnd=3)
            .encode(
                x=alt.X("delta_eok:Q", title="전월 대비 증감(억)"),
                y=alt.Y(
                    "factor:N",
                    title="상품군",
                    sort=alt.SortField(field="delta_eok", order="descending"),
                ),
                color=alt.Color(
                    "direction:N",
                    title="방향",
                    scale=alt.Scale(
                        domain=["증가", "감소", "변동 없음"],
                        range=["#168A70", "#D4515C", "#94A3B8"],
                    ),
                ),
                tooltip=[
                    alt.Tooltip("factor:N", title="상품군"),
                    alt.Tooltip("delta_eok:Q", title="증감(억)", format="+,.2f"),
                    alt.Tooltip(
                        "contribution_pct:Q",
                        title="순증감 기여율",
                        format="+.1%",
                    ),
                    alt.Tooltip("source:N", title="근거"),
                ],
            )
            .properties(height=max(220, 34 * len(rows)))
        )
        st.altair_chart(chart, use_container_width=True)
        display_rows = _format_for_display(
            rows[
                [
                    "factor",
                    "current_eok",
                    "comparison_eok",
                    "delta_eok",
                    "contribution_pct",
                    "direction",
                    "source",
                ]
            ]
        ).rename(
            columns={
                "factor": "상품군",
                "current_eok": "현재 누계",
                "comparison_eok": "전월 누계",
                "delta_eok": "증감",
                "contribution_pct": "순증감 기여율",
                "direction": "방향",
                "source": "근거",
            }
        )
        st.dataframe(display_rows, hide_index=True, use_container_width=True)
        st.caption(
            "순증감 기여율은 상품군 증감을 총 실적 차이로 나눈 값입니다. "
            "상쇄가 있으면 음수 또는 100% 초과가 가능하며, 총 차이가 0이면 표시하지 않습니다."
        )

    _render_org_activity_changes(
        month_df,
        member_df,
        current_month_key=analysis_month,
    )
    st.caption(P3_REFERENCE_NOTICE)


def _render_org_activity_changes(
    month_df: pd.DataFrame,
    member_df: pd.DataFrame,
    *,
    current_month_key: str | None,
) -> None:
    result = build_org_activity_changes(
        month_df,
        member_df,
        current_month_key=current_month_key,
    )
    st.markdown("#### 조직·활동 동행 변화")
    if result["status"] != INSIGHT_READY_STATUS:
        st.info(f"동행 지표 자료 부족: {result['reason']}")
        return
    rows = result["rows"]
    cards = tuple(
        render_kpi_card(
            str(row["metric"]),
            f"{_format_plain_number(row['current_value'])}{row['unit']}",
            sub=(
                f"{result['comparison_month']} 대비 "
                f"{_format_signed_plain_number(row['delta_value'])}{row['unit']}"
                f"{_format_optional_parenthesized_pct(row['change_pct'])}"
            ),
        )
        for row in rows.to_dict("records")
    )
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)
    st.caption(
        "지국·회원 변화는 실적의 원인이나 상품군 기여에 합산하지 않는 동행 지표입니다."
    )


def _render_interpretation_cards(
    month_df: pd.DataFrame,
    category_df: pd.DataFrame,
    branch_df: pd.DataFrame,
    member_df: pd.DataFrame,
) -> None:
    st.markdown(
        render_section_header(
            "해석 카드",
            "계산된 실적 기여와 인과로 단정하지 않는 동행 신호를 구분합니다.",
        ),
        unsafe_allow_html=True,
    )
    insights = _build_interpretations(month_df, category_df, branch_df, member_df)
    for insight in insights:
        st.markdown(f"- {insight}")


def _build_interpretations(
    month_df: pd.DataFrame,
    category_df: pd.DataFrame,
    branch_df: pd.DataFrame,
    member_df: pd.DataFrame,
) -> list[str]:
    _ = branch_df
    insights: list[str] = []
    latest = _latest_row(month_df)
    analysis_month = resolve_latest_exact_month_key(month_df)
    latest_month = str(latest.get("month_key") or "") if latest else ""
    if latest and analysis_month and latest_month != analysis_month:
        insights.append(
            f"[사실] 최신월 {latest_month}은 선택 영업일 미도달"
            f"(도달 {latest.get('used_idx')}영업일)이라 동영업일 비교에서 제외하고, "
            f"{analysis_month}을 분석월로 사용했습니다."
        )
    else:
        percentile = build_same_bizday_percentile(
            month_df,
            target_month_key=analysis_month,
        )
        if percentile["status"] == INSIGHT_READY_STATUS:
            insights.append(
                f"[분포] 분석월 {analysis_month}은 과거 적격월 대비 "
                f"{_to_float(percentile.get('percentile_pct')):,.1f} 백분위입니다."
            )
        else:
            insights.append("해석 보류: 동일 영업일차 분포 데이터가 부족합니다.")

    decomposition = build_category_delta_decomposition(
        month_df,
        category_df,
        current_month_key=analysis_month,
    )
    if decomposition["status"] == INSIGHT_READY_STATUS:
        rows = decomposition["rows"]
        non_residual = rows.loc[rows["is_residual"] == False]
        top_factor = (
            non_residual.iloc[non_residual["delta_eok"].abs().argmax()]
            if not non_residual.empty
            else None
        )
        top_text = (
            f", 최대 상품군 변화는 {top_factor['factor']} "
            f"({_format_signed_eok(top_factor['delta_eok'])})"
            if top_factor is not None
            else ""
        )
        insights.append(
            f"[분해] {decomposition['comparison_month']} → "
            f"{decomposition['current_month']} 총 실적 차이는 "
            f"{_format_signed_eok(decomposition['total_delta_eok'])}{top_text}입니다."
        )
    else:
        insights.append(f"해석 보류: {decomposition['reason']}")

    org_activity = build_org_activity_changes(
        month_df,
        member_df,
        current_month_key=analysis_month,
    )
    if org_activity["status"] == INSIGHT_READY_STATUS:
        insights.append(
            "[참고] 가동지국·구매회원 변화는 상품군 기여에 합산하지 않는 "
            "동행 지표이며 실적 차이의 원인으로 단정하지 않습니다."
        )
    else:
        insights.append("해석 보류: 조직·활동 동행 데이터가 부족합니다.")
    return insights


def _render_activity_crosscheck(bundle: Any, main_forecast_eok: float | None) -> None:
    result = build_activity_crosscheck(bundle, main_forecast_eok=main_forecast_eok)
    st.markdown(
        render_section_header(
            "활동기반 Cross-check",
            "ACTV/projection_method 기반 참고/검증 카드",
        ),
        unsafe_allow_html=True,
    )

    cards = (
        render_kpi_card(
            "활동기반 참고 추산 eok",
            _format_crosscheck_eok(result["activity_estimate_eok"]),
            sub=str(result["estimate_source"] or NO_DATA_STATUS),
            focus=True,
        ),
        render_kpi_card(
            "기존 예측값 eok",
            _format_crosscheck_eok(result["main_forecast_eok"]),
            sub="main_forecast_eok",
        ),
        render_kpi_card(
            "차이 eok",
            _format_crosscheck_eok(result["diff_eok"], signed=True),
            sub="activity - main",
        ),
        render_kpi_card(
            "차이 %",
            _format_crosscheck_pct(result["diff_pct"]),
            sub=str(result["signal"]),
        ),
    )
    st.markdown(f'<div class="kpi-grid">{"".join(cards)}</div>', unsafe_allow_html=True)

    details = pd.DataFrame(
        [
            ("signal", result["signal"]),
            ("estimate_source", result["estimate_source"] or NO_DATA_STATUS),
            ("explanation", result["explanation"]),
            ("confidence_note", result["confidence_note"]),
            ("final_forecast_modified", str(result["final_forecast_modified"])),
        ],
        columns=["item", "value"],
    )
    st.dataframe(details, hide_index=True, use_container_width=True)
    st.caption(ACTIVITY_CROSSCHECK_NOTICE)
    if result["signal"] == "INSUFFICIENT_DATA":
        st.info(ACTIVITY_CROSSCHECK_OPTIONAL_MISSING)


def _format_crosscheck_eok(value: object, *, signed: bool = False) -> str:
    number = _to_float(value)
    if number is None:
        return NO_DATA_STATUS
    sign = "+" if signed else ""
    return f"{number:{sign},.1f} eok"


def _format_crosscheck_pct(value: object) -> str:
    number = _to_float(value)
    if number is None:
        return NO_DATA_STATUS
    return f"{number:+,.1f}%"


def _render_table_and_chart(
    title: str,
    df: pd.DataFrame,
    *,
    value_column: str,
    color_column: str,
) -> None:
    st.markdown(render_section_header(title), unsafe_allow_html=True)
    if df.empty:
        st.info(NO_DATA_STATUS)
        return
    st.dataframe(_format_for_display(df), hide_index=True, use_container_width=True)
    chart_source = df.dropna(subset=[value_column]) if value_column in df.columns else pd.DataFrame()
    if chart_source.empty or "month_key" not in chart_source.columns:
        st.caption("차트 데이터 없음")
        return
    if color_column not in chart_source.columns:
        color_column = "month_key"
    chart = (
        alt.Chart(chart_source)
        .mark_bar(cornerRadiusTopLeft=2, cornerRadiusTopRight=2)
        .encode(
            x=alt.X(
                "month_key:N",
                title="month_key",
                sort=_sorted_month_keys(chart_source["month_key"].unique()),
            ),
            y=alt.Y(f"{value_column}:Q", title=value_column),
            color=alt.Color(f"{color_column}:N", title=color_column),
            tooltip=[
                column
                for column in chart_source.columns
                if column in {"month_key", color_column, value_column, "status", "used_idx"}
            ],
        )
        .properties(height=260)
    )
    st.altair_chart(chart, use_container_width=True)


def _default_selected_idx(frames: dict[str, pd.DataFrame], min_idx: int, max_idx: int) -> int:
    bizday_rows = _frame(frames, "bizday_rows")
    if bizday_rows.empty or "month_key" not in bizday_rows.columns or "idx" not in bizday_rows.columns:
        return max_idx
    prepared = bizday_rows.copy()
    prepared["idx"] = pd.to_numeric(prepared["idx"], errors="coerce")
    per_month_max = prepared.dropna(subset=["idx"]).groupby("month_key")["idx"].max()
    if per_month_max.empty:
        return max_idx
    latest_month = _latest_month_key(per_month_max.index)
    latest_max = int(per_month_max.loc[latest_month])
    common_max = int(per_month_max.min())
    return max(min_idx, min(latest_max, common_max, max_idx))


def resolve_raw_dashboard_selected_idx(
    context: Mapping[str, Any] | None,
    frames: dict[str, pd.DataFrame],
    min_idx: int,
    max_idx: int,
) -> tuple[int, bool]:
    """Resolve the RAW comparison index from the main app's exact as-of-date row."""
    linked_value = (
        context.get(RAW_DASHBOARD_SELECTED_BUSINESS_DAY_CONTEXT)
        if isinstance(context, Mapping)
        else None
    )
    numeric_value = _to_float(linked_value)
    if numeric_value is not None and float(numeric_value).is_integer():
        linked_idx = int(numeric_value)
        return max(min_idx, min(linked_idx, max_idx)), True
    return _default_selected_idx(frames, min_idx, max_idx), False


def _month_keys(frames: dict[str, pd.DataFrame]) -> list[str]:
    month_summaries = _frame(frames, "month_summaries")
    if not month_summaries.empty and "month_key" in month_summaries.columns:
        return _sorted_month_keys(month_summaries["month_key"].dropna().astype(str).unique())
    bizday_rows = _frame(frames, "bizday_rows")
    if not bizday_rows.empty and "month_key" in bizday_rows.columns:
        return _sorted_month_keys(bizday_rows["month_key"].dropna().astype(str).unique())
    return []


def _empty_month_row(month_key: str, selected_idx: int) -> dict[str, object]:
    return {
        "month_key": month_key,
        "selected_idx": int(selected_idx),
        "used_idx": None,
        "total_cum_manwon": None,
        "total_cum_eok": None,
        "active_branch_count": None,
        "member_cum": None,
        "reached_selected_idx": False,
        "status": NO_DATA_STATUS,
        "prev_month_delta_eok": None,
        "prev_month_delta_pct": None,
    }


def _empty_group_row(month_key: str, selected_idx: int, used_idx: int | None) -> dict[str, object]:
    return {
        "month_key": month_key,
        "selected_idx": int(selected_idx),
        "used_idx": used_idx,
        "group": OPTIONAL_MISSING_STATUS,
        "count": None,
        "revenue_manwon": None,
        "revenue_eok": None,
        "share_pct": None,
        "source": OPTIONAL_MISSING_STATUS,
        "status": OPTIONAL_MISSING_STATUS,
    }


def _member_row(
    month_key: str,
    selected_idx: int,
    used_idx: int | None,
    member_type: str,
    count: object,
    amount_manwon: object,
    source: str,
    status: str,
) -> dict[str, object]:
    amount = _to_float(amount_manwon)
    return {
        "month_key": month_key,
        "selected_idx": int(selected_idx),
        "used_idx": used_idx,
        "member_type": member_type,
        "member_cnt": _to_int(count),
        "member_amt_manwon": amount,
        "member_amt_eok": _manwon_to_eok(amount),
        "source": source,
        "status": status if count is not None or amount is not None else OPTIONAL_MISSING_STATUS,
    }


def _format_for_display(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in result.columns:
        if column.endswith("_eok") or column in {"prev_month_delta_eok"}:
            result[column] = result[column].map(_format_eok)
        elif column.endswith("_pct"):
            result[column] = result[column].map(_format_pct)
        elif column.endswith("_manwon"):
            result[column] = result[column].map(_format_manwon)
        elif column in {"reached_selected_idx", "fallback_used"}:
            result[column] = result[column].map(lambda value: "Y" if bool(value) else "N")
    return result


def _latest_row(df: pd.DataFrame) -> dict[str, object] | None:
    if df.empty or "month_key" not in df.columns:
        return None
    month_key = _latest_month_key(df["month_key"].dropna().astype(str).unique())
    rows = df.loc[df["month_key"].astype(str) == month_key]
    if rows.empty:
        return None
    return rows.iloc[-1].to_dict()


def _previous_row(df: pd.DataFrame) -> dict[str, object] | None:
    if df.empty or "month_key" not in df.columns:
        return None
    keys = _sorted_month_keys(df["month_key"].dropna().astype(str).unique())
    if len(keys) < 2:
        return None
    rows = df.loc[df["month_key"].astype(str) == keys[-2]]
    if rows.empty:
        return None
    return rows.iloc[-1].to_dict()


def _latest_member_value(member_df: pd.DataFrame, member_type: str, column: str) -> object | None:
    if member_df.empty or column not in member_df.columns:
        return None
    latest_month = _latest_month_key(member_df["month_key"].dropna().astype(str).unique())
    rows = member_df.loc[
        (member_df["month_key"].astype(str) == latest_month)
        & (member_df["member_type"].astype(str) == member_type)
    ]
    if rows.empty:
        return None
    return rows.iloc[-1].get(column)


def _frame(frames: dict[str, pd.DataFrame], key: str) -> pd.DataFrame:
    value = frames.get(key)
    return value if isinstance(value, pd.DataFrame) else pd.DataFrame()


def _sort_by_month_key(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "month_key" not in df.columns:
        return df
    result = df.copy()
    result["_month_sort_key"] = result["month_key"].map(_month_sort_key)
    result = result.sort_values("_month_sort_key", kind="stable").drop(columns=["_month_sort_key"])
    return result


def _sorted_month_keys(values: Any) -> list[str]:
    return sorted((str(value) for value in values), key=_month_sort_key)


def _latest_month_key(values: Any) -> str:
    keys = _sorted_month_keys(values)
    return keys[-1] if keys else ""


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


def _first_numeric_series(df: pd.DataFrame, columns: tuple[str, ...]) -> pd.Series:
    for column in columns:
        if column in df.columns:
            return pd.to_numeric(df[column], errors="coerce")
    return pd.Series([None] * len(df), index=df.index, dtype="float64")


def _pick_text(row: Mapping[str, object], keys: tuple[str, ...], default: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and not pd.isna(value):
            return str(value)
    return default


def _pick_number(
    row: Mapping[str, object],
    keys: tuple[str, ...],
    prefer_int: bool,
) -> int | float | None:
    for key in keys:
        value = row.get(key)
        number = _to_float(value)
        if number is not None:
            return int(number) if prefer_int else number
    return None


def _safe_ratio(numerator: object, denominator: object) -> float | None:
    top = _to_float(numerator)
    bottom = _to_float(denominator)
    if top is None or bottom is None or bottom == 0:
        return None
    return top / bottom


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
    if number is None:
        return None
    return int(number)


def _manwon_to_eok(value: object) -> float | None:
    number = _to_float(value)
    if number is None:
        return None
    return number / 10000


def _format_eok(value: object) -> str:
    number = _to_float(value)
    if number is None:
        return NO_DATA_STATUS
    return f"{number:,.1f}억"


def _format_signed_eok(value: object) -> str:
    number = _to_float(value)
    if number is None:
        return NO_DATA_STATUS
    return f"{number:+,.1f}억"


def _format_delta(delta: object, previous: object) -> str:
    delta_number = _to_float(delta)
    previous_number = _to_float(previous)
    if delta_number is None:
        return NO_DATA_STATUS
    pct = _safe_ratio(delta_number, previous_number)
    if pct is None:
        return _format_signed_eok(delta_number)
    return f"{_format_signed_eok(delta_number)} / {_format_pct(pct)}"


def _format_pct(value: object) -> str:
    number = _to_float(value)
    if number is None:
        return NO_DATA_STATUS
    return f"{number * 100:+,.1f}%"


def _format_manwon(value: object) -> str:
    number = _to_float(value)
    if number is None:
        return NO_DATA_STATUS
    return f"{number:,.0f}만원"


def _format_count(value: object) -> str:
    number = _to_int(value)
    if number is None:
        return NO_DATA_STATUS
    return f"{number:,}"


def _format_eok_range(minimum: object, maximum: object) -> str:
    minimum_number = _to_float(minimum)
    maximum_number = _to_float(maximum)
    if minimum_number is None or maximum_number is None:
        return NO_DATA_STATUS
    return f"{minimum_number:,.1f}~{maximum_number:,.1f}억"


def _format_plain_number(value: object) -> str:
    number = _to_float(value)
    if number is None:
        return NO_DATA_STATUS
    return f"{number:,.0f}"


def _format_signed_plain_number(value: object) -> str:
    number = _to_float(value)
    if number is None:
        return NO_DATA_STATUS
    return f"{number:+,.0f}"


def _format_optional_parenthesized_pct(value: object) -> str:
    number = _to_float(value)
    if number is None:
        return ""
    return f" ({number:+,.1%})"


def _require_streamlit() -> None:
    if st is None:
        raise RuntimeError("Streamlit is required to render raw dashboard page.")
