"""Tests for the Legal Metrology compliance engine."""

from app.services.compliance_engine import (
    detect_misleading_claims,
    run_compliance_check,
)


def compliant_payload() -> dict:
    """A label that satisfies every evaluated rule."""
    return {
        "product_name": "Full Cream Milk",
        "common_generic_name": "Milk",
        "manufacturer_name": "Amul Dairy",
        "manufacturer_address": "Anand, Gujarat 388001",
        "net_quantity": "500 ml",
        "net_quantity_unit": "ml",
        "net_quantity_numeric": 500,
        "mrp_raw": "MRP Rs. 30.00 (Incl. of all taxes)",
        "mrp_numeric": 30.0,
        "month_year_manufacture": "01/2026",
        "best_before_date": "Best Before 6 Months",
        "batch_lot_number": "AMT-4412",
        "consumer_care_name": "Amul Consumer Care",
        "consumer_care_phone": "1800 258 3333",
        "consumer_care_email": "care@amul.co.in",
        "product_category": "food",
        "is_imported": False,
        "country_of_origin": "India",
        "all_visible_text": "Amul Full Cream Milk. Net Qty 500 ml. MRP Rs. 30.00",
        "extraction_confidence": 0.94,
        "font_analysis": {"net_qty_font_height_mm": 4.5, "overall_legibility": "good"},
    }


def violations_by_rule(result: dict) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for violation in result["violations"]:
        grouped.setdefault(violation["rule_id"], []).append(violation)
    return grouped


def titles(result: dict) -> list[str]:
    return [violation["rule_title"] for violation in result["violations"]]


# ── happy path ───────────────────────────────────────────────────────────────
def test_fully_compliant_label_passes_every_check() -> None:
    result = run_compliance_check(compliant_payload(), scan_id="abc-123")

    assert result["overall_status"] == "compliant"
    assert result["compliance_score"] == 100.0
    assert result["total_violations"] == 0
    assert result["critical_violations"] == 0
    assert result["failed_checks"] == 0
    assert result["scan_id"] == "abc-123"
    assert result["total_checks"] >= 9


def test_extracted_declarations_cover_every_mandatory_rule() -> None:
    result = run_compliance_check(compliant_payload())
    rows = result["extracted_declarations"]
    assert len(rows) == 8
    assert all(row["detected"] for row in rows)
    assert {row["field"] for row in rows} >= {"mrp", "net_quantity", "manufacturer_name"}


def test_check_matrix_reports_every_evaluated_rule() -> None:
    result = run_compliance_check(compliant_payload())
    matrix = {entry["key"]: entry["status"] for entry in result["check_matrix"]}
    assert matrix["mrp"] == "pass"
    assert matrix["net_quantity"] == "pass"
    # Domestic package: the import-only rule is explicitly not applicable.
    assert matrix["country_of_origin"] == "skipped"


# ── Rule 4(1)(a) manufacturer ────────────────────────────────────────────────
def test_missing_manufacturer_is_critical() -> None:
    payload = compliant_payload()
    payload.update(manufacturer_name=None, manufacturer_address=None, packer_name=None)

    result = run_compliance_check(payload)

    assert violations_by_rule(result)["Rule 4(1)(a)"][0]["severity"] == "critical"
    assert result["overall_status"] == "non_compliant"


def test_name_without_address_is_a_distinct_violation() -> None:
    payload = compliant_payload()
    payload["manufacturer_address"] = None

    result = run_compliance_check(payload)

    assert violations_by_rule(result)["Rule 4(1)(a)"][0]["rule_title"] == (
        "Manufacturer/Packer Address Missing"
    )


def test_nullish_strings_are_treated_as_missing() -> None:
    payload = compliant_payload()
    payload["batch_lot_number"] = "N/A"
    payload["consumer_care_phone"] = "not visible"

    result = run_compliance_check(payload)

    found = titles(result)
    assert "Batch/Lot Number Not Declared" in found
    assert "Consumer Care Contact Number Missing" in found


# ── Rule 4(1)(f) / Rule 11 MRP ───────────────────────────────────────────────
def test_missing_mrp_is_critical() -> None:
    payload = compliant_payload()
    payload["mrp_raw"] = None

    result = run_compliance_check(payload)

    assert violations_by_rule(result)["Rule 4(1)(f)"][0]["severity"] == "critical"
    assert result["overall_status"] == "non_compliant"


def test_mrp_without_prefix_is_critical() -> None:
    payload = compliant_payload()
    payload["mrp_raw"] = "Rs. 30.00 (Incl. of all taxes)"

    result = run_compliance_check(payload)

    assert "MRP Prefix Missing or Non-Compliant" in titles(result)


def test_mrp_without_tax_statement_is_major_and_partial() -> None:
    payload = compliant_payload()
    payload["mrp_raw"] = "MRP Rs. 30.00"

    result = run_compliance_check(payload)

    violation = violations_by_rule(result)["Rule 11"][0]
    assert violation["rule_title"] == "MRP Tax Inclusion Not Stated"
    assert violation["severity"] == "major"
    assert result["overall_status"] == "partial"


# ── Rule 6 net quantity ──────────────────────────────────────────────────────
def test_missing_net_quantity_is_critical() -> None:
    payload = compliant_payload()
    payload.update(net_quantity=None, net_quantity_unit=None, net_quantity_numeric=None)

    result = run_compliance_check(payload)

    assert violations_by_rule(result)["Rule 4(1)(b)"][0]["severity"] == "critical"


