"""User accounts: administrators, enforcement officers and viewers."""

import enum

from sqlalchemy import Boolean, Column, DateTime, Enum, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base
from app.utils.enum_utils import enum_values


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OFFICER = "officer"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(
        Enum(UserRole, name="user_role", values_callable=enum_values),
        default=UserRole.OFFICER,
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    department = Column(String(255), nullable=True)
    employee_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    scans = relationship("Scan", back_populates="officer", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="officer")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<User {self.email} ({self.role})>"
