"""Generated compliance reports (PDF files on disk)."""

import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.utils.enum_utils import enum_values


class ReportFormat(str, enum.Enum):
    PDF = "pdf"
    JSON = "json"


class Report(Base):
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(String(64), unique=True, index=True, nullable=False)  # UUID
    scan_id = Column(Integer, ForeignKey("scans.id"), nullable=False, index=True)
    officer_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    title = Column(String(512), nullable=False)
    format = Column(
        Enum(ReportFormat, name="report_format", values_callable=enum_values),
        default=ReportFormat.PDF,
        nullable=False,
    )
    file_path = Column(String(1024), nullable=True)
    file_url = Column(String(512), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    scan = relationship("Scan", back_populates="reports")
    officer = relationship("User", back_populates="reports")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Report {self.report_id}>"
