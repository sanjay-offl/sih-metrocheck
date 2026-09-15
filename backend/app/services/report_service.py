"""
Report generation.

Produces the official inspection report: a ReportLab PDF laid out like a
government document, plus a machine-readable JSON twin for downstream systems.
"""

import json
import os
import uuid
from datetime import datetime
from typing import Any, Optional
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Image,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.core.config import settings

GOVT_BLUE = colors.HexColor("#003580")
GOVT_RED = colors.HexColor("#8B0000")
GOVT_GREY = colors.HexColor("#555555")
LIGHT_BLUE = colors.HexColor("#F0F4FF")
LIGHT_GREY = colors.HexColor("#F8F9FA")
BORDER_GREY = colors.HexColor("#CCCCCC")

STATUS_COLORS = {
    "compliant": colors.HexColor("#059669"),
    "non_compliant": colors.HexColor("#DC2626"),
    "partial": colors.HexColor("#D97706"),
    "pending": GOVT_GREY,
}

SEVERITY_COLORS = {
    "critical": colors.HexColor("#DC2626"),
    "major": colors.HexColor("#D97706"),
    "minor": colors.HexColor("#059669"),
}

# Standard PDF fonts are Latin-1 only, so rupees and dashes need transliteration.
_CHAR_REPLACEMENTS = {
    "\u20b9": "Rs.",
    "\u2014": "-",
    "\u2013": "-",
    "\u2018": "'",
    "\u2019": "'",
    "\u201c": '"',
    "\u201d": '"',
    "\u2022": "-",
    "\u00a0": " ",
}


def _safe(value: Any) -> str:
    """Make arbitrary text safe for the built-in PDF fonts and para markup."""
    if value is None:
        return "—"
    text = str(value)
    for source, target in _CHAR_REPLACEMENTS.items():
        text = text.replace(source, target)
    text = text.encode("latin-1", "replace").decode("latin-1")
    return escape(text)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "masthead": ParagraphStyle(
            "masthead", parent=base["Normal"], fontSize=13, fontName="Helvetica-Bold",
            textColor=GOVT_BLUE, alignment=TA_CENTER, spaceAfter=1,
        ),
        "subhead": ParagraphStyle(
            "subhead", parent=base["Normal"], fontSize=8.5, textColor=GOVT_GREY,
            alignment=TA_CENTER, leading=11,
        ),
        "title": ParagraphStyle(
            "title", parent=base["Normal"], fontSize=12, fontName="Helvetica-Bold",
            textColor=GOVT_RED, alignment=TA_CENTER, spaceBefore=6, spaceAfter=2,
        ),
        "section": ParagraphStyle(
            "section", parent=base["Normal"], fontSize=9.5, fontName="Helvetica-Bold",
            textColor=GOVT_BLUE, spaceBefore=6, spaceAfter=4,
        ),
        "body": ParagraphStyle("body", parent=base["Normal"], fontSize=9, leading=13, alignment=TA_LEFT),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontSize=8, leading=10.5),
        "cellbold": ParagraphStyle(
            "cellbold", parent=base["Normal"], fontSize=8, leading=10.5, fontName="Helvetica-Bold"
        ),
        "cellgrey": ParagraphStyle(
            "cellgrey", parent=base["Normal"], fontSize=8, leading=10.5, textColor=GOVT_GREY
        ),
        "footer": ParagraphStyle(
            "footer", parent=base["Normal"], fontSize=7, textColor=GOVT_GREY,
            alignment=TA_CENTER, leading=9,
        ),
    }


