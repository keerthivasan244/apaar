from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Credential, Student, User
from ..schemas import RevokeIn, TokenIn
from ..security import INSTITUTION, OFFICER, STUDENT, assert_college_access, require_roles, scoped_college_id
from ..services import credentials as creds
from .common import Page

router = APIRouter(tags=["credentials"])


def cred_out(c: Credential) -> dict:
    return {"id": c.id, "student_id": c.student_id, "student_name": c.student.name,
            "student_code": c.student.student_code, "token": c.token, "kid": c.kid,
            "issued_at": c.issued_at.isoformat(), **creds.status_of(c, c.id)}


@router.get("/keys/public")
def public_key():
    return creds.public_key_info()


@router.get("/credentials")
def list_credentials(page: Page = Depends(), college_id: int | None = None, db: Session = Depends(get_db),
                     user: User = Depends(require_roles(OFFICER, INSTITUTION))):
    college_id = scoped_college_id(user, college_id)
    stmt = select(Credential).join(Student)
    if college_id:
        stmt = stmt.where(Student.college_id == college_id)
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = db.scalars(page.apply(stmt.order_by(Credential.issued_at.desc())))
    return page.wrap([cred_out(c) for c in rows], total)


@router.post("/credentials/issue/{student_id}")
def issue_credential(student_id: int, db: Session = Depends(get_db),
                     user: User = Depends(require_roles(OFFICER, INSTITUTION))):
    student = db.get(Student, student_id)
    if student is None:
        raise HTTPException(404, "Student not found")
    assert_college_access(user, student.college_id)
    cred = creds.issue(db, student, actor=user.username, actor_role=user.role)
    db.commit()
    return cred_out(cred)


@router.get("/credentials/mine")
def my_credentials(db: Session = Depends(get_db), user: User = Depends(require_roles(STUDENT))):
    rows = db.scalars(select(Credential).where(Credential.student_id == user.student_id)
                      .order_by(Credential.issued_at.desc()))
    return [cred_out(c) for c in rows]


@router.post("/credentials/{cid}/revoke")
def revoke_credential(cid: str, body: RevokeIn, db: Session = Depends(get_db),
                      user: User = Depends(require_roles(OFFICER, INSTITUTION))):
    cred = db.get(Credential, cid)
    if cred is None:
        raise HTTPException(404, "Credential not found")
    assert_college_access(user, cred.student.college_id)
    if cred.revoked_at:
        raise HTTPException(409, "Credential is already revoked")
    creds.revoke(db, cred, body.reason, actor=user.username, actor_role=user.role)
    db.commit()
    return cred_out(cred)


@router.get("/credentials/status/{cid}")
def credential_status(cid: str, db: Session = Depends(get_db)):
    return creds.status_of(db.get(Credential, cid), cid)


@router.post("/credentials/verify")
def verify_credential(body: TokenIn, db: Session = Depends(get_db)):
    valid, payload = creds.verify_token(body.token)
    if not valid:
        return {"signature_valid": False, "status": None, "payload": None}
    cid = payload.get("cid", "")
    return {"signature_valid": True, "status": creds.status_of(db.get(Credential, cid), cid)["status"],
            "payload": payload}
