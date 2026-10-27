"""Consent-scoped verification (PRD 6.8)."""
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from ..config import get_policy
from ..models import Consent, Student, User, utcnow
from .adapters import apaar_registry, otp_sender
from .audit import record_for

FIELD_GETTERS = {
    "name": lambda s: s.name,
    "dob": lambda s: s.dob.isoformat(),
    "programme": lambda s: s.programme.name if s.programme else s.programme_raw,
    "admission_category": lambda s: s.admission_category,
    "student_code": lambda s: s.student_code,
}


def refresh(c: Consent) -> Consent:
    """Lazily expire approved consents past their TTL."""
    if c.status == "approved" and c.expires_at and c.expires_at <= utcnow():
        c.status = "expired"
    return c


def create(db: Session, verifier: User, apaar_id: str, fields: list[str], purpose: str) -> Consent:
    student = apaar_registry(db).lookup(apaar_id)
    if student is None:
        raise HTTPException(404, "No enrolment found for this APAAR ID")
    consent = Consent(student_id=student.id, verifier_user_id=verifier.id, purpose=purpose.strip(),
                      fields=list(dict.fromkeys(fields)), status="requested")
    db.add(consent)
    db.flush()
    otp_sender().send(None, otp_sender().current_otp())
    record_for(db, verifier, "CONSENT_REQUEST", "consent", consent.id,
               {"student_id": student.id, "fields": consent.fields, "purpose": consent.purpose})
    return consent


def _owned(db: Session, user: User, consent_id: int) -> Consent:
    c = db.get(Consent, consent_id)
    if c is None:
        raise HTTPException(404, "Consent request not found")
    owner = c.student_id == user.student_id if user.role == "student" else c.verifier_user_id == user.id
    if not owner:
        raise HTTPException(403, "This consent request belongs to someone else")
    return refresh(c)


def approve(db: Session, student: User, consent_id: int, otp: str) -> Consent:
    c = _owned(db, student, consent_id)
    if c.status != "requested":
        raise HTTPException(409, f"Request is already {c.status}")
    if otp.strip() != otp_sender().current_otp():
        raise HTTPException(400, "Incorrect OTP")
    now = utcnow()
    c.status, c.approved_at = "approved", now
    c.expires_at = now + timedelta(hours=get_policy()["consent_ttl_hours"])
    record_for(db, student, "CONSENT_APPROVE", "consent", c.id, {"fields": c.fields})
    return c


def deny(db: Session, student: User, consent_id: int) -> Consent:
    c = _owned(db, student, consent_id)
    if c.status != "requested":
        raise HTTPException(409, f"Request is already {c.status}")
    c.status = "denied"
    record_for(db, student, "CONSENT_DENY", "consent", c.id, {})
    return c


def revoke(db: Session, student: User, consent_id: int) -> Consent:
    c = _owned(db, student, consent_id)
    if c.status not in ("approved", "requested"):
        raise HTTPException(409, f"Request is already {c.status}")
    c.status = "revoked"
    record_for(db, student, "CONSENT_REVOKE", "consent", c.id, {})
    return c


def result(db: Session, verifier: User, consent_id: int) -> dict:
    c = _owned(db, verifier, consent_id)
    if c.status != "approved":
        raise HTTPException(403, f"Consent is {c.status}; data is available only while approved")
    s: Student = c.student
    return {"consent_id": c.id, "expires_at": c.expires_at.isoformat(),
            "data": {f: FIELD_GETTERS[f](s) for f in c.fields}}
