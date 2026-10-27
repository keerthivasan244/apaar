from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import INSTITUTION, OFFICER, assert_college_access, require_roles
from ..services.risk import DISCLAIMER, compute_risk

router = APIRouter(prefix="/risk", tags=["risk"])


@router.get("/colleges")
def risk_colleges(db: Session = Depends(get_db), _user: User = Depends(require_roles(OFFICER))):
    return compute_risk(db)


@router.get("/colleges/{college_id}")
def risk_college(college_id: int, db: Session = Depends(get_db),
                 user: User = Depends(require_roles(OFFICER, INSTITUTION))):
    assert_college_access(user, college_id)
    rows = compute_risk(db, [college_id])
    if not rows:
        raise HTTPException(404, "College not found")
    return rows[0] | {"disclaimer": DISCLAIMER}
