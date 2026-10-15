"""Onboarding interview and personal facts, independent of model availability."""
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.core.database import get_db, now
from app.core.errors import APIError, ok
from app.core.permissions import get_profile, require_roles
from app.models import ChatMessage
from app.api.ai import session_access
from app.models.consultation import ConsultationIntake, ProfileFact, ProfileFactRevision, AdviceCard
from app.services.intake import TEMPLATE_VERSION, QUESTIONS, QUESTION_MAP, FACT_LABELS, clean_value, check_key, intake_data, fact_data, facts_for, save_fact, build_advice, advice_data

router = APIRouter(prefix='/ai', tags=['康养问询与个人词条'])
resident_or_family = require_roles('ELDER', 'FAMILY')
profile_reader = require_roles('ELDER', 'FAMILY', 'CARE')
advice_user = require_roles('ELDER', 'FAMILY', 'CARE')


class ProfileRequest(BaseModel):
    profile_id: int = Field(gt=0)


class AnswerRequest(BaseModel):
    key: str = Field(min_length=1, max_length=50)
    value: str | list[str] | None = None
    skip: bool = False


class EntryRequest(BaseModel):
    key: str = Field(min_length=1, max_length=50)
    value: str | list[str]


class ConfirmRequest(BaseModel):
    entries: list[EntryRequest] = Field(max_length=6)


class FactRequest(BaseModel):
    value: str | list[str]


class FactCreateRequest(ProfileRequest):
    model_config = ConfigDict(extra='forbid')
    key: str = Field(min_length=1, max_length=50)
    value: str | list[str]
    source_message_id: int | None = Field(default=None, gt=0)


def accessible_intake(db, user, intake_id):
    row = db.get(ConsultationIntake, intake_id)
    if row is None:
        raise APIError(2002, '问询不存在', 404)
    get_profile(db, user, row.profile_id, lock=True)
    return db.scalar(select(ConsultationIntake).where(ConsultationIntake.id == intake_id)
                     .with_for_update().execution_options(populate_existing=True))


@router.post('/intake/start')
def start(body: ProfileRequest, db: Session = Depends(get_db), user=Depends(resident_or_family)):
    get_profile(db, user, body.profile_id, lock=True)
    row = db.scalar(select(ConsultationIntake).where(ConsultationIntake.profile_id == body.profile_id,
                    ConsultationIntake.template_version == TEMPLATE_VERSION).with_for_update().execution_options(populate_existing=True))
    if row is None:
        row = ConsultationIntake(profile_id=body.profile_id, template_version=TEMPLATE_VERSION, created_by=user.id, answers=[])
        db.add(row)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            get_profile(db, user, body.profile_id)
            row = db.scalar(select(ConsultationIntake).where(ConsultationIntake.profile_id == body.profile_id,
                            ConsultationIntake.template_version == TEMPLATE_VERSION))
            if row is None:
                raise
    return ok(intake_data(row))


@router.post('/intake/{intake_id}/answer')
def answer(intake_id: int, body: AnswerRequest, db: Session = Depends(get_db), user=Depends(resident_or_family)):
    row = accessible_intake(db, user, intake_id)
    if row.status == 'CONFIRMED':
        raise APIError(2001, '问询已经确认，请在个人词条中修改', 409)
    key = check_key(body.key)
    answers = list(row.answers or [])
    current = intake_data(row)['next_question']
    if key not in {a['key'] for a in answers} and (current is None or current['key'] != key):
        raise APIError(2001, '请按顺序回答当前问题，或修改已回答的问题')
    value = None if body.skip else clean_value(body.value)
    entry = {'key': key, 'label': FACT_LABELS[key], 'value': value, 'skipped': body.skip,
             'reported_by': user.id, 'answered_at': now().isoformat(timespec='seconds')}
    answers = [a for a in answers if a['key'] != key] + [entry]
    row.answers = sorted(answers, key=lambda a: list(QUESTION_MAP).index(a['key']))
    row.status = 'READY_TO_CONFIRM' if len(answers) == len(QUESTIONS) else 'IN_PROGRESS'
    db.commit()
    return ok(intake_data(row))


