from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime
from database import Base

class Entry(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True,index=True)
    content = Column(String,nullable=False)
    summary = Column(String,nullable=True)
    mood = Column(String,nullable=True)
    todos = Column(JSON,nullable=True)
    created_at = Column(DateTime,default=datetime.utcnow)








