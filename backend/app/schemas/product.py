"""Product schemas."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: Optional[str] = None
    barcode: Optional[str] = None
    category: Optional[str] = None
    manufacturer_name: Optional[str] = None
    manufacturer_address: Optional[str] = None
    net_quantity: Optional[str] = None
    mrp: Optional[float] = None
    image_url: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None


class ProductScanSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: str
    compliance_status: str
    compliance_score: Optional[float] = None
    total_violations: int = 0
    created_at: datetime


class ProductDetailResponse(ProductResponse):
    scans: list[ProductScanSummary] = []


class ProductListResponse(BaseModel):
    total: int
    items: list[ProductResponse]
