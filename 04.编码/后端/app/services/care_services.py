"""确定性院内服务；授权、接单、库存与呼叫不依赖模型。"""
from datetime import timedelta
from sqlalchemy import select, update
from app.core.database import now
from app.core.errors import APIError
from app.models import ElderProfile, FamilyBind, CareRelation, User, SysConfig
from app.models.care_services import (ServiceRequest, ServiceEvent, Activity, ActivityRegistration,
                                      Equipment, EquipmentLoan, ServiceNotification)

ACTIVE = ('SUBMITTED', 'ACCEPTED', 'IN_PROGRESS')
STATUS_NAMES = {'SUBMITTED': '待接单', 'ACCEPTED': '已接单', 'IN_PROGRESS': '正在处理',
                'COMPLETED': '已完成', 'REJECTED': '已拒绝', 'CANCELLED': '已取消'}
DEFAULT_CATALOG = [
    {'category': 'ENTERTAINMENT', 'name': '娱乐与陪伴', 'description': '打牌、棋类、唱歌及陪伴'},
    {'category': 'EXERCISE', 'name': '锻炼协助', 'description': '散步、适宜运动与活动协助'},
    {'category': 'DAILY_LIVING', 'name': '生活照料', 'description': '日常起居、洗护及便民协助'},
    {'category': 'CLEANING', 'name': '保洁与维修', 'description': '房间保洁、报修及设施帮助'},
    {'category': 'MEAL', 'name': '餐饮协助', 'description': '用餐、饮水及送餐需求'},
    {'category': 'OTHER', 'name': '其他服务', 'description': '尚未列出的院内服务需求'},
    {'category': 'CALL', 'name': '立即呼叫护工', 'description': '优先通知负责人员并记录应答'},
    {'category': 'EQUIPMENT', 'name': '设备申请', 'description': '申请借用、出库及归还'},
]


def profile_conditions(user):
    criteria = [ElderProfile.deleted == 0]
    if user.role == 'ELDER':
        criteria.append(ElderProfile.user_id == user.id)
    elif user.role == 'FAMILY':
        criteria.append(ElderProfile.id.in_(select(FamilyBind.profile_id).where(
            FamilyBind.family_user_id == user.id, FamilyBind.status == 'APPROVED')))
    elif user.role == 'CARE':
        criteria.append(ElderProfile.id.in_(select(CareRelation.profile_id).where(
            CareRelation.care_user_id == user.id, CareRelation.status == 1)))
    elif user.role != 'ADMIN':
        raise APIError(1002, '无权限使用院内服务', 403)
    return criteria


def visible_ids(db, user):
    return select(ElderProfile.id).where(*profile_conditions(user))


def get_service_profile(db, user, profile_id, lock=False):
    """Minimal identity ACL deliberately does not require health consent."""
    if not lock:
        profile = db.scalar(select(ElderProfile).where(ElderProfile.id == profile_id, *profile_conditions(user)))
        if profile:
            return profile
    else:
        # In MySQL REPEATABLE READ, an outer FOR UPDATE does not turn a nested
        # relation subquery into a current read. Lock and refresh each row
        # independently so authentication's earlier snapshot grants no access.
        profile = db.scalar(select(ElderProfile).where(ElderProfile.id == profile_id, ElderProfile.deleted == 0)
            .with_for_update().execution_options(populate_existing=True))
        if profile:
            if user.role == 'ADMIN' or (user.role == 'ELDER' and profile.user_id == user.id):
                return profile
            if user.role == 'FAMILY':
                query = select(FamilyBind).where(FamilyBind.family_user_id == user.id,
                    FamilyBind.profile_id == profile_id, FamilyBind.status == 'APPROVED')
            elif user.role == 'CARE':
                query = select(CareRelation).where(CareRelation.care_user_id == user.id,
                    CareRelation.profile_id == profile_id, CareRelation.status == 1)
            else:
                query = None
            if query is not None and db.scalar(query.with_for_update().execution_options(populate_existing=True)):
                return profile
    raise APIError(1002, '无权限访问该老人服务或档案已停用', 403)


def staff(user):
    if user.role not in ('CARE', 'ADMIN'):
        raise APIError(1002, '仅护工或管理员可以执行此操作', 403)


def admin(user):
    if user.role != 'ADMIN':
        raise APIError(1002, '仅管理员可以执行此操作', 403)


