"""Products observed during inspections."""

from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(512), nullable=True)
    barcode = Column(String(64), index=True, nullable=True)
    category = Column(String(64), nullable=True)
    manufacturer_name = Column(String(512), nullable=True)
    manufacturer_address = Column(Text, nullable=True)
    net_quantity = Column(String(128), nullable=True)
    mrp = Column(Float, nullable=True)
    image_url = Column(String(512), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    scans = relationship("Scan", back_populates="product")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Product {self.name!r}>"
