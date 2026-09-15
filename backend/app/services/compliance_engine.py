"""
Rule-based compliance engine.

Pure functions only — no database, network or filesystem access — which keeps
the legal logic unit-testable and reusable from the CLI, the API and the tests.

Every check appends either a violation or a pass, and each one records its
entry in a ``check_matrix`` so the UI can show the full audit trail.
"""

import re
from typing import Any, Optional

from app.utils.legal_rules import (
    ACCEPTED_QUANTITY_UNITS,
    CATEGORY_SPECIFIC_RULES,
    MANDATORY_DECLARATIONS,
    MISLEADING_FALSE_POSITIVES,
    MISLEADING_QUANTITY_PATTERNS,
    MRP_RULES,
    canonical_unit,
    get_required_font_size,
    parse_net_quantity,
    quantity_to_base,
)

SEVERITY_WEIGHTS = {"critical": 3, "major": 2, "minor": 1}

# Values the model may return when it could not read a field.
_NULLISH = {"", "null", "none", "n/a", "na", "not visible", "not found", "unknown", "-", "nil"}

_DATE_PATTERN = re.compile(
    r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{1,2})[\s/\-.,]*(\d{4})",
    re.IGNORECASE,
)


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────
def _clean(value: Any) -> Optional[str]:
    """Normalise a model-supplied value; empty/nullish strings become None."""
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text or text.lower() in _NULLISH:
        return None
    return text


def _violation(
    rule_id: str,
    rule_title: str,
    severity: str,
    description: str,
    required_value: Optional[str] = None,
    detected_value: Optional[str] = None,
    recommendation: str = "",
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "rule_title": rule_title,
        "severity": severity,
        "description": description,
        "detected_value": detected_value,
        "required_value": required_value,
        "recommendation": recommendation,
    }


