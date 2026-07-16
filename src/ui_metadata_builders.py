"""Pure builders for user-facing UI definitions, guides, and glossary rows."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import pandas as pd


Definition = Mapping[str, object]
DefinitionMap = Mapping[str, Definition]
GlossaryGroups = Sequence[tuple[str, Mapping[object, object]]]
GuideMap = Mapping[str, Mapping[str, object]]


def build_visual_metric_definition_df(
    metric_columns: tuple[str, ...],
    *,
    definitions: DefinitionMap,
) -> pd.DataFrame:
    """Return chart-series definitions in the requested metric order."""
    rows = []
    for column in metric_columns:
        definition = definitions.get(column, {})
        rows.append(
            {
                "범례": definition.get("label", column),
                "단위": definition.get("unit", ""),
                "수치 의미": definition.get("definition", "정의가 등록되지 않은 수치입니다."),
            }
        )
    return pd.DataFrame(rows)


def build_visual_reading_guide(
    guide_key: str,
    *,
    guides: GuideMap,
) -> dict[str, object]:
    """Return a visual reading guide with stable fallback values."""
    guide = guides.get(guide_key, {})
    return {
        "title": guide.get("title", ""),
        "steps": tuple(guide.get("steps", ())),
        "decision": guide.get("decision", ""),
    }


def build_forecast_definition_df(*, definitions: DefinitionMap) -> pd.DataFrame:
    """Return F-model display definitions in their configured order."""
    return pd.DataFrame(
        [
            {
                "model": model_id,
                "name": definition["name"],
                "description": definition["description"],
                "formula": definition["formula"],
            }
            for model_id, definition in definitions.items()
        ]
    )


def build_provision_definition_df(*, definitions: DefinitionMap) -> pd.DataFrame:
    """Return P-strategy display definitions in their configured order."""
    return _build_strategy_definition_df(definitions)


def build_overachievement_definition_df(*, definitions: DefinitionMap) -> pd.DataFrame:
    """Return O-strategy display definitions in their configured order."""
    return _build_strategy_definition_df(definitions)


def build_neutral_definition_df(*, definitions: DefinitionMap) -> pd.DataFrame:
    """Return N-strategy display definitions in their configured order."""
    return _build_strategy_definition_df(definitions)


def build_report_glossary_df(*, groups: GlossaryGroups) -> pd.DataFrame:
    """Return glossary rows while preserving group and code order."""
    rows: list[dict[str, object]] = []
    for group, definitions in groups:
        for code, definition in definitions.items():
            rows.append(
                {
                    "구분": group,
                    "코드": str(code),
                    "정의": definition,
                }
            )
    return pd.DataFrame(rows)


def build_risk_definition_df(*, definitions: Mapping[str, object]) -> pd.DataFrame:
    """Return scenario-risk definitions in their configured order."""
    return pd.DataFrame(
        [
            {
                "risk_level": risk_level,
                "definition": definition,
            }
            for risk_level, definition in definitions.items()
        ]
    )


def _build_strategy_definition_df(definitions: DefinitionMap) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "strategy": strategy_id,
                "name": definition["name"],
                "description": definition["description"],
            }
            for strategy_id, definition in definitions.items()
        ]
    )
