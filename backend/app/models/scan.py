"""Inspection scans: one uploaded label image plus its compliance verdict."""

import enum

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.utils.enum_utils import enum_values


class ScanStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class ComplianceStatus(str, enum.Enum):
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    PARTIAL = "partial"
    PENDING = "pending"


class Scan(Base):
    __tablename__ = "scans"

    id = Column(Integer, primary_key=True, index=True)
    scan_id = Column(String(64), unique=True, index=True, nullable=False)  # UUID
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True, index=True)

    image_url = Column(String(512), nullable=False)
    image_filename = Column(String(255), nullable=False)
    image_sha256 = Column(String(64), index=True, nullable=True)

    status = Column(
        Enum(ScanStatus, name="scan_status", values_callable=enum_values),
        default=ScanStatus.PENDING,
        nullable=False,
    )
    compliance_status = Column(
        Enum(ComplianceStatus, name="compliance_status", values_callable=enum_values),
        default=ComplianceStatus.PENDING,
        nullable=False,
    )
    compliance_score = Column(Float, nullable=True)  # 0-100

    # Raw Gemini / OCR payload and the rule-engine verdict.
    extracted_data = Column(JSON, nullable=True)
    compliance_result = Column(JSON, nullable=True)

    extraction_method = Column(String(32), nullable=True)  # gemini | ocr | cached
    error_message = Column(Text, nullable=True)

    location = Column(String(512), nullable=True)
    notes = Column(Text, nullable=True)
    total_violations = Column(Integer, default=0, nullable=False)
    critical_violations = Column(Integer, default=0, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    processing_started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    officer = relationship("User", back_populates="scans")
    product = relationship("Product", back_populates="scans")
    reports = relationship("Report", back_populates="scan", cascade="all, delete-orphan")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Scan {self.scan_id} {self.status}>"
