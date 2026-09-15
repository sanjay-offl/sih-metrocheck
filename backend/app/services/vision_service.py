"""
Label extraction.

Primary engine: Google Gemini Flash 2.0 vision (``gemini-2.0-flash``) driven by
a strict JSON prompt. Fallback engine: Tesseract OCR plus regex heuristics,
used when no API key is configured, when Gemini errors out, or when the model
returns unparseable output. Results are cached in Redis by image hash.
"""

import asyncio
import base64
import json
import logging
import re
from typing import Any, Optional

from app.core.config import settings
from app.services.cache_service import get_cached_extraction, set_cached_extraction
from app.utils.image_utils import mime_type_for, prepare_for_ocr, prepare_for_vision

logger = logging.getLogger(__name__)

try:  # The SDK is optional at import time so tests can run without it.
    import google.generativeai as genai

    if settings.gemini_api_key:
        genai.configure(api_key=settings.gemini_api_key)
except Exception:  # noqa: BLE001 - missing package or bad config
    genai = None  # type: ignore[assignment]


class ExtractionError(RuntimeError):
    """Raised when neither Gemini nor OCR could read the label."""


EXTRACTION_PROMPT = """
You are an expert in Indian consumer product law, specifically the Legal Metrology (Packaged Commodities) Rules, 2011.

Analyze this packaged product label image carefully. Extract every piece of text visible on the label and identify the following mandatory declarations as required by Indian law.

Return ONLY a valid JSON object with this exact structure. Do not include any explanation or markdown.

{
  "product_name": "string or null",
  "manufacturer_name": "string or null",
  "manufacturer_address": "string or null",
  "packer_name": "string or null",
  "packer_address": "string or null",
  "importer_name": "string or null",
  "importer_address": "string or null",
  "net_quantity": "string or null",
  "net_quantity_unit": "string or null",
  "net_quantity_numeric": "number or null",
  "mrp_raw": "string or null",
  "mrp_numeric": "number or null",
  "mrp_prefix": "string or null",
  "month_year_manufacture": "string or null",
  "best_before_date": "string or null",
  "expiry_date": "string or null",
  "batch_lot_number": "string or null",
  "consumer_care_name": "string or null",
  "consumer_care_address": "string or null",
  "consumer_care_phone": "string or null",
  "consumer_care_email": "string or null",
  "country_of_origin": "string or null",
  "common_generic_name": "string or null",
  "fssai_license": "string or null",
  "ingredients": "string or null",
  "nutritional_info_present": "boolean",
  "barcode_ean": "string or null",
  "fiber_content": "string or null",
  "voltage_wattage": "string or null",
  "product_category": "one of: food, beverage, cosmetic, pharmaceutical, textile, electronics, household, other",
  "is_imported": "boolean",
  "all_visible_text": "full verbatim text from label",
  "label_languages": ["list of language names detected"],
  "estimated_font_size_mrp_mm": "number or null",
  "estimated_font_size_net_qty_mm": "number or null",
  "font_size_readability": "good | poor | unknown",
  "extraction_confidence": "number between 0 and 1",
  "extraction_notes": "string — any observations about image quality, obscured text, etc."
}

Be extremely thorough. Check all sides of the package if visible. Look for small print. For MRP, check whether the literal prefix 'MRP' is printed, and whether the statement says the price is inclusive of all taxes. For net quantity, note the unit (g, kg, ml, L) and require SI units. Use null when a field is genuinely absent or unreadable — never invent values.
""".strip()

FONT_ANALYSIS_PROMPT = """
Analyze the font size of text on this product label.

Look specifically at:
1. The MRP (Maximum Retail Price) text — estimate the height of the numerals in millimetres
2. The Net Quantity text — estimate the height of the numerals in millimetres
3. Whether the declarations are printed in a legible size

Return only this JSON:
{
  "mrp_font_height_mm": number or null,
  "net_qty_font_height_mm": number or null,
  "overall_legibility": "good | fair | poor",
  "smallest_text_height_mm": number or null,
  "font_concerns": ["list of concerns or empty array"]
}
""".strip()

