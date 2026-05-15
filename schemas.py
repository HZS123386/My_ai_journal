from pydantic import BaseModel, ConfigDict, EmailStr
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
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# =========================
# 日记相关
# =========================

class EntryCreate(BaseModel):
    content: str
    tags: Optional[list[str]] = None


class EntryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content: str
    summary: Optional[str] = None
    mood: Optional[str] = None
    todos: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    created_at: datetime
    user_id: Optional[int] = None

class EntryListResponse(BaseModel):
    items: List[EntryResponse]
    total: int
    page: int
    page_size: int
    pages: int
