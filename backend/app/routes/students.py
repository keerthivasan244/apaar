from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import PlainTextResponse
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import College, Flag, Student, User
from ..schemas import StudentIn
from ..security import INSTITUTION, OFFICER, STUDENT, assert_college_access, get_current_user, require_roles, scoped_college_id
from ..services import validation
from ..services.ingest import MAX_BYTES, UploadError, parse_upload, template_csv
from .common import Page, mask_apaar

router = APIRouter(tags=["students"])


@router.get("/templates/students.csv", response_class=PlainTextResponse)
def students_template(_user: User = Depends(get_current_user)):
    return PlainTextResponse(template_csv(), media_type="text/csv",
                             headers={"Content-Disposition": 'attachment; filename="students_template.csv"'})


def _context(db: Session, user: User) -> validation.CollegeContext:
    college = db.get(College, user.college_id)
    if college is None:
        raise HTTPException(403, "Your account is not linked to an institution")
    return validation.CollegeContext(db, college)


@router.post("/students/bulk")
async def bulk_upload(file: UploadFile = File(...), dry_run: bool = Query(True), db: Session = Depends(get_db),
                      user: User = Depends(require_roles(INSTITUTION))):
    content = await file.read(MAX_BYTES + 1)  # parse_upload rejects anything over the limit
    try:
        raws = parse_upload(content, file.filename or "upload.csv")
    except UploadError as exc:
        raise HTTPException(422, str(exc))
    ctx = _context(db, user)
    results = validation.validate_rows(db, raws, ctx)
    response = {"dry_run": dry_run, "summary": validation.summarise(results),
                "rows": [r.as_dict() for r in results], "batch_id": None, "new_flags": None,
                "new_matches": None}
    if not dry_run:
        out = validation.commit_rows(db, ctx, results, actor=user.username, actor_role=user.role,
                                     filename=file.filename or "upload.csv")
        response.update(out)
    else:
        db.rollback()  # dry-run never writes
    return response


@router.post("/students")
def create_student(body: StudentIn, db: Session = Depends(get_db), user: User = Depends(require_roles(INSTITUTION))):
    raw = {k: ("" if v is None else str(v)).strip() for k, v in body.model_dump().items()}
    ctx = _context(db, user)
    results = validation.validate_rows(db, [raw], ctx)
    res = results[0]
    student_id = None
    if res.status != "error":
        validation.commit_rows(db, ctx, results, actor=user.username, actor_role=user.role, filename="(single record)")
        student_id = db.scalar(select(Student.id).where(Student.college_id == ctx.college.id,
                                                        Student.student_code == res.data["student_code"],
                                                        Student.year == ctx.year))
    return {"status": res.status, "issues": res.as_dict()["issues"], "student_id": student_id}


def student_summary(s: Student, user: User, open_codes: list[str]) -> dict:
    officer = user.role == OFFICER
    return {
        "id": s.id, "student_code": s.student_code, "name": s.name,
        "apaar_id": s.apaar_id if officer else mask_apaar(s.apaar_id),
        "college_id": s.college_id, "college_name": s.college.name,
        "programme": s.programme.name if s.programme else s.programme_raw, "programme_id": s.programme_id,
        "level": s.level, "year": s.year, "status": s.status, "gender": s.gender,
        "admission_category": s.admission_category, "social_category": s.social_category,
        "open_flags": open_codes,
    }


@router.get("/students")
def list_students(page: Page = Depends(), college_id: int | None = None, programme_id: int | None = None,
                  q: str | None = None, has_flag: bool | None = None, db: Session = Depends(get_db),
                  user: User = Depends(require_roles(OFFICER, INSTITUTION))):
    college_id = scoped_college_id(user, college_id)
    stmt = select(Student)
    if college_id:
        stmt = stmt.where(Student.college_id == college_id)
    if programme_id:
        stmt = stmt.where(Student.programme_id == programme_id)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(Student.name.ilike(like), Student.student_code.ilike(like), Student.apaar_id.ilike(like)))
    flagged = select(Flag.student_id).where(Flag.status == "open", Flag.student_id.is_not(None))
    if has_flag is True:
        stmt = stmt.where(Student.id.in_(flagged))
    elif has_flag is False:
        stmt = stmt.where(Student.id.not_in(flagged))
    total = db.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = list(db.scalars(page.apply(stmt.order_by(Student.college_id, Student.student_code))))
    codes: dict[int, list[str]] = {}
    if rows:
        for sid, code in db.execute(select(Flag.student_id, Flag.code).where(
                Flag.student_id.in_([r.id for r in rows]), Flag.status == "open")):
            codes.setdefault(sid, []).append(code)
    return page.wrap([student_summary(s, user, codes.get(s.id, [])) for s in rows], total)


@router.get("/students/me")
def my_profile(db: Session = Depends(get_db), user: User = Depends(require_roles(STUDENT))):
    s = db.get(Student, user.student_id) if user.student_id else None
    if s is None:
        raise HTTPException(404, "No student record is linked to this account")
    return {"id": s.id, "name": s.name, "student_code": s.student_code, "apaar_id": mask_apaar(s.apaar_id),
            "institution_name": s.college.name, "aicte_id": s.college.aicte_id,
            "programme": s.programme.name if s.programme else s.programme_raw, "year": s.year, "status": s.status}


@router.get("/students/{student_id}")
def get_student(student_id: int, db: Session = Depends(get_db),
                user: User = Depends(require_roles(OFFICER, INSTITUTION))):
    s = db.get(Student, student_id)
    if s is None:
        raise HTTPException(404, "Student not found")
    assert_college_access(user, s.college_id)
    from .flags import flag_out  # local import avoids a cycle

    flags = list(db.scalars(select(Flag).where(Flag.student_id == s.id).order_by(Flag.id)))
    out = student_summary(s, user, [f.code for f in flags if f.status == "open"])
    out.update({"father_name": s.father_name, "dob": s.dob.isoformat(), "shift": s.shift,
                "phone_last4": s.phone_last4, "flags": [flag_out(db, f, user) for f in flags]})
    return out
