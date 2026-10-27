from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import College, User
from ..security import INSTITUTION, OFFICER, assert_college_access, require_roles
from ..services import ledger

router = APIRouter(prefix="/colleges", tags=["colleges"])


def college_dict(c: College) -> dict:
    return {"id": c.id, "aicte_id": c.aicte_id, "name": c.name, "city": c.city, "state": c.state,
            "type": c.type, "prev_year_enrolment": c.prev_year_enrolment}


@router.get("")
def list_colleges(db: Session = Depends(get_db), _user: User = Depends(require_roles(OFFICER))):
    return [college_dict(c) for c in db.scalars(select(College).order_by(College.id))]


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
