"""Name and phone normalisation used for storage and fuzzy matching."""
import hashlib
import re

from ..config import get_settings

HONORIFICS = {"mr", "mrs", "ms", "dr", "shri", "smt", "kumari", "sri"}

# Spelling variants mapped to one canonical token. Extend freely.
VARIANTS = {
    "mohd": "mohammed", "md": "mohammed", "muhammad": "mohammed", "mohamed": "mohammed",
    "mohammad": "mohammed", "muhammed": "mohammed", "mohamad": "mohammed", "muhamad": "mohammed",
    "kumaar": "kumar",
    "sing": "singh",
}

_NON_ALPHA = re.compile(r"[^a-z\s]")
_REPEATED_VOWEL = re.compile(r"([aeiou])\1+")


def normalise_token(token: str) -> str:
    token = VARIANTS.get(token, token)
    token = _REPEATED_VOWEL.sub(r"\1", token)
    return VARIANTS.get(token, token)


def normalise_name(value: str | None) -> str:
    if not value:
        return ""
    cleaned = _NON_ALPHA.sub(" ", value.lower())
    tokens = [t for t in cleaned.split() if t not in HONORIFICS]
    return " ".join(normalise_token(t) for t in tokens)


def phone_digits(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", value or "")
    return digits[-10:] if len(digits) >= 10 else None


def hash_phone(value: str | None) -> tuple[str | None, str | None]:
    """Return (salted sha256 hash, last 4 digits) or (None, None) for a missing/short phone."""
    digits = phone_digits(value)
    if digits is None:
        return None, None
    digest = hashlib.sha256((get_settings().phone_salt + digits).encode()).hexdigest()
    return digest, digits[-4:]
