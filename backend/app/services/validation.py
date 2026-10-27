"""Row validation (blocking errors vs saved flags) and flag generation (PRD 6.3)."""
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_policy
from ..models import College, Flag, Student, UploadBatch, utcnow
from . import ledger, matching
from .audit import record
from .ingest import REQUIRED
from .normalise import hash_phone, normalise_name

BLOCKING = {
    "MISSING_REQUIRED_FIELD", "INVALID_DOB_FORMAT", "INVALID_GENDER", "INVALID_LEVEL", "INVALID_SHIFT",
    "INVALID_ADMISSION_CATEGORY", "INVALID_SOCIAL_CATEGORY", "YEAR_MISMATCH", "DUP_STUDENT_ID_IN_FILE",
    "STUDENT_ID_EXISTS",
}
SEVERITY = {
    "MISSING_APAAR": "medium", "INVALID_APAAR_FORMAT": "high", "DUP_SAME_COLLEGE": "high",
    "DUP_CROSS_COLLEGE": "critical", "INTAKE_EXCEEDED": "high", "SUPERNUMERARY_EXCEEDED": "high",
    "UNAPPROVED_PROGRAMME": "high", "CATEGORY_INCONSISTENT": "medium", "DOB_IMPLAUSIBLE": "medium",
}
# Warnings that become saved student-level flags on commit.
STUDENT_FLAG_CODES = {"MISSING_APAAR", "INVALID_APAAR_FORMAT", "UNAPPROVED_PROGRAMME",
                      "CATEGORY_INCONSISTENT", "DOB_IMPLAUSIBLE"}
PROGRAMME_FLAG_CODES = ("INTAKE_EXCEEDED", "SUPERNUMERARY_EXCEEDED")
DUP_CODES = ("DUP_SAME_COLLEGE", "DUP_CROSS_COLLEGE", "PROBABLE_DUP")

