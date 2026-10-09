import json
import uuid
from datetime import timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session
from app.core.database import get_db, now
from app.core.permissions import require_roles
from app.core.security import hash_password, set_config
from app.core.errors import APIError, ok
from app.models import User, ElderProfile, HealthRecord, HealthWarning, ChatSession, ChatMessage, SysConfig, KnowledgeDocument, KnowledgeChunk, CareRelation, FamilyBind, WarningHandleRecord
from app.services.serializers import user_data, dt
from app.services.thresholds import INDICATORS, indicator, threshold_data, parse_threshold
from .schemas import Register, EnabledInput, RoleInput, ThresholdInput, KnowledgeInput, AssignmentInput, IndicatorInput

router = APIRouter(prefix='/admin', tags=['管理员'], dependencies=[Depends(require_roles('ADMIN'))])
config_router = APIRouter(prefix='/config', tags=['系统配置'], dependencies=[Depends(require_roles('ELDER', 'FAMILY', 'CARE', 'ADMIN'))])


@router.get('/users')
def users(role: str | None = None, keyword: str = '', page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), db: Session = Depends(get_db)):
    criteria = []
    if role:
        if role not in ('ELDER', 'FAMILY', 'CARE', 'ADMIN'):
            raise APIError(2001, '用户角色无效')
        criteria.append(User.role == role)
    if keyword:
        escaped = keyword.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        criteria.append(User.name.like('%' + escaped + '%', escape='\\') | User.phone.like('%' + escaped + '%', escape='\\'))
    total = db.scalar(select(func.count()).select_from(User).where(*criteria))
    rows = db.scalars(select(User).where(*criteria).order_by(User.id).offset((page - 1) * page_size).limit(page_size))
    return ok({'list': [user_data(row) for row in rows], 'total': total, 'page': page, 'page_size': page_size})


@router.post('/users')
def create_user(body: Register, db: Session = Depends(get_db)):
    if body.role not in ('CARE', 'ADMIN'):
        raise APIError(2001, '管理员建号只允许 CARE 与 ADMIN')
    if db.scalar(select(User.id).where(User.phone == body.phone)):
        raise APIError(2001, '手机号已注册', 409)
    user = User(phone=body.phone, password_hash=hash_password(body.password), name=body.name, role=body.role)
    db.add(user)
    db.commit()
    return ok(user_data(user))


def target_user(db, user_id):
    user = db.scalar(select(User).where(User.id == user_id).with_for_update())
    if not user:
        raise APIError(2002, '用户不存在', 404)
    return user


def preserve_admin(db, target, current):
    if target.id == current.id:
        raise APIError(2001, '不能禁用本人或移除本人的管理员权限')
    if target.role == 'ADMIN' and target.status:
        admins = list(db.scalars(select(User).where(User.role == 'ADMIN', User.status == 1).with_for_update()))
        if len(admins) <= 1:
            raise APIError(2001, '至少保留一个启用的管理员')


@router.put('/users/{user_id}/status')
def change_status(user_id: int, body: EnabledInput, current=Depends(require_roles('ADMIN')), db: Session = Depends(get_db)):
    user = target_user(db, user_id)
    if not body.enabled:
        preserve_admin(db, user, current)
    user.status = int(body.enabled)
    # Rotate even on re-enable; old tokens never regain validity.
    set_config(db, f'auth_epoch:{user.id}', uuid.uuid4().hex)
    db.commit()
    return ok(user_data(user))


@router.put('/users/{user_id}/role')
def change_role(user_id: int, body: RoleInput, current=Depends(require_roles('ADMIN')), db: Session = Depends(get_db)):
    user = target_user(db, user_id)
    if user.role not in ('CARE', 'ADMIN'):
        raise APIError(2001, '仅护工与管理员角色可互换，老人及家属身份不能更换')
    if user.role == 'ADMIN' and body.role != 'ADMIN':
        preserve_admin(db, user, current)
    user.role = body.role
    set_config(db, f'auth_epoch:{user.id}', uuid.uuid4().hex)
    db.commit()
    return ok(user_data(user))


@router.get('/thresholds')
def thresholds(db: Session = Depends(get_db)):
    return ok([threshold_data(row) for row in db.scalars(select(SysConfig).where(SysConfig.group_name == 'threshold').order_by(SysConfig.id))])


