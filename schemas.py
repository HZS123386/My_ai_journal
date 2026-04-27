from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List


# =========================
# 用户相关
# =========================

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# =========================
# 日记相关
# =========================

class EntryCreate(BaseModel):
    content: str


class EntryResponse(BaseModel):
    id: int
    content: str
    summary: Optional[str] = None
    mood: Optional[str] = None
    todos: Optional[List[str]] = None
    created_at: datetime
    user_id: Optional[int] = None

    class Config:
        from_attributes = True