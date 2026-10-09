from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.database import get_db, now
from app.core.security import get_current_user
from app.core.permissions import get_profile, require_roles, visible_profile_ids, require_health_consent
from app.core.errors import APIError, ok
from app.models import User, ElderProfile, FamilyBind
from app.services.serializers import profile_data, dt
from app.services.thresholds import config_value
from .schemas import BindInput, ConfirmBind

router = APIRouter(prefix='/family', tags=['家属绑定'])


def data(db, relation):
    profile = db.get(ElderProfile, relation.profile_id)
    elder = db.get(User, profile.user_id)
    family = db.get(User, relation.family_user_id)
    return {'bind_id': relation.id, 'profile_id': profile.id, 'elder_name': profile.name, 'elder_phone_masked': elder.phone[:3] + '****' + elder.phone[-4:],
            'family_name': family.name, 'relation': relation.relation, 'note': relation.note, 'status': relation.status,
            'approved_by': relation.approved_by, 'approve_note': relation.approve_note, 'created_at': dt(relation.create_time), 'approved_at': dt(relation.approve_time)}


def max_bind(db, profile_id):
    # Locking current read is essential under MySQL REPEATABLE READ: the
    # authentication query can establish a snapshot before the profile lock.
    count = len(list(db.scalars(select(FamilyBind.id).where(FamilyBind.profile_id == profile_id, FamilyBind.status == 'APPROVED').with_for_update())))
    if count >= int(config_value(db, 'family_bind_max', '5')):
        raise APIError(4002, '该老人绑定的家属数量已达上限', 409)


@router.post('/bind')
def bind(body: BindInput, user=Depends(require_roles('FAMILY')), db: Session = Depends(get_db)):
    query = select(ElderProfile).join(User, ElderProfile.user_id == User.id).where(User.phone == body.phone, User.role == 'ELDER', User.status == 1, ElderProfile.deleted == 0)
    if body.profile_id:
        query = query.where(ElderProfile.id == body.profile_id)
    profile = db.scalar(query.order_by(ElderProfile.id).limit(1).with_for_update())
    if not profile:
        raise APIError(2002, '老人账号或健康档案不存在', 404)
    existing = db.scalar(select(FamilyBind.id).where(FamilyBind.profile_id == profile.id, FamilyBind.family_user_id == user.id, FamilyBind.status.in_(['PENDING', 'APPROVED'])).with_for_update())
    if existing:
        raise APIError(4001, '绑定申请已存在，请勿重复提交', 409)
    max_bind(db, profile.id)
    relation = FamilyBind(family_user_id=user.id, profile_id=profile.id, relation=body.relation, note=body.note)
    db.add(relation)
    db.commit()
    return ok(data(db, relation))


def confirmation_scope(db, user):
    if user.role == 'FAMILY':
        return [FamilyBind.family_user_id == user.id]
    return [FamilyBind.profile_id.in_(visible_profile_ids(db, user))]


@router.get('/bind-requests')
def requests(user=Depends(require_roles('ELDER', 'ADMIN', 'CARE')), db: Session = Depends(get_db)):
    rows = db.scalars(select(FamilyBind).where(FamilyBind.status == 'PENDING', *confirmation_scope(db, user)).order_by(FamilyBind.id.desc()))
    return ok([data(db, row) for row in rows])


@router.get('/binds')
def history(user=Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.scalars(select(FamilyBind).where(*confirmation_scope(db, user)).order_by(FamilyBind.id.desc()))
    return ok([data(db, row) for row in rows])


@router.put('/bind/{bind_id}/confirm')
def confirm(bind_id: int, body: ConfirmBind, user=Depends(require_roles('ELDER', 'CARE', 'ADMIN')), db: Session = Depends(get_db)):
    relation = db.get(FamilyBind, bind_id)
    if not relation:
        raise APIError(2002, '绑定申请不存在', 404)
    profile = get_profile(db, user, relation.profile_id, lock=True)
    # Refresh relation after serializing through the profile row lock.
    relation = db.scalar(select(FamilyBind).where(FamilyBind.id == bind_id).with_for_update().execution_options(populate_existing=True))
    if relation.status != 'PENDING':
        raise APIError(2001, '此申请已确认或撤销，请刷新', 409)
    if user.role != 'ELDER' and not body.note:
        raise APIError(2001, '代确认必须记录原因')
    if body.action == 'APPROVE':
        family = db.get(User, relation.family_user_id)
        if not family or not family.status:
            raise APIError(2001, '家属账号已禁用，不能确认申请')
        max_bind(db, profile.id)
    relation.status = 'APPROVED' if body.action == 'APPROVE' else 'REJECTED'
    relation.approved_by, relation.approve_note, relation.approve_time = user.id, body.note, now()
    db.commit()
    return ok(data(db, relation))


@router.get('/elders')
def elders(user=Depends(require_roles('FAMILY')), db: Session = Depends(get_db)):
    require_health_consent(db, user)
    relations = list(db.scalars(select(FamilyBind).where(FamilyBind.family_user_id == user.id, FamilyBind.status == 'APPROVED')))
    result = []
    for relation in relations:
        profile = db.get(ElderProfile, relation.profile_id)
        if profile and not profile.deleted:
            result.append(dict(profile_data(profile), bind_id=relation.id, relation=relation.relation))
    return ok(result)


@router.delete('/bind/{bind_id}')
def revoke(bind_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    relation = db.get(FamilyBind, bind_id)
    if not relation:
        raise APIError(2002, '绑定关系不存在', 404)
    profile = db.scalar(select(ElderProfile).where(ElderProfile.id == relation.profile_id).with_for_update())
    if user.role != 'ADMIN' and user.id not in (relation.family_user_id, profile.user_id):
        raise APIError(1002, '只有老人本人、该家属或管理员能解除关系', 403)
    relation = db.scalar(select(FamilyBind).where(FamilyBind.id == bind_id).with_for_update().execution_options(populate_existing=True))
    if relation.status not in ('APPROVED', 'PENDING'):
        raise APIError(2001, '绑定关系已经终止', 409)
    relation.status = 'REVOKED'
    db.commit()
    return ok()