@router.put('/thresholds/{config_id}')
def update_threshold(config_id: int, body: ThresholdInput, db: Session = Depends(get_db)):
    row = db.scalar(select(SysConfig).where(SysConfig.id == config_id, SysConfig.group_name == 'threshold').with_for_update())
    if not row:
        raise APIError(2002, '阈值不存在', 404)
    value = json.dumps({f'level{i}': getattr(body, f'level{i}_range') for i in range(4)}, ensure_ascii=False)
    try:
        parse_threshold(value)
    except (ValueError, TypeError):
        raise APIError(2001, '阈值表达式无效，支持 90~139、>=180、<40 或 >130')
    if len(value) > 500:
        raise APIError(2001, '阈值配置超过 500 字符')
    row.config_value, row.enabled = value, int(body.enabled)
    db.commit()
    return ok(threshold_data(row))


@router.get('/indicators')
def indicators(db: Session = Depends(get_db)):
    return ok([indicator(db, type) for type in INDICATORS])


@router.put('/indicators/{type}')
def update_indicator(type: str, body: IndicatorInput, db: Session = Depends(get_db)):
    if type not in INDICATORS:
        raise APIError(2001, '不支持的指标类型')
    for field, bounds in body.ranges.items():
        if field not in INDICATORS[type]['fields'] or bounds[0] > bounds[1]:
            raise APIError(2001, '录入范围字段或上下限无效')
    value = json.dumps(body.model_dump(), ensure_ascii=False, allow_nan=False)
    if len(value) > 500:
        raise APIError(2001, '指标配置超过 500 字符')
    set_config(db, 'indicator:' + type, value, 'indicator')
    db.commit()
    return ok(indicator(db, type))


def knowledge_data(row):
    return {'document_id': row.id, 'id': row.id, 'title': row.title, 'category': row.category, 'content': row.content,
            'enabled': bool(row.enabled), 'created_at': dt(row.create_time), 'updated_at': dt(row.update_time)}


def index(db):
    from app.agent.rag import rebuild_index
    return rebuild_index(db)


@router.get('/knowledge')
def knowledge(db: Session = Depends(get_db)):
    return ok([knowledge_data(row) for row in db.scalars(select(KnowledgeDocument).order_by(KnowledgeDocument.id.desc()))])


@router.post('/knowledge/reindex')
def reindex(db: Session = Depends(get_db)):
    result = index(db)
    db.commit()
    return ok(result)


@router.post('/knowledge')
def create_knowledge(body: KnowledgeInput, db: Session = Depends(get_db)):
    row = KnowledgeDocument(title=body.title, category=body.category, content=body.content, enabled=int(body.enabled))
    db.add(row)
    db.flush()
    index(db)
    db.commit()
    return ok(knowledge_data(row))


@router.put('/knowledge/{document_id}')
def update_knowledge(document_id: int, body: KnowledgeInput, db: Session = Depends(get_db)):
    row = db.get(KnowledgeDocument, document_id)
    if not row:
        raise APIError(2002, '知识条目不存在', 404)
    for name, value in body.model_dump().items():
        setattr(row, name, int(value) if name == 'enabled' else value)
    db.flush()
    index(db)
    db.commit()
    return ok(knowledge_data(row))


@router.delete('/knowledge/{document_id}')
def delete_knowledge(document_id: int, db: Session = Depends(get_db)):
    row = db.get(KnowledgeDocument, document_id)
    if not row:
        raise APIError(2002, '知识条目不存在', 404)
    db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.doc_id == document_id))
    db.delete(row)
    db.flush()
    index(db)
    db.commit()
    return ok()


