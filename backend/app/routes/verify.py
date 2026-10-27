import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ..db import get_db
from ..services.adapters import apaar_registry

router = APIRouter(prefix="/verify", tags=["verify"])

RATE_LIMIT = 30
WINDOW_SECONDS = 60
_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(request: Request) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    hits = _hits[ip]
    while hits and now - hits[0] > WINDOW_SECONDS:
        hits.popleft()
    if len(hits) >= RATE_LIMIT:
        raise HTTPException(429, "Too many lookups; try again in a minute")
    hits.append(now)


@router.get("/apaar/{apaar_id}", dependencies=[Depends(rate_limit)])
def public_lookup(apaar_id: str, db: Session = Depends(get_db)):
    s = apaar_registry(db).lookup(apaar_id)
    if s is None:
        return {"found": False, "enrolment_status": None, "institution_name": None, "programme": None, "year": None}
    return {"found": True, "enrolment_status": s.status, "institution_name": s.college.name,
            "programme": s.programme.name if s.programme else s.programme_raw, "year": s.year}
