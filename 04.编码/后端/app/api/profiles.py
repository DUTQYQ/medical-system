import json
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db, now
from app.core.security import get_current_user
from app.core.permissions import get_profile, profile_scope, require_roles, require_health_consent
from app.core.errors import APIError, ok
from app.models import ElderProfile, User, FamilyBind, CareRelation
from app.services.serializers import profile_data
from .schemas import ProfileInput

router = APIRouter(prefix='/profiles', tags=['健康档案'])


def fields(body):
    values = body.model_dump(exclude={'user_id', 'source_profile_id'})
    tags = json.dumps(body.chronic_tags, ensure_ascii=False)
    if len(tags) > 255:
        raise APIError(2001, '慢病标签总长度超过 255 字符')
    values['chronic_tags'] = tags
    return values


@router.get('')
def profiles(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return ok([profile_data(p) for p in db.scalars(select(ElderProfile).where(*profile_scope(user, db)).order_by(ElderProfile.id))])


@router.post('')
def create(body: ProfileInput, user=Depends(require_roles('ELDER', 'FAMILY', 'CARE', 'ADMIN')), db: Session = Depends(get_db)):
    require_health_consent(db, user)
    source = None
    if user.role in ('FAMILY', 'CARE'):
        if not body.source_profile_id:
            raise APIError(2001, '代建必须指定已授权的来源档案 source_profile_id')
        source = get_profile(db, user, body.source_profile_id, lock=True)
        target_id = source.user_id
        if body.user_id not in (None, target_id):
            raise APIError(1002, '不能为未授权的老人账号创建档案', 403)
    elif user.role == 'ADMIN':
        target_id = body.user_id
        if not target_id:
            raise APIError(2001, '管理员创建档案须指定已有老人账号 user_id')
    else:
        target_id = user.id
        if body.user_id not in (None, user.id):
            raise APIError(1002, '只能创建本人账号下的档案', 403)
    target = db.scalar(select(User).where(User.id == target_id).with_for_update())
    if not target or target.role != 'ELDER' or not target.status:
        raise APIError(2001, '档案必须归属于启用的老人账号')
    profile = ElderProfile(user_id=target_id, **fields(body))
    db.add(profile)
    db.flush()
    if user.role == 'FAMILY':
        previous = db.scalar(select(FamilyBind).where(FamilyBind.family_user_id == user.id, FamilyBind.profile_id == source.id, FamilyBind.status == 'APPROVED').with_for_update())
        db.add(FamilyBind(family_user_id=user.id, profile_id=profile.id, relation=previous.relation, status='APPROVED',
                          approved_by=previous.approved_by, approve_time=now(), note='按既有授权代建档案',
                          approve_note=f'来源档案 {source.id} 已授权；新档案仅创建家属继承授权，其他绑定不复制'))
    elif user.role == 'CARE':
        db.add(CareRelation(care_user_id=user.id, profile_id=profile.id, status=1))
    db.commit()
    return ok(profile_data(profile))


@router.get('/{profile_id}')
def detail(profile_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(profile_data(get_profile(db, user, profile_id)))


@router.put('/{profile_id}')
def update(profile_id: int, body: ProfileInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile(db, user, profile_id, lock=True)
    if body.user_id not in (None, profile.user_id):
        raise APIError(2001, '不能更换档案所属用户')
    for key, value in fields(body).items():
        setattr(profile, key, value)
    db.commit()
    return ok(profile_data(profile))


@router.delete('/{profile_id}')
def remove(profile_id: int, user=Depends(require_roles('ELDER', 'ADMIN')), db: Session = Depends(get_db)):
    profile = get_profile(db, user, profile_id, lock=True)
    profile.deleted = 1
    db.commit()
    return ok()
