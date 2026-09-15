"""Seed the database with the initial administrator and demo officers.

Usage:
    cd backend && python seed.py
"""

import sys
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select

from app.core.database import Base, SessionLocal, engine
from app.core.security import get_password_hash
from app.models.product import Product
from app.models.report import Report, ReportFormat
from app.models.scan import ComplianceStatus, Scan, ScanStatus
from app.models.user import User, UserRole

BASE_USERS = [
    {
        "email": "admin@metrocheck.gov.in",
        "full_name": "System Admin",
        "password": "Admin@1234",
        "role": UserRole.ADMIN,
        "department": "Administration",
        "employee_id": "ADMIN001",
    },
    {
        "email": "officer1@metrocheck.gov.in",
        "full_name": "Rajesh Kumar",
        "password": "Officer@1234",
        "role": UserRole.OFFICER,
        "department": "Enforcement - Delhi",
        "employee_id": "OFF001",
    },
    {
        "email": "officer2@metrocheck.gov.in",
        "full_name": "Priya Sharma",
        "password": "Officer@1234",
        "role": UserRole.OFFICER,
        "department": "Enforcement - Mumbai",
        "employee_id": "OFF002",
    },
    {
        "email": "viewer@metrocheck.gov.in",
        "full_name": "Audit Viewer",
        "password": "Viewer@1234",
        "role": UserRole.VIEWER,
        "department": "Audit & Review",
        "employee_id": "VIEW001",
    },
]


DEMO_PRODUCTS = [
    {
        "name": "Aarogya Rice 5kg",
        "barcode": "8901234567890",
        "category": "Food & Beverage",
        "manufacturer_name": "Aarogya Foods Pvt. Ltd.",
        "manufacturer_address": "Plot 12, Industrial Area, Delhi",
        "net_quantity": "5 kg",
        "mrp": 245.0,
        "image_url": "/uploads/demo/rice-5kg.png",
    },
    {
        "name": "CleanSip Mineral Water 1L",
        "barcode": "8909876543210",
        "category": "Beverages",
        "manufacturer_name": "CleanSip Beverages",
        "manufacturer_address": "B-14, GIDC, Ahmedabad",
        "net_quantity": "1 litre",
        "mrp": 42.0,
        "image_url": "/uploads/demo/water-1l.png",
    },
    {
        "name": "Swasthya Masala Mix",
        "barcode": "8904567891234",
        "category": "Spices",
        "manufacturer_name": "Swasthya Nutrition",
        "manufacturer_address": "Sector 18, Hyderabad",
        "net_quantity": "200 g",
        "mrp": 88.0,
        "image_url": "/uploads/demo/masala-200g.png",
    },
    {
        "name": "MetroCare Handwash 250ml",
        "barcode": "8903216549870",
        "category": "Household",
        "manufacturer_name": "MetroCare Hygiene",
        "manufacturer_address": "14/7, Pune MIDC",
        "net_quantity": "250 ml",
        "mrp": 120.0,
        "image_url": "/uploads/demo/handwash-250ml.png",
    },
]


