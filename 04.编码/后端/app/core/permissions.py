from fastapi import Depends
import json
from sqlalchemy import select
from app.models import ElderProfile, FamilyBind, CareRelation, SysConfig
from .errors import APIError
from .security import get_current_user


def require_roles(*roles):
    def dependency(user=Depends(get_current_user)):
        if user.role not in roles:
            raise APIError(1002, '无权限执行此操作', 403)
        return user
    return dependency


def require_health_consent(db, user):
    row = db.scalar(select(SysConfig).where(SysConfig.config_key == f'privacy_consent:{user.id}', SysConfig.enabled == 1))
    try:
        accepted = json.loads(row.config_value).get('accepted') is True if row else False
    except (ValueError, TypeError, AttributeError):
        accepted = False
    if not accepted:
        raise APIError(1002, '请先在个人中心确认健康数据使用授权', 403)


def profile_scope(user, db=None):
    if db is not None:
        require_health_consent(db, user)
    conditions = [ElderProfile.deleted == 0]
    if user.role == 'ELDER':
        conditions.append(ElderProfile.user_id == user.id)
    elif user.role == 'FAMILY':
        conditions.append(ElderProfile.id.in_(select(FamilyBind.profile_id).where(FamilyBind.family_user_id == user.id, FamilyBind.status == 'APPROVED')))
    elif user.role == 'CARE':
        conditions.append(ElderProfile.id.in_(select(CareRelation.profile_id).where(CareRelation.care_user_id == user.id, CareRelation.status == 1)))
    elif user.role != 'ADMIN':
        raise APIError(1002, '无权限', 403)
    return conditions


def visible_profile_ids(db, user):
    return list(db.scalars(select(ElderProfile.id).where(*profile_scope(user, db))))


def get_profile(db, user, profile_id, lock=False):
    require_health_consent(db, user)
    query = select(ElderProfile).where(ElderProfile.id == profile_id, ElderProfile.deleted == 0)
    if lock:
        query = query.with_for_update()
    profile = db.scalar(query)
    if not profile:
        raise APIError(2002, '档案不存在', 404)
    if user.role == 'ADMIN' or (user.role == 'ELDER' and profile.user_id == user.id):
        return profile
    if user.role == 'FAMILY':
        query = select(FamilyBind.id).where(FamilyBind.family_user_id == user.id, FamilyBind.profile_id == profile_id, FamilyBind.status == 'APPROVED')
    elif user.role == 'CARE':
        query = select(CareRelation.id).where(CareRelation.care_user_id == user.id, CareRelation.profile_id == profile_id, CareRelation.status == 1)
    else:
        query = None
    relation = db.scalar(query.with_for_update() if lock else query) if query is not None else None
    if relation:
        return profile
    raise APIError(1002, '无权限访问该档案', 403)