def _meta_table(scan_data: dict[str, Any], officer_name: str, compliance_result: dict[str, Any], report_no: str) -> Table:
    status_key = compliance_result.get("overall_status", "pending")
    status_label = status_key.upper().replace("_", " ")
    score = compliance_result.get("compliance_score", 0)

    data = [
        ["Report No:", f"MC-{report_no}", "Date:", datetime.now().strftime("%d %b %Y %H:%M")],
        ["Scan ID:", str(scan_data.get("scan_id", "N/A"))[:18], "Officer:", officer_name],
        [
            "Location:",
            scan_data.get("location") or "Not specified",
            "Status:",
            status_label,
        ],
        ["Compliance Score:", f"{score}%", "Method:", scan_data.get("extraction_method") or "—"],
    ]
    table = Table(data, colWidths=[3.3 * cm, 6.4 * cm, 2.9 * cm, 4.4 * cm])
    table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold"),
                ("TEXTCOLOR", (0, 0), (0, -1), GOVT_BLUE),
                ("TEXTCOLOR", (2, 0), (2, -1), GOVT_BLUE),
                ("TEXTCOLOR", (3, 2), (3, 2), STATUS_COLORS.get(status_key, GOVT_GREY)),
                ("FONTNAME", (3, 2), (3, 2), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 0), (-1, -1), [LIGHT_BLUE, colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.3, BORDER_GREY),
                ("PADDING", (0, 0), (-1, -1), 5),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _banner(compliance_result: dict[str, Any], styles: dict[str, ParagraphStyle]) -> Table:
    status_key = compliance_result.get("overall_status", "pending")
    color = STATUS_COLORS.get(status_key, GOVT_GREY)
    status_label = status_key.upper().replace("_", " ")
    score = compliance_result.get("compliance_score", 0)
    scored = (
        f"{status_label} — compliance score {score}% "
        f"({compliance_result.get('passed_checks', 0)} of "
        f"{compliance_result.get('total_checks', 0)} checks passed)"
    )
    table = Table(
        [[Paragraph(f"<b>{_safe(scored)}</b>", ParagraphStyle(
            "banner", parent=styles["body"], fontSize=11, textColor=color, alignment=TA_CENTER
        ))]],
        colWidths=[17 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 1.2, color),
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FDFDFD")),
                ("PADDING", (0, 0), (-1, -1), 9),
            ]
        )
    )
    return table


def _stats_table(compliance_result: dict[str, Any]) -> Table:
    stats = [
        ("Total Checks", compliance_result.get("total_checks", 0), colors.HexColor("#374151")),
        ("Checks Passed", compliance_result.get("passed_checks", 0), colors.HexColor("#059669")),
        ("Total Violations", compliance_result.get("total_violations", 0), colors.HexColor("#D97706")),
        ("Critical Violations", compliance_result.get("critical_violations", 0), colors.HexColor("#DC2626")),
    ]
    data = [
        [Paragraph(f"<b>{_safe(label)}</b>", ParagraphStyle("s", parent=_styles()["cell"], alignment=TA_CENTER)) for label, _, _ in stats],
        [Paragraph(f"<b>{_safe(value)}</b>", ParagraphStyle("v", parent=_styles()["cell"], fontSize=16, alignment=TA_CENTER, textColor=color)) for _, value, color in stats],
    ]
    table = Table(data, colWidths=[4.25 * cm] * 4)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GREY),
                ("BOX", (0, 0), (-1, -1), 1, BORDER_GREY),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, 0), 5),
                ("BOTTOMPADDING", (0, 1), (-1, 1), 6),
            ]
        )
    )
    return table


def _declarations_table(extracted_data: dict[str, Any]) -> Table:
    rows: list[list[Any]] = [
        [
            Paragraph("<b>Declaration</b>", _styles()["cellbold"]),
            Paragraph("<b>Extracted Value</b>", _styles()["cellbold"]),
            Paragraph("<b>Rule</b>", _styles()["cellbold"]),
            Paragraph("<b>Status</b>", _styles()["cellbold"]),
        ]
    ]

    fields = [
        ("Manufacturer/Packer Name", extracted_data.get("manufacturer_name") or extracted_data.get("packer_name"), "4(1)(a)"),
        ("Manufacturer/Packer Address", extracted_data.get("manufacturer_address") or extracted_data.get("packer_address"), "4(1)(a)"),
        ("Common / Generic Name", extracted_data.get("common_generic_name") or extracted_data.get("product_name"), "4(1)(d)"),
        ("Net Quantity", extracted_data.get("net_quantity"), "4(1)(b)"),
        ("Month/Year of Manufacture", extracted_data.get("month_year_manufacture"), "4(1)(c)"),
        ("MRP", extracted_data.get("mrp_raw"), "4(1)(f)"),
        ("Batch / Lot Number", extracted_data.get("batch_lot_number"), "4(1)(e)"),
        ("Consumer Care Contact", extracted_data.get("consumer_care_phone") or extracted_data.get("consumer_care_email"), "4(1)(g)"),
        ("Country of Origin", extracted_data.get("country_of_origin"), "4(1)(i)"),
        ("Best Before / Expiry", extracted_data.get("best_before_date") or extracted_data.get("expiry_date"), "4(1)(c)"),
        ("FSSAI Licence", extracted_data.get("fssai_license"), "FSS Act"),
    ]

    style_commands: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), GOVT_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER_GREY),
        ("PADDING", (0, 0), (-1, -1), 4.5),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]

    for index, (label, value, rule) in enumerate(fields, start=1):
        present = value not in (None, "", "—")
        rows.append(
            [
                Paragraph(_safe(label), _styles()["cell"]),
                Paragraph(_safe(value) if present else "<i>Not found on label</i>", _styles()["cell"] if present else _styles()["cellgrey"]),
                Paragraph(_safe(rule), _styles()["cellgrey"]),
                Paragraph(
                    "<b>PRESENT</b>" if present else "<b>MISSING</b>",
                    ParagraphStyle(
                        "st",
                        parent=_styles()["cell"],
                        textColor=colors.HexColor("#059669") if present else colors.HexColor("#DC2626"),
                    ),
                ),
            ]
        )
    table = Table(rows, colWidths=[4.6 * cm, 7.4 * cm, 2.2 * cm, 2.8 * cm], repeatRows=1)
    table.setStyle(TableStyle(style_commands))
    return table


