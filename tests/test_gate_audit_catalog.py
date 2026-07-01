from pathlib import Path

import yaml


REQUIRED_GATE_IDS = {
    "G09",
    "G10",
    "G12",
    "G13",
    "G15",
    "G18",
    "ALL",
}

REQUIRED_FIELDS = {
    "gate_id",
    "gate_name",
    "phase",
    "required_files",
    "pytest_targets",
    "required_keywords",
    "forbidden_patterns",
    "warning_keywords",
    "pass_conditions",
}

COMMON_FORBIDDEN_PATTERNS = {
    ".weekday(",
    "dt.weekday",
    "weekday(",
    "next_monday",
    "next_thursday",
    "day_name ==",
    "day_name in",
    "월요일",
    "목요일",
}


def _load_catalog() -> dict:
    root = Path(__file__).resolve().parents[1]
    catalog_path = root / "config" / "gate_audit_catalog.yaml"

    with catalog_path.open(encoding="utf-8") as catalog_file:
        catalog = yaml.safe_load(catalog_file)

    assert isinstance(catalog, dict)
    assert isinstance(catalog.get("gates"), list)
    return catalog


def test_gate_audit_catalog_loads() -> None:
    catalog = _load_catalog()

    assert catalog["gates"]


def test_required_gates_exist() -> None:
    catalog = _load_catalog()
    gate_ids = {gate["gate_id"] for gate in catalog["gates"]}

    assert REQUIRED_GATE_IDS <= gate_ids


def test_gate_ids_are_unique() -> None:
    catalog = _load_catalog()
    gate_ids = [gate["gate_id"] for gate in catalog["gates"]]

    assert len(gate_ids) == len(set(gate_ids))


def test_each_gate_has_required_fields_and_keywords() -> None:
    catalog = _load_catalog()

    for gate in catalog["gates"]:
        assert REQUIRED_FIELDS <= set(gate)
        assert gate["required_keywords"]


def test_each_gate_contains_common_forbidden_patterns() -> None:
    catalog = _load_catalog()

    for gate in catalog["gates"]:
        assert COMMON_FORBIDDEN_PATTERNS <= set(gate["forbidden_patterns"])
