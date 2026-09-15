"""Scan endpoints: upload a label image, then extract and adjudicate it."""

import asyncio
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.models.product import Product
from app.models.scan import ComplianceStatus, Scan, ScanStatus
from app.models.user import User, UserRole
from app.routes.auth import get_current_user, require_officer
from app.schemas.scan import ScanDetailResponse, ScanListResponse, ScanResponse
from app.services.cache_service import invalidate_extraction
from app.services.compliance_engine import run_compliance_check
from app.services.vision_service import extract_label_data, vision_engine
from app.utils.image_utils import (
    SUPPORTED_EXTENSIONS,
    SUPPORTED_MIME_TYPES,
    ImageValidationError,
    sha256_of_bytes,
    validate_image_bytes,
)
from app.utils.legal_rules import (
    CATEGORY_SPECIFIC_RULES,
    FONT_SIZE_REQUIREMENTS,
    LEGAL_METROLOGY_SOURCE,
    MANDATORY_DECLARATIONS,
    MRP_RULES,
    NET_QUANTITY_RULES,
    PROHIBITED_WORDS,
    get_all_rules,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan", tags=["Scan"])


# ─────────────────────────────────────────────────────────────────────────────
# Background pipeline
# ─────────────────────────────────────────────────────────────────────────────
def process_scan_task(scan_pk: int, image_path: str, image_sha256: str) -> None:
    """Extract declarations and adjudicate compliance for one scan.

    Runs in a worker thread with its own session: the request-scoped session is
    already closed by the time a background task executes.
    """
    db = SessionLocal()
    try:
        scan = db.get(Scan, scan_pk)
        if scan is None:
            logger.error("Scan %s disappeared before processing", scan_pk)
            return

        scan.status = ScanStatus.PROCESSING
        scan.processing_started_at = datetime.now(timezone.utc)
        db.commit()

        try:
            extracted = asyncio.run(extract_label_data(image_path, image_sha256))
            compliance = run_compliance_check(extracted, scan_id=scan.scan_id)

            scan.extracted_data = extracted
            scan.compliance_result = compliance
            scan.extraction_method = extracted.get("extraction_method")
            scan.status = ScanStatus.COMPLETED
            scan.compliance_status = ComplianceStatus(compliance["overall_status"])
            scan.compliance_score = compliance["compliance_score"]
            scan.total_violations = compliance["total_violations"]
            scan.critical_violations = compliance["critical_violations"]
            scan.completed_at = datetime.now(timezone.utc)
            scan.error_message = None

            _link_product(db, scan, extracted)
            db.commit()
        except Exception as exc:  # noqa: BLE001 - surfaced to the officer
            db.rollback()
            scan = db.get(Scan, scan_pk)
            if scan is not None:
                scan.status = ScanStatus.FAILED
                scan.error_message = str(exc)[:2000]
                scan.completed_at = datetime.now(timezone.utc)
                db.commit()
            logger.exception("Scan processing failed for scan %s", scan_pk)
    finally:
        db.close()


def _link_product(db: Session, scan: Scan, extracted: dict) -> None:
    """Attach the scan to a product row, reusing matches by barcode or name."""
    barcode = (extracted.get("barcode_ean") or "").strip() or None
    name = (extracted.get("product_name") or extracted.get("common_generic_name") or "").strip() or None

    product: Optional[Product] = None
    if barcode:
        product = db.execute(select(Product).where(Product.barcode == barcode)).scalars().first()
    if product is None and name:
        product = (
            db.execute(select(Product).where(func.lower(Product.name) == name.lower()))
            .scalars()
            .first()
        )

    if product is None:
        if not (name or barcode):
            return
        product = Product(
            name=name,
            barcode=barcode,
            category=extracted.get("product_category"),
            manufacturer_name=extracted.get("manufacturer_name") or extracted.get("packer_name"),
            manufacturer_address=extracted.get("manufacturer_address")
            or extracted.get("packer_address"),
            net_quantity=extracted.get("net_quantity"),
            mrp=extracted.get("mrp_numeric"),
            image_url=scan.image_url,
        )
        db.add(product)
        db.flush()
    else:
        # Keep the freshest values for the product master.
        product.category = extracted.get("product_category") or product.category
        product.manufacturer_name = (
            extracted.get("manufacturer_name") or product.manufacturer_name
        )
        product.net_quantity = extracted.get("net_quantity") or product.net_quantity
        product.mrp = extracted.get("mrp_numeric") or product.mrp

    scan.product_id = product.id


# ─────────────────────────────────────────────────────────────────────────────
# Rule reference (registered before /{scan_id} so it is not shadowed)
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/rules")
def list_legal_rules(current_user: User = Depends(get_current_user)):
    """Rule catalogue driving the compliance engine, for UI display."""
    return {
        "mandatory_declarations": get_all_rules(),
        "font_size_requirements": FONT_SIZE_REQUIREMENTS,
        "mrp_rules": MRP_RULES,
        "net_quantity_rules": NET_QUANTITY_RULES,
        "prohibited_words": PROHIBITED_WORDS,
        "category_specific_rules": CATEGORY_SPECIFIC_RULES,
        "total_rules": len(MANDATORY_DECLARATIONS),
        "source": LEGAL_METROLOGY_SOURCE,
    }


@router.get("/engine")
def extraction_engine(current_user: User = Depends(get_current_user)):
    """Which extraction engine this deployment will use."""
    return {
        "engine": vision_engine(),
        "model": settings.gemini_model if vision_engine() == "gemini" else "tesseract",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Upload & process
# ─────────────────────────────────────────────────────────────────────────────
@router.post("/upload", response_model=ScanResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_and_scan(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    location: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_officer),
):
    """Accept a label image and queue the AI compliance pipeline."""
    extension = Path(file.filename or "").suffix.lower()
    if file.content_type not in SUPPORTED_MIME_TYPES and extension not in SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400, detail="Only JPEG, PNG and WebP images are accepted"
        )

    content = await file.read()
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Image too large. Maximum allowed size is {settings.max_upload_size_mb}MB",
        )
    try:
        validate_image_bytes(content)
    except ImageValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    settings.upload_path.mkdir(parents=True, exist_ok=True)
    scan_uuid = str(uuid.uuid4())
    safe_extension = extension if extension in SUPPORTED_EXTENSIONS else ".jpg"
    filename = f"{scan_uuid}{safe_extension}"
    filepath = settings.upload_path / filename
    filepath.write_bytes(content)

    digest = sha256_of_bytes(content)
    scan = Scan(
        scan_id=scan_uuid,
        officer_id=current_user.id,
        image_url=f"/uploads/{filename}",
        image_filename=filename,
        image_sha256=digest,
        location=(location or "").strip() or None,
        notes=(notes or "").strip() or None,
        status=ScanStatus.PENDING,
        compliance_status=ComplianceStatus.PENDING,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)

    background_tasks.add_task(process_scan_task, scan.id, str(filepath), digest)
    return scan


