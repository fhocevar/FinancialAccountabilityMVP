from datetime import datetime
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

def now(): return datetime.utcnow()
class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(120))
    email: Mapped[str]=mapped_column(String(180), unique=True, index=True)
    password_hash: Mapped[str]=mapped_column(String(300))
    role: Mapped[str]=mapped_column(String(30), default="ADVISOR")
    active: Mapped[bool]=mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=now)
class Client(Base):
    __tablename__="clients"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(180), unique=True, index=True)
    aliases: Mapped[str]=mapped_column(Text, default="")
    owner: Mapped[str]=mapped_column(String(120), default="Unassigned")
    external_id: Mapped[str|None]=mapped_column(String(120), nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=now)
    commitments: Mapped[list["Commitment"]]=relationship(back_populates="client")
class Meeting(Base):
    __tablename__="meetings"
    id: Mapped[int]=mapped_column(primary_key=True)
    title: Mapped[str]=mapped_column(String(200))
    meeting_date: Mapped[str]=mapped_column(String(20))
    source_type: Mapped[str]=mapped_column(String(30), default="TEXT")
    original_filename: Mapped[str|None]=mapped_column(String(255), nullable=True)
    status: Mapped[str]=mapped_column(String(30), default="PROCESSED")
    transcript: Mapped[str]=mapped_column(Text, default="")
    created_by_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=now)
    commitments: Mapped[list["Commitment"]]=relationship(back_populates="meeting", cascade="all, delete-orphan")
class Commitment(Base):
    __tablename__="commitments"
    id: Mapped[int]=mapped_column(primary_key=True)
    meeting_id: Mapped[int]=mapped_column(ForeignKey("meetings.id"))
    client_id: Mapped[int|None]=mapped_column(ForeignKey("clients.id"), nullable=True)
    client_name: Mapped[str]=mapped_column(String(180), default="Unknown")
    description: Mapped[str]=mapped_column(Text)
    owner: Mapped[str]=mapped_column(String(120), default="Unassigned")
    due_date: Mapped[str|None]=mapped_column(String(20), nullable=True)
    status: Mapped[str]=mapped_column(String(30), default="OPEN")
    review_status: Mapped[str]=mapped_column(String(30), default="PENDING_REVIEW")
    confidence: Mapped[float]=mapped_column(Float, default=.5)
    evidence: Mapped[str]=mapped_column(Text, default="")
    created_at: Mapped[datetime]=mapped_column(DateTime, default=now)
    closed_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    meeting: Mapped[Meeting]=relationship(back_populates="commitments")
    client: Mapped[Client|None]=relationship(back_populates="commitments")
class AuditEvent(Base):
    __tablename__="audit_events"
    id: Mapped[int]=mapped_column(primary_key=True)
    commitment_id: Mapped[int|None]=mapped_column(ForeignKey("commitments.id"), nullable=True)
    user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id"), nullable=True)
    event_type: Mapped[str]=mapped_column(String(80))
    actor: Mapped[str]=mapped_column(String(120), default="system")
    details: Mapped[str]=mapped_column(Text, default="")
    before_json: Mapped[str]=mapped_column(Text, default="")
    after_json: Mapped[str]=mapped_column(Text, default="")
    created_at: Mapped[datetime]=mapped_column(DateTime, default=now)
