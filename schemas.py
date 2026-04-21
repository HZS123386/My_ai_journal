from pydantic import BaseModel, Field
from datetime import datetime

class EntryCreate(BaseModel):
    content: str

class EntryResponse(BaseModel):
    id: int
    content: str
    summary: str | None = None
    mood: str | None = None
    todos: list[str] = Field(default_factory=list)   #防止没提取到而报错
    created_at: datetime

    class Config:
        from_attributes = True