DEMO_SCAN_SPECS = [
    {
        "officer_email": "officer1@metrocheck.gov.in",
        "product_name": "Aarogya Rice 5kg",
        "location": "Kashmere Gate Market, Delhi",
        "status": ScanStatus.COMPLETED,
        "compliance_status": ComplianceStatus.NON_COMPLIANT,
        "compliance_score": 68.0,
        "total_violations": 3,
        "critical_violations": 1,
        "extracted_data": {
            "product_name": "Aarogya Rice",
            "manufacturer_name": "Aarogya Foods Pvt. Ltd.",
            "net_quantity": "5 kg",
            "batch_code": "AR-134",
            "month_year_manufacture": "08/2026",
        },
        "compliance_result": {
            "overall_status": "non_compliant",
            "compliance_score": 68,
            "total_checks": 12,
            "passed_checks": 8,
            "total_violations": 3,
            "critical_violations": 1,
            "violations": [
                {
                    "rule_id": "FSSAI-014",
                    "rule_title": "Mandatory net quantity not prominently displayed",
                    "severity": "critical",
                    "recommendation": "Print net quantity in a clear font on the front panel.",
                },
                {
                    "rule_id": "FSSAI-021",
                    "rule_title": "Manufacturing date not visible",
                    "severity": "major",
                    "recommendation": "Add manufacturing month and year on the pack.",
                },
                {
                    "rule_id": "FSSAI-041",
                    "rule_title": "Label not aligned with declaration standards",
                    "severity": "minor",
                    "recommendation": "Align the font and placement to approved packaging standards.",
                },
            ],
        },
        "days_ago": 1,
    },
    {
        "officer_email": "officer2@metrocheck.gov.in",
        "product_name": "CleanSip Mineral Water 1L",
        "location": "Lower Parel, Mumbai",
        "status": ScanStatus.COMPLETED,
        "compliance_status": ComplianceStatus.COMPLIANT,
        "compliance_score": 94.0,
        "total_violations": 0,
        "critical_violations": 0,
        "extracted_data": {
            "product_name": "CleanSip Mineral Water",
            "manufacturer_name": "CleanSip Beverages",
            "net_quantity": "1 litre",
            "batch_code": "CS-204",
            "month_year_manufacture": "09/2026",
        },
        "compliance_result": {
            "overall_status": "compliant",
            "compliance_score": 94,
            "total_checks": 11,
            "passed_checks": 11,
            "total_violations": 0,
            "critical_violations": 0,
            "violations": [],
        },
        "days_ago": 3,
    },
    {
        "officer_email": "officer1@metrocheck.gov.in",
        "product_name": "Swasthya Masala Mix",
        "location": "Nagar Chowk, Jaipur",
        "status": ScanStatus.COMPLETED,
        "compliance_status": ComplianceStatus.PARTIAL,
        "compliance_score": 81.0,
        "total_violations": 2,
        "critical_violations": 0,
        "extracted_data": {
            "product_name": "Swasthya Masala Mix",
            "manufacturer_name": "Swasthya Nutrition",
            "net_quantity": "200 g",
            "batch_code": "SM-089",
            "month_year_manufacture": "05/2026",
        },
        "compliance_result": {
            "overall_status": "partial",
            "compliance_score": 81,
            "total_checks": 10,
            "passed_checks": 8,
            "total_violations": 2,
            "critical_violations": 0,
            "violations": [
                {
                    "rule_id": "FSSAI-029",
                    "rule_title": "Ingredient list is incomplete",
                    "severity": "major",
                    "recommendation": "Add a complete ingredients declaration in the approved format.",
                },
                {
                    "rule_id": "FSSAI-052",
                    "rule_title": "Batch/lot code missing from front display",
                    "severity": "minor",
                    "recommendation": "Place batch and lot details next to the barcode.",
                },
            ],
        },
        "days_ago": 6,
    },
    {
        "officer_email": "officer2@metrocheck.gov.in",
        "product_name": "MetroCare Handwash 250ml",
        "location": "Bandra West, Mumbai",
        "status": ScanStatus.PROCESSING,
        "compliance_status": ComplianceStatus.PENDING,
        "compliance_score": None,
        "total_violations": 0,
        "critical_violations": 0,
        "extracted_data": {
            "product_name": "MetroCare Handwash",
            "manufacturer_name": "MetroCare Hygiene",
            "net_quantity": "250 ml",
            "batch_code": "MC-118",
            "month_year_manufacture": "10/2026",
        },
        "compliance_result": {
            "overall_status": "pending",
            "compliance_score": 0,
            "total_checks": 0,
            "passed_checks": 0,
            "total_violations": 0,
            "critical_violations": 0,
            "violations": [],
        },
        "days_ago": 9,
    },
]


def _seed_users(db):
    created = 0
    for spec in BASE_USERS:
        found = db.execute(select(User).where(User.email == spec["email"])).scalars().first()
        if found:
            continue
        db.add(
            User(
                email=spec["email"],
                full_name=spec["full_name"],
                hashed_password=get_password_hash(spec["password"]),
                role=spec["role"],
                department=spec["department"],
                employee_id=spec["employee_id"],
            )
        )
        created += 1
    db.commit()
    return created


