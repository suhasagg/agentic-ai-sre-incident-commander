from datetime import datetime
from sqlalchemy import String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from .database import Base

class Incident(Base):
    __tablename__="incidents"
    id: Mapped[str]=mapped_column(String(80), primary_key=True)
    service: Mapped[str]=mapped_column(String(120), index=True)
    severity: Mapped[str]=mapped_column(String(10))
    summary: Mapped[str]=mapped_column(Text)
    status: Mapped[str]=mapped_column(String(30), default="OPEN")
    analysis: Mapped[dict]=mapped_column(JSON, default=dict)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class IncidentEvent(Base):
    __tablename__="incident_events"
    id: Mapped[int]=mapped_column(primary_key=True, autoincrement=True)
    incident_id: Mapped[str]=mapped_column(ForeignKey("incidents.id"), index=True)
    kind: Mapped[str]=mapped_column(String(50))
    payload: Mapped[dict]=mapped_column(JSON)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Runbook(Base):
    __tablename__="runbooks"
    id: Mapped[str]=mapped_column(String(100), primary_key=True)
    service: Mapped[str]=mapped_column(String(120), index=True)
    title: Mapped[str]=mapped_column(String(250))
    text: Mapped[str]=mapped_column(Text)
    embedding: Mapped[list]=mapped_column(Vector(1536))
