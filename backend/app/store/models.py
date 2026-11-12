"""Persistent entities. No free patient text in logs."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.store.db import Base


def new_id() -> str:
    return uuid.uuid4().hex


def utcnow() -> datetime:
    return datetime.now(UTC)


class Worker(Base):
    __tablename__ = "workers"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    role: Mapped[str] = mapped_column(String(20), default="worker")
    state: Mapped[str | None] = mapped_column(String(2))
    district: Mapped[str | None] = mapped_column(String(100))
    language: Mapped[str] = mapped_column(String(5), default="hi")
    pin_hash: Mapped[str | None] = mapped_column(String(200))
    failed_logins: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class AuthSession(Base):
    """Login session. Only hashes of tokens are stored."""

    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"))
    access_hash: Mapped[str] = mapped_column(String(64), unique=True)
    refresh_hash: Mapped[str] = mapped_column(String(64), unique=True)
    access_expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    refresh_expires: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AuditEvent(Base):
    """Append-only (enforced by database triggers). Detail never holds free patient text."""

    __tablename__ = "audit_events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    actor_id: Mapped[str | None] = mapped_column(String(32))
    encounter_id: Mapped[str | None] = mapped_column(String(32))
    person_id: Mapped[str | None] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(50))
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    versions: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class Person(Base):
    __tablename__ = "persons"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"))
    name: Mapped[str] = mapped_column(String(200))
    age_years: Mapped[int | None] = mapped_column(Integer)
    age_months: Mapped[int | None] = mapped_column(Integer)
    sex: Mapped[str | None] = mapped_column(String(10))
    village: Mapped[str | None] = mapped_column(String(200))
    state: Mapped[str | None] = mapped_column(String(2))
    pregnant: Mapped[str] = mapped_column(String(10), default="unknown")
    ayushman_card_held: Mapped[str] = mapped_column(
        String(10), default="unknown"
    )  # household, optional
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Encounter(Base):
    __tablename__ = "encounters"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.id"))
    worker_id: Mapped[str] = mapped_column(ForeignKey("workers.id"))
    language: Mapped[str] = mapped_column(String(5))
    status: Mapped[str] = mapped_column(String(20), default="draft")
    pathway_id: Mapped[str | None] = mapped_column(String(100))
    pathway_version: Mapped[str | None] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_offline: Mapped[bool] = mapped_column(Boolean, default=False)
    synthetic: Mapped[bool] = mapped_column(Boolean, default=False)

    person: Mapped[Person] = relationship()
    facts: Mapped[list[FactRow]] = relationship(
        back_populates="encounter", cascade="all, delete-orphan", order_by="FactRow.id"
    )
    captures: Mapped[list[Capture]] = relationship(cascade="all, delete-orphan")
    triage_results: Mapped[list[TriageRow]] = relationship(
        cascade="all, delete-orphan", order_by="TriageRow.created_at"
    )
    extractions: Mapped[list[ExtractionRow]] = relationship(
        cascade="all, delete-orphan", order_by="ExtractionRow.created_at"
    )
    consents: Mapped[list[Consent]] = relationship(order_by="Consent.recorded_at")
    plans: Mapped[list[ReferralPlanRow]] = relationship(
        cascade="all, delete-orphan", order_by="ReferralPlanRow.created_at"
    )
    outputs: Mapped[list[OutputRow]] = relationship(
        cascade="all, delete-orphan", order_by="OutputRow.created_at"
    )


class Capture(Base):
    __tablename__ = "captures"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id"))
    kind: Mapped[str] = mapped_column(String(10))  # audio | text
    transcript: Mapped[str] = mapped_column(Text)
    transcript_original: Mapped[str | None] = mapped_column(Text)  # ASR output before edits
    audio_path: Mapped[str | None] = mapped_column(String(500))  # None once deleted
    asr_provider: Mapped[str | None] = mapped_column(String(40))
    asr_model_rev: Mapped[str | None] = mapped_column(String(200))
    duration_s: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class FactRow(Base):
    __tablename__ = "facts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id"))
    key: Mapped[str] = mapped_column(String(100))
    value: Mapped[Any] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    origin: Mapped[str] = mapped_column(String(20))
    source_span: Mapped[str | None] = mapped_column(Text)
    confirmed_by: Mapped[str | None] = mapped_column(String(32))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    encounter: Mapped[Encounter] = relationship(back_populates="facts")


class TriageRow(Base):
    __tablename__ = "triage_results"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id"))
    urgency: Mapped[str] = mapped_column(String(20))
    result: Mapped[dict[str, Any]] = mapped_column(JSON)  # full TriageResult
    confirmed_facts: Mapped[dict[str, Any]] = mapped_column(JSON)  # input, for replay
    ruleset_version: Mapped[str] = mapped_column(String(40))
    engine: Mapped[str] = mapped_column(String(10), default="server")
    superseded: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ExtractionRow(Base):
    """One extraction run: provider, model and prompt versions, outcome. No transcript copy."""

    __tablename__ = "extractions"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id"))
    capture_id: Mapped[str | None] = mapped_column(ForeignKey("captures.id"))
    provider: Mapped[str] = mapped_column(String(40))
    model_rev: Mapped[str] = mapped_column(String(200))
    prompt_version: Mapped[str] = mapped_column(String(40))
    degraded: Mapped[bool] = mapped_column(Boolean)
    reason: Mapped[str | None] = mapped_column(String(40))
    attempts: Mapped[int] = mapped_column(Integer)
    suggested: Mapped[int] = mapped_column(Integer)
    discarded: Mapped[int] = mapped_column(Integer)
    suggested_pathways: Mapped[list[str]] = mapped_column(JSON)
    unparsed_concerns: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Consent(Base):
    """Per-visit consent: record_audio, store_record, share_handoff. Append-only history."""

    __tablename__ = "consents"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    person_id: Mapped[str] = mapped_column(ForeignKey("persons.id"))
    encounter_id: Mapped[str | None] = mapped_column(ForeignKey("encounters.id"))
    kind: Mapped[str] = mapped_column(String(20))
    granted: Mapped[bool] = mapped_column(Boolean)
    recorded_by: Mapped[str] = mapped_column(String(32))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ReferralPlanRow(Base):
    __tablename__ = "referral_plans"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id"))
    triage_id: Mapped[str] = mapped_column(ForeignKey("triage_results.id"))
    facility_level: Mapped[str | None] = mapped_column(String(20))
    facility_names: Mapped[list[str]] = mapped_column(JSON)
    target_window: Mapped[str | None] = mapped_column(String(30))
    bring_list: Mapped[list[str]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class OutputRow(Base):
    __tablename__ = "outputs"
    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=new_id)
    encounter_id: Mapped[str] = mapped_column(ForeignKey("encounters.id"))
    triage_id: Mapped[str] = mapped_column(ForeignKey("triage_results.id"))
    kind: Mapped[str] = mapped_column(String(30))  # clinician_handoff | family_instructions
    language: Mapped[str] = mapped_column(String(5))
    body: Mapped[str] = mapped_column(Text)
    template_body: Mapped[str] = mapped_column(Text)
    generated_by: Mapped[str] = mapped_column(String(20))  # template | llm
    writer: Mapped[str | None] = mapped_column(String(200))
    check_failures: Mapped[list[str]] = mapped_column(JSON)
    edited_by_worker: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
