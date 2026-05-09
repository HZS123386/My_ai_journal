from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    phone = Column(String, unique=True, nullable=True, index=True)

    entries = relationship('Entry', back_populates='user',cascade='all, delete-orphan')


class Entry(Base):
    __tablename__ = "entries"

    id = Column(Integer, primary_key=True,index=True)
    content = Column(String,nullable=False)
    summary = Column(String,nullable=True)
    mood = Column(String,nullable=True)
    todos = Column(JSON,nullable=True)
    created_at = Column(DateTime,default=datetime.utcnow)

    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    user = relationship('User', back_populates='entries')






