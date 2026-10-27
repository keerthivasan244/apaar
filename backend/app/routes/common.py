"""Shared helpers for route modules."""
from fastapi import Query


class Page:
    def __init__(self, page: int = Query(1, ge=1), page_size: int = Query(25, ge=1, le=200)):
        self.page = page
        self.page_size = page_size

    def apply(self, stmt):
        return stmt.offset((self.page - 1) * self.page_size).limit(self.page_size)

    def wrap(self, items: list, total: int) -> dict:
        return {"items": items, "total": total, "page": self.page, "page_size": self.page_size}


def mask_apaar(apaar: str | None) -> str | None:
    if not apaar:
        return None
    return "X" * max(0, len(apaar) - 4) + apaar[-4:]
