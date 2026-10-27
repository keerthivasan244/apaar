"""Test setup: a temporary data directory and SQLite DB per test session, seeded once."""
import os
import tempfile

_tmp = tempfile.mkdtemp(prefix="apaar-test-")
os.environ["DATA_DIR"] = _tmp
os.environ.pop("DATABASE_URL", None)
os.environ["DEMO_MODE"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import create_app  # noqa: E402
from app.seed import reset_and_seed  # noqa: E402

_seeded = False


@pytest.fixture(scope="session")
def seeded():
    global _seeded
    if not _seeded:
        reset_and_seed()
        _seeded = True
    return True


@pytest.fixture
def reseed():
    """Use in tests that mutate data and need a clean slate."""
    reset_and_seed()
    yield


@pytest.fixture(scope="session")
def client(seeded):
    with TestClient(create_app(auto_seed=False)) as c:
        yield c


_tokens: dict[str, str] = {}


def login(client, username: str, password: str = "demo123") -> dict:
    if username not in _tokens:
        r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
        assert r.status_code == 200, r.text
        _tokens[username] = r.json()["access_token"]
    return {"Authorization": f"Bearer {_tokens[username]}"}


@pytest.fixture
def auth(client):
    return lambda username: login(client, username)
