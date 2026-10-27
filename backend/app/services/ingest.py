"""Parse uploaded CSV/XLSX files into raw row dicts keyed by template column."""
import io
from datetime import date, datetime

import pandas as pd

COLUMNS = [
    "student_id", "apaar_id", "name", "father_name", "dob", "gender", "phone", "programme",
    "level", "shift", "admission_category", "social_category", "year",
]
REQUIRED = [c for c in COLUMNS if c not in ("apaar_id", "phone")]
MAX_BYTES = 5 * 1024 * 1024
MAX_ROWS = 5000

TEMPLATE_EXAMPLE = {
    "student_id": "GIT26-9001", "apaar_id": "421912345678", "name": "Example Student",
    "father_name": "Example Parent", "dob": "2006-08-15", "gender": "F", "phone": "9800000000",
    "programme": "B.Tech Computer Science and Engineering", "level": "UG", "shift": "Day",
    "admission_category": "Regular", "social_category": "General", "year": "2026",
}


class UploadError(ValueError):
    """The file as a whole cannot be processed."""


def _cell_to_str(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def parse_upload(content: bytes, filename: str) -> list[dict]:
    if len(content) > MAX_BYTES:
        raise UploadError("File is larger than 5 MB")
    name = (filename or "").lower()
    try:
        if name.endswith(".xlsx"):
            df = pd.read_excel(io.BytesIO(content), dtype=object, engine="openpyxl")
        elif name.endswith(".csv") or not name:
            df = pd.read_csv(io.BytesIO(content), dtype=str, keep_default_na=False, encoding="utf-8-sig")
        else:
            raise UploadError("Only .csv and .xlsx files are accepted")
    except UploadError:
        raise
    except Exception as exc:  # pandas raises many parser-specific types
        raise UploadError(f"Could not read file: {exc}") from exc

    df.columns = [str(c).strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise UploadError(f"Missing required columns: {', '.join(missing)}")
    if len(df) > MAX_ROWS:
        raise UploadError(f"File has {len(df)} rows; the maximum is {MAX_ROWS}")

    rows = []
    for idx, record in enumerate(df.to_dict(orient="records")):
        row = {col: _cell_to_str(record.get(col)) for col in COLUMNS}
        if any(row.values()):  # skip fully blank rows
            row["_row"] = idx + 2  # spreadsheet line number (header is line 1)
            rows.append(row)
    return rows


def template_csv() -> str:
    return ",".join(COLUMNS) + "\n" + ",".join(TEMPLATE_EXAMPLE[c] for c in COLUMNS) + "\n"
