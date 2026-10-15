"""院内服务增量模型；不修改已有健康业务表。"""
from sqlalchemy import ForeignKey, Integer, String, Text, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
from app.models import ID, Times


class ServiceCatalog(Times, Base):
    __tablename__ = 'care_service_catalog'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(500))
    enabled: Mapped[int] = mapped_column(Integer, default=1)


class ServiceRequest(Times, Base):
    __tablename__ = 'care_service_request'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'))
    creator_id: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    category: Mapped[str] = mapped_column(String(30))
    title: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str] = mapped_column(String(150))
    requested_at: Mapped[object | None] = mapped_column(DateTime)
    priority: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default='SUBMITTED')
    assigned_to: Mapped[int | None] = mapped_column(ID, ForeignKey('user.id'))
    accepted_at: Mapped[object | None] = mapped_column(DateTime)
    completed_at: Mapped[object | None] = mapped_column(DateTime)
    escalated_at: Mapped[object | None] = mapped_column(DateTime)
    result: Mapped[str | None] = mapped_column(Text)
    active_call_key: Mapped[str | None] = mapped_column(String(30), unique=True)
    equipment_id: Mapped[int | None] = mapped_column(ID, ForeignKey('care_equipment.id'))
    quantity: Mapped[int | None] = mapped_column(Integer)


class ServiceEvent(Times, Base):
    __tablename__ = 'care_service_event'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ID, ForeignKey('care_service_request.id'))
    actor_id: Mapped[int | None] = mapped_column(ID, ForeignKey('user.id'))
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(Text)


class Activity(Times, Base):
    __tablename__ = 'care_activity'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(30))
    start_at: Mapped[object] = mapped_column(DateTime)
    end_at: Mapped[object] = mapped_column(DateTime)
    location: Mapped[str] = mapped_column(String(150))
    capacity: Mapped[int] = mapped_column(Integer)
    reserved_count: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default='PUBLISHED')
    creator_id: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))


class ActivityRegistration(Times, Base):
    __tablename__ = 'care_activity_registration'
    __table_args__ = (UniqueConstraint('activity_id', 'profile_id'),)
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    activity_id: Mapped[int] = mapped_column(ID, ForeignKey('care_activity.id'))
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'))
    creator_id: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    status: Mapped[str] = mapped_column(String(20), default='REGISTERED')
    recorded_by: Mapped[int | None] = mapped_column(ID, ForeignKey('user.id'))


class Equipment(Times, Base):
    __tablename__ = 'care_equipment'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100))
    total: Mapped[int] = mapped_column(Integer)
    available: Mapped[int] = mapped_column(Integer)
    damaged: Mapped[int] = mapped_column(Integer, default=0)
    description: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[int] = mapped_column(Integer, default=1)


class EquipmentLoan(Times, Base):
    __tablename__ = 'care_equipment_loan'
    __table_args__ = (UniqueConstraint('request_id'),)
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    request_id: Mapped[int] = mapped_column(ID, ForeignKey('care_service_request.id'))
    equipment_id: Mapped[int] = mapped_column(ID, ForeignKey('care_equipment.id'))
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'))
    quantity: Mapped[int] = mapped_column(Integer)
    issued_by: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    status: Mapped[str] = mapped_column(String(20), default='BORROWED')
    returned_at: Mapped[object | None] = mapped_column(DateTime)
    returned_by: Mapped[int | None] = mapped_column(ID, ForeignKey('user.id'))
    return_note: Mapped[str | None] = mapped_column(Text)


class ServiceNotification(Times, Base):
    __tablename__ = 'care_service_notification'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    recipient_id: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'))
    ref_type: Mapped[str] = mapped_column(String(30))
    ref_id: Mapped[int] = mapped_column(ID)
    title: Mapped[str] = mapped_column(String(100))
    content: Mapped[str | None] = mapped_column(Text)
    read_status: Mapped[str] = mapped_column(String(10), default='UNREAD')
    read_at: Mapped[object | None] = mapped_column(DateTime)


SERVICE_TABLES = [ServiceCatalog.__table__, Equipment.__table__, Activity.__table__,
                  ServiceRequest.__table__, ServiceEvent.__table__, ActivityRegistration.__table__,
                  EquipmentLoan.__table__, ServiceNotification.__table__]
