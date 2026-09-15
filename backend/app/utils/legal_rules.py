"""
Legal Metrology (Packaged Commodities) Rules, 2011 — machine readable rule set.

The Department of Consumer Affairs maintains the official Act and Rules index,
including the Packaged Commodities Rules and amendment notifications:
https://consumeraffairs.gov.in/pages/legal-metrology-act
"""

import re
from typing import Any

LEGAL_METROLOGY_SOURCE = {
    "title": "Legal Metrology (Packaged Commodities) Rules, 2011",
    "publisher": "Department of Consumer Affairs, Ministry of Consumer Affairs, Food & Public Distribution",
    "url": "https://consumeraffairs.gov.in/pages/legal-metrology-act",
    "scope": "Core packaged-commodity declarations, SI quantity units, MRP and category-specific checks",
    "amendment_note": "The official page lists amendments through 2026; verify the latest notification before enforcement action.",
}

# ─────────────────────────────────────────────────────────────────────────────
# Rule 4 — mandatory declarations on every package
# ─────────────────────────────────────────────────────────────────────────────
MANDATORY_DECLARATIONS: dict[str, dict[str, Any]] = {
    "manufacturer_name": {
        "rule": "Rule 4(1)(a)",
        "title": "Name and Address of Manufacturer/Packer/Importer",
        "description": (
            "Every package must bear the name and complete address of the "
            "manufacturer, packer, or importer"
        ),
        "severity": "critical",
        "applicable_to": "all",
        "extraction_fields": ["manufacturer_name", "manufacturer_address"],
    },
    "net_quantity": {
        "rule": "Rule 4(1)(b)",
        "title": "Net Quantity",
        "description": (
            "Net quantity of the commodity in SI units (g, kg, ml, L, m, cm, sq m)"
        ),
        "severity": "critical",
        "applicable_to": "all",
        "extraction_fields": ["net_quantity"],
    },
    "month_year_manufacture": {
        "rule": "Rule 4(1)(c)",
        "title": "Month and Year of Manufacture/Packing/Import",
        "description": (
            "Month and year in which the commodity is manufactured, packed or imported"
        ),
        "severity": "critical",
        "applicable_to": "all",
        "extraction_fields": ["month_year_manufacture"],
    },
    "common_generic_name": {
        "rule": "Rule 4(1)(d)",
        "title": "Common or Generic Name",
        "description": "Common or generic name of the commodity must be declared",
        "severity": "major",
        "applicable_to": "all",
        "extraction_fields": ["common_generic_name", "product_name"],
    },
    "batch_lot_number": {
        "rule": "Rule 4(1)(e)",
        "title": "Batch/Lot Number",
        "description": "Batch number, lot number, or code number for traceability",
        "severity": "major",
        "applicable_to": "all",
        "extraction_fields": ["batch_lot_number"],
    },
    "mrp": {
        "rule": "Rule 4(1)(f)",
        "title": "Maximum Retail Price (MRP)",
        "description": (
            "MRP inclusive of all taxes in Indian Rupees, prefixed with 'MRP' or "
            "'MRP (Incl. of all taxes)'"
        ),
        "severity": "critical",
        "applicable_to": "all",
        "extraction_fields": ["mrp_raw", "mrp_numeric"],
    },
    "consumer_care_details": {
        "rule": "Rule 4(1)(g)",
        "title": "Consumer Care Details",
        "description": "Name, address, and contact details of consumer care / grievance cell",
        "severity": "major",
        "applicable_to": "all",
        "extraction_fields": [
            "consumer_care_name",
            "consumer_care_phone",
            "consumer_care_email",
        ],
    },
    "country_of_origin": {
        "rule": "Rule 4(1)(i)",
        "title": "Country of Origin",
        "description": "Country of origin required for imported commodities",
        "severity": "critical",
        "applicable_to": "imports",
        "extraction_fields": ["country_of_origin"],
    },
}

# Declarations that only apply to imported packages.
IMPORT_ONLY_KEYS = {"country_of_origin"}