_EMPTY_FIELDS: dict[str, Any] = {
    "product_name": None,
    "manufacturer_name": None,
    "manufacturer_address": None,
    "packer_name": None,
    "packer_address": None,
    "importer_name": None,
    "importer_address": None,
    "net_quantity": None,
    "net_quantity_unit": None,
    "net_quantity_numeric": None,
    "mrp_raw": None,
    "mrp_numeric": None,
    "mrp_prefix": None,
    "month_year_manufacture": None,
    "best_before_date": None,
    "expiry_date": None,
    "batch_lot_number": None,
    "consumer_care_name": None,
    "consumer_care_address": None,
    "consumer_care_phone": None,
    "consumer_care_email": None,
    "country_of_origin": None,
    "common_generic_name": None,
    "fssai_license": None,
    "ingredients": None,
    "nutritional_info_present": False,
    "barcode_ean": None,
    "fiber_content": None,
    "voltage_wattage": None,
    "product_category": "other",
    "is_imported": False,
    "all_visible_text": None,
    "label_languages": [],
    "estimated_font_size_mrp_mm": None,
    "estimated_font_size_net_qty_mm": None,
    "font_size_readability": "unknown",
    "extraction_confidence": 0.0,
    "extraction_notes": None,
}


def vision_engine() -> str:
    """Which extraction engine is active for this deployment."""
    return "gemini" if (genai is not None and settings.gemini_api_key) else "ocr"


# ─────────────────────────────────────────────────────────────────────────────
# JSON plumbing
# ─────────────────────────────────────────────────────────────────────────────
def parse_json_payload(raw_text: str) -> dict[str, Any]:
    """Extract the JSON object from a model response that may be fenced."""
    text = (raw_text or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1] if len(text.split("```")) > 1 else text
        text = re.sub(r"^\s*(json|JSON)\s*", "", text).strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in the model response")
    return json.loads(text[start : end + 1])


def normalise_extraction(payload: dict[str, Any]) -> dict[str, Any]:
    """Merge a model payload over the empty schema so every key exists."""
    result = dict(_EMPTY_FIELDS)
    for key, value in (payload or {}).items():
        if key in result:
            result[key] = value
        else:
            result[key] = value  # keep unexpected keys, they are harmless
    # Numeric coercion, since models sometimes answer with strings.
    for numeric_field in ("net_quantity_numeric", "mrp_numeric", "extraction_confidence"):
        value = result.get(numeric_field)
        if isinstance(value, str):
            match = re.search(r"\d+(?:\.\d+)?", value)
            result[numeric_field] = float(match.group(0)) if match else None
    if isinstance(result.get("is_imported"), str):
        result["is_imported"] = result["is_imported"].strip().lower() in {"true", "yes", "1"}
    if isinstance(result.get("nutritional_info_present"), str):
        result["nutritional_info_present"] = (
            result["nutritional_info_present"].strip().lower() in {"true", "yes", "1"}
        )
    if not result.get("product_category"):
        result["product_category"] = "other"
    return result


# ─────────────────────────────────────────────────────────────────────────────
# Gemini
# ─────────────────────────────────────────────────────────────────────────────
def _gemini_call(image_bytes: bytes, mime_type: str, prompt: str) -> str:
    model = genai.GenerativeModel(settings.gemini_model)
    image_part = {"mime_type": mime_type, "data": image_bytes}
    response = model.generate_content(
        [prompt, image_part],
        generation_config={"temperature": 0.1, "response_mime_type": "application/json"},
    )
    return getattr(response, "text", "") or ""


def _run_gemini(image_path: str) -> dict[str, Any]:
    image_bytes = prepare_for_vision(image_path)
    mime_type = "image/jpeg" if not image_path.lower().endswith(".png") else mime_type_for(image_path)

    raw = _gemini_call(image_bytes, mime_type, EXTRACTION_PROMPT)
    extracted = normalise_extraction(parse_json_payload(raw))

    try:
        font_raw = _gemini_call(image_bytes, mime_type, FONT_ANALYSIS_PROMPT)
        extracted["font_analysis"] = parse_json_payload(font_raw)
    except Exception as exc:  # noqa: BLE001 - font pass is best-effort
        logger.info("Font analysis pass failed, falling back to extraction estimates: %s", exc)
        extracted["font_analysis"] = {
            "mrp_font_height_mm": extracted.get("estimated_font_size_mrp_mm"),
            "net_qty_font_height_mm": extracted.get("estimated_font_size_net_qty_mm"),
            "overall_legibility": extracted.get("font_size_readability", "unknown"),
            "font_concerns": [],
        }

    extracted["extraction_method"] = "gemini"
    extracted["model_used"] = settings.gemini_model
    return extracted