def admin_ids(db):
    return list(db.scalars(select(User.id).where(User.role == 'ADMIN', User.status == 1).order_by(User.id)))


def care_ids(db, profile_id):
    return list(db.scalars(select(User.id).join(CareRelation, CareRelation.care_user_id == User.id).where(
        CareRelation.profile_id == profile_id, CareRelation.status == 1, User.role == 'CARE', User.status == 1).order_by(User.id)))


def recipients(db, profile_id, include_admin=False):
    profile = db.get(ElderProfile, profile_id)
    ids = {profile.user_id} if profile else set()
    ids.update(db.scalars(select(FamilyBind.family_user_id).where(
        FamilyBind.profile_id == profile_id, FamilyBind.status == 'APPROVED')))
    cares = care_ids(db, profile_id)
    ids.update(cares)
    if include_admin or not cares:
        ids.update(admin_ids(db))
    return set(db.scalars(select(User.id).where(User.id.in_(ids), User.status == 1)))


def notify(db, profile_id, ref_type, ref_id, title, content, include_admin=False, only=None):
    ids = set(only) if only is not None else recipients(db, profile_id, include_admin)
    db.add_all(ServiceNotification(recipient_id=user_id, profile_id=profile_id, ref_type=ref_type,
        ref_id=ref_id, title=title, content=content, read_status='UNREAD') for user_id in ids)


def event(db, row, user, source, target, note):
    db.add(ServiceEvent(request_id=row.id, actor_id=user.id if user else None,
                        from_status=source, to_status=target, note=note))


def create_request(db, user, profile, *, category, title, description, location,
                   requested_at=None, equipment_id=None, quantity=None):
    cares, admins = care_ids(db, profile.id), admin_ids(db)
    row = ServiceRequest(profile_id=profile.id, creator_id=user.id, category=category,
        title=title, description=description, location=location, requested_at=requested_at,
        priority=3 if category == 'CALL' else 1, status='SUBMITTED',
        assigned_to=(cares or admins or [None])[0], equipment_id=equipment_id, quantity=quantity,
        active_call_key=str(profile.id) if category == 'CALL' else None)
    db.add(row)
    db.flush()
    event(db, row, user, None, 'SUBMITTED', '发起院内服务申请')
    notify(db, profile.id, 'SERVICE_REQUEST', row.id, '新呼叫，请优先应答' if category == 'CALL' else '新的院内服务申请',
           f'{profile.name}：{title}；位置：{location}', include_admin=not cares)
    if category == 'CALL' and not cares and admins:
        row.escalated_at = now()
        event(db, row, None, 'SUBMITTED', 'SUBMITTED', '无有效负责护工，已升级至管理员')
    elif category == 'CALL' and not cares:
        event(db, row, None, 'SUBMITTED', 'SUBMITTED', '暂无有效护工或管理员，请立即使用院内线下求助方式')
    return row


def get_request(db, user, request_id, lock=False):
    row = db.get(ServiceRequest, request_id)
    if not row:
        raise APIError(2002, '服务申请不存在', 404)
    get_service_profile(db, user, row.profile_id, lock)
    if lock:
        row = db.scalar(select(ServiceRequest).where(ServiceRequest.id == request_id).with_for_update()
                        .execution_options(populate_existing=True))
    return row


def validate_assignee(db, profile_id, user_id):
    user = db.scalar(select(User).where(User.id == user_id).with_for_update()
                     .execution_options(populate_existing=True))
    if not user or not user.status or user.role not in ('CARE', 'ADMIN'):
        raise APIError(2001, '处理人必须是有效护工或管理员')
    if user.role == 'CARE':
        relation = db.scalar(select(CareRelation).where(CareRelation.care_user_id == user_id,
            CareRelation.profile_id == profile_id, CareRelation.status == 1).with_for_update()
            .execution_options(populate_existing=True))
        if not relation:
            raise APIError(1002, '该护工未负责此老人，不能分派', 403)


