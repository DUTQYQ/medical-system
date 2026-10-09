"""SQLAlchemy 2 models, matching the existing 15-table schema exactly."""
from sqlalchemy import BigInteger, Integer, String, Text, Numeric, Date, DateTime, JSON, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base, now

ID = BigInteger().with_variant(Integer, 'sqlite')


class Times:
    create_time: Mapped[object] = mapped_column(DateTime, default=now)
    update_time: Mapped[object] = mapped_column(DateTime, default=now, onupdate=now)


class User(Times, Base):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    password_hash: Mapped[str] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(50))
    role: Mapped[str] = mapped_column(String(10))
    status: Mapped[int] = mapped_column(Integer, default=1)
    avatar: Mapped[str | None] = mapped_column(String(255))
    last_login_time: Mapped[object | None] = mapped_column(DateTime)


class ElderProfile(Times, Base):
    __tablename__ = 'elder_profile'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    name: Mapped[str] = mapped_column(String(50))
    gender: Mapped[str | None] = mapped_column(String(1))
    birthday: Mapped[object | None] = mapped_column(Date)
    height: Mapped[object | None] = mapped_column(Numeric(5, 1))
    weight: Mapped[object | None] = mapped_column(Numeric(5, 1))
    blood_type: Mapped[str | None] = mapped_column(String(5))
    allergy: Mapped[str | None] = mapped_column(String(255))
    medical_history: Mapped[str | None] = mapped_column(String(500))
    chronic_tags: Mapped[str | None] = mapped_column(String(255))
    emergency_contact: Mapped[str | None] = mapped_column(String(50))
    emergency_phone: Mapped[str | None] = mapped_column(String(20))
    deleted: Mapped[int] = mapped_column(Integer, default=0)


class FamilyBind(Times, Base):
    __tablename__ = 'family_bind'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    family_user_id: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'))
    relation: Mapped[str | None] = mapped_column(String(20))
    note: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(10), default='PENDING')
    approved_by: Mapped[int | None] = mapped_column(ID)
    approve_note: Mapped[str | None] = mapped_column(String(255))
    approve_time: Mapped[object | None] = mapped_column(DateTime)


class CareRelation(Times, Base):
    __tablename__ = 'care_relation'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    care_user_id: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'))
    status: Mapped[int] = mapped_column(Integer, default=1)


class HealthRecord(Times, Base):
    __tablename__ = 'health_record'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'))
    type: Mapped[str] = mapped_column(String(20))
    val1: Mapped[object | None] = mapped_column(Numeric(10, 2))
    val2: Mapped[object | None] = mapped_column(Numeric(10, 2))
    measured_at: Mapped[object] = mapped_column(DateTime)
    is_abnormal: Mapped[int] = mapped_column(Integer, default=0)
    remark: Mapped[str | None] = mapped_column(String(255))
    recorder_id: Mapped[int | None] = mapped_column(ID, ForeignKey('user.id'))


class HealthWarning(Times, Base):
    __tablename__ = 'health_warning'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'))
    record_id: Mapped[int | None] = mapped_column(ID, ForeignKey('health_record.id', ondelete='SET NULL'))
    type: Mapped[str] = mapped_column(String(20))
    value_text: Mapped[str | None] = mapped_column(String(50))
    level: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(15), default='PENDING')
    trigger_source: Mapped[str | None] = mapped_column(String(20))
    ai_summary: Mapped[str | None] = mapped_column(Text)
    summary_status: Mapped[str] = mapped_column(String(10), default='PENDING')


class AlertReceiver(Times, Base):
    __tablename__ = 'alert_receiver'
    __table_args__ = (UniqueConstraint('warning_id', 'user_id'),)
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    warning_id: Mapped[int] = mapped_column(ID, ForeignKey('health_warning.id'))
    user_id: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    read_status: Mapped[str] = mapped_column(String(10), default='UNREAD')
    read_time: Mapped[object | None] = mapped_column(DateTime)


class WarningHandleRecord(Times, Base):
    __tablename__ = 'warning_handle_record'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    warning_id: Mapped[int] = mapped_column(ID, ForeignKey('health_warning.id'))
    handler_id: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    action: Mapped[str] = mapped_column(String(20))
    result: Mapped[str | None] = mapped_column(String(500))


class ChatSession(Times, Base):
    __tablename__ = 'chat_session'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ID, ForeignKey('user.id'))
    profile_id: Mapped[int | None] = mapped_column(ID, ForeignKey('elder_profile.id'))
    title: Mapped[str | None] = mapped_column(String(100))


class ChatMessage(Times, Base):
    __tablename__ = 'chat_message'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ID, ForeignKey('chat_session.id'))
    role: Mapped[str] = mapped_column(String(10))
    content: Mapped[str] = mapped_column(Text)
    intent: Mapped[str | None] = mapped_column(String(20))
    agent: Mapped[str | None] = mapped_column(String(20))
    safety_level: Mapped[str | None] = mapped_column(String(5))
    sources: Mapped[str | None] = mapped_column(Text)
    warning_id: Mapped[int | None] = mapped_column(ID)


class SysConfig(Times, Base):
    __tablename__ = 'sys_config'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(String(50), unique=True)
    config_value: Mapped[str] = mapped_column(String(500))
    config_type: Mapped[str | None] = mapped_column(String(20))
    group_name: Mapped[str | None] = mapped_column(String(50))
    description: Mapped[str | None] = mapped_column(String(255))
    enabled: Mapped[int] = mapped_column(Integer, default=1)


class Medication(Times, Base):
    __tablename__ = 'medication'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    profile_id: Mapped[int] = mapped_column(ID, ForeignKey('elder_profile.id'))
    drug_name: Mapped[str] = mapped_column(String(100))
    dosage: Mapped[str | None] = mapped_column(String(50))
    take_time: Mapped[str | None] = mapped_column(String(100))
    remark: Mapped[str | None] = mapped_column(String(255))


class KnowledgeDocument(Times, Base):
    __tablename__ = 'knowledge_document'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200))
    category: Mapped[str | None] = mapped_column(String(50))
    content: Mapped[str | None] = mapped_column(Text)
    enabled: Mapped[int] = mapped_column(Integer, default=1)


class KnowledgeChunk(Times, Base):
    __tablename__ = 'knowledge_chunk'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(ID, ForeignKey('knowledge_document.id'))
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    chunk_text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[object | None] = mapped_column(JSON)


class AILog(Base):
    __tablename__ = 'ai_log'
    id: Mapped[int] = mapped_column(ID, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ID)
    agent: Mapped[str | None] = mapped_column(String(20))
    model: Mapped[str | None] = mapped_column(String(50))
    prompt_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    success: Mapped[int] = mapped_column(Integer, default=1)
    error_msg: Mapped[str | None] = mapped_column(String(500))
    create_time: Mapped[object] = mapped_column(DateTime, default=now)


AiLog = AILog
