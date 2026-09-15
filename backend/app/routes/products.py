"""Product catalogue built from inspected packages."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.product import Product
from app.models.scan import Scan
from app.models.user import User, UserRole
from app.routes.auth import get_current_user, require_admin, require_officer
from app.schemas.product import (
    ProductDetailResponse,
    ProductListResponse,
    ProductResponse,
    ProductScanSummary,
)

router = APIRouter(prefix="/products", tags=["Products"])


@router.get("/", response_model=ProductListResponse)
def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    q: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Product)
    if q:
        needle = f"%{q.strip()}%"
        statement = statement.where(
            or_(
                Product.name.ilike(needle),
                Product.manufacturer_name.ilike(needle),
                Product.barcode.ilike(needle),
            )
        )
    if category:
        statement = statement.where(Product.category == category)

    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    items = (
        db.execute(statement.order_by(Product.created_at.desc()).offset(skip).limit(limit))
        .scalars()
        .all()
    )
    return ProductListResponse(total=int(total), items=list(items))


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rows = db.execute(
        select(Product.category, func.count(Product.id)).group_by(Product.category)
    ).all()
    return {
        "categories": [
            {"category": category or "other", "count": int(count)} for category, count in rows
        ]
    }


@router.get("/{product_id}", response_model=ProductDetailResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    scans = (
        db.execute(
            select(Scan)
            .where(Scan.product_id == product_id)
            .order_by(Scan.created_at.desc())
            .limit(50)
        )
        .scalars()
        .all()
    )
    detail = ProductDetailResponse.model_validate(product)
    detail.scans = [
        ProductScanSummary(
            scan_id=scan.scan_id,
            compliance_status=scan.compliance_status.value if scan.compliance_status else "pending",
            compliance_score=scan.compliance_score,
            total_violations=scan.total_violations or 0,
            created_at=scan.created_at,
        )
        for scan in scans
    ]
    return detail


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_officer),
):
    """Correct OCR/AI mistakes in the product master (officer override)."""
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    editable = {"name", "barcode", "category", "manufacturer_name", "manufacturer_address", "net_quantity", "mrp"}
    for field, value in payload.items():
        if field in editable:
            setattr(product, field, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    # Detach scans rather than cascading, so inspection history survives.
    for scan in db.execute(select(Scan).where(Scan.product_id == product_id)).scalars().all():
        scan.product_id = None
    db.delete(product)
    db.commit()
    return None
