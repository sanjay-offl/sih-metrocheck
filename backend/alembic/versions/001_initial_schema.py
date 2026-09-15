"""initial schema: users, products, scans, reports

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-01-01 00:00:00
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

user_role = sa.Enum("admin", "officer", "viewer", name="user_role")
scan_status = sa.Enum("pending", "processing", "completed", "failed", name="scan_status")
compliance_status = sa.Enum(
    "compliant", "non_compliant", "partial", "pending", name="compliance_status"
)
report_format = sa.Enum("pdf", "json", name="report_format")


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role, nullable=False, server_default="officer"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.Column("employee_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_id"), "users", ["id"])
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=True),
        sa.Column("barcode", sa.String(length=64), nullable=True),
        sa.Column("category", sa.String(length=64), nullable=True),
        sa.Column("manufacturer_name", sa.String(length=512), nullable=True),
        sa.Column("manufacturer_address", sa.Text(), nullable=True),
        sa.Column("net_quantity", sa.String(length=128), nullable=True),
        sa.Column("mrp", sa.Float(), nullable=True),
        sa.Column("image_url", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_products_id"), "products", ["id"])
    op.create_index(op.f("ix_products_barcode"), "products", ["barcode"])

    op.create_table(
        "scans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("scan_id", sa.String(length=64), nullable=False),
        sa.Column("officer_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("image_url", sa.String(length=512), nullable=False),
        sa.Column("image_filename", sa.String(length=255), nullable=False),
        sa.Column("image_sha256", sa.String(length=64), nullable=True),
        sa.Column("status", scan_status, nullable=False, server_default="pending"),
        sa.Column("compliance_status", compliance_status, nullable=False, server_default="pending"),
        sa.Column("compliance_score", sa.Float(), nullable=True),
        sa.Column("extracted_data", sa.JSON(), nullable=True),
        sa.Column("compliance_result", sa.JSON(), nullable=True),
        sa.Column("extraction_method", sa.String(length=32), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=512), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("total_violations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("critical_violations", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["officer_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scans_id"), "scans", ["id"])
    op.create_index(op.f("ix_scans_scan_id"), "scans", ["scan_id"], unique=True)
    op.create_index(op.f("ix_scans_officer_id"), "scans", ["officer_id"])
    op.create_index(op.f("ix_scans_product_id"), "scans", ["product_id"])
    op.create_index(op.f("ix_scans_image_sha256"), "scans", ["image_sha256"])

    op.create_table(
        "reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("report_id", sa.String(length=64), nullable=False),
        sa.Column("scan_id", sa.Integer(), nullable=False),
        sa.Column("officer_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("format", report_format, nullable=False, server_default="pdf"),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("file_url", sa.String(length=512), nullable=True),
        sa.Column("file_size_bytes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scan_id"], ["scans.id"]),
        sa.ForeignKeyConstraint(["officer_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_reports_id"), "reports", ["id"])
    op.create_index(op.f("ix_reports_report_id"), "reports", ["report_id"], unique=True)
    op.create_index(op.f("ix_reports_scan_id"), "reports", ["scan_id"])
    op.create_index(op.f("ix_reports_officer_id"), "reports", ["officer_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_reports_officer_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_scan_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_report_id"), table_name="reports")
    op.drop_index(op.f("ix_reports_id"), table_name="reports")
    op.drop_table("reports")

    op.drop_index(op.f("ix_scans_image_sha256"), table_name="scans")
    op.drop_index(op.f("ix_scans_product_id"), table_name="scans")
    op.drop_index(op.f("ix_scans_officer_id"), table_name="scans")
    op.drop_index(op.f("ix_scans_scan_id"), table_name="scans")
    op.drop_index(op.f("ix_scans_id"), table_name="scans")
    op.drop_table("scans")

    op.drop_index(op.f("ix_products_barcode"), table_name="products")
    op.drop_index(op.f("ix_products_id"), table_name="products")
    op.drop_table("products")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_index(op.f("ix_users_id"), table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_type in (report_format, compliance_status, scan_status, user_role):
        enum_type.drop(bind, checkfirst=True)