# ─────────────────────────────────────────────────────────────────────────────
# Tesseract fallback
# ─────────────────────────────────────────────────────────────────────────────
_MRP_RE = re.compile(
    r"(?:MRP|M\.?\s?R\.?\s?P\.?|MAXIMUM\s+RETAIL\s+PRICE)[^\d\n]{0,18}?"
    r"(?:RS\.?|₹|INR)?\s*([\d][\d,]*(?:\.\d{1,2})?)",
    re.IGNORECASE,
)
_NET_QTY_RE = re.compile(
    r"(?:NET\s*(?:QTY|QUANTITY|WT|WEIGHT|VOL|VOLUME|CONTENT)\.?|N\.?W\.?)"
    r"\s*[:\-]?\s*([\d.,]+\s*(?:kgs?|gms?|gm|g|mgs?|ml|ltrs?|ltr|litres?|liters?|l|"
    r"pieces?|pcs?|nos?|numbers?))",
    re.IGNORECASE,
)
_MFG_DATE_RE = re.compile(
    r"(?:MFG|MFD|MANUFACTURED|PACKED|PKG|DATE\s*OF\s*(?:MFG|MANUFACTURE|PACKING))"
    r"\.?\s*(?:ON|DATE|DT)?\.?\s*[:\-]?\s*([^\n]{3,40})",
    re.IGNORECASE,
)
_BEST_BEFORE_RE = re.compile(
    r"(?:BEST\s*BEFORE|USE\s*BY|USE\s*BEFORE|EXP(?:IRY|IRES|\.)?)\s*[:\-]?\s*([^\n]{3,40})",
    re.IGNORECASE,
)
_BATCH_RE = re.compile(
    r"(?:BATCH|LOT|B\.?\s?NO\.?|CODE)\s*(?:NO\.?|NUMBER|#)?\s*[:\-]?\s*([A-Z0-9][A-Z0-9\-\/]{1,19})",
    re.IGNORECASE,
)
_PHONE_RE = re.compile(r"(?:\+91[\s\-]?)?\b(?:1800[\s\-]?\d{3}[\s\-]?\d{3,4}|[6-9]\d{9})\b")
_EMAIL_RE = re.compile(r"[\w.\-+]+@[\w\-]+\.[\w.\-]+")
_FSSAI_RE = re.compile(r"\b(1\d{13})\b")
_ORIGIN_RE = re.compile(
    r"(?:COUNTRY\s*OF\s*ORIGIN|MADE\s*IN|ORIGIN)\s*[:\-]?\s*([A-Za-z][A-Za-z .]{2,40})",
    re.IGNORECASE,
)
_IMPORTER_RE = re.compile(r"(?:IMPORTED\s*BY|IMPORTER)\s*[:\-]?\s*([^\n]{3,80})", re.IGNORECASE)
_MFR_RE = re.compile(
    r"(?:MFD\.?\s*BY|MFG\.?\s*BY|MANUFACTURED\s*BY|MARKETED\s*BY|PACKED\s*BY|"
    r"MANUFACTURER)\s*[:\-]?\s*([^\n]{3,90})",
    re.IGNORECASE,
)
_CARE_RE = re.compile(
    r"(?:CONSUMER\s*CARE|CUSTOMER\s*CARE|CARE\s*CELL|GRIEVANCE|CONTACT\s*US)"
    r"\s*[:\-]?\s*([^\n]{3,90})",
    re.IGNORECASE,
)
_ADDRESS_RE = re.compile(r"\b\d{6}\b|\b(?:ROAD|STREET|INDUSTRIAL|NAGAR|DISTRICT|DIST\.?|PLOT|SECTOR|VILLAGE)\b", re.IGNORECASE)

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "food": ("INGREDIENT", "NUTRITION", "BEST BEFORE", "FSSAI", "NET WT"),
    "beverage": ("DRINK", "JUICE", "BEVERAGE", "CARBONATED", "ML"),
    "cosmetic": ("CREAM", "LOTION", "SHAMPOO", "SOAP", "SKIN", "COSMETIC"),
    "pharmaceutical": ("TABLET", "CAPSULE", "SYRUP", "DOSE", "MEDICINE", "IP"),
    "textile": ("COTTON", "POLYESTER", "FABRIC", "WASH CARE", "SIZE", "FIBRE", "FIBER"),
    "electronics": ("VOLT", "WATT", "HZ", "ADAPTOR", "ADAPTER", "BATTERY", "INPUT"),
    "household": ("DETERGENT", "CLEANER", "DISINFECTANT", "PHENYL", "FLOOR"),
}


