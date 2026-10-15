"""院内服务 API，健康数据授权与生活服务权限分离。"""
from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, Query
from pydantic import Field, field_validator, model_validator
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.core.database import get_db, now
from app.core.security import get_current_user
from app.core.errors import APIError, ok
from app.models import ElderProfile, User, SysConfig
from app.models.care_services import (ServiceCatalog, ServiceRequest, ServiceEvent, Activity,
    ActivityRegistration, Equipment, EquipmentLoan, ServiceNotification)
from app.services import care_services as business
from .schemas import StrictModel

router = APIRouter(prefix='/services', tags=['院内服务'])


class LocalTimes(StrictModel):
    @field_validator('requested_at', 'start_at', 'end_at', check_fields=False)
    @classmethod
    def local_time(cls, value):
        if value is not None and value.tzinfo:
            raise ValueError('时间须采用中国本地时间，不带时区后缀')
        return value


class RequestInput(LocalTimes):
    profile_id: int = Field(gt=0)
    category: str = Field(pattern=r'^[A-Z_]{1,30}$')
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=2000)
    location: str = Field(min_length=1, max_length=150)
    requested_at: datetime | None = None


class CallInput(StrictModel):
    profile_id: int = Field(gt=0)
    location: str = Field(min_length=1, max_length=150)
    description: str = Field(default='', max_length=2000)


class TransitionInput(StrictModel):
    status: Literal['ACCEPTED', 'IN_PROGRESS', 'COMPLETED', 'REJECTED', 'CANCELLED']
    result: str = Field(default='', max_length=2000)
    assigned_to: int | None = Field(default=None, gt=0)


class CatalogInput(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=500)
    enabled: bool = True


class NewCatalogInput(CatalogInput):
    category: str = Field(pattern=r'^[A-Z_]{1,30}$')


class ActivityInput(LocalTimes):
    title: str = Field(min_length=1, max_length=100)
    category: str = Field(default='ENTERTAINMENT', max_length=30, min_length=1)
    start_at: datetime
    end_at: datetime
    location: str = Field(min_length=1, max_length=150)
    capacity: int = Field(ge=1, le=10000)
    description: str = Field(default='', max_length=2000)
    status: Literal['PUBLISHED', 'DRAFT'] = 'PUBLISHED'

    @model_validator(mode='after')
    def ordered_time(self):
        if self.start_at >= self.end_at:
            raise ValueError('活动结束时间须晚于开始时间')
        if self.start_at <= now():
            raise ValueError('活动开始时间须在未来')
        return self


class ActivityTransition(StrictModel):
    status: Literal['PUBLISHED', 'CLOSED', 'CANCELLED']


class RegistrationInput(StrictModel):
    profile_id: int = Field(gt=0)


class RegistrationTransition(StrictModel):
    status: Literal['CANCELLED', 'ATTENDED', 'ABSENT']


