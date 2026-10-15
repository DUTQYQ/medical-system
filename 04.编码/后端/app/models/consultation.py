"""Incremental consultation tables; imports register models without migrating a DB."""
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, now
from app.models import ID, Times


class ConsultationIntake(Times, Base):
    __tablename__ = 'consultation_intake'
    __table_args__ = (UniqueConstraint('profile_id', 'template_version', name='uq_intake_profile_template'),)
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'))
    template_version: Mapped[str] = mapped_column(String(20), default='life-v1')
    status: Mapped[str] = mapped_column(String(20), default='IN_PROGRESS')
    answers: Mapped[object] = mapped_column(JSON, default=list)
    created_by: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    confirmed_by: Mapped[int | None] = mapped_column(ID, ForeignKey('user.id'))
    confirmed_at: Mapped[object | None] = mapped_column(DateTime)


class ProfileFact(Times, Base):
    __tablename__ = 'profile_fact'
    __table_args__ = (UniqueConstraint('profile_id', 'fact_key', name='uq_fact_profile_key'),)
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'))
    fact_key: Mapped[str] = mapped_column(String(50))
    label: Mapped[str] = mapped_column(String(100))
    value: Mapped[object] = mapped_column(JSON)
    version: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default='CONFIRMED')
    source_intake_id: Mapped[int | None] = mapped_column(ID, ForeignKey('consultation_intake.id'))
    reported_by: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    confirmed_by: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    confirmed_at: Mapped[object] = mapped_column(DateTime, default=now)
    valid_until: Mapped[object | None] = mapped_column(DateTime)


class ProfileFactRevision(Base):
    __tablename__ = 'profile_fact_revision'
    __table_args__ = (UniqueConstraint('fact_id', 'version', name='uq_fact_revision_version'),)
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    fact_id: Mapped[int] = mapped_column(ID, ForeignKey('profile_fact.id'))
    version: Mapped[int] = mapped_column(Integer)
    value: Mapped[object] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20))
    changed_by: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    change_reason: Mapped[str] = mapped_column(String(100))
    source_intake_id: Mapped[int | None] = mapped_column(ID, ForeignKey('consultation_intake.id'))
    reported_by: Mapped[int | None] = mapped_column(ID, ForeignKey('user.id'))
    valid_until: Mapped[object | None] = mapped_column(DateTime)
    create_time: Mapped[object] = mapped_column(DateTime, default=now)


class AdviceCard(Times, Base):
    __tablename__ = 'advice_card'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'))
    created_by: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    title: Mapped[str] = mapped_column(String(100))
    mode: Mapped[str] = mapped_column(String(10))
    content: Mapped[object] = mapped_column(JSON)