def _violation_block(index: int, violation: dict[str, Any]) -> Table:
    severity = (violation.get("severity") or "minor").lower()
    severity_color = SEVERITY_COLORS.get(severity, GOVT_GREY)
    styles = _styles()

    detail_rows = [
        ("Description", violation.get("description")),
        ("Detected", violation.get("detected_value") or "Not found"),
        ("Required", violation.get("required_value")),
        ("Recommended fix", violation.get("recommendation")),
    ]

    data: list[list[Any]] = [
        [
            Paragraph(f"<b>Violation {index}</b>", styles["cellbold"]),
            Paragraph(
                f"<b>{_safe(violation.get('rule_id'))}</b> — {_safe(violation.get('rule_title'))}",
                styles["cell"],
            ),
            Paragraph(
                f"<b>{severity.upper()}</b>",
                ParagraphStyle("sev", parent=styles["cell"], textColor=severity_color),
            ),
        ]
    ]
    for label, value in detail_rows:
        data.append(
            [
                Paragraph(_safe(label), styles["cellgrey"]),
                Paragraph(_safe(value) if value else "—", styles["cell"]),
                "",
            ]
        )

    table = Table(data, colWidths=[3.0 * cm, 11.6 * cm, 2.4 * cm])
    commands = [
        ("SPAN", (1, 1), (2, 1)),
        ("SPAN", (1, 2), (2, 2)),
        ("SPAN", (1, 3), (2, 3)),
        ("SPAN", (1, 4), (2, 4)),
        ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
        ("BOX", (0, 0), (-1, -1), 0.9, severity_color),
        ("LINEBELOW", (0, 0), (-1, 0), 0.4, severity_color),
        ("INNERGRID", (0, 1), (-1, -1), 0.2, colors.HexColor("#EEEEEE")),
        ("PADDING", (0, 0), (-1, -1), 4.5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]
    table.setStyle(TableStyle(commands))
    return table


def _check_matrix_table(check_matrix: list[dict[str, Any]]) -> Table:
    styles = _styles()
    rows: list[list[Any]] = [
        [
            Paragraph("<b>Rule</b>", styles["cellbold"]),
            Paragraph("<b>Declaration checked</b>", styles["cellbold"]),
            Paragraph("<b>Severity</b>", styles["cellbold"]),
            Paragraph("<b>Result</b>", styles["cellbold"]),
        ]
    ]
    commands: list[tuple] = [
        ("BACKGROUND", (0, 0), (-1, 0), GOVT_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GREY]),
        ("GRID", (0, 0), (-1, -1), 0.3, BORDER_GREY),
        ("PADDING", (0, 0), (-1, -1), 4),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]
    status_meta = {
        "pass": ("PASS", colors.HexColor("#059669")),
        "fail": ("FAIL", colors.HexColor("#DC2626")),
        "skipped": ("N/A", colors.HexColor("#6B7280")),
    }

    for index, check in enumerate(check_matrix, start=1):
        label, color = status_meta.get(check.get("status", "skipped"), ("—", GOVT_GREY))
        rows.append(
            [
                Paragraph(_safe(check.get("rule_id")), styles["cellgrey"]),
                Paragraph(_safe(check.get("title")), styles["cell"]),
                Paragraph(_safe(check.get("severity", "").title()), styles["cellgrey"]),
                Paragraph(
                    f"<b>{label}</b>",
                    ParagraphStyle("r", parent=styles["cell"], textColor=color),
                ),
            ]
        )
        commands.append(("TEXTCOLOR", (1, index), (1, index), colors.black))

    table = Table(rows, colWidths=[2.6 * cm, 9.2 * cm, 2.4 * cm, 2.8 * cm], repeatRows=1)
    table.setStyle(TableStyle(commands))
    return table


