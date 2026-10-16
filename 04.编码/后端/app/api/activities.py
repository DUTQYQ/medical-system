"""Activity suggestions; scheduled activities remain under /services."""
import json
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.core.permissions import get_profile, require_roles
from app.core.errors import APIError, ok
from app.models import ActivityTemplate
from app.services.serializers import activity_data
from app.services.recommend import recommend_activities
from .schemas import ActivityInput

router = APIRouter(prefix='/activities', tags=['活动建议库'])


@router.get('')
def list_activities(user=Depends(get_current_user), db: Session = Depends(get_db)):
    query = select(ActivityTemplate).order_by(ActivityTemplate.id)
    if user.role != 'ADMIN':
        query = query.where(ActivityTemplate.enabled == 1)
    return ok([activity_data(row) for row in db.scalars(query)])


@router.get('/recommend')
def recommend(profile_id: int = Query(gt=0), user=Depends(get_current_user), db: Session = Depends(get_db)):
    return ok(recommend_activities(db, get_profile(db, user, profile_id)))


def save(db, body, activity_id=None):
    row = db.scalar(select(ActivityTemplate).where(ActivityTemplate.id == activity_id).with_for_update()
        .execution_options(populate_existing=True)) if activity_id else None
    if activity_id and row is None:
        raise APIError(2002, '活动建议不存在', 404)
    if db.scalar(select(ActivityTemplate.id).where(ActivityTemplate.code == body.code,
        ActivityTemplate.id != activity_id if activity_id else True)):
        raise APIError(2001, '活动编码已存在', 409)
    rules = json.dumps(body.rules.model_dump(exclude_none=True, exclude_defaults=True), ensure_ascii=False)
    if len(rules) > 1000:
        raise APIError(2001, '推荐规则过长，请减少标签数量')
    if row is None:
        row = ActivityTemplate(code=body.code, name=body.name)
        db.add(row)
    for name, value in body.model_dump(exclude={'rules'}).items():
        setattr(row, name, int(value) if name == 'enabled' else value)
    row.rules = rules
    db.commit()
    return ok(activity_data(row))


@router.post('')
def create_activity(body: ActivityInput, user=Depends(require_roles('ADMIN')), db: Session = Depends(get_db)):
    return save(db, body)


@router.put('/{activity_id}')
def update_activity(activity_id: int, body: ActivityInput, user=Depends(require_roles('ADMIN')), db: Session = Depends(get_db)):
    return save(db, body, activity_id)


@router.delete('/{activity_id}')
def delete_activity(activity_id: int, user=Depends(require_roles('ADMIN')), db: Session = Depends(get_db)):
    row = db.scalar(select(ActivityTemplate).where(ActivityTemplate.id == activity_id).with_for_update())
    if row is None:
        raise APIError(2002, '活动建议不存在', 404)
    row.enabled = 0
    db.commit()
    return ok(message='活动建议已停用；不会删除已经发布的院内活动或报名记录')
