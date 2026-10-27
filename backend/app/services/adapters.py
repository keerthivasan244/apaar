"""Interfaces to external national systems, with local mock implementations (demo mode).

Business code depends only on the interfaces; real APAAR / DigiLocker / SMS clients would plug in here.
"""
import logging
from abc import ABC, abstractmethod

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_policy, get_settings
from ..models import Student

log = logging.getLogger("apaar.adapters")


class ApaarRegistry(ABC):
    @abstractmethod
    def lookup(self, apaar_id: str) -> Student | None:
        """Return the current-year enrolment for an APAAR ID, or None."""


class DigiLocker(ABC):
    @abstractmethod
    def fetch(self, doc_id: str) -> dict | None: ...


class OtpSender(ABC):
    @abstractmethod
    def send(self, phone: str | None, otp: str) -> bool: ...

    @abstractmethod
    def current_otp(self) -> str: ...


class MockApaarRegistry(ApaarRegistry):
    """Checks that the APAAR exists in the seeded students table."""

    def __init__(self, db: Session):
        self.db = db

    def lookup(self, apaar_id: str) -> Student | None:
        year = get_policy()["academic_year"]
        return self.db.scalars(select(Student).where(Student.apaar_id == apaar_id.strip(), Student.year == year)
                               .order_by(Student.status, Student.id)).first()


class MockDigiLocker(DigiLocker):
    def fetch(self, doc_id: str) -> dict | None:
        return {"doc_id": doc_id, "issuer": "DigiLocker (simulated)", "available": False}


class MockOtpSender(OtpSender):
    """Never sends anything; the OTP is the fixed demo value."""

    def send(self, phone: str | None, otp: str) -> bool:
        log.info("Simulated OTP dispatch to phone ending %s", (phone or "----")[-4:])
        return True

    def current_otp(self) -> str:
        return get_settings().demo_otp


def apaar_registry(db: Session) -> ApaarRegistry:
    return MockApaarRegistry(db)


def otp_sender() -> OtpSender:
    return MockOtpSender()


def digilocker() -> DigiLocker:
    return MockDigiLocker()