@router.post('/intake/{intake_id}/confirm')
def confirm(intake_id: int, body: ConfirmRequest, db: Session = Depends(get_db), user=Depends(resident_or_family)):
    row = accessible_intake(db, user, intake_id)
    values = {check_key(e.key): clean_value(e.value) for e in body.entries}
    if len(values) != len(body.entries):
        raise APIError(2001, '确认词条不能重复')
    valid = {a['key']: a for a in row.answers or [] if not a['skipped']}
    if set(values) != set(valid):
        raise APIError(2001, '请确认全部非跳过词条；需移除内容时先将该问题标为跳过')
    if row.status == 'CONFIRMED':
        previous = {a['key']: a['value'] for a in row.answers or [] if not a['skipped']}
        if previous != values:
            raise APIError(2001, '确认已经完成，请在词条中修改', 409)
        return ok([fact_data(f, db) for f in facts_for(db, row.profile_id)])
    if row.status != 'READY_TO_CONFIRM':
        raise APIError(2001, '请先完成或跳过全部问题')
    for key, value in values.items():
        save_fact(db, row.profile_id, key, value, user, source_intake_id=row.id, reported_by=valid[key]['reported_by'])
    row.answers = [{**a, 'value': values.get(a['key'])} for a in row.answers]
    row.status, row.confirmed_by, row.confirmed_at = 'CONFIRMED', user.id, now()
    db.commit()
    return ok([fact_data(f, db) for f in facts_for(db, row.profile_id)])


@router.get('/facts')
def facts(profile_id: int = Query(gt=0), db: Session = Depends(get_db), user=Depends(profile_reader)):
    get_profile(db, user, profile_id)
    return ok([fact_data(f, db) for f in facts_for(db, profile_id)])


@router.post('/facts')
def create_fact(body: FactCreateRequest, db: Session = Depends(get_db), user=Depends(resident_or_family)):
    get_profile(db, user, body.profile_id, lock=True)
    check_key(body.key)
    reason, reported_by = '用户添加并确认个人词条', user.id
    if body.source_message_id is not None:
        message = db.scalar(select(ChatMessage).where(ChatMessage.id == body.source_message_id)
                            .with_for_update().execution_options(populate_existing=True))
        if message is None:
            raise APIError(2002, '引用的会话消息不存在', 404)
        session = session_access(db, user, message.session_id)
        if session.profile_id != body.profile_id:
            raise APIError(2001, '引用的消息须属于当前老人档案')
        if message.role not in ('user', 'assistant'):
            raise APIError(2001, '只能引用咨询问答消息')
        if message.role == 'user':
            reported_by = session.user_id
        reason = f'用户确认会话信息 message#{message.id}'
    row = save_fact(db, body.profile_id, body.key, body.value, user, reported_by=reported_by, change_reason=reason)
    db.commit()
    return ok(fact_data(row, db))


@router.put('/facts/{fact_id}')
def update_fact(fact_id: int, body: FactRequest, db: Session = Depends(get_db), user=Depends(resident_or_family)):
    row = db.get(ProfileFact, fact_id)
    if row is None:
        raise APIError(2002, '词条不存在', 404)
    get_profile(db, user, row.profile_id, lock=True)
    row = db.scalar(select(ProfileFact).where(ProfileFact.id == fact_id).with_for_update()
                    .execution_options(populate_existing=True))
    row = save_fact(db, row.profile_id, row.fact_key, body.value, user)
    db.commit()
    return ok(fact_data(row, db))


@router.delete('/facts/{fact_id}')
def revoke_fact(fact_id: int, db: Session = Depends(get_db), user=Depends(resident_or_family)):
    row = db.get(ProfileFact, fact_id)
    if row is None:
        raise APIError(2002, '词条不存在', 404)
    get_profile(db, user, row.profile_id, lock=True)
    row = db.scalar(select(ProfileFact).where(ProfileFact.id == fact_id).with_for_update()
                    .execution_options(populate_existing=True))
    if row.status != 'REVOKED':
        row.status = 'REVOKED'
        row.version += 1
        db.add(ProfileFactRevision(fact_id=row.id, version=row.version, value=row.value, status='REVOKED',
                                  changed_by=user.id, source_intake_id=row.source_intake_id,
                                  reported_by=row.reported_by, valid_until=row.valid_until, change_reason='用户撤销词条'))
        db.commit()
    return ok()


@router.post('/advice')
def create_advice(body: ProfileRequest, db: Session = Depends(get_db), user=Depends(advice_user)):
    profile = get_profile(db, user, body.profile_id)
    return ok(advice_data(build_advice(db, profile, user)))


@router.get('/advice')
def advice(profile_id: int = Query(gt=0), db: Session = Depends(get_db), user=Depends(advice_user)):
    get_profile(db, user, profile_id)
    rows = db.scalars(select(AdviceCard).where(AdviceCard.profile_id == profile_id,
        AdviceCard.created_by == user.id).order_by(AdviceCard.id.desc()).limit(30))
    return ok([advice_data(row) for row in rows])
