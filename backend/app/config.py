"""Environment settings and policy loading."""
import json
import logging
import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

log = logging.getLogger("apaar")

REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = Path(__file__).resolve().parent / "policy.json"
DEFAULT_JWT_SECRET = "demo-only-insecure-secret-change-me"


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    data_dir: Path
    database_url: str
    keys_dir: Path
    demo_mode: bool
    jwt_secret: str
    demo_otp: str
    phone_salt: str
    dev_cors: bool
    anthropic_api_key: str | None
    jwt_expiry_hours: int = 12
    frontend_dist: Path = field(default_factory=lambda: REPO_ROOT / "frontend" / "dist")


@lru_cache
def get_settings() -> Settings:
    data_dir = Path(os.getenv("DATA_DIR", REPO_ROOT / "data"))
    data_dir.mkdir(parents=True, exist_ok=True)
    db_url = os.getenv("DATABASE_URL") or f"sqlite:///{data_dir / 'app.db'}"
    secret = os.getenv("JWT_SECRET", DEFAULT_JWT_SECRET)
    if secret == DEFAULT_JWT_SECRET:
        log.warning("JWT_SECRET not set; using the insecure demo default")
    return Settings(
        data_dir=data_dir,
        database_url=db_url,
        keys_dir=Path(os.getenv("KEYS_DIR", data_dir / "keys")),
        demo_mode=_bool(os.getenv("DEMO_MODE"), True),
        jwt_secret=secret,
        demo_otp=os.getenv("DEMO_OTP", "123456"),
        phone_salt=os.getenv("PHONE_SALT", "apaar-demo-phone-salt"),
        dev_cors=_bool(os.getenv("DEV_CORS"), False),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY") or None,
    )


@lru_cache
def get_policy() -> dict:
    with open(POLICY_PATH, encoding="utf-8") as fh:
        return json.load(fh)
