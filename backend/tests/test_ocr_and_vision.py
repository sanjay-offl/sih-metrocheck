"""Tests for the OCR fallback parser and the vision-response plumbing."""

from pathlib import Path

import pytest

from app.services.compliance_engine import run_compliance_check
from app.services.vision_service import (
    ExtractionError,
    parse_json_payload,
    normalise_extraction,
    parse_ocr_text,
)

SAMPLE_LABEL_TEXT = """AMUL TAAZA MILK
Net Qty: 500 ml
MRP Rs. 30.00 (Incl. of all taxes)
Mfg. Date: 01/2024
Best Before: 6 Months from Packing
Batch No: AMT-4412
FSSAI Lic. No. 10012011000123
Marketed By: Amul Dairy, Anand, Gujarat 388001
Consumer Care: 1800 258 3333, care@amul.co.in"""


def test_ocr_parser_extracts_the_mandatory_declarations() -> None:
    result = parse_ocr_text(SAMPLE_LABEL_TEXT)

    assert result["net_quantity_numeric"] == 500.0
    assert (result["net_quantity_unit"] or "").lower() == "ml"
    assert result["mrp_numeric"] == 30.0
    assert "MRP" in (result["mrp_raw"] or "").upper()
    assert result["month_year_manufacture"] == "01/2024"
    assert result["best_before_date"] == "6 Months from Packing"
    assert result["batch_lot_number"] == "AMT-4412"
    assert result["fssai_license"] == "10012011000123"
    assert result["consumer_care_phone"] == "1800 258 3333"
    assert result["consumer_care_email"] == "care@amul.co.in"
    assert result["manufacturer_name"] == "Amul Dairy"
    assert "388001" in (result["manufacturer_address"] or "")
    assert result["product_category"] == "food"
    assert result["is_imported"] is False
    assert 0.3 <= result["extraction_confidence"] <= 0.75
    assert "Tesseract" in (result["extraction_notes"] or "")


def test_ocr_output_flows_through_the_compliance_engine() -> None:
    extracted = parse_ocr_text(SAMPLE_LABEL_TEXT)
    result = run_compliance_check(extracted)

    assert result["total_checks"] > 5
    assert result["scan_id"] is None
    # Rule 10 cannot be measured without AI vision, so it must be skipped
    # rather than counted as a failure.
    matrix = {entry["key"]: entry["status"] for entry in result["check_matrix"]}
    assert matrix["font_size"] == "skipped"


def test_ocr_parser_flags_imported_packages() -> None:
    text = "CHOCOLATE\nNet Qty: 100 g\nImported By: Global Foods Pvt Ltd\nCountry of Origin: Switzerland"

    result = parse_ocr_text(text)

    assert result["is_imported"] is True
    assert result["country_of_origin"] == "Switzerland"


def test_ocr_parser_returns_empty_shape_for_blank_text() -> None:
    result = parse_ocr_text("")

    assert result["all_visible_text"] is None
    assert result["mrp_numeric"] is None
    assert result["extraction_confidence"] is not None


# ── Gemini response plumbing ─────────────────────────────────────────────────
def test_parse_json_payload_handles_fenced_and_noisy_responses() -> None:
    assert parse_json_payload('{"mrp_numeric": 30}') == {"mrp_numeric": 30}
    assert parse_json_payload('```json\n{"mrp_numeric": 30}\n```') == {"mrp_numeric": 30}
    assert parse_json_payload('Here you go:\n{"a": 1}\nThanks!') == {"a": 1}


def test_parse_json_payload_rejects_non_json() -> None:
    with pytest.raises(ValueError):
        parse_json_payload("I cannot read this label")


def test_normalise_extraction_coerces_types_and_fills_gaps() -> None:
    result = normalise_extraction(
        {"mrp_numeric": "Rs. 30.00", "net_quantity_numeric": "500", "is_imported": "yes"}
    )

    assert result["mrp_numeric"] == 30.0
    assert result["net_quantity_numeric"] == 500.0
    assert result["is_imported"] is True
    assert result["product_category"] == "other"
    assert result["manufacturer_name"] is None


def test_ocr_fallback_on_missing_image_raises_extraction_error() -> None:
    from app.services import vision_service

    with pytest.raises(ExtractionError):
        vision_service._run_ocr(str(Path("does-not-exist.jpg")))


def test_ocr_fallback_reads_a_synthetic_label(tmp_path: Path) -> None:
    """End-to-end OCR check; skipped when tesseract is not installed."""
    pytesseract = pytest.importorskip("pytesseract")
    PIL = pytest.importorskip("PIL.Image")
    from PIL import Image, ImageDraw

    try:
        pytesseract.get_tesseract_version()
    except Exception:  # noqa: BLE001 - binary missing in this environment
        pytest.skip("tesseract binary is not installed")

    image = Image.new("RGB", (1000, 420), "white")
    draw = ImageDraw.Draw(image)
    draw.text((30, 40), "TEST BRAND SOAP", fill="black")
    draw.text((30, 140), "NET QTY: 500 G", fill="black")
    draw.text((30, 240), "MRP RS. 45.00 (INCL. OF ALL TAXES)", fill="black")
    draw.text((30, 340), "BATCH NO: TB-9981", fill="black")
    path = tmp_path / "label.png"
    image.save(path)

    from app.services import vision_service

    extracted = vision_service._run_ocr(str(path))

    assert extracted["extraction_method"] == "ocr"
    assert extracted["mrp_numeric"] == 45.0
    assert extracted["net_quantity_numeric"] == 500.0
