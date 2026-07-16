"""Importer for raw HTM dashboard JavaScript data objects."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from src.raw_dashboard_schema import (
    RawDashboardActivityProjection,
    RawDashboardBizdayRow,
    RawDashboardBundle,
    RawDashboardMonthSummary,
    RawDashboardWarning,
)


class RawDashboardParseError(ValueError):
    """Raised when raw dashboard HTM content cannot be parsed safely."""


_DECLARATION_TEMPLATE = r"\b(?:const|var|let)\s+{name}\s*=\s*"
_OPTIONAL_DICT_OBJECTS = ("COMP", "ACTV", "BRANCHSTATS", "BRANCHSTATS_OVERRIDE")
_OPTIONAL_ARRAY_OBJECTS = ("BIN_LABELS",)
_LARGE_ARRAY_OBJECTS = ("REP_AMOUNTS", "MEMBER_AMOUNTS")

DEFAULT_BRANCH_BIN_LABELS = [
    "1원~500만",
    "500만~1천만",
    "1천만~1.5천만",
    "1.5천만~2천만",
    "2천만~3천만",
    "3천만↑",
]


def extract_js_value(html_text: str, object_name: str) -> Any:
    """Extract a declared JavaScript object or array literal."""
    literal = _extract_assignment_literal(html_text, object_name)
    normalized = _normalize_js_object_literal(literal)

    try:
        return json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise RawDashboardParseError(
            f"Could not parse JavaScript value {object_name}: {exc.msg} "
            f"at line {exc.lineno}, column {exc.colno}."
        ) from exc


def extract_js_object(html_text: str, object_name: str) -> dict[str, Any]:
    """Extract a declared JavaScript object literal as a Python dict."""
    parsed = extract_js_value(html_text, object_name)

    if not isinstance(parsed, dict):
        raise RawDashboardParseError(f"JavaScript object {object_name} is not a dict.")
    return parsed


def parse_raw_dashboard_html(
    html_text: str,
    source_name: str | None = None,
) -> RawDashboardBundle:
    """Parse raw dashboard HTM text into a structured bundle."""
    try:
        agg = extract_js_object(html_text, "AGG")
    except (KeyError, RawDashboardParseError) as exc:
        raise RawDashboardParseError("Required JavaScript object AGG was not found or invalid.") from exc

    warnings: list[RawDashboardWarning] = []
    objects_found = ["AGG"]
    optional_values: dict[str, dict[str, Any] | None] = {}

    for object_name in _OPTIONAL_DICT_OBJECTS:
        if not _has_js_assignment(html_text, object_name):
            warnings.append(
                RawDashboardWarning(
                    code="MISSING_OPTIONAL_OBJECT",
                    message=f"Optional JavaScript object {object_name} was not found.",
                    object_name=object_name,
                )
            )
            optional_values[object_name] = None
            continue
        try:
            optional_values[object_name] = extract_js_object(html_text, object_name)
            objects_found.append(object_name)
        except RawDashboardParseError as exc:
            warnings.append(
                RawDashboardWarning(
                    code="OPTIONAL_OBJECT_PARSE_FAILED",
                    message=f"Optional JavaScript object {object_name} could not be parsed: {exc}",
                    object_name=object_name,
                )
            )
            optional_values[object_name] = None

    array_values: dict[str, list[Any]] = {}
    for object_name in _OPTIONAL_ARRAY_OBJECTS:
        if not _has_js_assignment(html_text, object_name):
            array_values[object_name] = []
            continue
        try:
            parsed_array = extract_js_value(html_text, object_name)
            if not isinstance(parsed_array, list):
                raise RawDashboardParseError(
                    f"JavaScript value {object_name} is not an array literal."
                )
            array_values[object_name] = parsed_array
            objects_found.append(object_name)
        except RawDashboardParseError as exc:
            warnings.append(
                RawDashboardWarning(
                    code="OPTIONAL_OBJECT_PARSE_FAILED",
                    message=f"Optional JavaScript value {object_name} could not be parsed: {exc}",
                    object_name=object_name,
                )
            )
            array_values[object_name] = []

    large_included: dict[str, bool] = {}
    for object_name in _LARGE_ARRAY_OBJECTS:
        included = _has_js_assignment(html_text, object_name)
        large_included[object_name] = included
        if included:
            objects_found.append(object_name)
        else:
            warnings.append(
                RawDashboardWarning(
                    code="MISSING_OPTIONAL_OBJECT",
                    message=f"Optional JavaScript object {object_name} was not found.",
                    object_name=object_name,
                )
            )

    month_summaries, bizday_rows = _build_month_data(agg)
    activity_projection = _extract_activity_projection(agg, optional_values["ACTV"])

    return RawDashboardBundle(
        source_name=source_name,
        objects_found=objects_found,
        warnings=warnings,
        agg=agg,
        comp=optional_values["COMP"],
        actv=optional_values["ACTV"],
        branchstats=optional_values["BRANCHSTATS"],
        branchstats_override=optional_values["BRANCHSTATS_OVERRIDE"],
        bin_labels=[str(value) for value in array_values["BIN_LABELS"]]
        or DEFAULT_BRANCH_BIN_LABELS.copy(),
        rep_amounts_included=large_included["REP_AMOUNTS"],
        member_amounts_included=large_included["MEMBER_AMOUNTS"],
        month_summaries=month_summaries,
        bizday_rows=bizday_rows,
        activity_projection=activity_projection,
    )


def parse_raw_dashboard_file(path: str | Path) -> RawDashboardBundle:
    """Read and parse a raw dashboard HTM file with utf-8, then cp949 fallback."""
    source_path = Path(path)
    decode_errors: list[UnicodeDecodeError] = []
    for encoding in ("utf-8", "cp949"):
        try:
            html_text = source_path.read_text(encoding=encoding)
            return parse_raw_dashboard_html(html_text, source_name=source_path.name)
        except UnicodeDecodeError as exc:
            decode_errors.append(exc)

    raise RawDashboardParseError(
        f"Could not decode raw dashboard file {source_path.name} with utf-8 or cp949."
    ) from decode_errors[-1]


def bundle_to_frames(bundle: RawDashboardBundle) -> dict[str, "pd.DataFrame"]:
    """Convert a parsed raw dashboard bundle into pandas DataFrames."""
    import pandas as pd

    month_summary_rows = [asdict(row) for row in bundle.month_summaries]
    bizday_rows = [asdict(row) for row in bundle.bizday_rows]

    category_total_rows = []
    for summary in bundle.month_summaries:
        for category, total_manwon in summary.category_totals_manwon.items():
            category_total_rows.append(
                {
                    "month_key": summary.month_key,
                    "category": category,
                    "total_manwon": total_manwon,
                    "total_eok": _manwon_to_eok(total_manwon),
                }
            )

    activity_rows = []
    if bundle.activity_projection is not None:
        activity_rows.append(asdict(bundle.activity_projection))

    frames = {
        "month_summaries": pd.DataFrame(month_summary_rows),
        "bizday_rows": pd.DataFrame(bizday_rows),
        "category_totals": pd.DataFrame(category_total_rows),
        "bizday_category_cum": pd.DataFrame(_build_bizday_category_rows(bundle.agg)),
        "group_stats": pd.DataFrame(_build_group_rows(bundle.agg)),
        "member_summary": pd.DataFrame(_build_member_rows(bundle.agg, bundle.month_summaries)),
        "branch_bins": pd.DataFrame(_build_branch_bin_rows(bundle.agg, bundle.bin_labels)),
        "activity_projection": pd.DataFrame(activity_rows),
        "warnings": pd.DataFrame([asdict(warning) for warning in bundle.warnings]),
    }
    frames.update(build_raw_dashboard_frames(bundle))
    frames["raw_table_inventory"] = build_raw_table_inventory(bundle, frames)
    return frames


STANDARD_RAW_TABLE_SPECS = (
    ("raw_agg_months", "AGG 월 메타데이터", "AGG"),
    ("raw_agg_categories", "AGG 월별 상품군", "AGG"),
    ("raw_agg_daily_series", "AGG 일자별 상품군 실적", "AGG"),
    ("raw_agg_bizday_series", "AGG 영업일별 누적 원문", "AGG"),
    ("raw_agg_category_totals", "AGG 월별 상품군 합계", "AGG"),
    ("raw_agg_group_stats", "AGG 월별 차월그룹", "AGG"),
    ("raw_agg_member_series", "AGG 구매회원 일자별 원문", "AGG"),
    ("raw_agg_member_status_counts", "AGG 구매회원 상태별 수", "AGG"),
    ("raw_agg_member_summary", "AGG 구매회원 월 요약", "AGG"),
    ("raw_agg_branch_bins_month", "AGG 지국 월마감 급간", "AGG"),
    ("raw_agg_projection", "AGG 당월 추산", "AGG"),
    ("raw_agg_projection_method", "AGG 추산 산출근거", "AGG"),
    ("raw_comp_months", "COMP 분석 월 목록", "COMP"),
    ("raw_comp_groups", "COMP 차월그룹 목록", "COMP"),
    ("raw_comp_rows", "COMP 19개월 종합분석", "COMP"),
    ("raw_comp_corr", "COMP 상관관계", "COMP"),
    ("raw_actv_metrics", "ACTV 모델 지표", "ACTV"),
    ("raw_actv_coef", "ACTV 회귀계수", "ACTV"),
    ("raw_actv_rows", "ACTV 월별 검증", "ACTV"),
    ("raw_actv_current", "ACTV 당월 참고추산", "ACTV"),
    ("raw_branchstats_months", "BRANCHSTATS 월 메타데이터", "BRANCHSTATS"),
    ("raw_branchstats_snapshots", "BRANCHSTATS 영업일 스냅샷", "BRANCHSTATS"),
    ("raw_branchstats_bins", "BRANCHSTATS 영업일 급간", "BRANCHSTATS"),
    ("raw_branchstats_override", "BRANCHSTATS 등록지국 보정", "BRANCHSTATS_OVERRIDE"),
)

LARGE_RAW_TABLE_SPECS = (
    ("raw_rep_total_headcount", "REP_AMOUNTS 그룹별 총인원", "REP_AMOUNTS"),
    ("raw_rep_amounts", "REP_AMOUNTS 개인 금액 상세", "REP_AMOUNTS"),
    ("raw_member_amounts", "MEMBER_AMOUNTS 회원 금액 상세", "MEMBER_AMOUNTS"),
)


def build_raw_dashboard_frames(bundle: RawDashboardBundle) -> dict[str, "pd.DataFrame"]:
    """Normalize every non-large source object into lossless tabular frames."""
    rows: dict[str, list[dict[str, Any]]] = {
        key: [] for key, _label, _source in STANDARD_RAW_TABLE_SPECS
    }
    sequence_keys = {
        "categories",
        "daily_series",
        "bizday_series",
        "member_series",
        "branch_bins_month",
    }

    for month_key, month_data in _iter_month_items(bundle.agg):
        month_meta = {
            key: value for key, value in month_data.items() if key not in sequence_keys
        }
        rows["raw_agg_months"].append(
            _flatten_mapping({"month_key": month_key, **month_meta})
        )
        for position, category in enumerate(_coerce_list(month_data.get("categories")), start=1):
            rows["raw_agg_categories"].append(
                {"month_key": month_key, "category_order": position, "category": category}
            )
        _append_flat_records(
            rows["raw_agg_daily_series"], month_key, month_data.get("daily_series")
        )
        _append_flat_records(
            rows["raw_agg_bizday_series"], month_key, month_data.get("bizday_series")
        )
        for category, amount in _coerce_float_map(
            month_data.get("category_totals_manwon")
        ).items():
            rows["raw_agg_category_totals"].append(
                {"month_key": month_key, "category": category, "total_manwon": amount}
            )
        _append_named_metrics(
            rows["raw_agg_group_stats"],
            month_key,
            "group",
            month_data.get("group_stats") or month_data.get("group"),
        )
        _append_flat_records(
            rows["raw_agg_member_series"], month_key, month_data.get("member_series")
        )
        _append_named_metrics(
            rows["raw_agg_member_status_counts"],
            month_key,
            "member_type",
            month_data.get("member_status_counts"),
            scalar_column="count",
        )
        _append_named_metrics(
            rows["raw_agg_member_summary"],
            month_key,
            "member_type",
            month_data.get("member_summary"),
        )
        for bin_index, count in enumerate(
            _coerce_list(month_data.get("branch_bins_month")), start=1
        ):
            rows["raw_agg_branch_bins_month"].append(
                {
                    "month_key": month_key,
                    "bin_index": bin_index,
                    "branch_bin": _branch_bin_label(bundle.bin_labels, bin_index),
                    "branch_count": count,
                }
            )
        projection = month_data.get("projection")
        if isinstance(projection, list):
            _append_flat_records(rows["raw_agg_projection"], month_key, projection)
        else:
            _append_single_mapping(rows["raw_agg_projection"], month_key, projection)
        _append_single_mapping(
            rows["raw_agg_projection_method"],
            month_key,
            month_data.get("projection_method"),
        )

    comp = bundle.comp or {}
    for position, month_key in enumerate(_coerce_list(comp.get("months")), start=1):
        rows["raw_comp_months"].append(
            {"month_order": position, "month_key": month_key}
        )
    for position, group in enumerate(_coerce_list(comp.get("groups")), start=1):
        rows["raw_comp_groups"].append({"group_order": position, "group": group})
    _append_flat_records(rows["raw_comp_rows"], None, comp.get("rows"))
    _append_single_mapping(rows["raw_comp_corr"], None, comp.get("corr"))

    actv = bundle.actv or {}
    actv_metrics = {
        key: value
        for key, value in actv.items()
        if key not in {"coef", "rows", "current"} and not isinstance(value, (dict, list))
    }
    if actv_metrics:
        rows["raw_actv_metrics"].append(_flatten_mapping(actv_metrics))
    _append_single_mapping(rows["raw_actv_coef"], None, actv.get("coef"))
    _append_flat_records(rows["raw_actv_rows"], None, actv.get("rows"))
    _append_single_mapping(rows["raw_actv_current"], None, actv.get("current"))

    for month_key, month_data in (bundle.branchstats or {}).items():
        if not isinstance(month_data, dict):
            continue
        month_meta = {
            key: value for key, value in month_data.items() if key != "snapshots"
        }
        rows["raw_branchstats_months"].append(
            _flatten_mapping({"month_key": month_key, **month_meta})
        )
        snapshots = month_data.get("snapshots")
        if not isinstance(snapshots, dict):
            continue
        for snapshot_date, snapshot in snapshots.items():
            if not isinstance(snapshot, dict):
                continue
            snapshot_meta = {
                key: value
                for key, value in snapshot.items()
                if key not in {"branch_bins_count", "branch_bins_revenue_manwon"}
            }
            rows["raw_branchstats_snapshots"].append(
                _flatten_mapping(
                    {"month_key": month_key, "snapshot_date": snapshot_date, **snapshot_meta}
                )
            )
            counts = _coerce_list(snapshot.get("branch_bins_count"))
            revenues = _coerce_list(snapshot.get("branch_bins_revenue_manwon"))
            for offset in range(max(len(counts), len(revenues))):
                bin_index = offset + 1
                rows["raw_branchstats_bins"].append(
                    {
                        "month_key": month_key,
                        "snapshot_date": snapshot_date,
                        "bin_index": bin_index,
                        "branch_bin": _branch_bin_label(bundle.bin_labels, bin_index),
                        "branch_count": counts[offset] if offset < len(counts) else None,
                        "revenue_manwon": revenues[offset] if offset < len(revenues) else None,
                    }
                )

    for month_key, value in (bundle.branchstats_override or {}).items():
        rows["raw_branchstats_override"].append(
            {"month_key": month_key, "total_registered_branches": value}
        )

    return {key: _records_to_frame(value) for key, value in rows.items()}


def build_raw_table_inventory(
    bundle: RawDashboardBundle,
    frames: dict[str, "pd.DataFrame"],
) -> "pd.DataFrame":
    """Return the complete raw-table catalog with eager/lazy loading status."""
    import pandas as pd

    inventory: list[dict[str, Any]] = []
    for table_key, label, source_object in STANDARD_RAW_TABLE_SPECS:
        frame = frames.get(table_key, pd.DataFrame())
        inventory.append(
            {
                "table_key": table_key,
                "table_name": label,
                "source_object": source_object,
                "row_count": int(frame.shape[0]),
                "column_count": int(frame.shape[1]),
                "loading_mode": "기본 로딩",
                "status": "준비됨" if not frame.empty else "원천 행 없음",
            }
        )

    large_presence = {
        "REP_AMOUNTS": bundle.rep_amounts_included,
        "MEMBER_AMOUNTS": bundle.member_amounts_included,
    }
    for table_key, label, source_object in LARGE_RAW_TABLE_SPECS:
        included = bool(large_presence.get(source_object))
        inventory.append(
            {
                "table_key": table_key,
                "table_name": label,
                "source_object": source_object,
                "row_count": None,
                "column_count": None,
                "loading_mode": "선택 시 지연 로딩",
                "status": "선택 가능" if included else "원천 객체 없음",
            }
        )
    return pd.DataFrame(inventory)


def extract_large_raw_table(html_text: str, table_key: str) -> "pd.DataFrame":
    """Materialize one explicitly selected REP/MEMBER amount table."""
    if table_key not in {item[0] for item in LARGE_RAW_TABLE_SPECS}:
        raise KeyError(f"Unknown large raw table: {table_key}")

    object_name = "MEMBER_AMOUNTS" if table_key == "raw_member_amounts" else "REP_AMOUNTS"
    value = extract_js_value(html_text, object_name)
    if isinstance(value, list):
        if table_key == "raw_rep_total_headcount":
            return _records_to_frame([])
        generic_rows = [item if isinstance(item, dict) else {"value": item} for item in value]
        return _records_to_frame(generic_rows)
    if not isinstance(value, dict):
        raise RawDashboardParseError(f"JavaScript value {object_name} has an unsupported shape.")

    rows: list[dict[str, Any]] = []
    if table_key == "raw_rep_total_headcount":
        for month_key, month_data in value.items():
            if not isinstance(month_data, dict):
                continue
            for group, count in (month_data.get("total_headcount") or {}).items():
                rows.append({"month_key": month_key, "group": group, "headcount": count})
        return _records_to_frame(rows)

    if table_key == "raw_rep_amounts":
        for month_key, month_data in value.items():
            if not isinstance(month_data, dict):
                continue
            for snapshot_date, snapshot in (month_data.get("snapshots") or {}).items():
                if not isinstance(snapshot, dict):
                    continue
                for group, amounts in snapshot.items():
                    for amount_index, amount in enumerate(_coerce_list(amounts), start=1):
                        rows.append(
                            {
                                "month_key": month_key,
                                "snapshot_date": snapshot_date,
                                "group": group,
                                "amount_index": amount_index,
                                "amount_manwon": amount,
                            }
                        )
        return _records_to_frame(rows)

    for month_key, snapshots in value.items():
        if not isinstance(snapshots, dict):
            continue
        for snapshot_date, snapshot in snapshots.items():
            if not isinstance(snapshot, dict):
                continue
            for member_type, amounts in snapshot.items():
                for amount_index, amount in enumerate(_coerce_list(amounts), start=1):
                    rows.append(
                        {
                            "month_key": month_key,
                            "snapshot_date": snapshot_date,
                            "member_type": member_type,
                            "amount_index": amount_index,
                            "amount_manwon": amount,
                        }
                    )
    return _records_to_frame(rows)


def _append_flat_records(
    target: list[dict[str, Any]],
    month_key: str | None,
    value: Any,
) -> None:
    for item in _coerce_list(value):
        record = item if isinstance(item, dict) else {"value": item}
        if month_key is not None:
            record = {"month_key": month_key, **record}
        target.append(_flatten_mapping(record))


def _append_named_metrics(
    target: list[dict[str, Any]],
    month_key: str,
    name_column: str,
    value: Any,
    *,
    scalar_column: str = "value",
) -> None:
    if isinstance(value, dict):
        for name, metrics in value.items():
            record: dict[str, Any] = {"month_key": month_key, name_column: name}
            if isinstance(metrics, dict):
                record.update(metrics)
            else:
                record[scalar_column] = metrics
            target.append(_flatten_mapping(record))
    elif isinstance(value, list):
        _append_flat_records(target, month_key, value)


def _append_single_mapping(
    target: list[dict[str, Any]],
    month_key: str | None,
    value: Any,
) -> None:
    if not isinstance(value, dict):
        return
    record = dict(value)
    if month_key is not None:
        record = {"month_key": month_key, **record}
    target.append(_flatten_mapping(record))


def _flatten_mapping(mapping: dict[str, Any], prefix: str = "") -> dict[str, Any]:
    flattened: dict[str, Any] = {}
    for key, value in mapping.items():
        column = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flattened.update(_flatten_mapping(value, column))
        elif isinstance(value, list):
            flattened[column] = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            flattened[column] = value
    return flattened


def _records_to_frame(records: list[dict[str, Any]]) -> "pd.DataFrame":
    import pandas as pd

    return pd.DataFrame(records)


def _branch_bin_label(labels: list[str], bin_index: int) -> str:
    if 1 <= bin_index <= len(labels):
        return labels[bin_index - 1]
    return f"급간 {bin_index}"


def _extract_assignment_literal(html_text: str, object_name: str) -> str:
    pattern = _DECLARATION_TEMPLATE.format(name=re.escape(object_name))
    match = re.search(pattern, html_text)
    if match is None:
        raise KeyError(f"JavaScript value {object_name} was not found.")

    value_start = match.end()
    while value_start < len(html_text) and html_text[value_start].isspace():
        value_start += 1

    if value_start >= len(html_text) or html_text[value_start] not in "{[":
        raise RawDashboardParseError(
            f"JavaScript value {object_name} is not an object or array literal."
        )

    value_end = _find_matching_delimiter(html_text, value_start)
    return html_text[value_start : value_end + 1]


def _extract_object_literal(html_text: str, object_name: str) -> str:
    """Backward-compatible private wrapper for object-only callers."""
    literal = _extract_assignment_literal(html_text, object_name)
    if not literal.startswith("{"):
        raise RawDashboardParseError(f"JavaScript object {object_name} is not an object literal.")
    return literal


def _has_js_assignment(html_text: str, object_name: str) -> bool:
    pattern = _DECLARATION_TEMPLATE.format(name=re.escape(object_name))
    return re.search(pattern, html_text) is not None


def _find_matching_brace(text: str, start: int) -> int:
    if start >= len(text) or text[start] != "{":
        raise RawDashboardParseError("Object literal must start with an opening brace.")
    return _find_matching_delimiter(text, start)


def _find_matching_delimiter(text: str, start: int) -> int:
    opener = text[start] if start < len(text) else ""
    closer = {"{": "}", "[": "]"}.get(opener)
    if closer is None:
        raise RawDashboardParseError("JavaScript literal must start with { or [.")

    depth = 0
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False

    for index in range(start, len(text)):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""

        if line_comment:
            if char in "\r\n":
                line_comment = False
            continue
        if block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
            continue
        if quote is not None:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue

        if char == "/" and next_char == "/":
            line_comment = True
            continue
        if char == "/" and next_char == "*":
            block_comment = True
            continue
        if char in ("'", '"', "`"):
            quote = char
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return index

    raise RawDashboardParseError("JavaScript literal delimiters were not balanced.")


def _normalize_js_object_literal(literal: str) -> str:
    no_comments = _strip_js_comments(literal)
    strings_normalized = _normalize_strings(no_comments)
    keys_quoted = _quote_unquoted_keys(strings_normalized)
    literals_replaced = _replace_js_literals(keys_quoted)
    return _remove_trailing_commas(literals_replaced)


def _strip_js_comments(text: str) -> str:
    output: list[str] = []
    quote: str | None = None
    escaped = False
    line_comment = False
    block_comment = False
    index = 0

    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""

        if line_comment:
            if char in "\r\n":
                line_comment = False
                output.append(char)
            index += 1
            continue
        if block_comment:
            if char == "*" and next_char == "/":
                block_comment = False
                index += 2
            else:
                index += 1
            continue
        if quote is not None:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue

        if char == "/" and next_char == "/":
            line_comment = True
            index += 2
            continue
        if char == "/" and next_char == "*":
            block_comment = True
            index += 2
            continue
        if char in ("'", '"', "`"):
            quote = char
        output.append(char)
        index += 1

    return "".join(output)


def _normalize_strings(text: str) -> str:
    output: list[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char in ("'", '"', "`"):
            normalized, index = _consume_js_string(text, index)
            output.append(normalized)
            continue
        output.append(char)
        index += 1
    return "".join(output)


def _consume_js_string(text: str, start: int) -> tuple[str, int]:
    quote = text[start]
    chars: list[str] = []
    index = start + 1

    while index < len(text):
        char = text[index]
        if char == quote:
            return json.dumps("".join(chars), ensure_ascii=False), index + 1
        if char != "\\":
            chars.append(char)
            index += 1
            continue

        if index + 1 >= len(text):
            raise RawDashboardParseError("String literal ended after an escape marker.")
        escaped = text[index + 1]
        if escaped in {"'", '"', "\\", "/"}:
            chars.append(escaped)
            index += 2
        elif escaped == "b":
            chars.append("\b")
            index += 2
        elif escaped == "f":
            chars.append("\f")
            index += 2
        elif escaped == "n":
            chars.append("\n")
            index += 2
        elif escaped == "r":
            chars.append("\r")
            index += 2
        elif escaped == "t":
            chars.append("\t")
            index += 2
        elif escaped == "u":
            chars.append(_decode_hex_escape(text, index + 2, 4))
            index += 6
        elif escaped == "x":
            chars.append(_decode_hex_escape(text, index + 2, 2))
            index += 4
        elif escaped in {"\r", "\n"}:
            index += 2
        else:
            chars.append(escaped)
            index += 2

    raise RawDashboardParseError("String literal was not closed.")


def _decode_hex_escape(text: str, start: int, length: int) -> str:
    token = text[start : start + length]
    if len(token) != length or not re.fullmatch(r"[0-9a-fA-F]+", token):
        raise RawDashboardParseError("String literal contains an invalid hex escape.")
    return chr(int(token, 16))


def _quote_unquoted_keys(text: str) -> str:
    output: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False
    expecting_key = False

    while index < len(text):
        char = text[index]
        if quote is not None:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue

        if char == '"':
            quote = char
            output.append(char)
            index += 1
            continue

        if char in "{,":
            expecting_key = True
            output.append(char)
            index += 1
            continue

        if expecting_key:
            whitespace_start = index
            while index < len(text) and text[index].isspace():
                index += 1
            output.append(text[whitespace_start:index])
            if index >= len(text):
                continue

            ident_start = index
            if _is_ident_start(text[index]):
                index += 1
                while index < len(text) and _is_ident_part(text[index]):
                    index += 1
                ident = text[ident_start:index]
                after_ident = index
                while after_ident < len(text) and text[after_ident].isspace():
                    after_ident += 1
                if after_ident < len(text) and text[after_ident] == ":":
                    output.append(json.dumps(ident))
                    index = after_ident
                    expecting_key = False
                    continue
                output.append(ident)
                expecting_key = False
                continue

            expecting_key = False
            continue

        output.append(char)
        if not char.isspace():
            expecting_key = False
        index += 1

    return "".join(output)


def _replace_js_literals(text: str) -> str:
    replacements = {
        "undefined": "null",
        "NaN": "null",
        "Infinity": "null",
    }
    output: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False

    while index < len(text):
        char = text[index]
        if quote is not None:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue

        if char == '"':
            quote = char
            output.append(char)
            index += 1
            continue

        matched = False
        for literal, replacement in replacements.items():
            if (
                text.startswith(literal, index)
                and _literal_boundary(text, index - 1)
                and _literal_boundary(text, index + len(literal))
            ):
                output.append(replacement)
                index += len(literal)
                matched = True
                break
        if matched:
            continue

        output.append(char)
        index += 1

    return "".join(output)


def _remove_trailing_commas(text: str) -> str:
    output: list[str] = []
    index = 0
    quote: str | None = None
    escaped = False

    while index < len(text):
        char = text[index]
        if quote is not None:
            output.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            index += 1
            continue

        if char == '"':
            quote = char
            output.append(char)
            index += 1
            continue

        if char == ",":
            lookahead = index + 1
            while lookahead < len(text) and text[lookahead].isspace():
                lookahead += 1
            if lookahead < len(text) and text[lookahead] in "}]":
                index += 1
                continue

        output.append(char)
        index += 1

    return "".join(output)


def _is_ident_start(char: str) -> bool:
    return char.isalpha() or char in {"_", "$"}


def _is_ident_part(char: str) -> bool:
    return char.isalnum() or char in {"_", "$"}


def _literal_boundary(text: str, index: int) -> bool:
    if index < 0 or index >= len(text):
        return True
    return not _is_ident_part(text[index])


def _build_month_data(
    agg: dict[str, Any],
) -> tuple[list[RawDashboardMonthSummary], list[RawDashboardBizdayRow]]:
    summaries: list[RawDashboardMonthSummary] = []
    rows: list[RawDashboardBizdayRow] = []

    for month_key, month_data in _iter_month_items(agg):
        bizday_series = _coerce_list(month_data.get("bizday_series") or month_data.get("bizdays"))
        category_totals_manwon = _coerce_float_map(
            month_data.get("category_totals_manwon")
            or month_data.get("category_totals")
            or month_data.get("category_amounts_manwon")
        )
        category_totals_eok = {
            category: _manwon_to_eok(amount)
            for category, amount in category_totals_manwon.items()
        }
        categories = _coerce_str_list(month_data.get("categories")) or list(category_totals_manwon)
        year, month = _extract_year_month(month_key, month_data)

        month_rows: list[RawDashboardBizdayRow] = []
        for position, raw_row in enumerate(bizday_series, start=1):
            if not isinstance(raw_row, dict):
                continue
            idx = _to_int(_pick(raw_row, "idx", "bizday_idx", "business_day_no")) or position
            total_cum_manwon = _to_float(
                _pick(raw_row, "total_cum_manwon", "total_cum", "cum_manwon")
            )
            row = RawDashboardBizdayRow(
                month_key=month_key,
                idx=idx,
                date=_to_optional_str(_pick(raw_row, "date", "base_date", "sales_date")),
                total_cum_manwon=total_cum_manwon,
                total_cum_eok=_manwon_to_eok(total_cum_manwon),
                active_branch_count=_to_int(
                    _pick(raw_row, "active_branch_count", "active_branches", "branch_count")
                ),
                member_cum=_to_int(_pick(raw_row, "member_cum", "member_cnt", "member_count")),
            )
            rows.append(row)
            month_rows.append(row)

        active_branch_count = _to_int(
            _pick(month_data, "active_branch_count", "active_branches", "branch_count")
        )
        if active_branch_count is None and month_rows:
            active_branch_count = month_rows[-1].active_branch_count

        total_purchasing_members = _to_int(
            _pick(month_data, "total_purchasing_members", "member_cnt", "member_count")
        )
        if total_purchasing_members is None and month_rows:
            total_purchasing_members = month_rows[-1].member_cum

        summaries.append(
            RawDashboardMonthSummary(
                month_key=month_key,
                year=year,
                month=month,
                categories=categories,
                category_totals_manwon=category_totals_manwon,
                category_totals_eok=category_totals_eok,
                bizday_count=len(month_rows),
                active_branch_count=active_branch_count,
                total_purchasing_members=total_purchasing_members,
            )
        )

    return summaries, rows


def _iter_month_items(agg: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    months = agg.get("months")
    if isinstance(months, dict):
        return [
            (str(key), value)
            for key, value in months.items()
            if isinstance(value, dict)
        ]
    if isinstance(months, list):
        return [
            (str(item.get("month_key") or item.get("key") or index + 1), item)
            for index, item in enumerate(months)
            if isinstance(item, dict)
        ]

    keyed_months = [
        (str(key), value)
        for key, value in agg.items()
        if isinstance(value, dict) and _looks_like_month_key(str(key))
    ]
    if keyed_months:
        return keyed_months

    month_key = _to_optional_str(agg.get("month_key")) or "unknown"
    return [(month_key, agg)]


def _looks_like_month_key(value: str) -> bool:
    return re.fullmatch(r"\d{2,4}[.-]\d{1,2}", value) is not None


def _extract_year_month(month_key: str, month_data: dict[str, Any]) -> tuple[int | None, int | None]:
    year = _to_int(month_data.get("year"))
    month = _to_int(month_data.get("month"))
    if year is not None and month is not None:
        return year, month

    match = re.fullmatch(r"(\d{2,4})[.-](\d{1,2})", month_key)
    if match is None:
        return year, month

    raw_year = int(match.group(1))
    if year is None:
        year = 2000 + raw_year if raw_year < 100 else raw_year
    if month is None:
        month = int(match.group(2))
    return year, month


def _extract_activity_projection(
    agg: dict[str, Any],
    actv: dict[str, Any] | None,
) -> RawDashboardActivityProjection | None:
    candidate: tuple[str | None, dict[str, Any]] | None = None

    if isinstance(actv, dict):
        method = actv.get("projection_method") or actv.get("projection") or actv
        if isinstance(method, dict):
            candidate = (_to_optional_str(method.get("month_key")), method)

    for month_key, month_data in _iter_month_items(agg):
        method = month_data.get("projection_method")
        if isinstance(method, dict):
            candidate = (month_key, method)

    if candidate is None:
        return None

    month_key, method = candidate
    estimate_eok, estimate_source = _pick_activity_estimate(method)
    method_warnings = method.get("warnings") or []
    if isinstance(method_warnings, str):
        method_warnings = [method_warnings]
    elif not isinstance(method_warnings, list):
        method_warnings = []

    return RawDashboardActivityProjection(
        month_key=_to_optional_str(method.get("month_key")) or month_key,
        estimate_eok=estimate_eok,
        estimate_source=estimate_source,
        model_type=_to_optional_str(method.get("type") or method.get("model_type")),
        insample_r2=_to_float(method.get("activity_model_insample_r2")),
        loo_r2=_to_float(method.get("activity_model_loo_r2")),
        loo_mape_pct=_to_float(method.get("activity_model_loo_mape_pct")),
        warnings=[str(item) for item in method_warnings],
    )


def _pick_activity_estimate(method: dict[str, Any]) -> tuple[float | None, str | None]:
    for key in ("team_adopted_estimate_eok", "est_month_total_eok"):
        value = _to_float(method.get(key))
        if value is not None:
            return value, key

    low = _to_float(method.get("field_pipeline_estimate_low_eok"))
    high = _to_float(method.get("field_pipeline_estimate_high_eok"))
    if low is not None and high is not None:
        return (low + high) / 2, "field_pipeline_estimate_midpoint_eok"
    if low is not None:
        return low, "field_pipeline_estimate_low_eok"
    if high is not None:
        return high, "field_pipeline_estimate_high_eok"
    return None, None


def _build_bizday_category_rows(agg: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for month_key, month_data in _iter_month_items(agg):
        for raw_row in _coerce_list(month_data.get("bizday_series") or month_data.get("bizdays")):
            if not isinstance(raw_row, dict):
                continue
            idx = _to_int(_pick(raw_row, "idx", "bizday_idx", "business_day_no"))
            category_values = _coerce_float_map(
                raw_row.get("category_cum_manwon")
                or raw_row.get("cat_cum_manwon")
                or raw_row.get("category_totals_manwon")
                or raw_row.get("categories_manwon")
            )
            for category, amount in category_values.items():
                rows.append(
                    {
                        "month_key": month_key,
                        "idx": idx,
                        "category": category,
                        "cum_manwon": amount,
                        "cum_eok": _manwon_to_eok(amount),
                    }
                )
    return rows


def _build_group_rows(agg: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for month_key, month_data in _iter_month_items(agg):
        bizday_found = False
        for position, raw_row in enumerate(
            _coerce_list(month_data.get("bizday_series") or month_data.get("bizdays")),
            start=1,
        ):
            if not isinstance(raw_row, dict):
                continue
            group_value = raw_row.get("group") or raw_row.get("group_stats")
            if not isinstance(group_value, (dict, list)):
                continue
            bizday_found = True
            idx = _to_int(_pick(raw_row, "idx", "bizday_idx", "business_day_no")) or position
            if isinstance(group_value, dict):
                for group_name, metrics in group_value.items():
                    row = {"month_key": month_key, "idx": idx, "group": group_name}
                    if isinstance(metrics, dict):
                        row.update(metrics)
                    else:
                        row["value"] = metrics
                    rows.append(row)
            else:
                for item in group_value:
                    if isinstance(item, dict):
                        rows.append({"month_key": month_key, "idx": idx, **item})
        if bizday_found:
            continue

        group_value = month_data.get("group") or month_data.get("group_stats")
        if isinstance(group_value, dict):
            for group_name, metrics in group_value.items():
                row = {"month_key": month_key, "group": group_name}
                if isinstance(metrics, dict):
                    row.update(metrics)
                else:
                    row["value"] = metrics
                rows.append(row)
        elif isinstance(group_value, list):
            for item in group_value:
                if isinstance(item, dict):
                    row = {"month_key": month_key}
                    row.update(item)
                    rows.append(row)
    return rows


def _build_member_rows(
    agg: dict[str, Any],
    summaries: list[RawDashboardMonthSummary],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    summary_by_key = {summary.month_key: summary for summary in summaries}
    for month_key, month_data in _iter_month_items(agg):
        bizday_found = False
        for position, raw_row in enumerate(
            _coerce_list(month_data.get("bizday_series") or month_data.get("bizdays")),
            start=1,
        ):
            if not isinstance(raw_row, dict):
                continue
            member_counts = raw_row.get("member_cnt")
            member_amounts = raw_row.get("member_amt_manwon")
            if not isinstance(member_counts, dict) and not isinstance(member_amounts, dict):
                continue
            bizday_found = True
            idx = _to_int(_pick(raw_row, "idx", "bizday_idx", "business_day_no")) or position
            member_types = list(
                dict.fromkeys(
                    [
                        *list(member_counts.keys() if isinstance(member_counts, dict) else []),
                        *list(member_amounts.keys() if isinstance(member_amounts, dict) else []),
                    ]
                )
            )
            for member_type in member_types:
                rows.append(
                    {
                        "month_key": month_key,
                        "idx": idx,
                        "date": _to_optional_str(raw_row.get("date")),
                        "member_type": str(member_type),
                        "member_cnt": _to_int(
                            member_counts.get(member_type)
                            if isinstance(member_counts, dict)
                            else None
                        ),
                        "member_amt_manwon": _to_float(
                            member_amounts.get(member_type)
                            if isinstance(member_amounts, dict)
                            else None
                        ),
                    }
                )
        if bizday_found:
            continue

        member_summary = month_data.get("member_summary")
        if isinstance(member_summary, dict) and any(
            isinstance(value, dict) for value in member_summary.values()
        ):
            for member_type, metrics in member_summary.items():
                if not isinstance(metrics, dict):
                    continue
                rows.append(
                    {
                        "month_key": month_key,
                        "member_type": str(member_type),
                        "member_cnt": _to_int(_pick(metrics, "count", "member_cnt")),
                        "member_amt_manwon": _to_float(
                            _pick(metrics, "amount_manwon", "member_amt_manwon")
                        ),
                        "share": _to_float(metrics.get("share")),
                    }
                )
            continue

        member_amt_manwon = _to_float(_pick(month_data, "member_amt_manwon", "member_amount_manwon"))
        summary = summary_by_key.get(month_key)
        rows.append(
            {
                "month_key": month_key,
                "member_cnt": _to_int(_pick(month_data, "member_cnt", "member_count")),
                "total_purchasing_members": (
                    summary.total_purchasing_members if summary is not None else None
                ),
                "member_amt_manwon": member_amt_manwon,
                "member_amt_eok": _manwon_to_eok(member_amt_manwon),
            }
        )
    return rows


def _build_branch_bin_rows(
    agg: dict[str, Any],
    bin_labels: list[str] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    labels = bin_labels or DEFAULT_BRANCH_BIN_LABELS
    for month_key, month_data in _iter_month_items(agg):
        bizday_found = False
        for position, raw_row in enumerate(
            _coerce_list(month_data.get("bizday_series") or month_data.get("bizdays")),
            start=1,
        ):
            if not isinstance(raw_row, dict):
                continue
            branch_bins = raw_row.get("branch_bins")
            if not isinstance(branch_bins, (dict, list)):
                continue
            bizday_found = True
            idx = _to_int(_pick(raw_row, "idx", "bizday_idx", "business_day_no")) or position
            if isinstance(branch_bins, dict):
                for bin_name, value in branch_bins.items():
                    row = {"month_key": month_key, "idx": idx, "bin": bin_name}
                    if isinstance(value, dict):
                        row.update(value)
                    else:
                        row["branch_count"] = value
                    rows.append(row)
            else:
                for offset, item in enumerate(branch_bins, start=1):
                    if isinstance(item, dict):
                        rows.append({"month_key": month_key, "idx": idx, **item})
                    else:
                        rows.append(
                            {
                                "month_key": month_key,
                                "idx": idx,
                                "bin": _branch_bin_label(labels, offset),
                                "branch_count": item,
                            }
                        )
        if bizday_found:
            continue

        branch_bins = (
            month_data.get("branch_bins")
            or month_data.get("branchstats")
            or month_data.get("branch_bins_month")
        )
        if isinstance(branch_bins, dict):
            for bin_name, value in branch_bins.items():
                row = {"month_key": month_key, "bin": bin_name}
                if isinstance(value, dict):
                    row.update(value)
                else:
                    row["value"] = value
                rows.append(row)
        elif isinstance(branch_bins, list):
            for offset, item in enumerate(branch_bins, start=1):
                if isinstance(item, dict):
                    row = {"month_key": month_key}
                    row.update(item)
                    rows.append(row)
                else:
                    rows.append(
                        {
                            "month_key": month_key,
                            "bin": _branch_bin_label(labels, offset),
                            "branch_count": item,
                        }
                    )
    return rows


def _coerce_float_map(value: Any) -> dict[str, float]:
    if isinstance(value, dict):
        result: dict[str, float] = {}
        for key, raw_amount in value.items():
            amount = _to_float(raw_amount)
            if amount is not None:
                result[str(key)] = amount
        return result

    if isinstance(value, list):
        result = {}
        for item in value:
            if not isinstance(item, dict):
                continue
            category = _to_optional_str(_pick(item, "category", "name", "label"))
            amount = _to_float(_pick(item, "amount_manwon", "total_manwon", "value"))
            if category is not None and amount is not None:
                result[category] = amount
        return result

    return {}


def _coerce_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _coerce_str_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _pick(mapping: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in mapping:
            return mapping[key]
    return None


def _to_float(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "")
        if not cleaned:
            return None
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _to_int(value: Any) -> int | None:
    number = _to_float(value)
    if number is None:
        return None
    return int(number)


def _to_optional_str(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _manwon_to_eok(value: float | None) -> float | None:
    if value is None:
        return None
    return value / 10000
