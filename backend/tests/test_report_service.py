"""Tests for the PDF / JSON report generator."""

import json
from pathlib import Path

from app.services.compliance_engine import run_compliance_check
from app.services.report_service import (
    _safe,
    generate_compliance_report_json,
    generate_compliance_report_pdf,
)

EXTRACTED = {
    "product_name": "Full Cream Milk",
    "manufacturer_name": "Amul Dairy",
    "manufacturer_address": "Anand, Gujarat 388001",
    "net_quantity": "500 ml",
    "mrp_raw": "MRP Rs. 30.00 (Incl. of all taxes)",
    "month_year_manufacture": "01/2026",
    "batch_lot_number": "AMT-4412",
    "consumer_care_phone": "1800 258 3333",
    "product_category": "food",
    "best_before_date": "6 Months",
    "extraction_confidence": 0.9,
    "extraction_notes": "Clean label, no glare.",
}


def make_result(payload_overrides: dict | None = None, scan_id: str = "11111111-2222-3333-4444-555555555555") -> dict:
    data = dict(EXTRACTED, **({"country_of_origin": None} if payload_overrides is None else payload_overrides))
    return run_compliance_check(data, scan_id=scan_id)


def test_safe_transliterates_pdf_unsafe_characters() -> None:
    assert _safe("MRP \u20b950.00 \u2014 Incl. of all taxes") == "MRP Rs.50.00 - Incl. of all taxes"
    assert _safe(None) == "\u2014"
    assert _safe("A & B <tag>") == "A &amp; B &lt;tag&gt;"


def test_pdf_report_is_written_with_violation_and_rule_sections(tmp_path: Path) -> None:
    result = make_result({"mrp_raw": None, "batch_lot_number": None, "consumer_care_phone": None})

    path = generate_compliance_report_pdf(
        scan_data={"scan_id": "11111111-2222-3333-4444-555555555555", "location": "Karol Bagh, Delhi"},
        extracted_data=EXTRACTED,
        compliance_result=result,
        officer_name="Rajesh Kumar",
        officer_department="Enforcement - Delhi",
        output_dir=str(tmp_path),
    )

    pdf = Path(path)
    assert pdf.exists()
    assert pdf.stat().st_size > 5000
    assert pdf.read_bytes()[:4] == b"%PDF"


def test_pdf_report_generates_for_a_fully_compliant_scan(tmp_path: Path) -> None:
    result = run_compliance_check(
        dict(EXTRACTED, font_analysis={"net_qty_font_height_mm": 4.5}), scan_id="abc"
    )
    assert result["total_violations"] == 0

    path = generate_compliance_report_pdf(
        scan_data={"scan_id": "abc"},
        extracted_data=EXTRACTED,
        compliance_result=result,
        officer_name="Priya Sharma",
        output_dir=str(tmp_path),
    )
    assert Path(path).stat().st_size > 4000


def test_json_report_round_trips_the_compliance_payload(tmp_path: Path) -> None:
    result = make_result(scan_id="abc-def")

    path = generate_compliance_report_json(
        scan_data={"scan_id": "abc-def"},
        extracted_data=EXTRACTED,
        compliance_result=result,
        officer_name="Priya Sharma",
        output_dir=str(tmp_path),
    )

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    assert payload["scan"]["scan_id"] == "abc-def"
    assert payload["compliance_result"]["scan_id"] == "abc-def"
    assert payload["generated_by"] == "Priya Sharma"
    assert "generated_at" in payload