# ─────────────────────────────────────────────────────────────────────────────
# Rule 10 — minimum height of numerals and letters
# ─────────────────────────────────────────────────────────────────────────────
FONT_SIZE_REQUIREMENTS: list[dict[str, Any]] = [
    {"min_qty_g": 0, "max_qty_g": 200, "min_height_mm": 1.0, "label": "up to 200g / 200ml"},
    {"min_qty_g": 200, "max_qty_g": 500, "min_height_mm": 2.0, "label": "200g-500g / 200ml-500ml"},
    {"min_qty_g": 500, "max_qty_g": 1000, "min_height_mm": 4.0, "label": "500g-1kg / 500ml-1L"},
    {"min_qty_g": 1000, "max_qty_g": float("inf"), "min_height_mm": 6.0, "label": "above 1kg / 1L"},
]

# ─────────────────────────────────────────────────────────────────────────────
# Rule 11 — MRP declaration format
# ─────────────────────────────────────────────────────────────────────────────
MRP_RULES: dict[str, Any] = {
    "prefix_required": True,
    "valid_prefixes": [
        "MRP",
        "MRP.",
        "MRP RS",
        "MRP RS.",
        "MRP ₹",
        "M.R.P",
        "M.R.P.",
        "MAXIMUM RETAIL PRICE",
    ],
    "tax_inclusion_phrases": ["incl", "inclusive", "all taxes"],
    "currency": "INR",
    "must_include_taxes": True,
    "format_note": "MRP Rs. XX.XX or MRP ₹XX.XX — inclusive of all taxes",
}

# ─────────────────────────────────────────────────────────────────────────────
# Rule 6 — net quantity units
# ─────────────────────────────────────────────────────────────────────────────
NET_QUANTITY_RULES: dict[str, Any] = {
    "units_weight": ["g", "kg", "mg", "gram", "grams", "kilogram", "kilograms"],
    "units_volume": ["ml", "l", "litre", "liter", "litres", "liters"],
    "units_length": ["m", "cm", "mm", "metre", "meter"],
    "units_area": ["sq m", "sq cm", "m2", "cm2", "sq ft"],
    "units_count": ["pieces", "piece", "pcs", "pc", "nos", "no", "numbers", "n"],
    "note": (
        "Must be in SI units. Dual declaration is allowed (e.g. 500g / 1.1 lb) "
        "but the SI unit must be primary."
    ),
}

# Rule 6 also permits these, mostly for imported / legacy packs.
ACCEPTED_QUANTITY_UNITS: set[str] = {
    unit.lower()
    for group in (
        "units_weight",
        "units_volume",
        "units_length",
        "units_area",
        "units_count",
    )
    for unit in NET_QUANTITY_RULES[group]
}

# Conversion factors to a gram / millilitre equivalent for font-size lookups.
UNIT_TO_BASE_FACTOR: dict[str, float] = {
    "mg": 0.001,
    "g": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "kg": 1000.0,
    "kilogram": 1000.0,
    "kilograms": 1000.0,
    "ml": 1.0,
    "l": 1000.0,
    "litre": 1000.0,
    "liter": 1000.0,
    "litres": 1000.0,
    "liters": 1000.0,
    "cm": 1.0,
    "mm": 0.1,
    "m": 100.0,
}

# ─────────────────────────────────────────────────────────────────────────────
# Rule 14 — misleading / prohibited words
# ─────────────────────────────────────────────────────────────────────────────
PROHIBITED_WORDS: list[str] = ["free", "extra", "bonus", "more", "larger", "bigger"]

# Only flag when the word is used to imply additional quantity.
MISLEADING_QUANTITY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\d+\s*%?\s*(free|extra|bonus)\b", re.IGNORECASE),
    re.compile(r"\b(free|extra|bonus)\s*\d+\s*(g|gm|kg|ml|l|litre|liter|piece|pcs|nos)\b", re.IGNORECASE),
    re.compile(r"\b(bonus|jumbo|mega)\s*(pack|size)\b", re.IGNORECASE),
]

# Phrases that legitimately contain a prohibited word and must not be flagged.
MISLEADING_FALSE_POSITIVES: list[str] = [
    "sugar free",
    "free from",
    "gluten free",
    "fat free",
    "duty free",
    "toll free",
    "free of cost",
    "preservative free",
    "cholesterol free",
    "lactose free",
]

