from datetime import timedelta

from app.models import Consent, utcnow


def _request(client, auth, fields=("name", "programme")):
    r = client.post("/api/v1/consents", json={"apaar_id": "421900000101", "fields": list(fields),
                                               "purpose": "Pre-employment verification"}, headers=auth("verifier"))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "requested"
    return r.json()["id"]


def test_public_lookup_is_minimal(client):
    r = client.get("/api/v1/verify/apaar/421900000101").json()
    assert r == {"found": True, "enrolment_status": "active", "institution_name": "Greenfield Institute of Technology",
                 "programme": "B.Tech Computer Science and Engineering", "year": 2026}
    assert client.get("/api/v1/verify/apaar/000000000000").json()["found"] is False


def test_consent_flow(client, auth, db, restore_seed):
    cid = _request(client, auth)
    assert client.get(f"/api/v1/consents/{cid}/result", headers=auth("verifier")).status_code == 403
    inbox = client.get("/api/v1/consents/mine", headers=auth("student")).json()
    assert inbox[0]["verifier_organisation"] == "Acme Hiring Pvt Ltd (demo)"

    assert client.post(f"/api/v1/consents/{cid}/approve", json={"otp": "000000"},
                       headers=auth("student")).status_code == 400
    assert client.post(f"/api/v1/consents/{cid}/approve", json={"otp": "123456"},
                       headers=auth("verifier")).status_code == 403
    r = client.post(f"/api/v1/consents/{cid}/approve", json={"otp": "123456"}, headers=auth("student"))
    assert r.json()["status"] == "approved"

    res = client.get(f"/api/v1/consents/{cid}/result", headers=auth("verifier")).json()
    assert res["data"] == {"name": "Ananya Rao", "programme": "B.Tech Computer Science and Engineering"}

    # Expiry
    c = db.get(Consent, cid)
    c.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()
    assert client.get(f"/api/v1/consents/{cid}/result", headers=auth("verifier")).status_code == 403
    assert client.get("/api/v1/consents/mine", headers=auth("verifier")).json()[0]["status"] == "expired"

    # Revocation
    cid2 = _request(client, auth, ("dob",))
    client.post(f"/api/v1/consents/{cid2}/approve", json={"otp": "123456"}, headers=auth("student"))
    assert client.get(f"/api/v1/consents/{cid2}/result", headers=auth("verifier")).json()["data"] == {"dob": "2006-01-15"}
    assert client.post(f"/api/v1/consents/{cid2}/revoke", headers=auth("student")).json()["status"] == "revoked"
    assert client.get(f"/api/v1/consents/{cid2}/result", headers=auth("verifier")).status_code == 403

    # Deny
    cid3 = _request(client, auth)
    assert client.post(f"/api/v1/consents/{cid3}/deny", headers=auth("student")).json()["status"] == "denied"
    assert client.get(f"/api/v1/consents/{cid3}/result", headers=auth("verifier")).status_code == 403


def test_consent_validation(client, auth):
    r = client.post("/api/v1/consents", json={"apaar_id": "421900000101", "fields": ["phone"], "purpose": "x y z"},
                    headers=auth("verifier"))
    assert r.status_code == 422
    r = client.post("/api/v1/consents", json={"apaar_id": "999999999999", "fields": ["name"], "purpose": "check"},
                    headers=auth("verifier"))
    assert r.status_code == 404
    assert client.post("/api/v1/consents", json={}, headers=auth("student")).status_code == 403


def test_public_lookup_rate_limit(client):
    from app.routes import verify

    verify._hits.clear()
    codes = [client.get("/api/v1/verify/apaar/421900000101").status_code for _ in range(31)]
    assert codes[:30] == [200] * 30 and codes[30] == 429
    verify._hits.clear()


def test_student_profile(client, auth):
    me = client.get("/api/v1/students/me", headers=auth("student")).json()
    assert me["name"] == "Ananya Rao" and me["apaar_id"] == "XXXXXXXX0101"
    assert client.get("/api/v1/students/me", headers=auth("inst_a")).status_code == 403
