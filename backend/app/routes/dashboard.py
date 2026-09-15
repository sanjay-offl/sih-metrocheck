"""Dashboard analytics for the enforcement console."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.scan import ComplianceStatus, Scan, ScanStatus
from app.models.user import User, UserRole
from app.routes.auth import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


def _apply_scope(statement, current_user: User, officer_id: int | None = None):
    """Administrators see everything; everyone else sees their own work.

    Works for both entity selects and aggregate selects, provided the caller
    has already anchored the FROM clause with ``Scan``.
    """
    if current_user.role != UserRole.ADMIN:
        return statement.where(Scan.officer_id == current_user.id)
    if officer_id:
        return statement.where(Scan.officer_id == officer_id)
    return statement


@router.get("/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = _apply_scope(select(Scan), current_user)

    def count_where(*criteria) -> int:
        statement = base
        for criterion in criteria:
            statement = statement.where(criterion)
        return int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)

    total_scans = count_where()
    completed = count_where(Scan.status == ScanStatus.COMPLETED)
    processing = count_where(Scan.status.in_([ScanStatus.PENDING, ScanStatus.PROCESSING]))
    failed = count_where(Scan.status == ScanStatus.FAILED)
    compliant = count_where(Scan.compliance_status == ComplianceStatus.COMPLIANT)
    non_compliant = count_where(Scan.compliance_status == ComplianceStatus.NON_COMPLIANT)
    partial = count_where(Scan.compliance_status == ComplianceStatus.PARTIAL)

    aggregate = db.execute(
        _apply_scope(
            select(
                func.avg(Scan.compliance_score),
                func.sum(Scan.total_violations),
                func.sum(Scan.critical_violations),
            ).select_from(Scan),
            current_user,
        )
    ).one()
    avg_score = float(aggregate[0] or 0)
    total_violations = int(aggregate[1] or 0)
    critical_violations = int(aggregate[2] or 0)

    recent_scans = (
        db.execute(base.order_by(Scan.created_at.desc()).limit(5)).scalars().all()
    )

    return {
        "total_scans": total_scans,
        "completed_scans": completed,
        "processing_scans": processing,
        "failed_scans": failed,
        "compliant": compliant,
        "non_compliant": non_compliant,
        "partial": partial,
        "average_compliance_score": round(avg_score, 1),
        "total_violations": total_violations,
        "critical_violations": critical_violations,
        "compliance_rate": round(compliant / total_scans * 100, 1) if total_scans else 0.0,
        "recent_scans": [
            {
                "scan_id": scan.scan_id,
                "status": scan.compliance_status.value if scan.compliance_status else "pending",
                "scan_status": scan.status.value if scan.status else "pending",
                "score": scan.compliance_score,
                "violations": scan.total_violations,
                "location": scan.location,
                "created_at": scan.created_at.isoformat() if scan.created_at else None,
            }
            for scan in recent_scans
        ],
    }


@router.get("/trends")
def get_trends(
    days: int = Query(14, ge=1, le=180),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Daily inspection volume, compliance mix and average score."""
    since = datetime.now(timezone.utc) - timedelta(days=days - 1)
    statement = _apply_scope(select(Scan).where(Scan.created_at >= since), current_user)
    scans = db.execute(statement.order_by(Scan.created_at.asc())).scalars().all()

    buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {"scans": 0, "compliant": 0, "non_compliant": 0, "partial": 0, "_scores": []}
    )
    for scan in scans:
        if not scan.created_at:
            continue
        day = scan.created_at.date().isoformat()
        bucket = buckets[day]
        bucket["scans"] += 1
        status_value = scan.compliance_status.value if scan.compliance_status else "pending"
        if status_value in ("compliant", "non_compliant", "partial"):
            bucket[status_value] += 1
        if scan.compliance_score is not None:
            bucket["_scores"].append(scan.compliance_score)

    today = datetime.now(timezone.utc).date()
    series = []
    for offset in range(days - 1, -1, -1):
        day = (today - timedelta(days=offset)).isoformat()
        bucket = buckets.get(day) or {"scans": 0, "compliant": 0, "non_compliant": 0, "partial": 0, "_scores": []}
        scores = bucket.pop("_scores", [])
        series.append(
            {
                "date": day,
                **bucket,
                "average_score": round(sum(scores) / len(scores), 1) if scores else 0.0,
            }
        )
    return {"days": days, "series": series}


@router.get("/violations")
def get_violation_breakdown(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rank the most frequently breached rules across recent inspections."""
    statement = _apply_scope(
        select(Scan)
        .where(Scan.compliance_result.isnot(None))
        .order_by(Scan.created_at.desc())
        .limit(500),
        current_user,
    )
    scans = db.execute(statement).scalars().all()

    counter: Counter[tuple[str, str, str]] = Counter()
    examples: dict[str, dict[str, Any]] = {}
    severity_totals: Counter[str] = Counter()
    recent: list[dict[str, Any]] = []

    for scan in scans:
        result = scan.compliance_result or {}
        for violation in result.get("violations", []) or []:
            key = (
                violation.get("rule_id", "—"),
                violation.get("rule_title", "—"),
                violation.get("severity", "minor"),
            )
            counter[key] += 1
            severity_totals[key[2]] += 1
            if key[0] not in examples:
                examples[key[0]] = {
                    "rule_id": key[0],
                    "rule_title": key[1],
                    "severity": key[2],
                    "recommendation": violation.get("recommendation"),
                    "first_seen_scan": scan.scan_id,
                }
            if len(recent) < 25:
                recent.append(
                    {
                        "scan_id": scan.scan_id,
                        "rule_id": key[0],
                        "rule_title": key[1],
                        "severity": key[2],
                        "created_at": scan.created_at.isoformat() if scan.created_at else None,
                    }
                )

    ranked = []
    for (rule_id, rule_title, severity), occurrences in counter.most_common(limit):
        ranked.append(
            {
                "rule_id": rule_id,
                "rule_title": rule_title,
                "severity": severity,
                "occurrences": occurrences,
                **{k: v for k, v in examples.get(rule_id, {}).items() if k not in {"rule_id", "rule_title", "severity"}},
            }
        )

    return {
        "scans_analysed": len(scans),
        "total_violations": sum(severity_totals.values()),
        "by_severity": {
            "critical": severity_totals.get("critical", 0),
            "major": severity_totals.get("major", 0),
            "minor": severity_totals.get("minor", 0),
        },
        "top_rules": ranked,
        "recent_violations": recent,
    }
