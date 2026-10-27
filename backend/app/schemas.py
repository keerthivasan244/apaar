"""Pydantic request/response schemas."""
from typing import Literal

from pydantic import BaseModel, Field


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    id: int
    username: str
    role: str
    display_name: str
    college_id: int | None = None
    student_id: int | None = None
    organisation: str | None = None


class LoginOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class ReviewIn(BaseModel):
    status: Literal["confirmed", "dismissed"]
    note: str | None = Field(default=None, max_length=2000)


class StudentIn(BaseModel):
    student_id: str
    apaar_id: str | None = None
    name: str
    father_name: str
    dob: str
    gender: str
    phone: str | None = None
    programme: str
    level: str
    shift: str
    admission_category: str
    social_category: str
    year: int | str


class RevokeIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)


class TokenIn(BaseModel):
    token: str = Field(min_length=1, max_length=4000)


ConsentField = Literal["name", "dob", "programme", "admission_category", "student_code"]


class ConsentIn(BaseModel):
    apaar_id: str = Field(min_length=1, max_length=64)
    fields: list[ConsentField] = Field(min_length=1)
    purpose: str = Field(min_length=3, max_length=500)


class OtpIn(BaseModel):
    otp: str = Field(min_length=1, max_length=12)


class TamperIn(BaseModel):
    entry_id: int | None = None


class NlqIn(BaseModel):
    question: str = Field(min_length=3, max_length=500)
