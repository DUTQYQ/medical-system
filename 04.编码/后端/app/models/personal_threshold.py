"""Additive individual rules and immutable measurement assessment evidence."""
from sqlalchemy import ForeignKey, String, Text, Integer, DateTime, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models import ID, Times


class ProfileThresholdVersion(Times, Base):
    __tablename__ = 'profile_threshold_version'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'), index=True)
    indicator: Mapped[str] = mapped_column(String(30), index=True)
    config_id: Mapped[int | None] = mapped_column(ID, ForeignKey('sys_config.id'))
    restore_default: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default='PENDING', index=True)
    reason: Mapped[str] = mapped_column(String(500))
    proposed_by: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    reviewed_by: Mapped[int | None] = mapped_column(ID, ForeignKey('user.id'))
    review_note: Mapped[str | None] = mapped_column(String(500))
    reviewed_at: Mapped[object | None] = mapped_column(DateTime)


class HealthAssessment(Times, Base):
    __tablename__ = 'health_assessment'
    __table_args__ = (UniqueConstraint('record_id'), UniqueConstraint('warning_id'))
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'), index=True)
    record_id: Mapped[int | None] = mapped_column(ID, ForeignKey('health_record.id', ondelete='SET NULL'))
    warning_id: Mapped[int | None] = mapped_column(ID, ForeignKey('health_warning.id', ondelete='SET NULL'))
    risk_level: Mapped[int] = mapped_column(Integer)
    thresholds: Mapped[dict] = mapped_column(JSON)
    values: Mapped[dict] = mapped_column(JSON)