def _first_line_match(regex: re.Pattern[str], text: str) -> Optional[str]:
    match = regex.search(text)
    if not match:
        return None
    value = re.sub(r"\s+", " ", match.group(1)).strip(" .,:;-")
    return value or None


def _guess_address(lines: list[str], anchor: Optional[str]) -> Optional[str]:
    """Pick the line following a manufacturer / consumer-care anchor."""
    if not anchor:
        return None
    if _ADDRESS_RE.search(anchor):
        # The anchor already reads as an address (it carries a pincode).
        return anchor.strip()
    for index, line in enumerate(lines):
        if anchor[:18].upper() in line.upper():
            for candidate in lines[index + 1 : index + 4]:
                if _ADDRESS_RE.search(candidate):
                    return candidate.strip()
    return None


def _split_name_address(line: Optional[str]) -> tuple[Optional[str], Optional[str]]:
    """Split a single printed line such as 'Amul Dairy, Anand, Gujarat 388001'."""
    if not line:
        return None, None
    if _ADDRESS_RE.search(line) and "," in line:
        head = line.split(",", 1)[0].strip(" .,:;-")
        return (head or line), line
    return line, None


def parse_ocr_text(text: str) -> dict[str, Any]:
    """Heuristically derive declarations from raw OCR text."""
    result = dict(_EMPTY_FIELDS)
    lines = [line.strip() for line in (text or "").splitlines() if line.strip()]
    upper_text = text.upper()

    result["all_visible_text"] = text.strip() or None

    mrp_match = _MRP_RE.search(upper_text)
    if mrp_match:
        value = mrp_match.group(1).replace(",", "")
        try:
            result["mrp_numeric"] = float(value)
        except ValueError:
            result["mrp_numeric"] = None
        start = max(0, mrp_match.start() - 4)
        result["mrp_raw"] = re.sub(r"\s+", " ", upper_text[start : mrp_match.end()]).strip()
        result["mrp_prefix"] = "MRP" if "MRP" in upper_text[mrp_match.start() : mrp_match.end() + 12] else None

    qty_match = _NET_QTY_RE.search(upper_text)
    if qty_match:
        result["net_quantity"] = re.sub(r"\s+", " ", qty_match.group(1)).strip()
        numeric = re.search(r"([\d.,]+)", result["net_quantity"])
        unit = re.search(r"([A-Za-z]+)$", result["net_quantity"])
        if numeric:
            try:
                result["net_quantity_numeric"] = float(numeric.group(1).replace(",", ""))
            except ValueError:
                result["net_quantity_numeric"] = None
        if unit:
            result["net_quantity_unit"] = unit.group(1)

    result["month_year_manufacture"] = _first_line_match(_MFG_DATE_RE, text)
    result["best_before_date"] = _first_line_match(_BEST_BEFORE_RE, text)
    if "BEST BEFORE" in upper_text or "USE BY" in upper_text:
        result["expiry_date"] = result["best_before_date"]
    result["batch_lot_number"] = _first_line_match(_BATCH_RE, upper_text)

    phone = _PHONE_RE.search(text)
    if phone:
        result["consumer_care_phone"] = phone.group(0).strip()
    email = _EMAIL_RE.search(text)
    if email:
        result["consumer_care_email"] = email.group(0).strip()

    fssai = _FSSAI_RE.search(text)
    if fssai:
        result["fssai_license"] = fssai.group(1)

    result["country_of_origin"] = _first_line_match(_ORIGIN_RE, text)
    importer = _first_line_match(_IMPORTER_RE, text)
    if importer:
        result["importer_name"] = importer
    result["is_imported"] = bool(importer or result["country_of_origin"]) or "IMPORTED" in upper_text

    manufacturer = _first_line_match(_MFR_RE, text)
    if manufacturer:
        name, inline_address = _split_name_address(manufacturer)
        result["manufacturer_name"] = name
        result["manufacturer_address"] = inline_address or _guess_address(lines, manufacturer)

    care = _first_line_match(_CARE_RE, text)
    if care:
        result["consumer_care_name"] = care
        result["consumer_care_address"] = _guess_address(lines, care)

    if lines:
        result["product_name"] = lines[0][:160]
        result["common_generic_name"] = lines[0][:160]

    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(keyword in upper_text for keyword in keywords):
            result["product_category"] = category
            break

    filled = sum(
        1
        for key, value in result.items()
        if key not in {"product_category", "is_imported", "all_visible_text", "extraction_confidence"}
        and value not in (None, "", [])
    )
    result["extraction_confidence"] = round(min(0.35 + filled * 0.05, 0.7), 2)
    result["font_size_readability"] = "unknown"
    result["extraction_notes"] = (
        "Extracted with Tesseract OCR heuristics (Gemini vision unavailable). "
        "Font size was not measured; Rule 10 could not be evaluated."
    )
    return result


