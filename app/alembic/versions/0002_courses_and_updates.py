"""courses and employee updates

Revision ID: 0002_courses_and_updates
Revises: 0001_initial
Create Date: 2026-02-26
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_courses_and_updates"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=255), nullable=True),
        sa.Column("requires_refresh", sa.Boolean(), nullable=False),
        sa.Column("refresh_interval_days", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_unique_constraint("uq_courses_title", "courses", ["title"])

    op.create_table(
        "employee_courses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("employee_id", sa.Integer(), sa.ForeignKey("employees.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.Integer(), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("completed_date", sa.Date(), nullable=True),
        sa.Column("next_refresh_due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("employee_id", "course_id", name="uq_employee_course"),
    )
    op.create_index("ix_employee_courses_employee_id", "employee_courses", ["employee_id"], unique=False)
    op.create_index("ix_employee_courses_course_id", "employee_courses", ["course_id"], unique=False)
    op.create_index(
        "ix_employee_courses_next_refresh_due_date",
        "employee_courses",
        ["next_refresh_due_date"],
        unique=False,
    )

    op.create_table(
        "employee_course_updates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "employee_course_id",
            sa.Integer(),
            sa.ForeignKey("employee_courses.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("update_date", sa.Date(), nullable=False),
        sa.Column("next_refresh_due_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_employee_course_updates_employee_course_id", "employee_course_updates", ["employee_course_id"], unique=False)
    op.create_index("ix_employee_course_updates_update_date", "employee_course_updates", ["update_date"], unique=False)
    op.create_index(
        "ix_employee_course_updates_next_refresh_due_date",
        "employee_course_updates",
        ["next_refresh_due_date"],
        unique=False,
    )

    op.create_table(
        "course_update_attachments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "course_update_id",
            sa.Integer(),
            sa.ForeignKey("employee_course_updates.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("stored_path", sa.String(length=500), nullable=False),
        sa.Column("mime_type", sa.String(length=120), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("uploaded_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index(
        "ix_course_update_attachments_course_update_id",
        "course_update_attachments",
        ["course_update_id"],
        unique=False,
    )
    op.create_index(
        "ix_course_update_attachments_checksum_sha256",
        "course_update_attachments",
        ["checksum_sha256"],
        unique=False,
    )
    op.create_unique_constraint("uq_course_update_attachments_stored_path", "course_update_attachments", ["stored_path"])


def downgrade() -> None:
    op.drop_constraint("uq_course_update_attachments_stored_path", "course_update_attachments", type_="unique")
    op.drop_index("ix_course_update_attachments_checksum_sha256", table_name="course_update_attachments")
    op.drop_index("ix_course_update_attachments_course_update_id", table_name="course_update_attachments")
    op.drop_table("course_update_attachments")

    op.drop_index("ix_employee_course_updates_next_refresh_due_date", table_name="employee_course_updates")
    op.drop_index("ix_employee_course_updates_update_date", table_name="employee_course_updates")
    op.drop_index("ix_employee_course_updates_employee_course_id", table_name="employee_course_updates")
    op.drop_table("employee_course_updates")

    op.drop_index("ix_employee_courses_next_refresh_due_date", table_name="employee_courses")
    op.drop_index("ix_employee_courses_course_id", table_name="employee_courses")
    op.drop_index("ix_employee_courses_employee_id", table_name="employee_courses")
    op.drop_table("employee_courses")

    op.drop_constraint("uq_courses_title", "courses", type_="unique")
    op.drop_table("courses")
