from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import College, Flag, User
from ..security import INSTITUTION, OFFICER, assert_college_access, require_roles
from ..services import ledger
from ..services.risk import compute_risk

router = APIRouter(prefix="/colleges", tags=["colleges"])


def college_dict(c: College) -> dict:
    return {"id": c.id, "aicte_id": c.aicte_id, "name": c.name, "city": c.city, "state": c.state,
            "type": c.type, "prev_year_enrolment": c.prev_year_enrolment}


@router.get("")
def list_colleges(db: Session = Depends(get_db), _user: User = Depends(require_roles(OFFICER))):
    risk = {r["college_id"]: r for r in compute_risk(db)}
    open_flags = dict(db.execute(select(Flag.college_id, func.count()).where(Flag.status == "open")
                                 .group_by(Flag.college_id)).all())
    out = []
    for c in db.scalars(select(College).order_by(College.id)):
        r = risk[c.id]
        out.append(college_dict(c) | {"students": r["facts"]["active_students"],
                                      "open_flags": open_flags.get(c.id, 0), "risk_score": r["score"],
                                      "risk_band": r["band"], "top_reason": (r["reasons"] or [None])[0]})
    return out


@router.get("/{college_id}")
def get_college(college_id: int, db: Session = Depends(get_db),
                user: User = Depends(require_roles(OFFICER, INSTITUTION))):
    assert_college_access(user, college_id)
    college = db.get(College, college_id)
    if college is None:
        raise HTTPException(404, "College not found")
    return college_dict(college)


@router.get("/{college_id}/programmes")
def college_programmes(college_id: int, db: Session = Depends(get_db),
                       user: User = Depends(require_roles(OFFICER, INSTITUTION))):
    assert_college_access(user, college_id)
    if db.get(College, college_id) is None:
        raise HTTPException(404, "College not found")
    return ledger.college_ledger(db, college_id)