@router.post("/{scan_id}/reprocess", response_model=ScanResponse)
def reprocess_scan(
    scan_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_officer),
):
    """Re-run extraction for a scan, bypassing the extraction cache."""
    scan = db.execute(select(Scan).where(Scan.scan_id == scan_id)).scalars().first()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    if current_user.role != UserRole.ADMIN and scan.officer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only reprocess your own scans")

    image_path = settings.upload_path / scan.image_filename
    if not image_path.exists():
        raise HTTPException(status_code=410, detail="The original image is no longer available")
    if scan.image_sha256:
        invalidate_extraction(
            scan.image_sha256,
            settings.gemini_model if vision_engine() == "gemini" else "ocr",
        )

    scan.status = ScanStatus.PENDING
    scan.compliance_status = ComplianceStatus.PENDING
    scan.error_message = None
    db.commit()
    db.refresh(scan)

    background_tasks.add_task(process_scan_task, scan.id, str(image_path), scan.image_sha256 or "")
    return scan


# ─────────────────────────────────────────────────────────────────────────────
# Read
# ─────────────────────────────────────────────────────────────────────────────
@router.get("/", response_model=ScanListResponse)
def list_scans(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status_filter: Optional[ScanStatus] = Query(None, alias="status"),
    compliance_status: Optional[ComplianceStatus] = None,
    q: Optional[str] = None,
    officer_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = select(Scan)
    if current_user.role != UserRole.ADMIN:
        base = base.where(Scan.officer_id == current_user.id)
    elif officer_id:
        base = base.where(Scan.officer_id == officer_id)

    if status_filter is not None:
        base = base.where(Scan.status == status_filter)
    if compliance_status is not None:
        base = base.where(Scan.compliance_status == compliance_status)
    if q:
        needle = f"%{q.strip()}%"
        base = base.where(
            or_(
                Scan.scan_id.ilike(needle),
                Scan.location.ilike(needle),
                Scan.notes.ilike(needle),
                Scan.image_filename.ilike(needle),
            )
        )

    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    items = (
        db.execute(base.order_by(Scan.created_at.desc()).offset(skip).limit(limit))
        .scalars()
        .all()
    )
    return ScanListResponse(total=int(total), items=list(items))


@router.get("/{scan_id}", response_model=ScanDetailResponse)
def get_scan_result(
    scan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    scan = db.execute(select(Scan).where(Scan.scan_id == scan_id)).scalars().first()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    # Reads are allowed for every authenticated role; writes are scoped above.
    return scan


@router.delete("/{scan_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scan(
    scan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_officer),
):
    scan = db.execute(select(Scan).where(Scan.scan_id == scan_id)).scalars().first()
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    if current_user.role != UserRole.ADMIN and scan.officer_id != current_user.id:
        raise HTTPException(status_code=403, detail="You can only delete your own scans")

    image_path = settings.upload_path / scan.image_filename
    db.delete(scan)
    db.commit()
    try:
        if image_path.exists():
            os.remove(image_path)
    except OSError as exc:  # pragma: no cover - filesystem edge case
        logger.warning("Could not delete image %s: %s", image_path, exc)
    return None
