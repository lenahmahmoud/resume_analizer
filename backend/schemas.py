from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


class JobIn(BaseModel):
    title: str = Field(min_length=2, max_length=150)
    company: str = Field(min_length=1, max_length=150)
    location: str = Field(default="Remote", max_length=150)
    job_type: str = Field(default="Full-time", max_length=50)
    description: str = Field(min_length=20, max_length=10000)
    required_skills: list[str] = Field(default_factory=list, max_length=40)


class JobOut(JobIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime


class ImproveIn(BaseModel):
    target_job_id: Optional[int] = None
    target_role: Optional[str] = Field(default=None, max_length=150)


class ChatIn(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    resume_id: Optional[int] = None