@router.get('/statistics')
def statistics(range: str = Query('7d', pattern=r'^(1d|7d|30d|90d|day|week|month)$'), db: Session = Depends(get_db)):
    days = {'1d': 1, '7d': 7, '30d': 30, '90d': 90, 'day': 1, 'week': 7, 'month': 30}[range]
    end = now()
    start = end - timedelta(days=days)
    users_total = db.scalar(select(func.count()).select_from(User))
    active = db.scalar(select(func.count()).select_from(User).where(User.last_login_time >= start, User.last_login_time <= end))
    consults = list(db.scalars(select(ChatMessage).where(ChatMessage.role == 'user', ChatMessage.create_time >= start, ChatMessage.create_time <= end)))
    warnings = list(db.scalars(select(HealthWarning).where(HealthWarning.create_time >= start, HealthWarning.create_time <= end)))
    users = list(db.scalars(select(User).where(User.create_time >= start, User.create_time <= end)))
    handles = db.scalar(select(func.count()).select_from(WarningHandleRecord).where(WarningHandleRecord.create_time >= start, WarningHandleRecord.create_time <= end))
    dates = [(start + timedelta(days=i)).strftime('%Y-%m-%d') for i in builtins_range(days + 1)]
    totals = {name: db.scalar(select(func.count()).select_from(model)) for name, model in (
        ('users', User), ('health_records', HealthRecord), ('chat_sessions', ChatSession), ('chat_messages', ChatMessage),
        ('warnings', HealthWarning), ('handles', WarningHandleRecord), ('knowledge_documents', KnowledgeDocument), ('knowledge_chunks', KnowledgeChunk))}
    totals['profiles'] = db.scalar(select(func.count()).select_from(ElderProfile).where(ElderProfile.deleted == 0))
    totals['family_binds'] = db.scalar(select(func.count()).select_from(FamilyBind).where(FamilyBind.status == 'APPROVED'))
    totals['care_relations'] = db.scalar(select(func.count()).select_from(CareRelation).where(CareRelation.status == 1))
    return ok({'users': users_total, 'total_users': users_total, 'registered_users': len(users), 'active_users': active,
               'consultations': len(consults), 'warnings': len(warnings), 'module_totals': totals,
               'pending': sum(row.status in ('PENDING', 'PROCESSING') for row in warnings), 'handled': handles,
               'resolved': sum(row.status == 'RESOLVED' for row in warnings), 'range': range, 'period_start': dt(start), 'period_end': dt(end),
               'statistic_basis': '新增/咨询/预警按创建时间；待处理为周期内创建且当前待处理预警；已处理次数按处理记录时间；活跃用户按最后登录时间；模块总量为全部历史实际记录。',
               'role_counts': {role: db.scalar(select(func.count()).select_from(User).where(User.role == role)) for role in ('ELDER', 'FAMILY', 'CARE', 'ADMIN')},
               'chart': {'dates': dates, 'users': [sum(row.create_time.strftime('%Y-%m-%d') == date for row in users) for date in dates],
                         'consultations': [sum(row.create_time.strftime('%Y-%m-%d') == date for row in consults) for date in dates],
                         'warnings': [sum(row.create_time.strftime('%Y-%m-%d') == date for row in warnings) for date in dates]}})


builtins_range = range


@router.get('/care-assignments')
@router.get('/care-relations')
def assignments(db: Session = Depends(get_db)):
    rows = db.scalars(select(CareRelation).order_by(CareRelation.id.desc()))
    return ok([{'relation_id': row.id, 'id': row.id, 'care_user_id': row.care_user_id, 'care_name': db.get(User, row.care_user_id).name,
                'profile_id': row.profile_id, 'elder_name': db.get(ElderProfile, row.profile_id).name, 'enabled': bool(row.status)} for row in rows])


@router.post('/care-assignments')
@router.post('/care-relations')
def assign(body: AssignmentInput, db: Session = Depends(get_db)):
    profile = db.scalar(select(ElderProfile).where(ElderProfile.id == body.profile_id, ElderProfile.deleted == 0).with_for_update())
    care = db.get(User, body.care_user_id)
    if not profile or not care or care.role != 'CARE' or (body.enabled and not care.status):
        raise APIError(2001, '请选择有效老人档案与启用的护工账号')
    row = db.scalar(select(CareRelation).where(CareRelation.profile_id == body.profile_id, CareRelation.care_user_id == body.care_user_id).with_for_update())
    if not row:
        row = CareRelation(care_user_id=body.care_user_id, profile_id=body.profile_id)
        db.add(row)
    row.status = int(body.enabled)
    db.commit()
    return ok({'relation_id': row.id, 'care_user_id': row.care_user_id, 'profile_id': row.profile_id, 'enabled': bool(row.status)})


@router.delete('/care-relations/{relation_id}')
def revoke_assignment(relation_id: int, db: Session = Depends(get_db)):
    row = db.get(CareRelation, relation_id)
    if not row:
        raise APIError(2002, '护工分配不存在', 404)
    db.scalar(select(ElderProfile).where(ElderProfile.id == row.profile_id).with_for_update())
    row = db.scalar(select(CareRelation).where(CareRelation.id == relation_id).with_for_update().execution_options(populate_existing=True))
    row.status = 0
    db.commit()
    return ok()


@config_router.get('/indicators')
def public_indicators(db: Session = Depends(get_db)):
    return ok([indicator(db, type) for type in INDICATORS])


@config_router.get('/thresholds')
def public_thresholds(db: Session = Depends(get_db)):
    return ok([threshold_data(row) for row in db.scalars(select(SysConfig).where(SysConfig.group_name == 'threshold', SysConfig.enabled == 1).order_by(SysConfig.id))])
