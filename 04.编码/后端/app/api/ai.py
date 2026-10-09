import json
from datetime import timedelta
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session
from app.core.database import get_db, now
from app.core.errors import APIError, ok
from app.core.permissions import get_profile, visible_profile_ids, require_roles
from app.core.security import get_current_user
from app.models import User, ChatSession, ChatMessage, AILog
from app.agent.workflow import run_chat, classify, number_config

router = APIRouter(prefix='/ai', tags=['AI咨询'])


class ChatRequest(BaseModel):
    profile_id: int = Field(gt=0)
    session_id: int | None = Field(default=None, gt=0)
    question: str = Field(min_length=1, max_length=2000)

    @field_validator('question')
    @classmethod
    def nonempty(cls, value):
        value = value.strip()
        if not value:
            raise ValueError('问题不能为空')
        return value


def session_access(db, user, session_id, *, write=False):
    session = db.get(ChatSession, session_id)
    if session is None:
        raise APIError(2002, '会话不存在', 404)
    if session.profile_id is None:
        raise APIError(1002, '会话不属于可访问的健康档案', 403)
    get_profile(db, user, session.profile_id)
    if write and session.user_id != user.id and user.role != 'ADMIN':
        raise APIError(1002, '只能修改本人发起的会话', 403)
    return session


@router.post('/chat')
def chat(payload: ChatRequest, db: Session = Depends(get_db), user: User = Depends(require_roles('ELDER', 'FAMILY'))):
    profile = get_profile(db, user, payload.profile_id)
    if len(payload.question) > number_config(db, 'ai_question_max_chars', 2000, maximum=2000):
        raise APIError(2001, '问题超过系统配置的字数上限')
    session = None
    if payload.session_id:
        session = session_access(db, user, payload.session_id, write=True)
        if session.profile_id != profile.id:
            raise APIError(2001, '会话与当前老人档案不一致，请新建会话')
    intent = classify(db, payload.question)
    daily_limit = number_config(db, 'ai_daily_limit', 50)
    today = now().replace(hour=0, minute=0, second=0, microsecond=0)
    # Reservation rows survive conversation deletion, preventing allowance bypass.
    db.scalar(select(User).where(User.id == user.id).with_for_update())
    count = db.scalar(select(func.count(AILog.id)).where(AILog.user_id == user.id,
                      AILog.agent == 'CONSULT_ATTEMPT', AILog.create_time >= today))
    # Safety alerts must still be created after the consultation allowance runs out.
    if intent != 'EMERGENCY' and count >= daily_limit:
        raise APIError(3002, '今日咨询次数已达上限', 429)
    if session is None:
        session = ChatSession(user_id=user.id, profile_id=profile.id, title=payload.question[:100])
        db.add(session)
        db.flush()
    # Persist the attempt so failures do not bypass per-day cost control.
    question_message = ChatMessage(session_id=session.id, role='user', content=payload.question)
    db.add(question_message)
    if intent != 'EMERGENCY':
        db.add(AILog(user_id=user.id, agent='CONSULT_ATTEMPT', model='quota', success=0))
    db.commit()
    result = run_chat(db, user, profile, payload.question)
    message = ChatMessage(session_id=session.id, role='assistant', content=result['answer'], intent=result['intent'],
                          agent=result['agent'], safety_level=result['safety_level'], sources=json.dumps(result['sources'], ensure_ascii=False), warning_id=result['warning_id'])
    session.update_time = now()
    db.add(message)
    db.commit()
    data = {key: result[key] for key in ('answer', 'intent', 'agent', 'safety_level', 'risk_level', 'sources', 'warning_id', 'disclaimer', 'model_status')}
    data.update(session_id=session.id, message_id=message.id)
    if 'retrieval' in result:
        data['retrieval'] = result['retrieval']
    return ok(data)


@router.get('/sessions')
def sessions(profile_id: int | None = Query(default=None, gt=0), db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if profile_id:
        get_profile(db, user, profile_id)
        ids = [profile_id]
    else:
        ids = visible_profile_ids(db, user)
    rows = db.scalars(select(ChatSession).where(ChatSession.profile_id.in_(ids)).order_by(ChatSession.update_time.desc()))
    return ok([{'session_id': row.id, 'profile_id': row.profile_id, 'title': row.title, 'created_at': row.create_time.strftime('%Y-%m-%d %H:%M:%S'),
                'updated_at': row.update_time.strftime('%Y-%m-%d %H:%M:%S'), 'can_delete': row.user_id == user.id or user.role == 'ADMIN'} for row in rows])


@router.get('/sessions/{session_id}/messages')
def messages(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session_access(db, user, session_id)
    rows = db.scalars(select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.create_time, ChatMessage.id))
    return ok([{'message_id': row.id, 'role': row.role, 'content': row.content, 'intent': row.intent, 'agent': row.agent,
                'safety_level': row.safety_level, 'sources': json.loads(row.sources or '[]'), 'warning_id': row.warning_id,
                'created_at': row.create_time.strftime('%Y-%m-%d %H:%M:%S')} for row in rows])


@router.delete('/sessions/{session_id}')
def delete_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = session_access(db, user, session_id, write=True)
    db.execute(delete(ChatMessage).where(ChatMessage.session_id == session_id))
    db.delete(session)
    db.commit()
    return ok()
