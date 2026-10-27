"""SQLAlchemy models (PRD section 7)."""
from datetime import date, datetime, timezone

from sqlalchemy import JSON, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(String(256))
    role: Mapped[str] = mapped_column(String(32))
    display_name: Mapped[str] = mapped_column(String(128))
    college_id: Mapped[int | None] = mapped_column(ForeignKey("colleges.id"), nullable=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True)
    organisation: Mapped[str | None] = mapped_column(String(128), nullable=True)


class College(Base):
    __tablename__ = "colleges"
    id: Mapped[int] = mapped_column(primary_key=True)
    aicte_id: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    city: Mapped[str] = mapped_column(String(64))
    state: Mapped[str] = mapped_column(String(64))
    type: Mapped[str] = mapped_column(String(32))
    prev_year_enrolment: Mapped[int] = mapped_column(Integer, default=0)
    programmes: Mapped[list["Programme"]] = relationship(back_populates="college", order_by="Programme.id")


class Programme(Base):
    __tablename__ = "programmes"
    id: Mapped[int] = mapped_column(primary_key=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), index=True)
    name: Mapped[str] = mapped_column(String(128))
    level: Mapped[str] = mapped_column(String(16))
    shift: Mapped[str] = mapped_column(String(16))
    approved_intake: Mapped[int] = mapped_column(Integer)
    college: Mapped[College] = relationship(back_populates="programmes")


class Student(Base):
    __tablename__ = "students"
    __table_args__ = (UniqueConstraint("college_id", "student_code", "year"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), index=True)
    programme_id: Mapped[int | None] = mapped_column(ForeignKey("programmes.id"), nullable=True)
    programme_raw: Mapped[str] = mapped_column(String(128))
    level: Mapped[str] = mapped_column(String(16))
    shift: Mapped[str] = mapped_column(String(16))
    year: Mapped[int] = mapped_column(Integer, index=True)
    student_code: Mapped[str] = mapped_column(String(64))
    apaar_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    name: Mapped[str] = mapped_column(String(128))
    name_norm: Mapped[str] = mapped_column(String(128))
    father_name: Mapped[str] = mapped_column(String(128))
    father_name_norm: Mapped[str] = mapped_column(String(128))
    dob: Mapped[date] = mapped_column(Date, index=True)
    gender: Mapped[str] = mapped_column(String(1))
    phone_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    admission_category: Mapped[str] = mapped_column(String(16))
    social_category: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16), default="active")
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("upload_batches.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    college: Mapped[College] = relationship()
    programme: Mapped[Programme | None] = relationship()


class UploadBatch(Base):
    __tablename__ = "upload_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"))
    uploaded_by: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(256))
    rows_total: Mapped[int] = mapped_column(Integer, default=0)
    rows_saved: Mapped[int] = mapped_column(Integer, default=0)
    rows_error: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class Flag(Base):
    __tablename__ = "flags"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int | None] = mapped_column(ForeignKey("students.id"), nullable=True, index=True)
    college_id: Mapped[int] = mapped_column(ForeignKey("colleges.id"), index=True)
    programme_id: Mapped[int | None] = mapped_column(ForeignKey("programmes.id"), nullable=True)
    code: Mapped[str] = mapped_column(String(32), index=True)
    severity: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="open", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    match_id: Mapped[int | None] = mapped_column(ForeignKey("match_candidates.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    student: Mapped[Student | None] = relationship()
    college: Mapped[College] = relationship()
    programme: Mapped[Programme | None] = relationship()


class MatchCandidate(Base):
    __tablename__ = "match_candidates"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_a_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    student_b_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    score: Mapped[float] = mapped_column(Float)
    band: Mapped[str] = mapped_column(String(16))
    components: Mapped[dict] = mapped_column(JSON, default=dict)
    explanations: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="pending")
    reviewed_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    student_a: Mapped[Student] = relationship(foreign_keys=[student_a_id])
    student_b: Mapped[Student] = relationship(foreign_keys=[student_b_id])


class Consent(Base):
    __tablename__ = "consents"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    verifier_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    purpose: Mapped[str] = mapped_column(Text)
    fields: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="requested")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    student: Mapped[Student] = relationship()
    verifier: Mapped[User] = relationship()


class Credential(Base):
    __tablename__ = "credentials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"), index=True)
    token: Mapped[str] = mapped_column(Text)
    kid: Mapped[str] = mapped_column(String(16))
    issued_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    revoked_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    student: Mapped[Student] = relationship()


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[str] = mapped_column(String(40))
    actor: Mapped[str] = mapped_column(String(64))
    actor_role: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(32))
    entity_type: Mapped[str] = mapped_column(String(32))
    entity_id: Mapped[str] = mapped_column(String(64))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    prev_hash: Mapped[str] = mapped_column(String(64))
    hash: Mapped[str] = mapped_column(String(64))
