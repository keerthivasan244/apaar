from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Consent, User
from ..schemas import ConsentIn, OtpIn
from ..security import STUDENT, VERIFIER, require_roles
from ..services import consent as svc

router = APIRouter(prefix="/consents", tags=["consents"])


def consent_out(c: Consent, viewer: User) -> dict:
    s = c.student
    out = {"id": c.id, "purpose": c.purpose, "fields": c.fields, "status": c.status,
           "created_at": c.created_at.isoformat(),
           "approved_at": c.approved_at.isoformat() if c.approved_at else None,
           "expires_at": c.expires_at.isoformat() if c.expires_at else None,
           "verifier_organisation": c.verifier.organisation, "verifier_name": c.verifier.display_name}
    if viewer.role == VERIFIER:
        out.update({"apaar_id": s.apaar_id, "institution_name": s.college.name})
    return out


@router.post("")
def request_consent(body: ConsentIn, db: Session = Depends(get_db), user: User = Depends(require_roles(VERIFIER))):
    c = svc.create(db, user, body.apaar_id, body.fields, body.purpose)
    db.commit()
    return consent_out(c, user)


@router.get("/mine")
def my_consents(db: Session = Depends(get_db), user: User = Depends(require_roles(STUDENT, VERIFIER))):
    col = Consent.student_id if user.role == STUDENT else Consent.verifier_user_id
    key = user.student_id if user.role == STUDENT else user.id
    rows = [svc.refresh(c) for c in db.scalars(select(Consent).where(col == key).order_by(Consent.id.desc()))]
    db.commit()  # persist lazy expiries
    return [consent_out(c, user) for c in rows]


@router.post("/{consent_id}/approve")
def approve(consent_id: int, body: OtpIn, db: Session = Depends(get_db), user: User = Depends(require_roles(STUDENT))):
    c = svc.approve(db, user, consent_id, body.otp)
    db.commit()
    return consent_out(c, user)


@router.post("/{consent_id}/deny")
def deny(consent_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(STUDENT))):
    c = svc.deny(db, user, consent_id)
    db.commit()
    return consent_out(c, user)


@router.post("/{consent_id}/revoke")
def revoke(consent_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(STUDENT))):
    c = svc.revoke(db, user, consent_id)
    db.commit()
    return consent_out(c, user)


@router.get("/{consent_id}/result")
def result(consent_id: int, db: Session = Depends(get_db), user: User = Depends(require_roles(VERIFIER))):
    return svc.result(db, user, consent_id)
