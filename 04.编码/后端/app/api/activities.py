import json
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import get_profile, require_roles
from app.core.errors import APIError, ok
from app.models import Activity
from app.services.serializers import activity_data
from app.services.recommend import recommend_activities
from .schemas import ActivityInput

router = APIRouter(prefix='/activities', tags=['活动推荐'])


@router.get('')
def list_activities(user=Depends(get_current_user), db: Session = Depends(get_db)):
    return ok([activity_data(row) for row in db.scalars(select(Activity).order_by(Activity.id))])


@router.get('/recommend')
def recommend(profile_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    profile = get_profile(db, user, profile_id)
    return ok(recommend_activities(db, profile))


@router.post('')
def create_activity(body: ActivityInput, user=Depends(require_roles('ADMIN')), db: Session = Depends(get_db)):
    if db.scalar(select(Activity.id).where(Activity.code == body.code)):
        raise APIError(2001, '活动编码已存在', 409)
    rules = json.dumps(body.rules, ensure_ascii=False)
    if len(rules) > 1000:
        raise APIError(2001, '规则配置超过 1000 字符')
    row = Activity(code=body.code, name=body.name, category=body.category, intensity=body.intensity,
                   description=body.description, benefits=body.benefits, duration_hint=body.duration_hint,
                   rules=rules, contraindications=body.contraindications, enabled=int(body.enabled))
    db.add(row)
    db.commit()
    return ok(activity_data(row))


@router.put('/{activity_id}')
def update_activity(activity_id: int, body: ActivityInput, user=Depends(require_roles('ADMIN')), db: Session = Depends(get_db)):
    row = db.get(Activity, activity_id)
    if not row:
        raise APIError(2002, '活动不存在', 404)
    if db.scalar(select(Activity.id).where(Activity.code == body.code, Activity.id != activity_id)):
        raise APIError(2001, '活动编码已存在', 409)
    rules = json.dumps(body.rules, ensure_ascii=False)
    if len(rules) > 1000:
        raise APIError(2001, '规则配置超过 1000 字符')
    for name, value in body.model_dump().items():
        setattr(row, name, rules if name == 'rules' else (int(value) if name == 'enabled' else value))
    db.commit()
    return ok(activity_data(row))


@router.delete('/{activity_id}')
def delete_activity(activity_id: int, user=Depends(require_roles('ADMIN')), db: Session = Depends(get_db)):
    row = db.get(Activity, activity_id)
    if not row:
        raise APIError(2002, '活动不存在', 404)
    db.delete(row)
    db.commit()
    return ok()