class EquipmentInput(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    total: int = Field(ge=0, le=100000)
    description: str = Field(default='', max_length=2000)


class EquipmentUpdate(StrictModel):
    enabled: bool | None = None
    total: int | None = Field(default=None, ge=0, le=100000)
    description: str | None = Field(default=None, max_length=2000)


class ServiceSettingsInput(StrictModel):
    call_timeout_seconds: int = Field(ge=15, le=3600)


class EquipmentRequest(CallInput):
    quantity: int = Field(ge=1, le=10000)


class ReturnInput(StrictModel):
    damaged: bool = False
    note: str = Field(default='', max_length=2000)


def time(value):
    return value.isoformat(timespec='seconds') if value else None


def request_data(db, row):
    profile, creator = db.get(ElderProfile, row.profile_id), db.get(User, row.creator_id)
    assigned = db.get(User, row.assigned_to) if row.assigned_to else None
    return {'id': row.id, 'request_id': row.id, 'profile_id': row.profile_id,
        'elder_name': profile.name if profile else None, 'creator_id': row.creator_id,
        'creator_name': creator.name if creator else None, 'category': row.category,
        'title': row.title, 'description': row.description, 'location': row.location,
        'requested_at': time(row.requested_at), 'priority': row.priority, 'status': row.status,
        'assigned_to': row.assigned_to, 'assigned_name': assigned.name if assigned else None,
        'accepted_at': time(row.accepted_at), 'completed_at': time(row.completed_at),
        'escalated_at': time(row.escalated_at), 'result': row.result,
        'equipment_id': row.equipment_id, 'quantity': row.quantity,
        'created_at': time(row.create_time), 'updated_at': time(row.update_time)}


def activity_data(row):
    return {'id': row.id, 'activity_id': row.id, 'title': row.title, 'category': row.category,
        'start_at': time(row.start_at), 'end_at': time(row.end_at), 'location': row.location,
        'capacity': row.capacity, 'registered_count': row.reserved_count,
        'remaining': max(0, row.capacity - row.reserved_count), 'description': row.description,
        'status': row.status, 'creator_id': row.creator_id}


def registration_data(db, row):
    profile = db.get(ElderProfile, row.profile_id)
    return {'id': row.id, 'registration_id': row.id, 'activity_id': row.activity_id,
        'profile_id': row.profile_id, 'elder_name': profile.name if profile else None,
        'status': row.status, 'creator_id': row.creator_id, 'recorded_by': row.recorded_by,
        'created_at': time(row.create_time)}


def equipment_data(row):
    return {'id': row.id, 'equipment_id': row.id, 'name': row.name, 'total': row.total,
        'available': row.available, 'damaged': row.damaged, 'description': row.description,
        'enabled': bool(row.enabled)}


def loan_data(db, row):
    profile, equipment = db.get(ElderProfile, row.profile_id), db.get(Equipment, row.equipment_id)
    return {'id': row.id, 'loan_id': row.id, 'request_id': row.request_id,
        'profile_id': row.profile_id, 'elder_name': profile.name if profile else None,
        'equipment_id': row.equipment_id, 'equipment_name': equipment.name if equipment else None,
        'quantity': row.quantity, 'status': row.status, 'issued_by': row.issued_by,
        'created_at': time(row.create_time), 'returned_at': time(row.returned_at),
        'returned_by': row.returned_by, 'return_note': row.return_note}


def sweep(db):
    if business.escalate_overdue_calls(db):
        db.commit()


def catalog_rows(db, user):
    rows = {item['category']: dict(item, enabled=True) for item in business.DEFAULT_CATALOG}
    for row in db.scalars(select(ServiceCatalog).order_by(ServiceCatalog.id)):
        rows[row.category] = {'id': row.id, 'category': row.category, 'name': row.name,
                             'description': row.description, 'enabled': bool(row.enabled)}
    return [row for row in rows.values() if row['enabled'] or user.role == 'ADMIN']


@router.get('/profiles')
def profiles(user=Depends(get_current_user), db: Session = Depends(get_db)):
    result = []
    for row in db.scalars(select(ElderProfile).where(*business.profile_conditions(user)).order_by(ElderProfile.id)):
        location = db.scalar(select(ServiceRequest.location).where(ServiceRequest.profile_id == row.id)
            .order_by(ServiceRequest.id.desc()).limit(1))
        result.append({'profile_id': row.id, 'name': row.name, 'location': location})
    return ok(result)


@router.get('/catalog')
def catalog(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(catalog_rows(db, user))


@router.post('/catalog')
def new_catalog(body: NewCatalogInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    business.admin(user)
    if any(row['category'] == body.category for row in catalog_rows(db, user)):
        raise APIError(2001, '类别已存在，请使用编辑接口', 409)
    row = ServiceCatalog(**body.model_dump(exclude={'enabled'}), enabled=int(body.enabled))
    db.add(row)
    db.commit()
    return ok({'id': row.id, **body.model_dump()})


@router.put('/catalog/{category}')
def edit_catalog(category: str, body: CatalogInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    business.admin(user)
    if category in ('CALL', 'EQUIPMENT') and not body.enabled:
        raise APIError(2001, '呼叫和设备为系统类别，不能禁用')
    if not any(item['category'] == category for item in catalog_rows(db, user)):
        raise APIError(2002, '服务类别不存在', 404)
    row = db.scalar(select(ServiceCatalog).where(ServiceCatalog.category == category).with_for_update())
    if not row:
        row = ServiceCatalog(category=category, name=body.name)
        db.add(row)
    row.name, row.description, row.enabled = body.name, body.description, int(body.enabled)
    db.commit()
    return ok({'id': row.id, 'category': category, **body.model_dump()})


@router.get('/requests')
def requests(profile_id: int | None = None, status: str | None = None, category: str | None = None,
             page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
             user=Depends(get_current_user), db: Session = Depends(get_db)):
    sweep(db)
    criteria = [ServiceRequest.profile_id.in_(business.visible_ids(db, user))]
    if profile_id:
        business.get_service_profile(db, user, profile_id)
        criteria.append(ServiceRequest.profile_id == profile_id)
    if status:
        if status not in (*business.ACTIVE, 'COMPLETED', 'REJECTED', 'CANCELLED'):
            raise APIError(2001, '服务状态无效')
        criteria.append(ServiceRequest.status == status)
    if category:
        criteria.append(ServiceRequest.category == category)
    total = db.scalar(select(func.count()).select_from(ServiceRequest).where(*criteria))
    rows = db.scalars(select(ServiceRequest).where(*criteria).order_by(ServiceRequest.priority.desc(),
        ServiceRequest.create_time, ServiceRequest.id).offset((page-1)*page_size).limit(page_size))
    return ok({'list': [request_data(db, row) for row in rows], 'total': total, 'page': page, 'page_size': page_size})


@router.post('/requests')
def new_request(body: RequestInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    profile = business.get_service_profile(db, user, body.profile_id, True)
    if body.category in ('CALL', 'EQUIPMENT'):
        raise APIError(2001, '请使用专门的呼叫或设备申请入口')
    if not any(row['category'] == body.category and row['enabled'] for row in catalog_rows(db, user)):
        raise APIError(2001, '服务类别不存在或已停用')
    row = business.create_request(db, user, profile, **body.model_dump(exclude={'profile_id'}))
    db.commit()
    return ok(request_data(db, row))


@router.post('/calls')
def call(body: CallInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    sweep(db)
    profile = business.get_service_profile(db, user, body.profile_id, True)
    row = db.scalar(select(ServiceRequest).where(ServiceRequest.active_call_key == str(profile.id)).with_for_update())
    if row:
        return ok(dict(request_data(db, row), reused=True))
    try:
        row = business.create_request(db, user, profile, category='CALL', title='立即呼叫护工',
            description=body.description, location=body.location)
    except IntegrityError:
        # The unique active_call_key also covers simultaneous browser clicks.
        db.rollback()
        business.get_service_profile(db, user, body.profile_id)
        row = db.scalar(select(ServiceRequest).where(ServiceRequest.active_call_key == str(body.profile_id)))
        if not row:
            raise
        return ok(dict(request_data(db, row), reused=True))
    db.commit()
    return ok(dict(request_data(db, row), reused=False))


@router.get('/requests/{request_id}')
def request_detail(request_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    sweep(db)
    row = business.get_request(db, user, request_id)
    result = request_data(db, row)
    result['events'] = []
    for item in db.scalars(select(ServiceEvent).where(ServiceEvent.request_id == row.id).order_by(ServiceEvent.id)):
        actor = db.get(User, item.actor_id) if item.actor_id else None
        result['events'].append({'id': item.id, 'actor_id': item.actor_id,
            'actor_name': actor.name if actor else '系统', 'from_status': item.from_status,
            'to_status': item.to_status, 'note': item.note, 'created_at': time(item.create_time)})
    return ok(result)


@router.post('/requests/{request_id}/transition')
def transition(request_id: int, body: TransitionInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    row = business.get_request(db, user, request_id, True)
    business.transition_request(db, user, row, body.status, body.result, body.assigned_to)
    db.commit()
    return ok(request_data(db, row))


@router.get('/activities')
def activities(user=Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(Activity)
    if user.role not in ('CARE', 'ADMIN'):
        query = query.where(Activity.status != 'DRAFT')
    return ok([activity_data(row) for row in db.scalars(query.order_by(Activity.start_at.desc(), Activity.id.desc()))])


@router.post('/activities')
def new_activity(body: ActivityInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    business.staff(user)
    row = Activity(**body.model_dump(), creator_id=user.id, reserved_count=0)
    db.add(row)
    db.commit()
    return ok(activity_data(row))


@router.post('/activities/{activity_id}/transition')
def activity_transition(activity_id: int, body: ActivityTransition,
                        user=Depends(get_current_user), db: Session = Depends(get_db)):
    business.staff(user)
    row = db.scalar(select(Activity).where(Activity.id == activity_id).with_for_update())
    if not row:
        raise APIError(2002, '活动不存在', 404)
    if user.role == 'CARE' and row.creator_id != user.id:
        raise APIError(1002, '仅活动创建者或管理员可以变更活动', 403)
    source, target = row.status, body.status
    allowed = {'DRAFT': ('PUBLISHED', 'CANCELLED'), 'PUBLISHED': ('CLOSED', 'CANCELLED'),
               'CLOSED': ('CANCELLED',)}
    if target not in allowed.get(source, ()):
        raise APIError(2001, '活动状态已变化或不允许该操作', 409)
    if target == 'PUBLISHED' and row.start_at <= now():
        raise APIError(2001, '活动已经开始，不能发布', 409)
    changed = db.execute(update(Activity).where(Activity.id == row.id, Activity.status == source)
        .values(status=target, update_time=now()).execution_options(synchronize_session=False)).rowcount
    if changed != 1:
        raise APIError(2001, '其他人员已变更活动，请刷新', 409)
    if target == 'CANCELLED':
        registrations = list(db.scalars(select(ActivityRegistration).where(
            ActivityRegistration.activity_id == row.id, ActivityRegistration.status == 'REGISTERED').with_for_update()))
        db.execute(update(ActivityRegistration).where(ActivityRegistration.activity_id == row.id,
            ActivityRegistration.status == 'REGISTERED').values(status='CANCELLED', recorded_by=user.id, update_time=now()))
        # Keep genuine attendance history; only unfulfilled reservations are released.
        db.execute(update(Activity).where(Activity.id == row.id)
            .values(reserved_count=Activity.reserved_count - len(registrations), update_time=now()))
        for registration in registrations:
            business.notify(db, registration.profile_id, 'ACTIVITY', row.id, '活动已取消',
                            f'{row.title}已取消，您的报名名额已释放。')
    db.refresh(row)
    db.commit()
    return ok(activity_data(row))


@router.post('/activities/{activity_id}/register')
def register(activity_id: int, body: RegistrationInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    row = business.register(db, user, activity_id, body.profile_id)
    db.commit()
    return ok(registration_data(db, row))


@router.get('/activities/{activity_id}/registrations')
def registrations(activity_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    if not db.get(Activity, activity_id):
        raise APIError(2002, '活动不存在', 404)
    rows = db.scalars(select(ActivityRegistration).where(ActivityRegistration.activity_id == activity_id,
        ActivityRegistration.profile_id.in_(business.visible_ids(db, user))).order_by(ActivityRegistration.id))
    return ok([registration_data(db, row) for row in rows])


@router.post('/registrations/{registration_id}/transition')
def registration_transition(registration_id: int, body: RegistrationTransition,
        user=Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.get(ActivityRegistration, registration_id)
    if not row:
        raise APIError(2002, '报名记录不存在', 404)
    activity = db.scalar(select(Activity).where(Activity.id == row.activity_id).with_for_update())
    business.get_service_profile(db, user, row.profile_id, True)
    row = db.scalar(select(ActivityRegistration).where(ActivityRegistration.id == registration_id).with_for_update()
                    .execution_options(populate_existing=True))
    if row.status != 'REGISTERED':
        raise APIError(2001, '报名已经处理，请刷新', 409)
    if body.status == 'CANCELLED' and user.role in ('ELDER', 'FAMILY') and row.creator_id != user.id:
        raise APIError(1002, '只能取消本人提交的活动报名', 403)
    if body.status != 'CANCELLED':
        business.staff(user)
        if activity.status in ('CANCELLED', 'DRAFT'):
            raise APIError(2001, '活动未发布或已取消，不能记录出席情况', 409)
        if activity.start_at > now():
            raise APIError(2001, '活动尚未开始，不能记录出席情况', 409)
    elif activity.start_at <= now() and user.role not in ('CARE', 'ADMIN'):
        raise APIError(2001, '活动已经开始，请联系工作人员取消', 409)
    changed = db.execute(update(ActivityRegistration).where(ActivityRegistration.id == row.id,
        ActivityRegistration.status == 'REGISTERED').values(status=body.status, recorded_by=user.id,
        update_time=now()).execution_options(synchronize_session=False)).rowcount
    if changed != 1:
        raise APIError(2001, '其他人员已处理，请刷新', 409)
    if body.status == 'CANCELLED':
        db.execute(update(Activity).where(Activity.id == activity.id, Activity.reserved_count > 0)
                   .values(reserved_count=Activity.reserved_count - 1, update_time=now()))
    db.refresh(row)
    status_text = {'CANCELLED': '已取消报名', 'ATTENDED': '已出席', 'ABSENT': '未出席'}[body.status]
    business.notify(db, row.profile_id, 'ACTIVITY', activity.id, '活动报名状态更新', f'{activity.title}：{status_text}')
    db.commit()
    return ok(registration_data(db, row))


@router.get('/equipment')
def equipment(user=Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(Equipment).order_by(Equipment.id)
    if user.role != 'ADMIN':
        query = query.where(Equipment.enabled == 1)
    return ok([equipment_data(row) for row in db.scalars(query)])


@router.post('/equipment')
def new_equipment(body: EquipmentInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    business.admin(user)
    row = Equipment(**body.model_dump(), available=body.total, damaged=0, enabled=1)
    db.add(row)
    db.commit()
    return ok(equipment_data(row))


@router.put('/equipment/{equipment_id}')
def update_equipment(equipment_id: int, body: EquipmentUpdate,
                     user=Depends(get_current_user), db: Session = Depends(get_db)):
    business.admin(user)
    values = body.model_dump(exclude_none=True)
    if not values:
        raise APIError(2001, '请至少填写一个设备配置项')
    row = db.scalar(select(Equipment).where(Equipment.id == equipment_id).with_for_update())
    if not row:
        raise APIError(2002, '设备不存在', 404)
    borrowed = row.total - row.available - row.damaged
    if borrowed < 0:
        raise APIError(5001, '库存数据不一致，请核验借用和损坏记录', 503)
    new_total = values.get('total', row.total)
    if new_total < borrowed + row.damaged:
        raise APIError(2001, '设备总量不能小于已借出数量与损坏库存之和', 409)
    values['available'] = new_total - borrowed - row.damaged
    values['update_time'] = now()
    if 'enabled' in values:
        values['enabled'] = int(values['enabled'])
    changed = db.execute(update(Equipment).where(Equipment.id == row.id, Equipment.total == row.total,
        Equipment.available == row.available, Equipment.damaged == row.damaged).values(**values)
        .execution_options(synchronize_session=False)).rowcount
    if changed != 1:
        raise APIError(2001, '库存已变化，请刷新后重试', 409)
    db.refresh(row)
    db.commit()
    return ok(equipment_data(row))


@router.post('/equipment/{equipment_id}/request')
def equipment_request(equipment_id: int, body: EquipmentRequest,
                      user=Depends(get_current_user), db: Session = Depends(get_db)):
    profile = business.get_service_profile(db, user, body.profile_id, True)
    item = db.get(Equipment, equipment_id)
    if not item or not item.enabled:
        raise APIError(2002, '设备不存在或已停用', 404)
    if body.quantity > item.available:
        raise APIError(2001, '当前设备库存不足', 409)
    row = business.create_request(db, user, profile, category='EQUIPMENT', title=f'借用{item.name}'[:100],
        description=body.description, location=body.location, equipment_id=item.id, quantity=body.quantity)
    db.commit()
    return ok(request_data(db, row))


@router.get('/loans')
def loans(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(EquipmentLoan).where(EquipmentLoan.profile_id.in_(business.visible_ids(db, user)))
        .order_by(EquipmentLoan.id.desc()))
    return ok([loan_data(db, row) for row in rows])


@router.post('/loans/{loan_id}/return')
def loan_return(loan_id: int, body: ReturnInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    row = business.return_loan(db, user, loan_id, body.damaged, body.note)
    db.commit()
    return ok(loan_data(db, row))


@router.get('/notifications')
def notifications(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
                  user=Depends(get_current_user), db: Session = Depends(get_db)):
    sweep(db)
    criteria = [ServiceNotification.recipient_id == user.id,
                ServiceNotification.profile_id.in_(business.visible_ids(db, user))]
    total = db.scalar(select(func.count()).select_from(ServiceNotification).where(*criteria))
    unread = db.scalar(select(func.count()).select_from(ServiceNotification).where(*criteria,
                        ServiceNotification.read_status == 'UNREAD'))
    rows = db.scalars(select(ServiceNotification).where(*criteria).order_by(ServiceNotification.id.desc())
        .offset((page-1)*page_size).limit(page_size))
    return ok({'list': [{'id': row.id, 'notification_id': row.id, 'profile_id': row.profile_id,
        'ref_type': row.ref_type, 'ref_id': row.ref_id, 'title': row.title, 'content': row.content,
        'read_status': row.read_status, 'created_at': time(row.create_time), 'read_at': time(row.read_at)} for row in rows],
        'total': total, 'unread_count': unread, 'page': page, 'page_size': page_size})


@router.post('/notifications/{notification_id}/read')
def notification_read(notification_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    row = db.scalar(select(ServiceNotification).where(ServiceNotification.id == notification_id,
        ServiceNotification.recipient_id == user.id,
        ServiceNotification.profile_id.in_(business.visible_ids(db, user))).with_for_update())
    if not row:
        raise APIError(1002, '通知不存在或已失去访问权限', 403)
    row.read_status, row.read_at = 'READ', now()
    db.commit()
    return ok({'id': row.id, 'read_status': row.read_status})


@router.get('/dashboard')
def dashboard(user=Depends(get_current_user), db: Session = Depends(get_db)):
    sweep(db)
    criteria = [ServiceRequest.profile_id.in_(business.visible_ids(db, user))]
    rows = db.execute(select(ServiceRequest.status, func.count()).where(*criteria).group_by(ServiceRequest.status)).all()
    counts = dict(rows)
    calls = db.scalar(select(func.count()).select_from(ServiceRequest).where(*criteria,
        ServiceRequest.category == 'CALL', ServiceRequest.status.in_(business.ACTIVE)))
    escalated = db.scalar(select(func.count()).select_from(ServiceRequest).where(*criteria,
        ServiceRequest.escalated_at.is_not(None), ServiceRequest.status == 'SUBMITTED'))
    return ok({'counts': counts, 'pending': counts.get('SUBMITTED', 0),
        'in_progress': counts.get('ACCEPTED', 0) + counts.get('IN_PROGRESS', 0),
        'completed': counts.get('COMPLETED', 0), 'active_calls': calls, 'escalated_calls': escalated})


@router.get('/settings')
def service_settings(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return ok({'call_timeout_seconds': business.call_timeout_seconds(db)})


@router.put('/settings')
def update_service_settings(body: ServiceSettingsInput,
                            user=Depends(get_current_user), db: Session = Depends(get_db)):
    business.admin(user)
    row = db.scalar(select(SysConfig).where(SysConfig.config_key == 'service_call_timeout_seconds').with_for_update())
    if row:
        row.config_value, row.enabled = str(body.call_timeout_seconds), 1
    else:
        db.add(SysConfig(config_key='service_call_timeout_seconds', config_value=str(body.call_timeout_seconds),
            config_type='number', group_name='services', description='院内呼叫无人应答升级管理员的秒数', enabled=1))
    db.commit()
    return ok({'call_timeout_seconds': body.call_timeout_seconds})