# ─────────────────────────────────────────────────────────────────────────────
# Category specific declaration duties
# ─────────────────────────────────────────────────────────────────────────────
CATEGORY_SPECIFIC_RULES: dict[str, dict[str, dict[str, str]]] = {
    "food": {
        "best_before_expiry": {
            "rule": "Rule 4(1)(c)",
            "description": "Best before / expiry date required for food items",
            "severity": "critical",
        }
    },
    "beverage": {
        "best_before_expiry": {
            "rule": "Rule 4(1)(c)",
            "description": "Best before / expiry date required for beverages",
            "severity": "critical",
        }
    },
    "textile": {
        "fiber_content": {
            "rule": "Schedule II",
            "description": "Fiber/material composition percentage required",
            "severity": "major",
        }
    },
    "electronics": {
        "voltage_wattage": {
            "rule": "Schedule III",
            "description": "Voltage, wattage, or energy rating required",
            "severity": "major",
        }
    },
}

# Product categories the vision model may return.
PRODUCT_CATEGORIES: list[str] = [
    "food",
    "beverage",
    "cosmetic",
    "pharmaceutical",
    "textile",
    "electronics",
    "household",
    "other",
]


def get_required_font_size(net_quantity_grams: float) -> dict[str, Any]:
    """Minimum numeral height (mm) for a given net quantity in g/ml."""
    for rule in FONT_SIZE_REQUIREMENTS:
        if rule["min_qty_g"] <= net_quantity_grams < rule["max_qty_g"]:
            return rule
    return FONT_SIZE_REQUIREMENTS[-1]


def get_all_rules() -> list[dict[str, Any]]:
    """All mandatory declaration definitions, for the frontend rule browser."""
    return [{"key": key, **rule} for key, rule in MANDATORY_DECLARATIONS.items()]


def quantity_to_base(numeric: float | None, unit: str | None) -> float | None:
    """Convert a declared quantity to its gram / millilitre equivalent."""
    if numeric is None:
        return None
    if not unit:
        return float(numeric)
    return float(numeric) * UNIT_TO_BASE_FACTOR.get(unit.strip().lower(), 1.0)


_QUANTITY_RE = re.compile(
    r"(?P<numeric>\d+(?:\.\d+)?)\s*(?P<unit>"
    r"kgs?|kg|gms?|gm|g|mgs?|mg|mls?|ml|ltrs?|ltr|litres?|liters?|l|"
    r"cms?|cm|mms?|mm|sq\s*m|m2|cm2|pieces?|pcs?|nos?|numbers?)\b",
    re.IGNORECASE,
)

_UNIT_CANONICAL: dict[str, str] = {
    "kg": "kg", "kgs": "kg", "kilogram": "kg", "kilograms": "kg",
    "g": "g", "gm": "g", "gms": "g", "gram": "g", "grams": "g",
    "mg": "mg", "mgs": "mg",
    "l": "L", "ltr": "L", "ltrs": "L", "litre": "L", "liter": "L",
    "litres": "L", "liters": "L",
    "ml": "ml", "mls": "ml",
    "cm": "cm", "cms": "cm", "mm": "mm", "mms": "mm",
    "sq m": "sq m", "m2": "sq m", "cm2": "sq cm",
    "pc": "pcs", "pcs": "pcs", "piece": "pcs", "pieces": "pcs",
    "no": "nos", "nos": "nos", "number": "nos", "numbers": "nos",
}


def canonical_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    cleaned = unit.strip().lower().replace(".", "")
    return _UNIT_CANONICAL.get(cleaned, cleaned)


def parse_net_quantity(text: str | None) -> tuple[float | None, str | None]:
    """Extract (numeric, canonical unit) from a free-text net quantity string."""
    if not text:
        return None, None
    match = _QUANTITY_RE.search(str(text))
    if not match:
        return None, None
    return float(match.group("numeric")), canonical_unit(match.group("unit"))


def build_extraction_schema_hint() -> str:
    """Field list used to build the vision prompt (single source of truth)."""
    return ", ".join(sorted({f for r in MANDATORY_DECLARATIONS.values() for f in r["extraction_fields"]}))
