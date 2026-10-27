"""Roster and compliance exports (CSV/XLSX) with formula-injection protection."""
import csv
import io

from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..models import College, Flag, Student
from .risk import compute_risk

ROSTER_COLUMNS = ["student_code", "apaar_id", "name", "father_name", "dob", "gender", "programme", "level",
                  "shift", "admission_category", "social_category", "status", "open_flags"]
COMPLIANCE_COLUMNS = ["aicte_id", "college", "state", "approved_intake", "admitted", "over_by", "open_flags",
                      "duplicate_students", "risk_score", "risk_band"]


def safe_cell(value):
    """Neutralise spreadsheet formulas in exported text (=, +, -, @ prefixes)."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@"):
        return "'" + value
    return value


def roster_rows(db: Session, college_id: int, mask) -> list[dict]:
    flag_counts = dict(db.execute(select(Flag.student_id, func.count()).where(
        Flag.college_id == college_id, Flag.status == "open", Flag.student_id.is_not(None))
        .group_by(Flag.student_id)).all())
    rows = []
    for s in db.scalars(select(Student).where(Student.college_id == college_id).order_by(Student.student_code)):
        rows.append({
            "student_code": s.student_code, "apaar_id": mask(s.apaar_id) or "", "name": s.name,
            "father_name": s.father_name, "dob": s.dob.isoformat(), "gender": s.gender,
            "programme": s.programme.name if s.programme else s.programme_raw, "level": s.level,
            "shift": s.shift, "admission_category": s.admission_category, "social_category": s.social_category,
            "status": s.status, "open_flags": flag_counts.get(s.id, 0),
        })
    return rows


def compliance_rows(db: Session) -> list[dict]:
    open_flags = dict(db.execute(select(Flag.college_id, func.count()).where(Flag.status == "open")
                                 .group_by(Flag.college_id)).all())
    rows = []
    for r in sorted(compute_risk(db), key=lambda x: x["college_id"]):
        f = r["facts"]
        rows.append({
            "aicte_id": r["aicte_id"], "college": r["name"], "state": r["state"],
            "approved_intake": f["approved_intake"], "admitted": f["admitted"], "over_by": f["excess"],
            "open_flags": open_flags.get(r["college_id"], 0), "duplicate_students": f["duplicate_students"],
            "risk_score": r["score"], "risk_band": r["band"],
        })
    return rows


def to_csv(rows: list[dict], columns: list[str]) -> bytes:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=columns)
    writer.writeheader()
    for row in rows:
        writer.writerow({k: safe_cell(row.get(k)) for k in columns})
    return buf.getvalue().encode("utf-8-sig")


def to_xlsx(rows: list[dict], columns: list[str], title: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = title[:31]
    ws.append(columns)
    for row in rows:
        ws.append([safe_cell(row.get(k)) for k in columns])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def college_name(db: Session, college_id: int) -> str:
    c = db.get(College, college_id)
    return c.aicte_id if c else str(college_id)
