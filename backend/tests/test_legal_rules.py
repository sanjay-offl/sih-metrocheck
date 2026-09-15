"""Tests for the rule data and parsing helpers."""

import pytest

from app.utils.legal_rules import (
    LEGAL_METROLOGY_SOURCE,
    MANDATORY_DECLARATIONS,
    canonical_unit,
    get_all_rules,
    get_required_font_size,
    parse_net_quantity,
    quantity_to_base,
)


@pytest.mark.parametrize(
    ("quantity_g", "expected_mm"),
    [
        (0, 1.0),
        (100, 1.0),
        (200, 2.0),
        (499.9, 2.0),
        (500, 4.0),
        (999, 4.0),
        (1000, 6.0),
        (25000, 6.0),
    ],
)
def test_font_size_thresholds(quantity_g: float, expected_mm: float) -> None:
    assert get_required_font_size(quantity_g)["min_height_mm"] == expected_mm


@pytest.mark.parametrize(
    ("text", "expected_numeric", "expected_unit"),
    [
        ("500 g", 500.0, "g"),
        ("Net Qty: 1 kg", 1.0, "kg"),
        ("750ml", 750.0, "ml"),
        ("1.5 L", 1.5, "L"),
        ("2 ltrs", 2.0, "L"),
        ("200 GMS", 200.0, "g"),
        ("10 pieces", 10.0, "pcs"),
        ("no quantity here", None, None),
        (None, None, None),
    ],
)
def test_parse_net_quantity(text, expected_numeric, expected_unit) -> None:
    numeric, unit = parse_net_quantity(text)
    assert numeric == expected_numeric
    assert unit == expected_unit


@pytest.mark.parametrize(
    ("unit", "expected"),
    [("GMS", "g"), ("Kg", "kg"), ("ltr", "L"), ("PIECES", "pcs"), ("nos", "nos")],
)
def test_canonical_unit(unit: str, expected: str) -> None:
    assert canonical_unit(unit) == expected


def test_quantity_to_base_converts_kilograms() -> None:
    assert quantity_to_base(1.5, "kg") == 1500.0
    assert quantity_to_base(500, "g") == 500.0
    assert quantity_to_base(None, "kg") is None


def test_rule_catalogue_is_complete() -> None:
    rules = get_all_rules()
    assert len(rules) == len(MANDATORY_DECLARATIONS) == 8
    assert all(rule["rule"] and rule["severity"] for rule in rules)
    severities = {rule["severity"] for rule in rules}
    assert severities <= {"critical", "major", "minor"}


def test_rule_catalogue_has_official_source() -> None:
    assert LEGAL_METROLOGY_SOURCE["publisher"] == "Department of Consumer Affairs, Ministry of Consumer Affairs, Food & Public Distribution"
    assert LEGAL_METROLOGY_SOURCE["url"] == "https://consumeraffairs.gov.in/pages/legal-metrology-act"
