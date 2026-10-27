from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import User
from ..security import INSTITUTION, OFFICER, assert_college_access, require_roles
from ..services import reports
from .common import mask_apaar

router = APIRouter(prefix="/reports", tags=["reports"])

MEDIA = {"csv": "text/csv", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def _file(rows, columns, fmt: str, name: str) -> Response:
    body = reports.to_csv(rows, columns) if fmt == "csv" else reports.to_xlsx(rows, columns, name)
    return Response(body, media_type=MEDIA[fmt],
                    headers={"Content-Disposition": f'attachment; filename="{name}.{fmt}"'})


@router.get("/roster")
def roster(college_id: int | None = None, format: Literal["csv", "xlsx"] = Query("csv"),
           db: Session = Depends(get_db), user: User = Depends(require_roles(OFFICER, INSTITUTION))):
    if user.role == INSTITUTION:
        college_id = user.college_id
    if college_id is None:
        college_id = 1
    assert_college_access(user, college_id)
    mask = (lambda a: a) if user.role == OFFICER else mask_apaar
    rows = reports.roster_rows(db, college_id, mask)
    return _file(rows, reports.ROSTER_COLUMNS, format, f"roster_{reports.college_name(db, college_id)}")


@router.get("/compliance")
def compliance(format: Literal["csv", "xlsx"] = Query("csv"), db: Session = Depends(get_db),
               _user: User = Depends(require_roles(OFFICER))):
    return _file(reports.compliance_rows(db), reports.COMPLIANCE_COLUMNS, format, "compliance")
