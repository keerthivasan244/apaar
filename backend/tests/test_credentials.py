import base64

from nacl.signing import VerifyKey
from sqlalchemy import select

from app.models import Credential, Student
from app.services import credentials as creds


def _flip(token: str, index: int) -> str:
    ch = token[index]
    return token[:index] + ("B" if ch != "B" else "C") + token[index + 1:]


def test_round_trip_and_tamper():
    token = creds.sign_payload({"cid": "x", "sid": "S1"})
    assert creds.verify_token(token) == (True, {"cid": "x", "sid": "S1"})
    for idx in (5, len(token) // 2, len(token) - 3):
        assert creds.verify_token(_flip(token, idx))[0] is False
    assert creds.verify_token("garbage")[0] is False


def test_signature_matches_public_key_like_the_browser(client):
    """The browser verifies the signature over the ASCII payload_b64 with the published key."""
    info = client.get("/api/v1/keys/public").json()
    assert info["kid"] == "k1" and info["algorithm"] == "Ed25519"
    token = creds.sign_payload({"hello": "world"})
    payload_b64, sig_b64 = token.split(".")
    key = VerifyKey(base64.b64decode(info["public_key_b64"]))
    key.verify(payload_b64.encode(), creds.b64url_decode(sig_b64))


def test_seeded_credentials(client, db):
    ananya = db.scalar(select(Student).where(Student.apaar_id == "421900000101"))
    valid = db.scalar(select(Credential).where(Credential.student_id == ananya.id))
    r = client.post("/api/v1/credentials/verify", json={"token": valid.token}).json()
    assert r["signature_valid"] and r["status"] == "valid"
    assert r["payload"]["apaar"] == "XXXXXXXX0101" and r["payload"]["inst"] == "SYN-0001"

    dev = db.scalar(select(Credential).join(Student).where(Student.name == "Dev Malhotra"))
    r = client.post("/api/v1/credentials/verify", json={"token": dev.token}).json()
    assert r["signature_valid"] is True and r["status"] == "revoked"
    status = client.get(f"/api/v1/credentials/status/{dev.id}").json()
    assert status["status"] == "revoked" and status["reason"] == "Withdrawn from programme"
    assert client.get("/api/v1/credentials/status/nope").json()["status"] == "unknown"

    bad = client.post("/api/v1/credentials/verify", json={"token": _flip(valid.token, 10)}).json()
    assert bad == {"signature_valid": False, "status": None, "payload": None}


def test_issue_revoke_permissions(client, auth, db, restore_seed):
    c1_student = db.scalar(select(Student).where(Student.college_id == 1).limit(1))
    c2_student = db.scalar(select(Student).where(Student.college_id == 2).limit(1))
    assert client.post(f"/api/v1/credentials/issue/{c2_student.id}", headers=auth("inst_a")).status_code == 403
    assert client.post(f"/api/v1/credentials/issue/{c1_student.id}", headers=auth("student")).status_code == 403
    r = client.post(f"/api/v1/credentials/issue/{c1_student.id}", headers=auth("inst_a"))
    assert r.status_code == 200 and r.json()["status"] == "valid"
    cid = r.json()["id"]
    assert client.post(f"/api/v1/credentials/{cid}/revoke", json={"reason": "test"},
                       headers=auth("inst_b")).status_code == 403
    r = client.post(f"/api/v1/credentials/{cid}/revoke", json={"reason": "test"}, headers=auth("officer"))
    assert r.json()["status"] == "revoked"
    mine = client.get("/api/v1/credentials/mine", headers=auth("student")).json()
    assert len(mine) == 1 and mine[0]["status"] == "valid"
    listed = client.get("/api/v1/credentials", headers=auth("inst_a")).json()
    assert listed["total"] == 3