def detect_misleading_claims(all_visible_text: Optional[str]) -> list[str]:
    """Return quantity-implying marketing claims that breach Rule 14."""
    text = _clean(all_visible_text)
    if not text:
        return []

    claims: list[str] = []
    for sentence in re.split(r"[\n.;|]+", text):
        lowered = sentence.lower()
        if any(fp in lowered for fp in MISLEADING_FALSE_POSITIVES):
            continue
        for pattern in MISLEADING_QUANTITY_PATTERNS:
            match = pattern.search(sentence)
            if match:
                claims.append(match.group(0).strip())
                break
    # De-duplicate while keeping order.
    return list(dict.fromkeys(claims))


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────
def run_compliance_check(
    extracted_data: dict[str, Any] | None,
    scan_id: Optional[str] = None,
) -> dict[str, Any]:
    """Evaluate extracted label data against the Legal Metrology Rules, 2011."""
    data = extracted_data or {}

    violations: list[dict[str, Any]] = []
    passed_checks: list[str] = []
    skipped_checks: list[str] = []
    check_matrix: list[dict[str, Any]] = []

    def record(
        key: str,
        status: str,
        *,
        detail: Optional[str] = None,
        rule_id: Optional[str] = None,
        title: Optional[str] = None,
        severity: Optional[str] = None,
    ) -> None:
        definition = MANDATORY_DECLARATIONS.get(key, {})
        check_matrix.append(
            {
                "key": key,
                "rule_id": rule_id or definition.get("rule", "—"),
                "title": title or definition.get("title", key),
                "severity": severity or definition.get("severity", "major"),
                "status": status,  # pass | fail | skipped
                "detail": detail,
            }
        )

    is_imported = bool(data.get("is_imported"))
    category = (_clean(data.get("product_category")) or "other").lower()
    if category not in CATEGORY_SPECIFIC_RULES and category not in {"food", "beverage"}:
        category = category or "other"

    # ── CHECK 1: Manufacturer / packer name and address (Rule 4(1)(a)) ──────
    mfr_name = _clean(data.get("manufacturer_name")) or _clean(data.get("packer_name"))
    mfr_address = _clean(data.get("manufacturer_address")) or _clean(data.get("packer_address"))
    importer_name = _clean(data.get("importer_name"))
    importer_address = _clean(data.get("importer_address"))

    if not mfr_name and not importer_name:
        violations.append(
            _violation(
                "Rule 4(1)(a)",
                "Manufacturer/Packer Name Missing",
                "critical",
                "The name of the manufacturer, packer or importer is not declared on the label.",
                required_value="Full name of manufacturer, packer, or importer",
                recommendation=(
                    "Print the complete legal name of the manufacturer, packer or "
                    "importer prominently on the package."
                ),
            )
        )
        record("manufacturer_name", "fail")
    elif not (mfr_address or importer_address):
        violations.append(
            _violation(
                "Rule 4(1)(a)",
                "Manufacturer/Packer Address Missing",
                "critical",
                "The complete postal address of the manufacturer, packer or importer is not declared.",
                required_value="Complete postal address including pin code",
                detected_value=mfr_name or importer_name,
                recommendation=(
                    "Add the complete address with pin code of the manufacturer, "
                    "packer or importer."
                ),
            )
        )
        record("manufacturer_name", "fail")
    else:
        passed_checks.append("Rule 4(1)(a): Manufacturer/Packer Name & Address")
        record("manufacturer_name", "pass")

    # ── CHECK 2: Net quantity (Rule 4(1)(b) and Rule 6) ─────────────────────
    net_qty = _clean(data.get("net_quantity"))
    raw_unit = _clean(data.get("net_quantity_unit"))
    numeric = data.get("net_quantity_numeric")
    try:
        numeric = float(numeric) if numeric is not None else None
    except (TypeError, ValueError):
        numeric = None

    if numeric is None:
        parsed_numeric, parsed_unit = parse_net_quantity(net_qty)
        numeric = parsed_numeric
        raw_unit = raw_unit or parsed_unit

    unit = canonical_unit(raw_unit) or (parse_net_quantity(net_qty)[1])

    if not net_qty:
        violations.append(
            _violation(
                "Rule 4(1)(b)",
                "Net Quantity Not Declared",
                "critical",
                "Net quantity of the commodity is not declared on the package.",
                required_value="Net quantity in SI units (g, kg, ml, L, m, etc.)",
                recommendation="Declare the net quantity in standard SI units clearly on the label.",
            )
        )
        record("net_quantity", "fail")
    elif unit and unit.lower() not in ACCEPTED_QUANTITY_UNITS:
        violations.append(
            _violation(
                "Rule 6",
                "Non-Standard Unit of Measurement",
                "major",
                f"Net quantity declared in a non-standard unit: '{raw_unit or unit}'",
                required_value="Standard SI units: g, kg, ml, L, m, cm",
                detected_value=net_qty,
                recommendation=f"Replace '{raw_unit or unit}' with the equivalent SI unit.",
            )
        )
        record("net_quantity", "fail", rule_id="Rule 6", title="Net Quantity Unit")
    else:
        passed_checks.append("Rule 4(1)(b): Net Quantity")
        record("net_quantity", "pass")

    # ── CHECK 3: Month and year of manufacture (Rule 4(1)(c)) ───────────────
    mfg_date = _clean(data.get("month_year_manufacture"))
    if not mfg_date:
        violations.append(
            _violation(
                "Rule 4(1)(c)",
                "Month/Year of Manufacture Not Declared",
                "critical",
                "Month and year of manufacture, packing or import is not declared.",
                required_value="Month and Year (e.g. 'Mfg: Jan 2024' or '01/2024')",
                recommendation="Print 'Mfg. Date:' or 'Packed on:' with the month and year.",
            )
        )
        record("month_year_manufacture", "fail")
    elif not _DATE_PATTERN.search(mfg_date):
        violations.append(
            _violation(
                "Rule 4(1)(c)",
                "Manufacture Date Format Non-Standard",
                "minor",
                f"Date format '{mfg_date}' may not clearly indicate month and year.",
                required_value="Format like 'Jan 2024', '01/2024' or 'January 2024'",
                detected_value=mfg_date,
                recommendation="Use a standard date format that shows both month and year.",
            )
        )
        record("month_year_manufacture", "fail")
    else:
        passed_checks.append("Rule 4(1)(c): Month/Year of Manufacture")
        record("month_year_manufacture", "pass")

    # ── CHECK 4: MRP (Rule 4(1)(f) and Rule 11) ─────────────────────────────
    mrp_raw = _clean(data.get("mrp_raw"))
    mrp_numeric = data.get("mrp_numeric")
    try:
        mrp_numeric = float(mrp_numeric) if mrp_numeric is not None else None
    except (TypeError, ValueError):
        mrp_numeric = None

    mrp_failed = False
    if not mrp_raw:
        violations.append(
            _violation(
                "Rule 4(1)(f)",
                "MRP Not Declared",
                "critical",
                "Maximum Retail Price (MRP) is not declared on the package.",
                required_value="MRP inclusive of all taxes in Indian Rupees",
                recommendation="Print 'MRP ₹XX (Incl. of all taxes)' prominently on the label.",
            )
        )
        mrp_failed = True
    else:
        mrp_upper = mrp_raw.upper()
        has_valid_prefix = any(prefix.upper() in mrp_upper for prefix in MRP_RULES["valid_prefixes"])
        states_taxes = any(
            phrase in mrp_upper for phrase in ("INCL", "INCLUSIVE", "ALL TAXES")
        ) or "INCL. OF ALL TAXES" in mrp_upper

        if not has_valid_prefix:
            violations.append(
                _violation(
                    "Rule 11",
                    "MRP Prefix Missing or Non-Compliant",
                    "critical",
                    f"MRP declaration '{mrp_raw}' does not carry the required 'MRP' prefix.",
                    required_value="Prefix 'MRP' before the price",
                    detected_value=mrp_raw,
                    recommendation=(
                        "Declare the price as 'MRP Rs. XX' or 'MRP ₹XX (Incl. of all taxes)'."
                    ),
                )
            )
            mrp_failed = True

        if not states_taxes:
            violations.append(
                _violation(
                    "Rule 11",
                    "MRP Tax Inclusion Not Stated",
                    "major",
                    "MRP declaration does not state that it is inclusive of all taxes.",
                    required_value="MRP (Incl. of all taxes) or MRP (inclusive of all taxes)",
                    detected_value=mrp_raw,
                    recommendation="Add '(Incl. of all taxes)' after the MRP declaration.",
                )
            )
            mrp_failed = True

        if not mrp_failed:
            passed_checks.append("Rule 4(1)(f): MRP Declaration")
            record("mrp", "pass")

    if mrp_failed:
        record("mrp", "fail")

    # ── CHECK 5: Consumer care details (Rule 4(1)(g)) ───────────────────────
    cc_name = _clean(data.get("consumer_care_name"))
    cc_phone = _clean(data.get("consumer_care_phone"))
    cc_email = _clean(data.get("consumer_care_email"))
    cc_address = _clean(data.get("consumer_care_address"))

    if not cc_name and not cc_phone and not cc_email:
        violations.append(
            _violation(
                "Rule 4(1)(g)",
                "Consumer Care Details Missing",
                "major",
                "Consumer care name, address or contact details are not declared.",
                required_value="Name, address and contact number/email of the consumer care cell",
                recommendation="Add a 'Consumer Care:' section with name, address and phone/email.",
            )
        )
        record("consumer_care_details", "fail")
    elif not cc_phone:
        violations.append(
            _violation(
                "Rule 4(1)(g)",
                "Consumer Care Contact Number Missing",
                "major",
                "Consumer care telephone number is not declared.",
                required_value="Phone number for consumer grievances",
                detected_value=cc_name or cc_address or cc_email,
                recommendation="Add a phone number for the consumer care cell.",
            )
        )
        record("consumer_care_details", "fail")
    else:
        passed_checks.append("Rule 4(1)(g): Consumer Care Details")
        record("consumer_care_details", "pass")

    # ── CHECK 6: Country of origin (Rule 4(1)(i)) — imports only ────────────
    if is_imported:
        country = _clean(data.get("country_of_origin"))
        if not country:
            violations.append(
                _violation(
                    "Rule 4(1)(i)",
                    "Country of Origin Not Declared (Import)",
                    "critical",
                    "This appears to be an imported product; the country of origin must be declared.",
                    required_value="Country of origin (e.g. 'Country of Origin: China')",
                    recommendation="Declare 'Country of Origin: [Country Name]' on the label.",
                )
            )
            record("country_of_origin", "fail")
        else:
            passed_checks.append("Rule 4(1)(i): Country of Origin")
            record("country_of_origin", "pass")
    else:
        # Keep the rule visible in the matrix as explicitly not applicable.
        record(
            "country_of_origin",
            "skipped",
            detail="Domestic product — declaration applies to imports only",
        )

    # ── CHECK 7: Common / generic name (Rule 4(1)(d)) ───────────────────────
    generic_name = _clean(data.get("common_generic_name")) or _clean(data.get("product_name"))
    if not generic_name:
        violations.append(
            _violation(
                "Rule 4(1)(d)",
                "Common/Generic Name Not Declared",
                "major",
                "The common or generic name of the commodity is not declared.",
                required_value="Common or generic name of the commodity",
                recommendation="Add the common or generic name of the commodity to the label.",
            )
        )
        record("common_generic_name", "fail")
    else:
        passed_checks.append("Rule 4(1)(d): Common/Generic Name")
        record("common_generic_name", "pass")

    # ── CHECK 8: Batch / lot number (Rule 4(1)(e)) ──────────────────────────
    batch = _clean(data.get("batch_lot_number"))
    if not batch:
        violations.append(
            _violation(
                "Rule 4(1)(e)",
                "Batch/Lot Number Not Declared",
                "major",
                "Batch number, lot number or production code is not declared.",
                required_value="Batch No., Lot No. or Code No.",
                recommendation="Add 'Batch No.:' or 'Lot No.:' followed by the identification code.",
            )
        )
        record("batch_lot_number", "fail")
    else:
        passed_checks.append("Rule 4(1)(e): Batch/Lot Number")
        record("batch_lot_number", "pass")

    # ── CHECK 9: Font size (Rule 10) ────────────────────────────────────────
    font_analysis = data.get("font_analysis") or {}
    net_qty_font = font_analysis.get("net_qty_font_height_mm")
    try:
        net_qty_font = float(net_qty_font) if net_qty_font is not None else None
    except (TypeError, ValueError):
        net_qty_font = None

    base_quantity = quantity_to_base(numeric, unit)
    if base_quantity is None or net_qty_font is None:
        skipped_checks.append(
            "Rule 10: Font Size Requirement (no reliable measurement available)"
        )
        record(
            "font_size",
            "skipped",
            rule_id="Rule 10",
            title="Font Size Requirement",
            severity="major",
            detail="No reliable glyph measurement was returned for this image",
        )
    else:
        required_font = get_required_font_size(base_quantity)
        required_min_mm = required_font["min_height_mm"]
        if net_qty_font < required_min_mm:
            violations.append(
                _violation(
                    "Rule 10",
                    "Font Size Below Legal Minimum",
                    "major",
                    (
                        f"Net quantity text height (~{net_qty_font}mm) is below the minimum "
                        f"required height of {required_min_mm}mm for products of this size "
                        f"({required_font['label']})."
                    ),
                    required_value=f"Minimum {required_min_mm}mm height",
                    detected_value=f"~{net_qty_font}mm",
                    recommendation=(
                        f"Increase the font so numerals and letters in the net quantity "
                        f"declaration are at least {required_min_mm}mm tall."
                    ),
                )
            )
            record(
                "font_size",
                "fail",
                rule_id="Rule 10",
                title="Font Size Requirement",
                severity="major",
            )
        else:
            passed_checks.append("Rule 10: Font Size Requirement")
            record(
                "font_size",
                "pass",
                rule_id="Rule 10",
                title="Font Size Requirement",
                severity="major",
            )

    # ── CHECK 10: Best before / expiry for food & beverage ──────────────────
    if category in {"food", "beverage"}:
        best_before = _clean(data.get("best_before_date")) or _clean(data.get("expiry_date"))
        if not best_before:
            violations.append(
                _violation(
                    "Rule 4(1)(c)",
                    "Best Before / Expiry Date Missing (Food Item)",
                    "critical",
                    "Food and beverage products must declare a best before date or expiry date.",
                    required_value="'Best before' or 'Use by' date",
                    recommendation="Add 'Best Before:' or 'Use by:' with the date on the label.",
                )
            )
            record(
                "best_before",
                "fail",
                rule_id="Rule 4(1)(c)",
                title="Best Before / Expiry Date",
                severity="critical",
            )
        else:
            passed_checks.append("Rule 4(1)(c): Best Before / Expiry Date")
            record(
                "best_before",
                "pass",
                rule_id="Rule 4(1)(c)",
                title="Best Before / Expiry Date",
                severity="critical",
            )

    # ── CHECK 11: Category specific declarations (Schedules II / III) ───────
    if category == "textile":
        fiber = _clean(data.get("fiber_content"))
        if not fiber:
            violations.append(
                _violation(
                    "Schedule II",
                    "Fibre Composition Not Declared",
                    "major",
                    "Textile packages must declare the fibre composition by percentage.",
                    required_value="Fibre content, e.g. '100% Cotton'",
                    recommendation="Declare the fibre composition as a percentage on the label.",
                )
            )
            record("fiber_content", "fail", rule_id="Schedule II", title="Fibre Composition")
        else:
            passed_checks.append("Schedule II: Fibre Composition")
            record("fiber_content", "pass", rule_id="Schedule II", title="Fibre Composition")
    elif category == "electronics":
        rating = _clean(data.get("voltage_wattage"))
        if not rating:
            violations.append(
                _violation(
                    "Schedule III",
                    "Voltage / Wattage Not Declared",
                    "major",
                    "Electrical appliances must declare voltage, wattage or energy rating.",
                    required_value="Voltage (V), wattage (W) or energy rating",
                    recommendation="Declare the rated voltage and power consumption on the label.",
                )
            )
            record("voltage_wattage", "fail", rule_id="Schedule III", title="Voltage / Wattage")
        else:
            passed_checks.append("Schedule III: Voltage / Wattage")
            record("voltage_wattage", "pass", rule_id="Schedule III", title="Voltage / Wattage")

    # ── CHECK 12: Misleading words (Rule 14) ────────────────────────────────
    claims = detect_misleading_claims(data.get("all_visible_text"))
    if claims:
        violations.append(
            _violation(
                "Rule 14",
                "Potentially Misleading Words on Package",
                "minor",
                (
                    "Words that may mislead the consumer about quantity were found: "
                    + ", ".join(f"'{c}'" for c in claims[:5])
                ),
                required_value="No misleading quantity claims",
                detected_value=", ".join(claims[:5]),
                recommendation=(
                    "Remove the qualifying words or provide the actual quantity "
                    "difference on the label."
                ),
            )
        )
        record("misleading_words", "fail", rule_id="Rule 14", title="Misleading Words")

    # ── Score ───────────────────────────────────────────────────────────────
    total_checks = len(violations) + len(passed_checks)
    if total_checks == 0:
        compliance_score = 100.0
    else:
        total_weight = sum(SEVERITY_WEIGHTS.get(v["severity"], 1) for v in violations)
        max_possible_weight = total_checks * SEVERITY_WEIGHTS["critical"]
        compliance_score = max(0.0, round(100.0 * (1 - total_weight / max_possible_weight), 1))

    critical_count = sum(1 for v in violations if v["severity"] == "critical")

    if not violations:
        overall_status = "compliant"
        summary = (
            "This product label is compliant with the Legal Metrology (Packaged "
            "Commodities) Rules, 2011. All mandatory declarations were found and "
            "correctly formatted."
        )
    elif critical_count > 0:
        overall_status = "non_compliant"
        summary = (
            f"This product label has {len(violations)} violation(s), including "
            f"{critical_count} critical violation(s), under the Legal Metrology "
            f"(Packaged Commodities) Rules, 2011. Immediate corrective action is required."
        )
    else:
        overall_status = "partial"
        summary = (
            f"This product label is partially compliant with {len(violations)} "
            f"minor/major violation(s) under the Legal Metrology (Packaged Commodities) "
            f"Rules, 2011. Corrections are recommended."
        )

    return {
        "scan_id": scan_id,
        "overall_status": overall_status,
        "compliance_score": compliance_score,
        "total_checks": total_checks,
        "passed_checks": len(passed_checks),
        "failed_checks": len(violations),
        "total_violations": len(violations),
        "critical_violations": critical_count,
        "major_violations": sum(1 for v in violations if v["severity"] == "major"),
        "minor_violations": sum(1 for v in violations if v["severity"] == "minor"),
        "violations": violations,
        "passed_checks_list": passed_checks,
        "skipped_checks": skipped_checks,
        "check_matrix": check_matrix,
        "extracted_declarations": build_extracted_declarations(data),
        "summary": summary,
    }


def build_extracted_declarations(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten the extraction payload into one row per mandatory declaration."""
    confidence = data.get("extraction_confidence")
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0

    rows: list[dict[str, Any]] = []
    for key, definition in MANDATORY_DECLARATIONS.items():
        values = [_clean(data.get(field)) for field in definition["extraction_fields"]]
        value = next((v for v in values if v), None)
        rows.append(
            {
                "field": key,
                "value": value,
                "detected": value is not None,
                "confidence": confidence,
                "raw_text": value,
                "rule": definition["rule"],
                "title": definition["title"],
                "severity": definition["severity"],
            }
        )
    return rows