def _image_flowable(image_path: Optional[str]) -> Optional[Image]:
    """Embed a thumbnail of the inspected label when the file still exists."""
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        from PIL import Image as PILImage

        with PILImage.open(image_path) as source:
            width, height = source.size
        max_width, max_height = 7.2 * cm, 7.2 * cm
        scale = min(max_width / width, max_height / height, 1.0)
        return Image(image_path, width=width * scale, height=height * scale)
    except Exception:  # noqa: BLE001 - image embedding is a nice-to-have
        return None


def _page_furniture(canvas, doc) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(GOVT_GREY)
    canvas.drawString(2 * cm, 1.15 * cm, "MetroCheck — Legal Metrology Compliance System")
    canvas.drawRightString(A4[0] - 2 * cm, 1.15 * cm, f"Page {doc.page}")
    canvas.restoreState()


def generate_compliance_report_pdf(
    scan_data: dict[str, Any],
    extracted_data: dict[str, Any],
    compliance_result: dict[str, Any],
    officer_name: str,
    officer_department: Optional[str] = None,
    output_dir: Optional[str] = None,
    image_path: Optional[str] = None,
) -> str:
    """Render the inspection report; returns the absolute file path."""
    directory = output_dir or str(settings.reports_path)
    os.makedirs(directory, exist_ok=True)

    report_no = str(uuid.uuid4())[:8].upper()
    scan_ref = str(scan_data.get("scan_id") or report_no)[:12]
    filename = f"MetroCheck_Report_{scan_ref}.pdf"
    filepath = os.path.join(directory, filename)

    styles = _styles()
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.6 * cm,
        bottomMargin=1.8 * cm,
        title=f"MetroCheck Compliance Report {scan_ref}",
        author="MetroCheck — Department of Consumer Affairs",
        subject="Legal Metrology (Packaged Commodities) Rules, 2011 compliance inspection",
    )

    story: list[Any] = []

    # Header
    story.append(Paragraph("GOVERNMENT OF INDIA", styles["masthead"]))
    story.append(
        Paragraph(
            "Ministry of Consumer Affairs, Food &amp; Public Distribution<br/>"
            "Department of Consumer Affairs — Legal Metrology Division",
            styles["subhead"],
        )
    )
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=2, color=GOVT_BLUE))
    story.append(Paragraph("PACKAGED COMMODITY COMPLIANCE INSPECTION REPORT", styles["title"]))
    story.append(
        Paragraph(
            "Under the Legal Metrology (Packaged Commodities) Rules, 2011",
            styles["subhead"],
        )
    )
    story.append(HRFlowable(width="100%", thickness=1, color=GOVT_RED))
    story.append(Spacer(1, 10))

    # Metadata + banner
    story.append(_meta_table(scan_data, officer_name, compliance_result, report_no))
    story.append(Spacer(1, 10))
    story.append(_banner(compliance_result, styles))
    story.append(Spacer(1, 12))

    # Summary
    story.append(Paragraph("1. INSPECTION SUMMARY", styles["section"]))
    story.append(Paragraph(_safe(compliance_result.get("summary")), styles["body"]))
    story.append(Spacer(1, 10))
    story.append(_stats_table(compliance_result))
    story.append(Spacer(1, 14))

    # Label image + extraction context
    thumbnail = _image_flowable(image_path)
    extraction_rows = [
        ("Extraction engine", scan_data.get("extraction_method") or "—"),
        ("Extraction confidence", extracted_data.get("extraction_confidence") or "—"),
        ("Product category", extracted_data.get("product_category") or "other"),
        ("Imported package", "Yes" if extracted_data.get("is_imported") else "No"),
        ("OCR / AI notes", extracted_data.get("extraction_notes") or "—"),
    ]
    context_table = Table(
        [
            [
                Paragraph(f"<b>{_safe(label)}</b>", styles["cellgrey"]),
                Paragraph(_safe(value), styles["cell"]),
            ]
            for label, value in extraction_rows
        ],
        colWidths=[4.6 * cm, 12.4 * cm],
    )
    context_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.3, BORDER_GREY),
                ("BACKGROUND", (0, 0), (0, -1), LIGHT_GREY),
                ("PADDING", (0, 0), (-1, -1), 4.5),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )

    story.append(Paragraph("2. LABEL &amp; EXTRACTION DETAILS", styles["section"]))
    if thumbnail is not None:
        image_table = Table(
            [[thumbnail, context_table]],
            colWidths=[7.6 * cm, 9.4 * cm],
        )
        image_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (1, 0), (1, 0), 8),
                    ("BOX", (0, 0), (0, 0), 0.3, BORDER_GREY),
                    ("PADDING", (0, 0), (0, 0), 4),
                ]
            )
        )
        story.append(image_table)
    else:
        story.append(context_table)
    story.append(Spacer(1, 14))

    # Declarations
    story.append(Paragraph("3. EXTRACTED MANDATORY DECLARATIONS", styles["section"]))
    story.append(_declarations_table(extracted_data))
    story.append(Spacer(1, 14))

    # Violations
    violations = compliance_result.get("violations") or []
    story.append(Paragraph("4. VIOLATION DETAILS", styles["section"]))
    if violations:
        for index, violation in enumerate(violations, start=1):
            story.append(KeepTogether([_violation_block(index, violation), Spacer(1, 8)]))
    else:
        story.append(
            Paragraph(
                "No violations detected. The package was found compliant with every rule "
                "evaluated in this inspection.",
                ParagraphStyle("ok", parent=styles["body"], textColor=colors.HexColor("#059669")),
            )
        )
    story.append(Spacer(1, 12))

    # Check matrix
    check_matrix = compliance_result.get("check_matrix") or []
    if check_matrix:
        story.append(PageBreak())
        story.append(Paragraph("5. RULE-BY-RULE CHECK MATRIX", styles["section"]))
        story.append(Paragraph(
            "Every rule evaluated during this inspection, including those that were "
            "not applicable to this package.",
            styles["subhead"],
        ))
        story.append(Spacer(1, 6))
        story.append(_check_matrix_table(check_matrix))

        skipped = compliance_result.get("skipped_checks") or []
        if skipped:
            story.append(Spacer(1, 8))
            story.append(Paragraph("Checks that could not be evaluated", styles["section"]))
            for item in skipped:
                story.append(Paragraph(f"• {_safe(item)}", styles["cellgrey"]))

    story.append(Spacer(1, 16))

    # Signature block
    signature_data = [
        [
            Paragraph(
                f"<b>Inspecting Officer:</b> {_safe(officer_name)}"
                + (f"<br/><b>Department:</b> {_safe(officer_department)}" if officer_department else ""),
                styles["cell"],
            ),
            Paragraph(
                "Signature: ____________________<br/><br/>"
                "Date: ____________________&nbsp;&nbsp;&nbsp;Place: ____________________",
                styles["cell"],
            ),
        ]
    ]
    signature = Table(signature_data, colWidths=[8.5 * cm, 8.5 * cm])
    signature.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, GOVT_BLUE),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, BORDER_GREY),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(signature)
    story.append(Spacer(1, 12))

    story.append(HRFlowable(width="100%", thickness=0.8, color=GOVT_BLUE))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"This report was generated by the MetroCheck AI compliance system on "
            f"{datetime.now().strftime('%d %b %Y at %H:%M')} IST for scan "
            f"{_safe(scan_ref)}. It is an automated assessment and is subject to review "
            f"by a legal metrology officer before any enforcement action is taken. "
            f"Rule references are to the Legal Metrology (Packaged Commodities) Rules, 2011.",
            styles["footer"],
        )
    )

    doc.build(story, onFirstPage=_page_furniture, onLaterPages=_page_furniture)
    return filepath


def generate_compliance_report_json(
    scan_data: dict[str, Any],
    extracted_data: dict[str, Any],
    compliance_result: dict[str, Any],
    officer_name: str,
    output_dir: Optional[str] = None,
) -> str:
    """Write the machine-readable twin of the PDF report."""
    directory = output_dir or str(settings.reports_path)
    os.makedirs(directory, exist_ok=True)

    scan_ref = str(scan_data.get("scan_id") or uuid.uuid4())[:12]
    filepath = os.path.join(directory, f"MetroCheck_Report_{scan_ref}.json")

    payload = {
        "generated_at": datetime.now().isoformat(),
        "generated_by": officer_name,
        "system": "MetroCheck",
        "scan": scan_data,
        "extracted_data": extracted_data,
        "compliance_result": compliance_result,
    }
    with open(filepath, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)

    return filepath