def test_non_si_unit_is_major() -> None:
    payload = compliant_payload()
    payload.update(net_quantity="500 pounds", net_quantity_unit="pounds", net_quantity_numeric=500)

    result = run_compliance_check(payload)

    assert violations_by_rule(result)["Rule 6"][0]["severity"] == "major"


def test_quantity_is_parsed_when_only_text_is_returned() -> None:
    payload = compliant_payload()
    payload.update(net_quantity="1 kg", net_quantity_unit=None, net_quantity_numeric=None)
    payload["font_analysis"] = {"net_qty_font_height_mm": 7.0}

    result = run_compliance_check(payload)

    # The parsed unit is SI, so the net quantity check passes...
    assert "Rule 4(1)(b): Net Quantity" in result["passed_checks_list"]
    # ...and 7mm clears the 6mm requirement for packages above 1kg.
    assert result["total_violations"] == 0


# ── Rule 10 font size ────────────────────────────────────────────────────────
def test_small_font_is_flagged_with_the_right_threshold() -> None:
    payload = compliant_payload()  # 500 g/ml => 4 mm minimum
    payload["font_analysis"] = {"net_qty_font_height_mm": 1.5}

    result = run_compliance_check(payload)

    violation = violations_by_rule(result)["Rule 10"][0]
    assert violation["severity"] == "major"
    assert "4.0mm" in violation["required_value"]


def test_font_check_is_skipped_without_a_measurement() -> None:
    payload = compliant_payload()
    payload.pop("font_analysis")

    result = run_compliance_check(payload)

    assert "Rule 10" not in violations_by_rule(result)
    assert result["skipped_checks"]
    matrix = {entry["key"]: entry["status"] for entry in result["check_matrix"]}
    assert matrix["font_size"] == "skipped"


# ── date, food, import and category branches ─────────────────────────────────
def test_missing_manufacture_date_is_critical() -> None:
    payload = compliant_payload()
    payload["month_year_manufacture"] = None

    result = run_compliance_check(payload)

    assert violations_by_rule(result)["Rule 4(1)(c)"][0]["rule_title"] == (
        "Month/Year of Manufacture Not Declared"
    )


def test_non_standard_date_format_is_minor() -> None:
    payload = compliant_payload()
    payload["month_year_manufacture"] = "January"

    result = run_compliance_check(payload)

    violation = violations_by_rule(result)["Rule 4(1)(c)"][0]
    assert violation["severity"] == "minor"


def test_food_without_best_before_is_critical() -> None:
    payload = compliant_payload()
    payload["best_before_date"] = None
    payload["expiry_date"] = None

    result = run_compliance_check(payload)

    assert "Best Before / Expiry Date Missing (Food Item)" in titles(result)


def test_import_without_country_of_origin_is_critical() -> None:
    payload = compliant_payload()
    payload["is_imported"] = True
    payload["country_of_origin"] = None

    result = run_compliance_check(payload)

    assert violations_by_rule(result)["Rule 4(1)(i)"][0]["severity"] == "critical"


def test_textile_requires_fibre_composition() -> None:
    payload = compliant_payload()
    payload["product_category"] = "textile"
    payload["fiber_content"] = None

    result = run_compliance_check(payload)

    assert "Fibre Composition Not Declared" in titles(result)


def test_electronics_requires_voltage_rating() -> None:
    payload = compliant_payload()
    payload["product_category"] = "electronics"
    payload["voltage_wattage"] = None

    result = run_compliance_check(payload)

    assert "Voltage / Wattage Not Declared" in titles(result)


# ── Rule 14 misleading claims ────────────────────────────────────────────────
def test_misleading_claims_are_detected() -> None:
    assert detect_misleading_claims("Get 20% extra free now") == ["20% extra"]
    assert detect_misleading_claims("Free 50g in every pack") == ["Free 50g"]
    assert detect_misleading_claims("Jumbo Pack offer") == ["Jumbo Pack"]


def test_legitimate_uses_are_not_flagged() -> None:
    assert detect_misleading_claims("Sugar free. Gluten free. Free from preservatives.") == []
    assert detect_misleading_claims("Toll free 1800 258 3333") == []
    assert detect_misleading_claims("") == []


def test_misleading_claim_produces_minor_violation() -> None:
    payload = compliant_payload()
    payload["all_visible_text"] = "Net Qty 500 ml. Buy now and get 10% extra!"

    result = run_compliance_check(payload)

    violation = violations_by_rule(result)["Rule 14"][0]
    assert violation["severity"] == "minor"
    assert result["overall_status"] == "partial"


# ── scoring ──────────────────────────────────────────────────────────────────
def test_score_orders_by_severity_of_the_findings() -> None:
    compliant = run_compliance_check(compliant_payload())

    minor_payload = compliant_payload()
    minor_payload["month_year_manufacture"] = "January"
    minor = run_compliance_check(minor_payload)

    critical_payload = compliant_payload()
    critical_payload["mrp_raw"] = None
    critical = run_compliance_check(critical_payload)

    assert compliant["compliance_score"] > minor["compliance_score"] > critical["compliance_score"]
    assert critical["compliance_score"] > 0


def test_empty_payload_is_non_compliant_not_crashing() -> None:
    result = run_compliance_check({})

    assert result["overall_status"] == "non_compliant"
    assert result["compliance_score"] < 50
    assert result["summary"]


def test_none_payload_is_handled() -> None:
    result = run_compliance_check(None)
    assert result["total_violations"] > 0