def transition_request(db, user, row, target, result='', assigned_to=None):
    source = row.status
    if target == 'CANCELLED':
        if source != 'SUBMITTED' or user.role not in ('ELDER', 'FAMILY', 'CARE', 'ADMIN'):
            raise APIError(2001, '仅待接单申请可以取消', 409)
        if user.role in ('ELDER', 'FAMILY') and row.creator_id != user.id:
            raise APIError(1002, '只能撤回本人提交的服务申请', 403)
    else:
        staff(user)
        allowed = {'SUBMITTED': ('ACCEPTED', 'REJECTED'), 'ACCEPTED': ('IN_PROGRESS',),
                   'IN_PROGRESS': ('COMPLETED',)}
        if target not in allowed.get(source, ()):
            raise APIError(2001, '状态已变化或不允许该操作，请刷新', 409)
        if target != 'ACCEPTED' and user.role == 'CARE' and row.assigned_to != user.id:
            raise APIError(1002, '仅接单人员可以处理此工单', 403)
    if target in ('REJECTED', 'COMPLETED') and not result.strip():
        raise APIError(2001, '请填写处理结果或拒绝原因')
    values = {'status': target, 'update_time': now()}
    if target == 'ACCEPTED':
        assignee = assigned_to if assigned_to is not None else user.id
        if user.role != 'ADMIN' and assignee != user.id:
            raise APIError(1002, '仅管理员可以分派给其他人员', 403)
        validate_assignee(db, row.profile_id, assignee)
        values.update(assigned_to=assignee, accepted_at=now())
    elif assigned_to is not None:
        raise APIError(2001, '仅接单时可以指定处理人')
    if target not in ACTIVE:
        values.update(completed_at=now(), active_call_key=None)
    if result:
        values['result'] = result
    # Conditional write protects against double acceptance even without row locks.
    changed = db.execute(update(ServiceRequest).where(ServiceRequest.id == row.id,
        ServiceRequest.status == source).values(**values).execution_options(synchronize_session=False)).rowcount
    if changed != 1:
        raise APIError(2001, '其他人员已处理，请刷新后重试', 409)
    if row.equipment_id and target == 'ACCEPTED':
        stock = db.execute(update(Equipment).where(Equipment.id == row.equipment_id, Equipment.enabled == 1,
            Equipment.available >= row.quantity).values(available=Equipment.available - row.quantity,
            update_time=now()).execution_options(synchronize_session=False)).rowcount
        if stock != 1:
            raise APIError(2001, '设备库存不足或已停用，未接单未出库', 409)
        db.add(EquipmentLoan(request_id=row.id, equipment_id=row.equipment_id, profile_id=row.profile_id,
                             quantity=row.quantity, issued_by=user.id, status='BORROWED'))
    db.refresh(row)
    event(db, row, user, source, target, result or '服务状态变更')
    notify(db, row.profile_id, 'SERVICE_REQUEST', row.id, '服务申请进度更新',
           f'{row.title}：{STATUS_NAMES[target]}' + (f'；{result}' if result else ''))
    return row


def register(db, user, activity_id, profile_id):
    activity = db.scalar(select(Activity).where(Activity.id == activity_id).with_for_update())
    if not activity:
        raise APIError(2002, '活动不存在', 404)
    # All activity mutations take the activity lock before profile/registration
    # locks, including cancellation, to avoid reversing lock order.
    get_service_profile(db, user, profile_id, True)
    if activity.status != 'PUBLISHED' or activity.start_at <= now():
        raise APIError(2001, '活动未开放报名或已经开始', 409)
    row = db.scalar(select(ActivityRegistration).where(ActivityRegistration.activity_id == activity_id,
                    ActivityRegistration.profile_id == profile_id).with_for_update())
    if row and row.status != 'CANCELLED':
        raise APIError(2001, '已经报名，请勿重复提交', 409)
    changed = db.execute(update(Activity).where(Activity.id == activity.id, Activity.reserved_count < Activity.capacity,
        Activity.status == 'PUBLISHED').values(reserved_count=Activity.reserved_count + 1,
        update_time=now()).execution_options(synchronize_session=False)).rowcount
    if changed != 1:
        raise APIError(2001, '活动名额已满', 409)
    if row:
        row.status, row.creator_id, row.recorded_by = 'REGISTERED', user.id, None
    else:
        row = ActivityRegistration(activity_id=activity.id, profile_id=profile_id, creator_id=user.id, status='REGISTERED')
        db.add(row)
    db.flush()
    notify(db, profile_id, 'ACTIVITY', activity.id, '活动报名成功', f'{activity.title}；位置：{activity.location}')
    return row


