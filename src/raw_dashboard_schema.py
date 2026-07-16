"""Dataclasses for raw HTM dashboard import results."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RawDashboardWarning:
    code: str
    message: str
    object_name: str | None = None


@dataclass
class RawDashboardBizdayRow:
    month_key: str
    idx: int
    date: str | None
    total_cum_manwon: float | None
    total_cum_eok: float | None
    active_branch_count: int | None
    member_cum: int | None


@dataclass
class RawDashboardMonthSummary:
    month_key: str
    year: int | None
    month: int | None
    categories: list[str]
    category_totals_manwon: dict[str, float]
    category_totals_eok: dict[str, float]
    bizday_count: int
    active_branch_count: int | None
    total_purchasing_members: int | None


@dataclass
class RawDashboardActivityProjection:
    month_key: str | None
    estimate_eok: float | None
    estimate_source: str | None
    model_type: str | None
    insample_r2: float | None
    loo_r2: float | None
    loo_mape_pct: float | None
    warnings: list[str]


@dataclass(repr=False)
class RawDashboardBundle:
    source_name: str | None
    objects_found: list[str]
    warnings: list[RawDashboardWarning]
    agg: dict[str, Any]
    comp: dict[str, Any] | None
    actv: dict[str, Any] | None
    branchstats: dict[str, Any] | None
    branchstats_override: dict[str, Any] | None
    bin_labels: list[str]
    rep_amounts_included: bool
    member_amounts_included: bool
    month_summaries: list[RawDashboardMonthSummary]
    bizday_rows: list[RawDashboardBizdayRow]
    activity_projection: RawDashboardActivityProjection | None

    def __repr__(self) -> str:
        return (
            "RawDashboardBundle("
            f"source_name={self.source_name!r}, "
            f"objects_found={self.objects_found!r}, "
            f"warnings={len(self.warnings)}, "
            f"agg_keys={len(self.agg)}, "
            f"comp_included={self.comp is not None}, "
            f"actv_included={self.actv is not None}, "
            f"branchstats_included={self.branchstats is not None}, "
            f"branchstats_override_included={self.branchstats_override is not None}, "
            f"bin_labels={len(self.bin_labels)}, "
            f"rep_amounts_included={self.rep_amounts_included}, "
            f"member_amounts_included={self.member_amounts_included}, "
            f"month_summaries={len(self.month_summaries)}, "
            f"bizday_rows={len(self.bizday_rows)}, "
            f"activity_projection={self.activity_projection is not None}"
            ")"
        )
