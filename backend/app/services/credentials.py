"""Ed25519-signed enrolment credentials (PRD 6.7)."""
import base64
import json
import time
import uuid

from nacl.exceptions import BadSignatureError
from nacl.signing import SigningKey, VerifyKey
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import Credential, Student, utcnow
from .audit import canonical_json, record

KID = "k1"


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _key_paths():
    d = get_settings().keys_dir
    return d / "ed25519_private.key", d / "ed25519_public.key"


def signing_key() -> SigningKey:
    """Load the keypair, generating it on first use."""
    priv, pub = _key_paths()
    if priv.exists():
        return SigningKey(priv.read_bytes())
    priv.parent.mkdir(parents=True, exist_ok=True)
    key = SigningKey.generate()
    priv.write_bytes(bytes(key))
    priv.chmod(0o600)
    pub.write_bytes(bytes(key.verify_key))
    return key


def public_key_info() -> dict:
    return {"kid": KID, "algorithm": "Ed25519",
            "public_key_b64": base64.b64encode(bytes(signing_key().verify_key)).decode()}


def sign_payload(payload: dict) -> str:
    payload_b64 = b64url(canonical_json(payload).encode("utf-8"))
    sig = signing_key().sign(payload_b64.encode("ascii")).signature
    return f"{payload_b64}.{b64url(sig)}"


def verify_token(token: str) -> tuple[bool, dict | None]:
    try:
        payload_b64, sig_b64 = token.strip().split(".")
        VerifyKey(bytes(signing_key().verify_key)).verify(payload_b64.encode("ascii"), b64url_decode(sig_b64))
        return True, json.loads(b64url_decode(payload_b64))
    except (ValueError, BadSignatureError, UnicodeError, json.JSONDecodeError):
        return False, None


def masked_apaar(apaar: str | None) -> str | None:
    return "X" * 8 + apaar[-4:] if apaar else None


def issue(db: Session, student: Student, *, actor: str, actor_role: str) -> Credential:
    cid = str(uuid.uuid4())
    payload = {
        "v": 1, "cid": cid, "sid": student.student_code, "apaar": masked_apaar(student.apaar_id),
        "inst": student.college.aicte_id, "inst_name": student.college.name,
        "prog": student.programme.name if student.programme else student.programme_raw, "yr": student.year,
        "status": student.status, "iat": int(time.time()), "kid": KID,
    }
    cred = Credential(id=cid, student_id=student.id, token=sign_payload(payload), kid=KID, issued_at=utcnow())
    db.add(cred)
    record(db, actor=actor, actor_role=actor_role, action="CREDENTIAL_ISSUE", entity_type="credential",
           entity_id=cid, payload={"student_id": student.id, "college_id": student.college_id})
    return cred


def revoke(db: Session, cred: Credential, reason: str, *, actor: str, actor_role: str) -> Credential:
    cred.revoked_at, cred.revoked_reason = utcnow(), reason
    record(db, actor=actor, actor_role=actor_role, action="CREDENTIAL_REVOKE", entity_type="credential",
           entity_id=cred.id, payload={"student_id": cred.student_id, "reason": reason})
    return cred


def status_of(cred: Credential | None, cid: str) -> dict:
    if cred is None:
        return {"cid": cid, "status": "unknown", "revoked_at": None, "reason": None}
    if cred.revoked_at:
        return {"cid": cid, "status": "revoked", "revoked_at": cred.revoked_at.isoformat(),
                "reason": cred.revoked_reason}
    return {"cid": cid, "status": "valid", "revoked_at": None, "reason": None}
