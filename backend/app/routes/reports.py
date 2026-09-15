"""Compliance report endpoints (PDF and JSON)."""

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.report import Report, ReportFormat
from app.models.scan import Scan
from app.models.user import User, UserRole
from app.routes.auth import get_current_user, require_officer
from app.schemas.report import ReportGenerateResponse, ReportResponse, ReportSummaryItem
from app.services.report_service import (
    generate_compliance_report_json,
    generate_compliance_report_pdf,
)

router = APIRouter(prefix="/reports", tags=["Reports"])

MEDIA_TYPES = {
    ReportFormat.PDF: "application/pdf",
    ReportFormat.JSON: "application/json",
}


def _download_url(report_id: str) -> str:
    return f"/api/v1/reports/download/{report_id}"


def _scan_or_404(db: Session, scan_id: str) -> Scan:
    scan = db.execute(select(Scan).where(Scan.scan_id == scan_id)).scalars().first()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.post("/generate/{scan_id}", response_model=ReportGenerateResponse)
def generate_report(
    scan_id: str,
    format: ReportFormat = Query(ReportFormat.PDF, description="pdf or json"),
    force: bool = Query(False, description="Regenerate even if a report exists"),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_officer),
):
    """Render (or re-render) the official report for a completed scan."""
    scan = _scan_or_404(db, scan_id)
    if scan.status.value != "completed" or not scan.compliance_result:
        raise HTTPException(status_code=400, detail="Scan has not finished processing yet")

    existing = (
        db.execute(
            select(Report).where(Report.scan_id == scan.id, Report.format == format)
        )
        .scalars()
        .first()
    )
    if existing and not force and existing.file_path and os.path.exists(existing.file_path):
        return ReportGenerateResponse(
            report_id=existing.report_id,
            download_url=_download_url(existing.report_id),
            title=existing.title,
        )

    scan_data = {
        "scan_id": scan.scan_id,
        "location": scan.location,
        "notes": scan.notes,
        "created_at": scan.created_at.isoformat() if scan.created_at else None,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
        "extraction_method": scan.extraction_method,
        "image_url": scan.image_url,
    }
    image_path = settings.upload_path / scan.image_filename

    if format == ReportFormat.PDF:
        file_path = generate_compliance_report_pdf(
            scan_data=scan_data,
            extracted_data=scan.extracted_data or {},
            compliance_result=scan.compliance_result or {},
            officer_name=current_user.full_name,
            officer_department=current_user.department,
            image_path=str(image_path) if image_path.exists() else None,
        )
    else:
        file_path = generate_compliance_report_json(
            scan_data=scan_data,
            extracted_data=scan.extracted_data or {},
            compliance_result=scan.compliance_result or {},
            officer_name=current_user.full_name,
        )

    title = f"Compliance Report — {scan.scan_id[:8].upper()} ({format.value.upper()})"
    file_size = os.path.getsize(file_path) if os.path.exists(file_path) else None

    if existing:
        existing.file_path = file_path
        existing.file_size_bytes = file_size
        existing.title = title
        report = existing
    else:
        report = Report(
            report_id=str(uuid.uuid4()),
            scan_id=scan.id,
            officer_id=current_user.id,
            title=title,
            format=format,
            file_path=file_path,
            file_url=None,
            file_size_bytes=file_size,
        )
        db.add(report)

    db.flush()
    report.file_url = _download_url(report.report_id)
    db.commit()
    db.refresh(report)

    return ReportGenerateResponse(
        report_id=report.report_id,
        download_url=report.file_url,
        title=report.title,
    )


@router.get("/", response_model=list[ReportSummaryItem])
def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Report).order_by(Report.created_at.desc()).offset(skip).limit(limit)
    if current_user.role != UserRole.ADMIN:
        statement = statement.where(Report.officer_id == current_user.id)

    reports = db.execute(statement).scalars().all()
    items: list[ReportSummaryItem] = []
    for report in reports:
        item = ReportSummaryItem.model_validate(report)
        scan = db.get(Scan, report.scan_id)
        if scan is not None:
            item.scan_ref = scan.scan_id
            item.compliance_status = (
                scan.compliance_status.value if scan.compliance_status else None
            )
        items.append(item)
    return items


@router.get("/{report_id}", response_model=ReportSummaryItem)
def get_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = (
        db.execute(select(Report).where(Report.report_id == report_id)).scalars().first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    item = ReportSummaryItem.model_validate(report)
    scan = db.get(Scan, report.scan_id)
    if scan is not None:
        item.scan_ref = scan.scan_id
        item.compliance_status = scan.compliance_status.value if scan.compliance_status else None
    return item


@router.get("/download/{report_id}")
def download_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = (
        db.execute(select(Report).where(Report.report_id == report_id)).scalars().first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if not report.file_path or not os.path.exists(report.file_path):
        raise HTTPException(status_code=410, detail="Report file is no longer available")

    extension = "pdf" if report.format == ReportFormat.PDF else "json"
    scan = db.get(Scan, report.scan_id)
    scan_ref = (scan.scan_id[:8].upper() if scan else report.report_id[:8].upper())

    return FileResponse(
        report.file_path,
        media_type=MEDIA_TYPES.get(report.format, "application/octet-stream"),
        filename=f"MetroCheck_Report_{scan_ref}.{extension}",
    )


@router.delete("/{report_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report(
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = (
        db.execute(select(Report).where(Report.report_id == report_id)).scalars().first()
    )
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    if current_user.role != UserRole.ADMIN and report.officer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own reports")

    file_path: Optional[str] = report.file_path
    db.delete(report)
    db.commit()
    if file_path and os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:  # pragma: no cover - filesystem edge case
            pass
    return None
