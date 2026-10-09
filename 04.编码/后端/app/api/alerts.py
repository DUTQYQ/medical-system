from datetime import timedelta
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session
from app.core.database import get_db, now
from app.core.security import get_current_user
from app.core.permissions import visible_profile_ids, get_profile, require_roles
from app.core.errors import APIError, ok
from app.models import HealthWarning, AlertReceiver, ElderProfile, WarningHandleRecord, User
from app.services.serializers import age, dt
from app.services.thresholds import indicator, INDICATORS
from app.services.alerts import generate_summary
from .schemas import HandleInput, StatusInput
from .health import trend_data

router = APIRouter(prefix='/alerts', tags=['预警中心'])
notifications = APIRouter(prefix='/notifications', tags=['站内通知'])


def accessible_conditions(db, user):
    # Live relationships define permission; receivers define notification/read
    # state only. New authorized caregivers can inspect earlier warning history.
    return [HealthWarning.profile_id.in_(visible_profile_ids(db, user))]


def get_warning(db, user, warning_id, lock=False):
    warning = db.get(HealthWarning, warning_id)
    if not warning:
        raise APIError(2002, '预警不存在', 404)
    get_profile(db, user, warning.profile_id, lock=lock)
    if lock:
        warning = db.scalar(select(HealthWarning).where(HealthWarning.id == warning_id).with_for_update().execution_options(populate_existing=True))
    return warning


def handle_data(db, record):
    handler = db.get(User, record.handler_id)
    warning = db.get(HealthWarning, record.warning_id)
    profile = db.get(ElderProfile, warning.profile_id) if warning else None
    return {'handle_id': record.id, 'warning_id': record.warning_id, 'handler_id': record.handler_id, 'handler_name': handler.name if handler else None,
            'elder_name': profile.name if profile else None, 'profile_id': profile.id if profile else None,
            'action': record.action, 'result': record.result, 'created_at': dt(record.create_time)}


def warning_data(db, user, warning):
    profile = db.get(ElderProfile, warning.profile_id)
    receiver = db.scalar(select(AlertReceiver).where(AlertReceiver.warning_id == warning.id, AlertReceiver.user_id == user.id))
    handle = db.scalar(select(WarningHandleRecord).where(WarningHandleRecord.warning_id == warning.id).order_by(WarningHandleRecord.id.desc()).limit(1))
    meta = indicator(db, warning.type) if warning.type in INDICATORS else {'unit': ''}
    return {'warning_id': warning.id, 'profile_id': warning.profile_id, 'elder_name': profile.name if profile else None,
            'elder_age': age(profile.birthday) if profile else None, 'type': warning.type, 'value_text': warning.value_text, 'unit': meta['unit'],
            'level': warning.level, 'level_text': ['正常', '轻度', '较高', '高风险'][warning.level], 'ai_summary': warning.ai_summary,
            'summary_status': warning.summary_status, 'status': warning.status, 'my_read_status': receiver.read_status if receiver else ('READ' if user.role == 'ADMIN' else 'UNREAD'),
            'trigger_source': warning.trigger_source, 'created_at': dt(warning.create_time),
            'handler_name': handle_data(db, handle)['handler_name'] if handle else None, 'handle_result': handle.result if handle else None}


def read_warning(db, user, warning):
    receiver = db.scalar(select(AlertReceiver).where(AlertReceiver.warning_id == warning.id, AlertReceiver.user_id == user.id).with_for_update())
    if receiver:
        receiver.read_status, receiver.read_time = 'READ', now()
    elif user.role != 'ADMIN':
        db.add(AlertReceiver(warning_id=warning.id, user_id=user.id, read_status='READ', read_time=now()))


