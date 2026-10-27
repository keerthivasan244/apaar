"""Scripted version of the PRD section 11 demo (steps 1 to 15) plus role-permission checks."""
from pathlib import Path

import pytest

SEED_DATA = Path(__file__).resolve().parents[1] / "seed_data"
API = "/api/v1"


@pytest.fixture
def h(client):
    """Fresh logins (tokens survive resets because user ids are stable)."""
    def headers(user):
        r = client.post(f"{API}/auth/login", json={"username": user, "password": "demo123"})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    return {u: headers(u) for u in ("inst_a", "inst_b", "officer", "student", "verifier")}


def upload(client, headers, name, dry_run):
    r = client.post(f"{API}/students/bulk?dry_run={'true' if dry_run else 'false'}",
                    files={"file": (name, (SEED_DATA / name).read_bytes(), "text/csv")}, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


def flip(token: str, i: int = 25) -> str:
    return token[:i] + ("A" if token[i] != "A" else "B") + token[i + 1:]


def test_demo_script(client, h, restore_seed):
    # Pre-step: reset
    assert client.post(f"{API}/admin/demo/reset", headers=h["officer"]).status_code == 200
    before = client.get(f"{API}/analytics/overview", headers=h["officer"]).json()["totals"]

    # 1. clean upload
    assert upload(client, h["inst_a"], "c1_clean.csv", True)["summary"] == {"total": 40, "ok": 40, "warnings": 0, "errors": 0}
    out = upload(client, h["inst_a"], "c1_clean.csv", False)
    assert (out["rows_saved"], out["new_flags"]) == (40, 0)

    # 2. upload with issues
    dry = upload(client, h["inst_a"], "c1_with_issues.csv", True)
    assert dry["summary"] == {"total": 40, "ok": 36, "warnings": 3, "errors": 1}
    out = upload(client, h["inst_a"], "c1_with_issues.csv", False)
    assert out["rows_saved"] == 39 and out["rows_skipped"] == 1 and out["new_matches"] >= 2 and out["new_flags"] > 0

    # 3. officer dashboard
    ov = client.get(f"{API}/analytics/overview", headers=h["officer"]).json()
    assert ov["totals"]["students"] == before["students"] + 79
    assert ov["totals"]["pending_matches"] == before["pending_matches"] + 2
    assert {r["college_id"] for r in ov["top_over_intake"][:2]} == {2, 3}
    assert ov["top_risk"][0]["college_id"] == 3 and ov["top_risk"][0]["band"] == "high"

    # 4. Muhammad Aslam match
    matches = client.get(f"{API}/matches?status=pending", headers=h["officer"]).json()["items"]
    aslam = next(m for m in matches if m["student_b"]["name"] == "Muhammad Aslam")
    detail = client.get(f"{API}/matches/{aslam['id']}", headers=h["officer"]).json()
    assert detail["score"] >= 0.90
    text = " ".join(detail["explanations"])
    assert "spelling variants" in text and "Date of birth identical" in text
    assert detail["student_a"]["college_name"] and detail["student_b"]["college_name"]
    r = client.patch(f"{API}/matches/{aslam['id']}", json={"status": "confirmed", "note": "same person"}, headers=h["officer"])
    assert r.json()["status"] == "confirmed"
    linked = client.get(f"{API}/flags?code=PROBABLE_DUP&status=confirmed", headers=h["officer"]).json()["items"]
    assert any(f["match_id"] == aslam["id"] for f in linked)

    # 5. risk for College 3
    c3 = client.get(f"{API}/risk/colleges/3", headers=h["officer"]).json()
    assert c3["score"] >= 65 and c3["band"] == "high" and len(c3["reasons"]) == 3 and len(c3["components"]) == 5

    # 6. student credential
    mine = client.get(f"{API}/credentials/mine", headers=h["student"]).json()
    token = mine[0]["token"]
    assert client.get(f"{API}/credentials/status/{mine[0]['id']}").json()["status"] == "valid"

    # 7. verifier lookup + consent request
    assert client.get(f"{API}/verify/apaar/421900000101").json()["found"] is True
    r = client.post(f"{API}/consents", json={"apaar_id": "421900000101", "fields": ["name", "programme"],
                                             "purpose": "Pre-employment verification"}, headers=h["verifier"])
    cid = r.json()["id"]
    assert r.json()["status"] == "requested"
    assert client.get(f"{API}/consents/{cid}/result", headers=h["verifier"]).status_code == 403

    # 8. student approves
    assert client.post(f"{API}/consents/{cid}/approve", json={"otp": "123456"}, headers=h["student"]).json()["status"] == "approved"

    # 9. verifier sees exactly name and programme
    data = client.get(f"{API}/consents/{cid}/result", headers=h["verifier"]).json()["data"]
    assert set(data) == {"name", "programme"} and "dob" not in data

    # 10. signature valid (the offline path is covered in the browser; the server check uses the same key)
    assert client.post(f"{API}/credentials/verify", json={"token": token}).json()["signature_valid"] is True

    # 11. one changed character fails
    assert client.post(f"{API}/credentials/verify", json={"token": flip(token)}).json()["signature_valid"] is False

    # 12. Dev Malhotra: valid signature, revoked
    tokens = client.get(f"{API}/admin/demo/tokens").json()
    dev = next(t["token"] for t in tokens if t["label"].startswith("Dev Malhotra"))
    res = client.post(f"{API}/credentials/verify", json={"token": dev}).json()
    assert res["signature_valid"] is True and res["status"] == "revoked"
    status = client.get(f"{API}/credentials/status/{res['payload']['cid']}").json()
    assert status["reason"] == "Withdrawn from programme"

    # 13. chain intact
    v = client.get(f"{API}/audit/verify", headers=h["officer"]).json()
    assert v["intact"] is True and v["entries_checked"] >= 9
    actions = {a["action"] for a in client.get(f"{API}/audit?page_size=200", headers=h["officer"]).json()["items"]}
    assert {"UPLOAD_COMMIT", "MATCH_REVIEW", "CONSENT_REQUEST", "CONSENT_APPROVE", "DEMO_RESET"} <= actions

    # 14. tamper breaks at the tampered entry
    tampered = client.post(f"{API}/admin/demo/tamper-audit", headers=h["officer"]).json()["entry_id"]
    v = client.get(f"{API}/audit/verify", headers=h["officer"]).json()
    assert v["intact"] is False and v["first_broken_id"] == tampered

    # 15. reset restores integrity
    assert client.post(f"{API}/admin/demo/reset", headers=h["officer"]).status_code == 200
    assert client.get(f"{API}/audit/verify", headers=h["officer"]).json()["intact"] is True


def test_role_permissions(client, h):
    # institution cannot read another college
    assert client.get(f"{API}/colleges/2", headers=h["inst_a"]).status_code == 403
    assert client.get(f"{API}/colleges/2/programmes", headers=h["inst_a"]).status_code == 403
    assert client.get(f"{API}/analytics/colleges/2", headers=h["inst_a"]).status_code == 403
    students = client.get(f"{API}/students?college_id=2", headers=h["inst_a"]).json()["items"]
    assert students and all(s["college_id"] == 1 for s in students)
    c2_student = client.get(f"{API}/students?college_id=2", headers=h["officer"]).json()["items"][0]
    assert client.get(f"{API}/students/{c2_student['id']}", headers=h["inst_a"]).status_code == 403
    flags = client.get(f"{API}/flags?college_id=3", headers=h["inst_a"]).json()["items"]
    assert all(f["college_id"] == 1 for f in flags)
    # APAAR masked for institutions, full for officers
    assert students[0]["apaar_id"].startswith("XXXX")
    assert not c2_student["apaar_id"].startswith("X")
    # verifier cannot read results without consent, nor officer data
    r = client.post(f"{API}/consents", json={"apaar_id": "421900000101", "fields": ["dob"], "purpose": "check dob"},
                    headers=h["verifier"])
    assert client.get(f"{API}/consents/{r.json()['id']}/result", headers=h["verifier"]).status_code == 403
    assert client.get(f"{API}/students", headers=h["verifier"]).status_code == 403
    # student cannot access officer routes
    for path in ("/analytics/overview", "/risk/colleges", "/matches", "/audit", "/audit/verify", "/colleges",
                 "/reports/compliance"):
        assert client.get(f"{API}{path}", headers=h["student"]).status_code == 403, path
    assert client.post(f"{API}/admin/demo/reset", headers=h["student"]).status_code == 403
    assert client.post(f"{API}/admin/demo/tamper-audit", headers=h["inst_a"]).status_code == 403
    # public endpoints never return personal data
    pub = client.get(f"{API}/verify/apaar/421900000101").json()
    assert set(pub) == {"found", "enrolment_status", "institution_name", "programme", "year"}


def test_performance(client, h):
    import time

    for path in ("/analytics/overview", "/risk/colleges", "/colleges"):
        start = time.perf_counter()
        assert client.get(f"{API}{path}", headers=h["officer"]).status_code == 200
        assert time.perf_counter() - start < 1.0, path
