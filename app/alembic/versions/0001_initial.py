"""initial

Revision ID: 0001_initial
Revises: 
Create Date: 2026-02-25
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "employees",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("factorial_employee_id", sa.String(length=64), nullable=False),
        sa.Column("first_name", sa.String(length=120), nullable=False),
        sa.Column("last_name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=120), nullable=True),
        sa.Column("cost_center", sa.String(length=120), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_employees_factorial_employee_id", "employees", ["factorial_employee_id"], unique=True)

    op.create_table(
        "certifications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cert_type", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=255), nullable=True),
        sa.Column("issued_date", sa.Date(), nullable=True),
        sa.Column("expiry_date", sa.Date(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_certifications_cert_type", "certifications", ["cert_type"], unique=False)
    op.create_index("ix_certifications_expiry_date", "certifications", ["expiry_date"], unique=False)

    op.create_table(
        "attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("certification_id", sa.Integer(), sa.ForeignKey("certifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_unique_constraint("uq_attachments_stored_path", "attachments", ["stored_path"])
    op.create_index("ix_attachments_checksum_sha256", "attachments", ["checksum_sha256"], unique=False)

    op.create_table(
        "alert_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cert_type", sa.String(length=120), nullable=True),
        sa.Column("thresholds_csv", sa.String(length=120), nullable=False),
        sa.Column("email_enabled", sa.Boolean(), nullable=False),
        sa.Column("webhook_enabled", sa.Boolean(), nullable=False),
        sa.Column("recipient_emails", sa.Text(), nullable=False),
    )

    op.create_table(
        "alert_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("certification_id", sa.Integer(), sa.ForeignKey("certifications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("threshold_days", sa.Integer(), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("certification_id", "threshold_days", name="uq_alert_once"),
    )

    op.create_table(
        "settings",
        sa.Column("key", sa.String(length=120), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity", sa.String(length=120), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=False),
        sa.Column("metadata_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("settings")
    op.drop_table("alert_logs")
    op.drop_table("alert_settings")
    op.drop_index("ix_attachments_checksum_sha256", table_name="attachments")
    op.drop_constraint("uq_attachments_stored_path", "attachments", type_="unique")
    op.drop_table("attachments")
    op.drop_index("ix_certifications_expiry_date", table_name="certifications")
    op.drop_index("ix_certifications_cert_type", table_name="certifications")
    op.drop_table("certifications")
    op.drop_index("ix_employees_factorial_employee_id", table_name="employees")
    op.drop_table("employees")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
