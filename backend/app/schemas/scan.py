"""Scan, extraction and compliance-result schemas."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from app.models.scan import ComplianceStatus, ScanStatus


class ExtractedDeclaration(BaseModel):
    """A single mandatory declaration found (or not found) on the label."""

    field: str
    value: Optional[str] = None
    detected: bool
    confidence: float = 0.0
    raw_text: Optional[str] = None


class ViolationItem(BaseModel):
    rule_id: str
    rule_title: str
    severity: str  # critical | major | minor
    description: str
    detected_value: Optional[str] = None
    required_value: Optional[str] = None
    recommendation: str


class ComplianceCheckResult(BaseModel):
    scan_id: Optional[str] = None
    overall_status: ComplianceStatus
    compliance_score: float
    total_checks: int
    passed_checks: int
    failed_checks: int
    total_violations: int
    critical_violations: int
    violations: list[ViolationItem] = []
    passed_checks_list: list[str] = []
    extracted_declarations: list[ExtractedDeclaration] = []
    summary: str


class ScanCreate(BaseModel):
    location: Optional[str] = None
    notes: Optional[str] = None


class ScanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    scan_id: str
    status: ScanStatus
    compliance_status: ComplianceStatus
    compliance_score: Optional[float] = None
    total_violations: int = 0
    critical_violations: int = 0
    image_url: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    officer_id: int
    extraction_method: Optional[str] = None


class ScanDetailResponse(ScanResponse):
    extracted_data: Optional[dict[str, Any]] = None
    compliance_result: Optional[dict[str, Any]] = None
    notes: Optional[str] = None
    location: Optional[str] = None
    error_message: Optional[str] = None


class ScanListResponse(BaseModel):
    total: int
    items: list[ScanResponse]
