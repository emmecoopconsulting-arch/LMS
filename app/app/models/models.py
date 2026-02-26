from datetime import datetime, date, UTC
from sqlalchemy import (
    String,
    Integer,
    Date,
    DateTime,
    Boolean,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="viewer")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    factorial_employee_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    first_name: Mapped[str] = mapped_column(String(120))
    last_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cost_center: Mapped[str | None] = mapped_column(String(120), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    certifications = relationship("Certification", back_populates="employee")
    employee_courses = relationship("EmployeeCourse", back_populates="employee", cascade="all, delete-orphan")


class Certification(Base):
    __tablename__ = "certifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    cert_type: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(255))
    provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    issued_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    expiry_date: Mapped[date] = mapped_column(Date, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    employee = relationship("Employee", back_populates="certifications")
    attachments = relationship("Attachment", back_populates="certification", cascade="all, delete-orphan")


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requires_refresh: Mapped[bool] = mapped_column(Boolean, default=False)
    refresh_interval_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    employee_courses = relationship("EmployeeCourse", back_populates="course", cascade="all, delete-orphan")


class EmployeeCourse(Base):
    __tablename__ = "employee_courses"
    __table_args__ = (UniqueConstraint("employee_id", "course_id", name="uq_employee_course"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id", ondelete="CASCADE"), index=True)
    completed_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    next_refresh_due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    employee = relationship("Employee", back_populates="employee_courses")
    course = relationship("Course", back_populates="employee_courses")
    updates = relationship("EmployeeCourseUpdate", back_populates="employee_course", cascade="all, delete-orphan")


class EmployeeCourseUpdate(Base):
    __tablename__ = "employee_course_updates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    employee_course_id: Mapped[int] = mapped_column(
        ForeignKey("employee_courses.id", ondelete="CASCADE"), index=True
    )
    update_date: Mapped[date] = mapped_column(Date, index=True)
    next_refresh_due_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )

    employee_course = relationship("EmployeeCourse", back_populates="updates")
    attachments = relationship(
        "CourseUpdateAttachment", back_populates="course_update", cascade="all, delete-orphan"
    )


class Attachment(Base):
    __tablename__ = "attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id", ondelete="CASCADE"))
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500), unique=True)
    mime_type: Mapped[str] = mapped_column(String(120))
    file_size: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    certification = relationship("Certification", back_populates="attachments")


class CourseUpdateAttachment(Base):
    __tablename__ = "course_update_attachments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    course_update_id: Mapped[int] = mapped_column(
        ForeignKey("employee_course_updates.id", ondelete="CASCADE"), index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    stored_path: Mapped[str] = mapped_column(String(500), unique=True)
    mime_type: Mapped[str] = mapped_column(String(120))
    file_size: Mapped[int] = mapped_column(Integer)
    checksum_sha256: Mapped[str] = mapped_column(String(64), index=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    uploaded_by: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)

    course_update = relationship("EmployeeCourseUpdate", back_populates="attachments")


class AlertSetting(Base):
    __tablename__ = "alert_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    cert_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    thresholds_csv: Mapped[str] = mapped_column(String(120), default="90,60,30,14,7,1")
    email_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    webhook_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    recipient_emails: Mapped[str] = mapped_column(Text, default="")


class AlertLog(Base):
    __tablename__ = "alert_logs"
    __table_args__ = (UniqueConstraint("certification_id", "threshold_days", name="uq_alert_once"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    certification_id: Mapped[int] = mapped_column(ForeignKey("certifications.id", ondelete="CASCADE"), index=True)
    threshold_days: Mapped[int] = mapped_column(Integer)
    last_sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))


class Setting(Base):
    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String(120), primary_key=True)
    value: Mapped[str] = mapped_column(Text, default="")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    actor_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    action: Mapped[str] = mapped_column(String(120))
    entity: Mapped[str] = mapped_column(String(120))
    entity_id: Mapped[str] = mapped_column(String(120))
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))
