"""Report schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.report import ReportFormat


class ReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    report_id: str
    scan_id: int
    officer_id: int
    title: str
    format: ReportFormat
    file_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    created_at: datetime


class ReportGenerateResponse(BaseModel):
    report_id: str
    download_url: str
    title: str


class ReportSummaryItem(ReportResponse):
    """Report row enriched with the parent scan reference."""

    scan_ref: Optional[str] = None
    compliance_status: Optional[str] = None