ADMISSION_CATEGORIES = ["Regular", "EWS", "Sports", "TFW", "PMSSS", "NRI", "OCI", "FN"]
_DOB_ISO = re.compile(r"^(\d{4})-(\d{2})-(\d{2})$")
_DOB_DAY_FIRST = re.compile(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$")


@dataclass
class Issue:
    code: str
    field: str
    message: str
    hint: str = ""
    severity: str = ""

    def __post_init__(self):
        if not self.severity:
            self.severity = "error" if self.code in BLOCKING else SEVERITY.get(self.code, "medium")

    @property
    def blocking(self) -> bool:
        return self.code in BLOCKING


@dataclass
class RowResult:
    row: int
    raw: dict
    issues: list[Issue] = field(default_factory=list)
    data: dict | None = None  # cleaned values; None when the row has blocking errors

    @property
    def status(self) -> str:
        if any(i.blocking for i in self.issues):
            return "error"
        return "warning" if self.issues else "ok"

    def as_dict(self) -> dict:
        return {
            "row": self.row, "status": self.status, "issues": [asdict(i) for i in self.issues],
            "data": {"student_code": self.raw.get("student_id", ""), "name": self.raw.get("name", "")},
        }


def norm_key(text: str) -> str:
    return " ".join((text or "").lower().split())


class CollegeContext:
    """Per-college lookups needed to validate rows."""

    def __init__(self, db: Session, college: College, year: int | None = None):
        self.college = college
        self.year = year or get_policy()["academic_year"]
        self.programmes = {norm_key(p.name): p for p in college.programmes}
        self.existing_codes = set(db.scalars(
            select(Student.student_code).where(Student.college_id == college.id, Student.year == self.year)))


def parse_dob(value: str) -> date | None:
    value = (value or "").strip()
    try:
        if m := _DOB_ISO.match(value):
            return date(int(m[1]), int(m[2]), int(m[3]))
        if m := _DOB_DAY_FIRST.match(value):
            return date(int(m[3]), int(m[2]), int(m[1]))
    except ValueError:
        return None
    return None


def age_on_july_first(dob: date, year: int) -> int:
    ref = date(year, 7, 1)
    return ref.year - dob.year - ((ref.month, ref.day) < (dob.month, dob.day))


def apaar_valid(apaar: str | None) -> bool:
    return bool(apaar) and re.fullmatch(get_policy()["apaar_regex"], apaar) is not None


def _canonical(value: str, allowed: list[str]) -> str | None:
    lookup = {a.lower(): a for a in allowed}
    return lookup.get((value or "").strip().lower())


def student_warnings(data: dict, ctx: CollegeContext) -> list[Issue]:
    """Non-blocking issues for a cleaned row; these become saved flags."""
    policy = get_policy()
    issues = []
    apaar = data["apaar_id"]
    if not apaar:
        issues.append(Issue("MISSING_APAAR", "apaar_id", "APAAR ID is missing",
                            "Collect the student's 12-digit APAAR ID"))
    elif not apaar_valid(apaar):
        issues.append(Issue("INVALID_APAAR_FORMAT", "apaar_id", "APAAR must be exactly 12 digits",
                            "Remove spaces or letters"))
    if data["programme_id"] is None:
        issues.append(Issue("UNAPPROVED_PROGRAMME", "programme",
                            f"Programme '{data['programme_raw']}' is not approved for this institution",
                            "Use the exact name of an approved programme"))
    if data["admission_category"] == "FN" and data["social_category"] != "NA":
        issues.append(Issue("CATEGORY_INCONSISTENT", "social_category",
                            f"Foreign national admission with social category {data['social_category']}",
                            "Foreign national (FN) admissions use social category NA"))
    lo, hi = policy["age_range_on_1_july"][data["level"]]
    age = age_on_july_first(data["dob"], ctx.year)
    if not lo <= age <= hi:
        issues.append(Issue("DOB_IMPLAUSIBLE", "dob",
                            f"Age {age} on 1 July {ctx.year} is outside {lo} to {hi} for {data['level']}",
                            "Check the date of birth"))
    return issues


def check_row(raw: dict, ctx: CollegeContext, row_no: int) -> RowResult:
    policy = get_policy()
    res = RowResult(row=row_no, raw=raw)
    add = res.issues.append
    for col in REQUIRED:
        if not raw.get(col, "").strip():
            add(Issue("MISSING_REQUIRED_FIELD", col, f"Required field '{col}' is empty", f"Fill in {col}"))
    present = lambda col: bool(raw.get(col, "").strip())  # noqa: E731

    dob = parse_dob(raw.get("dob", ""))
    if present("dob") and dob is None:
        add(Issue("INVALID_DOB_FORMAT", "dob", f"Date of birth '{raw['dob']}' is not a valid date",
                  "Use YYYY-MM-DD or DD/MM/YYYY"))
    gender = _canonical(raw.get("gender", ""), policy["genders"])
    if present("gender") and gender is None:
        add(Issue("INVALID_GENDER", "gender", f"Gender '{raw['gender']}' is not valid", "Use M, F or O"))
    level = _canonical(raw.get("level", ""), policy["levels"])
    if present("level") and level is None:
        add(Issue("INVALID_LEVEL", "level", f"Level '{raw['level']}' is not valid", "Use UG, PG or DIPLOMA"))
    shift = _canonical(raw.get("shift", ""), policy["shifts"])
    if present("shift") and shift is None:
        add(Issue("INVALID_SHIFT", "shift", f"Shift '{raw['shift']}' is not valid", "Use Day or Evening"))
    adm = _canonical(raw.get("admission_category", ""), ADMISSION_CATEGORIES)
    if present("admission_category") and adm is None:
        add(Issue("INVALID_ADMISSION_CATEGORY", "admission_category",
                  f"Admission category '{raw['admission_category']}' is not valid",
                  "Use one of: " + ", ".join(ADMISSION_CATEGORIES)))
    social = _canonical(raw.get("social_category", ""), policy["social_categories"])
    if present("social_category") and social is None:
        add(Issue("INVALID_SOCIAL_CATEGORY", "social_category",
                  f"Social category '{raw['social_category']}' is not valid",
                  "Use one of: " + ", ".join(policy["social_categories"])))
    if present("year") and raw["year"].strip() != str(ctx.year):
        add(Issue("YEAR_MISMATCH", "year", f"Year '{raw['year']}' does not match academic year {ctx.year}",
                  f"Use {ctx.year}"))
    code = raw.get("student_id", "").strip()
    if code and code in ctx.existing_codes:
        add(Issue("STUDENT_ID_EXISTS", "student_id", f"Student ID '{code}' already exists for {ctx.year}",
                  "Use a new student ID or edit the existing record"))
    if res.issues:
        return res

    programme = ctx.programmes.get(norm_key(raw["programme"]))
    phone_hash, last4 = hash_phone(raw.get("phone"))
    apaar = raw.get("apaar_id", "").strip() or None
    res.data = {
        "student_code": code, "apaar_id": apaar, "name": raw["name"].strip(),
        "father_name": raw["father_name"].strip(), "dob": dob, "gender": gender,
        "phone_hash": phone_hash, "phone_last4": last4, "programme_id": programme.id if programme else None,
        "programme_raw": raw["programme"].strip(), "level": level, "shift": shift,
        "admission_category": adm, "social_category": social, "year": ctx.year,
    }
    res.issues.extend(student_warnings(res.data, ctx))
    return res


def validate_rows(db: Session, raws: list[dict], ctx: CollegeContext) -> list[RowResult]:
    results = []
    seen_codes: set[str] = set()
    for i, raw in enumerate(raws):
        res = check_row(raw, ctx, raw.get("_row", i + 2))
        code = raw.get("student_id", "").strip()
        if code and code in seen_codes:
            res.issues.append(Issue("DUP_STUDENT_ID_IN_FILE", "student_id",
                                    f"Student ID '{code}' appears more than once in this file",
                                    "Each student ID must be unique"))
            res.data = None
        seen_codes.add(code)
        results.append(res)

    # Exact APAAR conflicts (within file, or with records already in the database).
    savable = [r for r in results if r.data and apaar_valid(r.data["apaar_id"])]
    apaars = {r.data["apaar_id"] for r in savable}
    existing: dict[str, set[int]] = {}
    if apaars:
        stmt = select(Student.apaar_id, Student.college_id).where(
            Student.apaar_id.in_(apaars), Student.year == ctx.year, Student.status == "active")
        for apaar, cid in db.execute(stmt):
            existing.setdefault(apaar, set()).add(cid)
    file_counts: dict[str, int] = {}
    for r in savable:
        file_counts[r.data["apaar_id"]] = file_counts.get(r.data["apaar_id"], 0) + 1
    for r in savable:
        apaar = r.data["apaar_id"]
        colleges = existing.get(apaar, set())
        if file_counts[apaar] > 1 or ctx.college.id in colleges:
            r.issues.append(Issue("DUP_SAME_COLLEGE", "apaar_id",
                                  "This APAAR ID is already used by another record of your institution",
                                  "Check whether this is the same student"))
        if colleges - {ctx.college.id}:
            r.issues.append(Issue("DUP_CROSS_COLLEGE", "apaar_id",
                                  "This APAAR ID is already enrolled at another institution this year",
                                  "Verify the APAAR ID with the student"))
    return results


def summarise(results: list[RowResult]) -> dict:
    statuses = [r.status for r in results]
    return {"total": len(results), "ok": statuses.count("ok"), "warnings": statuses.count("warning"),
            "errors": statuses.count("error")}


# ---------------------------------------------------------------- flag generation

def add_student_flag(db: Session, student: Student, code: str, message: str, *, evidence: dict | None = None,
                     severity: str | None = None, match_id: int | None = None) -> Flag | None:
    """Create a student-level flag unless one already exists for (student, code, counterpart)."""
    evidence = evidence or {}
    counterpart = evidence.get("counterpart_student_id")
    for existing in db.scalars(select(Flag).where(Flag.student_id == student.id, Flag.code == code)):
        if existing.evidence.get("counterpart_student_id") == counterpart:
            return None
    flag = Flag(student_id=student.id, college_id=student.college_id, programme_id=student.programme_id,
                code=code, severity=severity or SEVERITY[code], message=message, evidence=evidence,
                match_id=match_id)
    db.add(flag)
    return flag


def flag_student(db: Session, student: Student, ctx: CollegeContext) -> int:
    data = {"apaar_id": student.apaar_id, "programme_id": student.programme_id,
            "programme_raw": student.programme_raw, "admission_category": student.admission_category,
            "social_category": student.social_category, "level": student.level, "dob": student.dob}
    created = 0
    for issue in student_warnings(data, ctx):
        if add_student_flag(db, student, issue.code, issue.message, evidence={"field": issue.field}):
            created += 1
    return created


def detect_exact_duplicates(db: Session, students: list[Student], year: int) -> int:
    created = 0
    by_apaar = {s.apaar_id: s for s in students if apaar_valid(s.apaar_id)}
    if not by_apaar:
        return 0
    stmt = select(Student).where(Student.apaar_id.in_(by_apaar), Student.year == year, Student.status == "active")
    groups: dict[str, list[Student]] = {}
    for s in db.scalars(stmt):
        groups.setdefault(s.apaar_id, []).append(s)
    new_ids = {s.id for s in students}
    for apaar, members in groups.items():
        for a in members:
            for b in members:
                if a.id == b.id or (a.id not in new_ids and b.id not in new_ids):
                    continue
                same = a.college_id == b.college_id
                code = "DUP_SAME_COLLEGE" if same else "DUP_CROSS_COLLEGE"
                msg = (f"APAAR {apaar} is also used by record {b.student_code} in this institution" if same
                       else f"APAAR {apaar} is also active at another institution this year")
                evidence = {"apaar_id": apaar, "counterpart_student_id": b.id,
                            "counterpart_college_id": b.college_id}
                if add_student_flag(db, a, code, msg, evidence=evidence):
                    created += 1
    return created


def recompute_programme_flags(db: Session, college_id: int) -> int:
    """Idempotently sync INTAKE_EXCEEDED / SUPERNUMERARY_EXCEEDED flags with the ledger."""
    created = 0
    desired: dict[tuple, tuple[str, dict, int]] = {}
    for p in ledger.college_ledger(db, college_id):
        if p["over_by"] > 0:
            desired[(p["id"], "INTAKE_EXCEEDED", None)] = (
                f"{p['name']}: admitted {p['admitted']} against {p['approved_intake']} approved seats "
                f"(over by {p['over_by']})",
                {"approved_intake": p["approved_intake"], "admitted": p["admitted"], "over_by": p["over_by"]},
                p["id"])
        for cat, s in p["supernumerary"].items():
            if s["over_by"] > 0:
                desired[(p["id"], "SUPERNUMERARY_EXCEEDED", cat)] = (
                    f"{p['name']}: {s['count']} {cat} admissions against a cap of {s['cap']} "
                    f"(over by {s['over_by']})",
                    {"category": cat, "count": s["count"], "cap": s["cap"], "over_by": s["over_by"]},
                    p["id"])
    existing = db.scalars(select(Flag).where(Flag.college_id == college_id, Flag.code.in_(PROGRAMME_FLAG_CODES)))
    seen = set()
    for flag in existing:
        key = (flag.programme_id, flag.code, flag.evidence.get("category"))
        if key in desired:
            seen.add(key)
            flag.message, flag.evidence, _ = desired[key]
            if flag.status == "resolved_auto":
                flag.status = "open"
        elif flag.status == "open":
            db.delete(flag)
        elif flag.status != "resolved_auto":
            flag.status = "resolved_auto"
    for key, (message, evidence, pid) in desired.items():
        if key not in seen:
            db.add(Flag(college_id=college_id, programme_id=pid, code=key[1], severity=SEVERITY[key[1]],
                        message=message, evidence=evidence))
            created += 1
    return created


def save_students(db: Session, ctx: CollegeContext, results: list[RowResult], batch_id: int | None,
                  created_at: datetime | None = None) -> list[Student]:
    students = []
    for r in results:
        if r.status == "error" or r.data is None:
            continue
        d = r.data
        s = Student(
            college_id=ctx.college.id, programme_id=d["programme_id"], programme_raw=d["programme_raw"],
            level=d["level"], shift=d["shift"], year=d["year"], student_code=d["student_code"],
            apaar_id=d["apaar_id"], name=d["name"], name_norm=normalise_name(d["name"]),
            father_name=d["father_name"], father_name_norm=normalise_name(d["father_name"]),
            dob=d["dob"], gender=d["gender"], phone_hash=d["phone_hash"], phone_last4=d["phone_last4"],
            admission_category=d["admission_category"], social_category=d["social_category"],
            status="active", batch_id=batch_id, created_at=created_at or utcnow(),
        )
        db.add(s)
        students.append(s)
        ctx.existing_codes.add(d["student_code"])
    db.flush()
    return students


def post_insert(db: Session, ctx: CollegeContext, students: list[Student], *, run_matching: bool = True) -> dict:
    """Generate all flags and matches for newly inserted students."""
    new_flags = sum(flag_student(db, s, ctx) for s in students)
    new_flags += detect_exact_duplicates(db, students, ctx.year)
    db.flush()
    new_flags += recompute_programme_flags(db, ctx.college.id)
    new_matches = 0
    if run_matching:
        m_count, m_flags = matching.match_new_students(db, students)
        new_matches += m_count
        new_flags += m_flags
    db.flush()
    return {"new_flags": new_flags, "new_matches": new_matches}


def commit_rows(db: Session, ctx: CollegeContext, results: list[RowResult], *, actor: str, actor_role: str,
                filename: str) -> dict:
    summary = summarise(results)
    batch = UploadBatch(college_id=ctx.college.id, uploaded_by=actor, filename=filename,
                        rows_total=summary["total"], rows_error=summary["errors"])
    db.add(batch)
    db.flush()
    students = save_students(db, ctx, results, batch.id)
    batch.rows_saved = len(students)
    counts = post_insert(db, ctx, students)
    record(db, actor=actor, actor_role=actor_role, action="UPLOAD_COMMIT", entity_type="upload_batch",
           entity_id=batch.id, payload={"college_id": ctx.college.id, "filename": filename,
                                        "rows_saved": batch.rows_saved, "rows_error": batch.rows_error,
                                        **counts})
    db.commit()
    return {"batch_id": batch.id, "rows_saved": batch.rows_saved, "rows_skipped": summary["errors"], **counts}