@router.get('/statistics')
def statistics(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = list(db.scalars(select(HealthWarning).where(*accessible_conditions(db, user))))
    unread_ids = set(db.scalars(select(AlertReceiver.warning_id).where(AlertReceiver.user_id == user.id, AlertReceiver.read_status == 'UNREAD')))
    return ok({'pending': sum(row.status in ('PENDING', 'PROCESSING') for row in rows), 'high_risk': sum(row.level == 3 and row.status in ('PENDING', 'PROCESSING') for row in rows),
               'today_new': sum(row.create_time.date() == now().date() for row in rows), 'handled': sum(row.status == 'RESOLVED' for row in rows),
               'unread': sum(row.id in unread_ids for row in rows)})


@router.get('')
def listing(status: str | None = None, level: int | None = Query(None, ge=0, le=3), profile_id: int | None = None,
            page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user=Depends(get_current_user), db: Session = Depends(get_db)):
    criteria = accessible_conditions(db, user)
    if status:
        if status not in ('PENDING', 'PROCESSING', 'RESOLVED', 'IGNORED'):
            raise APIError(2001, '预警状态无效')
        criteria.append(HealthWarning.status == status)
    if level is not None:
        criteria.append(HealthWarning.level == level)
    if profile_id:
        get_profile(db, user, profile_id)
        criteria.append(HealthWarning.profile_id == profile_id)
    total = db.scalar(select(func.count()).select_from(HealthWarning).where(*criteria))
    rows = db.scalars(select(HealthWarning).where(*criteria).order_by(HealthWarning.create_time.desc(), HealthWarning.id.desc()).offset((page - 1) * page_size).limit(page_size))
    return ok({'list': [warning_data(db, user, row) for row in rows], 'total': total, 'page': page, 'page_size': page_size})


@router.get('/{warning_id}')
def detail(warning_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    warning = get_warning(db, user, warning_id)
    read_warning(db, user, warning)
    db.commit()
    result = warning_data(db, user, warning)
    result['history_trend'] = trend_data(db, warning.profile_id, warning.type, 7) if warning.type in INDICATORS else {'dates': [], 'series': []}
    result['handles'] = [handle_data(db, row) for row in db.scalars(select(WarningHandleRecord).where(WarningHandleRecord.warning_id == warning_id).order_by(WarningHandleRecord.id))]
    return ok(result)


@router.post('/{warning_id}/handle')
def handle(warning_id: int, body: HandleInput, user=Depends(require_roles('FAMILY', 'CARE', 'ADMIN')), db: Session = Depends(get_db)):
    warning = get_warning(db, user, warning_id, lock=True)
    if warning.status not in ('PENDING', 'PROCESSING'):
        raise APIError(2001, '预警已处理或忽略，请刷新查看处理记录', 409)
    record = WarningHandleRecord(warning_id=warning.id, handler_id=user.id, action=body.action, result=body.result)
    db.add(record)
    warning.status = 'RESOLVED'
    read_warning(db, user, warning)
    db.commit()
    return ok({'warning_id': warning.id, 'status': warning.status, 'handle': handle_data(db, record)})


@router.put('/{warning_id}/status')
def change_status(warning_id: int, body: StatusInput, user=Depends(require_roles('FAMILY', 'CARE', 'ADMIN')), db: Session = Depends(get_db)):
    warning = get_warning(db, user, warning_id, lock=True)
    if warning.status not in ('PENDING', 'PROCESSING'):
        raise APIError(2001, '预警已终结，不能再次变更状态', 409)
    if warning.status == body.status:
        return ok({'warning_id': warning.id, 'status': warning.status})
    warning.status = body.status
    if body.status == 'IGNORED':
        db.add(WarningHandleRecord(warning_id=warning.id, handler_id=user.id, action='OBSERVE', result='人工忽略预警，保持观察'))
    db.commit()
    return ok({'warning_id': warning.id, 'status': warning.status})


@router.post('/{warning_id}/read')
def read(warning_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    warning = get_warning(db, user, warning_id)
    read_warning(db, user, warning)
    db.commit()
    return ok()


@router.post('/{warning_id}/summary/retry')
def retry(warning_id: int, tasks: BackgroundTasks, user=Depends(get_current_user), db: Session = Depends(get_db)):
    warning = get_warning(db, user, warning_id, lock=True)
    if warning.summary_status != 'FAILED':
        raise APIError(2001, '仅生成失败的摘要可以重试', 409)
    warning.summary_status = 'PENDING'
    db.commit()
    tasks.add_task(generate_summary, warning.id)
    return ok({'summary_status': 'PENDING'})


@notifications.get('/unread')
def unread(user=Depends(get_current_user), db: Session = Depends(get_db)):
    criteria = accessible_conditions(db, user) + [HealthWarning.id.in_(select(AlertReceiver.warning_id).where(AlertReceiver.user_id == user.id, AlertReceiver.read_status == 'UNREAD'))]
    result = db.execute(select(func.count(HealthWarning.id), func.max(HealthWarning.level)).where(*criteria)).one()
    return ok({'unread': result[0], 'latest_level': result[1]})


@notifications.get('')
def notification_list(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user=Depends(get_current_user), db: Session = Depends(get_db)):
    criteria = accessible_conditions(db, user) + [HealthWarning.id.in_(select(AlertReceiver.warning_id).where(AlertReceiver.user_id == user.id))]
    total = db.scalar(select(func.count()).select_from(HealthWarning).where(*criteria))
    rows = db.scalars(select(HealthWarning).where(*criteria).order_by(HealthWarning.id.desc()).offset((page - 1) * page_size).limit(page_size))
    return ok({'list': [dict(warning_data(db, user, row), notification_id=row.id) for row in rows], 'total': total, 'page': page, 'page_size': page_size})


@notifications.post('/read-all')
def read_all(user=Depends(get_current_user), db: Session = Depends(get_db)):
    warning_ids = select(HealthWarning.id).where(*accessible_conditions(db, user))
    result = db.execute(update(AlertReceiver).where(AlertReceiver.user_id == user.id, AlertReceiver.warning_id.in_(warning_ids), AlertReceiver.read_status == 'UNREAD').values(read_status='READ', read_time=now()))
    db.commit()
    return ok({'updated': result.rowcount})


@notifications.post('/{warning_id}/read')
def notification_read(warning_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return read(warning_id, user, db)
