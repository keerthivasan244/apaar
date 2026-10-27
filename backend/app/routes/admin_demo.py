import random

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import SessionLocal, get_db
from ..models import AuditLog, Credential, Student, User
from ..schemas import TamperIn
from ..security import OFFICER, require_roles
from ..services.audit import record

router = APIRouter(prefix="/admin/demo", tags=["demo"])


def demo_only() -> None:
    if not get_settings().demo_mode:
        raise HTTPException(403, "Demo endpoints are disabled (DEMO_MODE=false)")


@router.post("/reset", dependencies=[Depends(demo_only)])
def reset(db: Session = Depends(get_db), user: User = Depends(require_roles(OFFICER))):
    from ..seed import reset_and_seed

    actor, role = user.username, user.role
    db.close()  # release the request's connection before dropping tables
    summary = reset_and_seed()
    with SessionLocal() as fresh:
        record(fresh, actor=actor, actor_role=role, action="DEMO_RESET", entity_type="database",
               entity_id="all", payload={"students": summary["students"]})
        fresh.commit()
    return {"status": "reset", **summary}


@router.post("/tamper-audit", dependencies=[Depends(demo_only)])
def tamper(body: TamperIn | None = None, db: Session = Depends(get_db),
           _user: User = Depends(require_roles(OFFICER))):
    max_id = db.scalar(select(func.max(AuditLog.id))) or 0
    if max_id < 1:
        raise HTTPException(409, "Audit log is empty")
    entry_id = body.entry_id if body and body.entry_id else (random.randint(2, max_id - 1) if max_id > 2 else 1)
    row = db.get(AuditLog, entry_id)
    if row is None:
        raise HTTPException(404, "Audit entry not found")
    # Deliberately bypass the audit service: change the payload without rehashing.
    db.execute(update(AuditLog).where(AuditLog.id == entry_id)
               .values(payload={**(row.payload or {}), "tampered": True, "note": "edited directly in the DB"}))
    db.commit()
    return {"entry_id": entry_id}


@router.get("/tokens", dependencies=[Depends(demo_only)])
def demo_tokens(db: Session = Depends(get_db)):
    """Seeded sample credentials so presenters can open them on /verify (demo mode only)."""
    out = []
    for c in db.scalars(select(Credential).join(Student).order_by(Credential.issued_at)):
        out.append({"label": f"{c.student.name} ({'revoked' if c.revoked_at else 'valid'})", "token": c.token})
    return out