def _seed_products(db):
    created = 0
    for spec in DEMO_PRODUCTS:
        found = db.execute(select(Product).where(Product.barcode == spec["barcode"])).scalars().first()
        if found:
            continue
        db.add(
            Product(
                name=spec["name"],
                barcode=spec["barcode"],
                category=spec["category"],
                manufacturer_name=spec["manufacturer_name"],
                manufacturer_address=spec["manufacturer_address"],
                net_quantity=spec["net_quantity"],
                mrp=spec["mrp"],
                image_url=spec["image_url"],
            )
        )
        created += 1
    db.commit()
    return created


def _seed_scans_and_reports(db):
    user_map = {user.email: user for user in db.execute(select(User)).scalars().all()}
    product_map = {product.name: product for product in db.execute(select(Product)).scalars().all()}

    created_scans = 0
    for spec in DEMO_SCAN_SPECS:
        officer = user_map.get(spec["officer_email"])
        product = product_map.get(spec["product_name"])
        if not officer or not product:
            continue

        scan = Scan(
            scan_id=str(uuid4()),
            officer_id=officer.id,
            product_id=product.id,
            image_url=f"/uploads/demo/{product.id}.jpg",
            image_filename=f"{product.id}.jpg",
            image_sha256=f"{uuid4().hex[:16]}",
            status=spec["status"],
            compliance_status=spec["compliance_status"],
            compliance_score=spec["compliance_score"],
            extracted_data=spec["extracted_data"],
            compliance_result=spec["compliance_result"],
            extraction_method="gemini",
            location=spec["location"],
            notes="Demo inspection record for local preview with realistic compliance outcomes.",
            total_violations=spec["total_violations"],
            critical_violations=spec["critical_violations"],
            created_at=datetime.now(timezone.utc) - timedelta(days=spec["days_ago"]),
            processing_started_at=(datetime.now(timezone.utc) - timedelta(days=spec["days_ago"])) if spec["status"] != ScanStatus.PENDING else None,
            completed_at=(datetime.now(timezone.utc) - timedelta(days=spec["days_ago"])) if spec["status"] == ScanStatus.COMPLETED else None,
        )
        db.add(scan)
        db.flush()

        report = Report(
            report_id=f"MC-{uuid4().hex[:8].upper()}",
            scan_id=scan.id,
            officer_id=officer.id,
            title=f"Inspection Report - {product.name}",
            format=ReportFormat.PDF,
            file_path=f"/generated_reports/{scan.scan_id}.pdf",
            file_url=f"/generated_reports/{scan.scan_id}.pdf",
            file_size_bytes=204800 + product.id * 100,
        )
        db.add(report)
        created_scans += 1

    db.commit()
    return created_scans


def seed() -> int:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    user_created, existing = 0, 0
    try:
        user_created = _seed_users(db)
        product_created = _seed_products(db)
        scan_created = _seed_scans_and_reports(db)

        for spec in BASE_USERS:
            found = db.execute(select(User).where(User.email == spec["email"])).scalars().first()
            if found:
                existing += 1
    finally:
        db.close()

    print("=" * 68)
    print(" MetroCheck seed complete")
    print("=" * 68)
    print(f" Users created : {user_created}")
    print(f" Products created : {product_created}")
    print(f" Demo scans created : {scan_created}")
    print(f" Users skipped : {existing} (already present)")
    print("-" * 68)
    for spec in BASE_USERS:
        print(f" {spec['role'].value:<8} {spec['email']:<32} {spec['password']}")
    print(" Demo products in the dashboard:")
    for spec in DEMO_PRODUCTS:
        print(f" - {spec['name']} ({spec['category']})")
    print("-" * 68)
    print(" Change these passwords before any non-demo deployment.")
    print("=" * 68)
    return 0


if __name__ == "__main__":
    sys.exit(seed())