def return_loan(db, user, loan_id, damaged=False, note=''):
    staff(user)
    row = db.get(EquipmentLoan, loan_id)
    if not row:
        raise APIError(2002, '借用记录不存在', 404)
    get_service_profile(db, user, row.profile_id, True)
    row = db.scalar(select(EquipmentLoan).where(EquipmentLoan.id == loan_id).with_for_update()
                    .execution_options(populate_existing=True))
    if row.status != 'BORROWED':
        return row
    changed = db.execute(update(EquipmentLoan).where(EquipmentLoan.id == loan_id, EquipmentLoan.status == 'BORROWED')
        .values(status='RETURNED_DAMAGED' if damaged else 'RETURNED', returned_at=now(), returned_by=user.id,
                return_note=note, update_time=now()).execution_options(synchronize_session=False)).rowcount
    if changed == 1:
        values = {'damaged': Equipment.damaged + row.quantity} if damaged else {'available': Equipment.available + row.quantity}
        db.execute(update(Equipment).where(Equipment.id == row.equipment_id).values(**values, update_time=now()))
        request = db.get(ServiceRequest, row.request_id)
        event(db, request, user, request.status, request.status, '设备归还：损坏件转维修库存' if damaged else '设备已完整归还')
        notify(db, row.profile_id, 'LOAN', row.id, '设备归还记录', note or ('损坏件已转维修，不计入可用库存' if damaged else '设备已归还'))
    db.refresh(row)
    return row


def call_timeout_seconds(db):
    config = db.scalar(select(SysConfig).where(SysConfig.config_key == 'service_call_timeout_seconds', SysConfig.enabled == 1))
    try:
        return max(15, min(3600, int(config.config_value))) if config else 300
    except (TypeError, ValueError):
        return 300


def escalate_overdue_calls(db):
    """Caller owns commit; can run on a timer and during workbench polling."""
    timeout = call_timeout_seconds(db)
    admins = admin_ids(db)
    count = 0
    # Staff assignments are live permissions, not permanent grants. Hand over
    # active tasks if their old assignee was disabled or lost the care relation.
    active_rows = list(db.scalars(select(ServiceRequest).where(ServiceRequest.status.in_(ACTIVE)).with_for_update()))
    for row in active_rows:
        carers = care_ids(db, row.profile_id)
        valid = set(carers + admins)
        if row.assigned_to not in valid:
            replacement = (carers or admins or [None])[0]
            if replacement != row.assigned_to:
                changed = db.execute(update(ServiceRequest).where(ServiceRequest.id == row.id,
                    ServiceRequest.status.in_(ACTIVE), ServiceRequest.assigned_to == row.assigned_to)
                    .values(assigned_to=replacement, update_time=now())
                    .execution_options(synchronize_session=False)).rowcount
                if changed:
                    event(db, row, None, row.status, row.status, '原处理人停用或照护权限撤销，已重新分派')
                    notify(db, row.profile_id, 'SERVICE_REQUEST', row.id, '服务任务重新分派',
                           f'{row.title}；位置：{row.location}', include_admin=not carers)
                    db.refresh(row)
                    count += 1
    candidates = list(db.scalars(select(ServiceRequest).where(ServiceRequest.category == 'CALL',
        ServiceRequest.status.in_(ACTIVE), ServiceRequest.escalated_at.is_(None)).with_for_update()))
    for row in candidates:
        has_care = bool(care_ids(db, row.profile_id))
        overdue = row.status == 'SUBMITTED' and row.create_time <= now() - timedelta(seconds=timeout)
        if not admins or (has_care and not overdue):
            continue
        changed = db.execute(update(ServiceRequest).where(ServiceRequest.id == row.id,
            ServiceRequest.status.in_(ACTIVE), ServiceRequest.escalated_at.is_(None))
            .values(escalated_at=now(), update_time=now(), assigned_to=(admins or [None])[0])
            .execution_options(synchronize_session=False)).rowcount
        if changed:
            note = '呼叫未及时应答，已升级管理员' if has_care else '无有效负责护工，已立即升级管理员'
            event(db, row, None, row.status, row.status, note)
            notify(db, row.profile_id, 'SERVICE_REQUEST', row.id, '呼叫超时，请立即处理' if has_care else '呼叫无人负责，请立即处理',
                   f'{row.title}；位置：{row.location}', only=admins)
            count += 1
    return count
