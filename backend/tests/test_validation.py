import io

import pytest
from sqlalchemy import select

from app.models import College, Flag, Student
from app.services.validation import CollegeContext, apaar_valid, check_row, parse_dob

CLEAN = {
    "student_id": "TEST-0001", "apaar_id": "421977770001", "name": "Test Person", "father_name": "Test Parent",
    "dob": "2006-05-04", "gender": "F", "phone": "9876543210", "programme": "B.Tech Mechanical Engineering",
    "level": "UG", "shift": "Day", "admission_category": "Regular", "social_category": "General", "year": "2026",
}


@pytest.fixture
def ctx(db):
    return CollegeContext(db, db.get(College, 1))


def codes(res):
    return {i.code for i in res.issues}


def test_clean_row_has_no_issues(ctx):
    res = check_row(dict(CLEAN), ctx, 2)
    assert res.status == "ok" and res.issues == []
    assert res.data["programme_id"] is not None


@pytest.mark.parametrize("value,ok", [
    ("421900000101", True), ("12345", False), ("ABCD12345678", False), ("4219 0000 0031", False),
    ("4219000001011", False), ("", False),
])
def test_apaar_regex(value, ok):
    assert apaar_valid(value) is ok


@pytest.mark.parametrize("value,expected", [
    ("2005-03-14", (2005, 3, 14)), ("14/03/2005", (2005, 3, 14)), ("14-03-2005", (2005, 3, 14)),
    ("31/02/2005", None), ("2005/03/14", None), ("March 3 2005", None),
])
def test_parse_dob(value, expected):
    d = parse_dob(value)
    assert (d.year, d.month, d.day) == expected if expected else d is None


@pytest.mark.parametrize("field,value,code", [
    ("name", "", "MISSING_REQUIRED_FIELD"),
    ("dob", "31/02/2005", "INVALID_DOB_FORMAT"),
    ("gender", "X", "INVALID_GENDER"),
    ("level", "PHD", "INVALID_LEVEL"),
    ("shift", "Night", "INVALID_SHIFT"),
    ("admission_category", "VIP", "INVALID_ADMISSION_CATEGORY"),
    ("social_category", "XYZ", "INVALID_SOCIAL_CATEGORY"),
    ("year", "2025", "YEAR_MISMATCH"),
])
def test_blocking_errors(ctx, field, value, code):
    res = check_row({**CLEAN, field: value}, ctx, 2)
    assert code in codes(res)
    assert res.status == "error" and res.data is None


@pytest.mark.parametrize("changes,code", [
    ({"apaar_id": ""}, "MISSING_APAAR"),
    ({"apaar_id": "ABCD12345678"}, "INVALID_APAAR_FORMAT"),
    ({"programme": "B.Tech Underwater Basket Weaving"}, "UNAPPROVED_PROGRAMME"),
    ({"admission_category": "FN", "social_category": "OBC"}, "CATEGORY_INCONSISTENT"),
    ({"dob": "1960-01-01"}, "DOB_IMPLAUSIBLE"),
])
def test_warnings(ctx, changes, code):
    res = check_row({**CLEAN, **changes}, ctx, 2)
    assert codes(res) == {code}
    assert res.status == "warning" and res.data is not None


def test_programme_match_is_case_and_space_insensitive(ctx):
    res = check_row({**CLEAN, "programme": "  b.tech   MECHANICAL engineering "}, ctx, 2)
    assert res.status == "ok"


def _csv(rows):
    cols = list(CLEAN)
    lines = [",".join(cols)] + [",".join(r[c] for c in cols) for r in rows]
    return io.BytesIO(("\n".join(lines) + "\n").encode())


def test_bulk_dry_run_and_commit(client, auth, db, restore_seed):
    rows = [
        {**CLEAN, "student_id": "T-1", "apaar_id": "421977770011"},
        {**CLEAN, "student_id": "T-2", "apaar_id": "BAD"},
        {**CLEAN, "student_id": "T-3", "apaar_id": "421977770013", "dob": "31/02/2005"},
        {**CLEAN, "student_id": "T-1", "apaar_id": "421977770014"},  # duplicate student id
    ]
    files = {"file": ("t.csv", _csv(rows).getvalue(), "text/csv")}
    before = db.query(Student).count()
    r = client.post("/api/v1/students/bulk?dry_run=true", files=files, headers=auth("inst_a"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"] == {"total": 4, "ok": 1, "warnings": 1, "errors": 2}
    assert body["rows"][0]["row"] == 2
    assert db.query(Student).count() == before  # dry-run writes nothing

    r = client.post("/api/v1/students/bulk?dry_run=false", files=files, headers=auth("inst_a"))
    body = r.json()
    assert body["rows_saved"] == 2 and body["batch_id"] is not None and body["new_flags"] == 1
    db.expire_all()
    saved = db.scalar(select(Student).where(Student.student_code == "T-2"))
    assert [f.code for f in db.scalars(select(Flag).where(Flag.student_id == saved.id))] == ["INVALID_APAAR_FORMAT"]
    # Re-uploading the same IDs is blocked rather than crashing on the unique constraint.
    r = client.post("/api/v1/students/bulk?dry_run=true", files=files, headers=auth("inst_a"))
    assert r.json()["summary"]["errors"] == 4


def test_intake_flags_are_idempotent(client, auth, db, restore_seed):
    ledger = client.get("/api/v1/colleges/1/programmes", headers=auth("inst_a")).json()
    me = next(p for p in ledger if p["name"] == "B.Tech Mechanical Engineering")
    need = me["approved_intake"] - me["admitted"] + 2
    rows = [{**CLEAN, "student_id": f"IX-{i}", "apaar_id": f"4219888{i:05d}"} for i in range(need)]
    files = {"file": ("t.csv", _csv(rows).getvalue(), "text/csv")}
    r = client.post("/api/v1/students/bulk?dry_run=false", files=files, headers=auth("inst_a"))
    assert r.status_code == 200
    me = next(p for p in client.get("/api/v1/colleges/1/programmes", headers=auth("inst_a")).json()
              if p["id"] == me["id"])
    assert me["over_by"] == 2
    flags = client.get("/api/v1/flags?code=INTAKE_EXCEEDED", headers=auth("inst_a")).json()
    assert flags["total"] == 1 and "over by 2" in flags["items"][0]["message"]
    # A second commit that changes nothing in this programme keeps exactly one flag.
    other = [{**CLEAN, "student_id": "IX-extra", "apaar_id": "421988899999",
              "programme": "B.Tech Computer Science and Engineering"}]
    client.post("/api/v1/students/bulk?dry_run=false", files={"file": ("u.csv", _csv(other).getvalue())},
                headers=auth("inst_a"))
    assert client.get("/api/v1/flags?code=INTAKE_EXCEEDED", headers=auth("inst_a")).json()["total"] == 1


def test_bulk_rejects_bad_files(client, auth):
    r = client.post("/api/v1/students/bulk", files={"file": ("x.txt", b"hello")}, headers=auth("inst_a"))
    assert r.status_code == 422
    r = client.post("/api/v1/students/bulk", files={"file": ("x.csv", b"name,dob\nA,2005-01-01\n")},
                    headers=auth("inst_a"))
    assert r.status_code == 422 and "Missing required columns" in r.json()["detail"]
    r = client.post("/api/v1/students/bulk", files={"file": ("x.csv", b"a")}, headers=auth("officer"))
    assert r.status_code == 403


def test_template(client, auth):
    r = client.get("/api/v1/templates/students.csv", headers=auth("verifier"))
    assert r.status_code == 200 and r.text.startswith("student_id,apaar_id,name")