def _run_ocr(image_path: str) -> dict[str, Any]:
    try:
        import pytesseract
    except ImportError as exc:  # pragma: no cover - depends on environment
        raise ExtractionError(
            "Gemini vision is unavailable and pytesseract is not installed. "
            "Set GEMINI_API_KEY or install tesseract-ocr and pytesseract."
        ) from exc

    try:
        image = prepare_for_ocr(image_path)
        text = pytesseract.image_to_string(image, config="--oem 3 --psm 6")
    except Exception as exc:  # noqa: BLE001 - TesseractNotFoundError etc.
        raise ExtractionError(
            "Gemini vision is unavailable and Tesseract OCR could not run: "
            f"{exc}. Set GEMINI_API_KEY or install the tesseract-ocr binary."
        ) from exc

    if not text.strip():
        raise ExtractionError("OCR produced no readable text from this image")

    extracted = parse_ocr_text(text)
    extracted["font_analysis"] = {
        "mrp_font_height_mm": None,
        "net_qty_font_height_mm": None,
        "overall_legibility": "unknown",
        "smallest_text_height_mm": None,
        "font_concerns": ["Font size could not be measured without AI vision"],
    }
    extracted["extraction_method"] = "ocr"
    extracted["model_used"] = "tesseract"
    return extracted


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────
async def extract_label_data(image_path: str, image_sha256: str | None = None) -> dict[str, Any]:
    """Extract declarations from a label image (cached, Gemini, then OCR)."""
    cache_model = settings.gemini_model if vision_engine() == "gemini" else "ocr"

    if image_sha256:
        cached = get_cached_extraction(image_sha256, cache_model)
        if cached:
            cached["extraction_method"] = "cached"
            return cached

    extracted: dict[str, Any]

    if vision_engine() == "gemini":
        try:
            extracted = await asyncio.to_thread(_run_gemini, image_path)
        except Exception as exc:  # noqa: BLE001 - graceful degradation
            logger.warning("Gemini extraction failed, falling back to OCR: %s", exc)
            try:
                extracted = await asyncio.to_thread(_run_ocr, image_path)
                extracted["extraction_notes"] = (
                    f"{extracted.get('extraction_notes') or ''} "
                    f"Gemini error: {type(exc).__name__}."
                ).strip()
            except ExtractionError:
                raise
    else:
        extracted = await asyncio.to_thread(_run_ocr, image_path)

    if image_sha256 and extracted.get("extraction_method") in {"gemini", "ocr"}:
        set_cached_extraction(image_sha256, cache_model, extracted)

    return extracted
