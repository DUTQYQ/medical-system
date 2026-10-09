from fastapi import APIRouter, Depends, Query
from datetime import datetime
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.permissions import require_roles, visible_profile_ids, get_profile
from app.core.errors import APIError, ok
from app.models import ElderProfile, HealthRecord, HealthWarning, WarningHandleRecord
from app.services.serializers import profile_data, record_data, age, dt, value_text
from .alerts import warning_data, handle_data

router = APIRouter(prefix='/care', tags=['护工'])


def care_data(db, profile):
    records = list(db.scalars(select(HealthRecord).where(HealthRecord.profile_id == profile.id).order_by(HealthRecord.measured_at.desc(), HealthRecord.id.desc())))
    latest = {}
    for record in records:
        latest.setdefault(record.type, record)
    warnings = list(db.scalars(select(HealthWarning).where(HealthWarning.profile_id == profile.id, HealthWarning.status.in_(['PENDING', 'PROCESSING']))))
    risk = max([row.level for row in warnings], default=0)
    bp, sugar, sleep = latest.get('BLOOD_PRESSURE'), latest.get('BLOOD_SUGAR'), latest.get('SLEEP')
    return {'profile_id': profile.id, 'elder_name': profile.name, 'age': age(profile.birthday), 'gender': profile.gender, 'address': None,
            'status': 'ABNORMAL' if risk >= 2 else ('WATCH' if risk else 'NORMAL'), 'latest_bp': value_text(bp.type, bp.val1, bp.val2) if bp else None,
            'latest_sugar': float(sugar.val1) if sugar else None, 'sleep_hours': float(sleep.val1) if sleep else None,
            'pending_warnings': len(warnings), 'updated_at': dt(max([profile.update_time] + [row.update_time for row in records]))}


@router.get('/elders')
def elders(status: str | None = None, start_at: datetime | None = None, end_at: datetime | None = None,
           user=Depends(require_roles('CARE')), db: Session = Depends(get_db)):
    if status and status not in ('NORMAL', 'WATCH', 'ABNORMAL'):
        raise APIError(2001, '老人状态无效')
    if (start_at and start_at.tzinfo) or (end_at and end_at.tzinfo):
        raise APIError(2001, '筛选时间须采用中国本地时间，不带时区后缀')
    if start_at and end_at and start_at > end_at:
        raise APIError(2001, '开始时间不能晚于结束时间')
    criteria = [ElderProfile.id.in_(visible_profile_ids(db, user))]
    if start_at or end_at:
        measured = select(HealthRecord.profile_id)
        if start_at:
            measured = measured.where(HealthRecord.measured_at >= start_at)
        if end_at:
            measured = measured.where(HealthRecord.measured_at <= end_at)
        criteria.append(ElderProfile.id.in_(measured))
    rows = [care_data(db, profile) for profile in db.scalars(select(ElderProfile).where(*criteria))]
    if status:
        rows = [row for row in rows if row['status'] == status]
    rows.sort(key=lambda row: ({'ABNORMAL': 0, 'WATCH': 1, 'NORMAL': 2}[row['status']], row['profile_id']))
    return ok(rows)


@router.get('/elders/{profile_id}')
def detail(profile_id: int, user=Depends(require_roles('CARE')), db: Session = Depends(get_db)):
    profile = get_profile(db, user, profile_id)
    records = db.scalars(select(HealthRecord).where(HealthRecord.profile_id == profile_id).order_by(HealthRecord.measured_at.desc()).limit(20))
    warnings = db.scalars(select(HealthWarning).where(HealthWarning.profile_id == profile_id).order_by(HealthWarning.id.desc()).limit(20))
    return ok({'profile': profile_data(profile), 'latest_records': [record_data(row) for row in records], 'alerts': [warning_data(db, user, row) for row in warnings]})


@router.get('/handles')
def handles(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user=Depends(require_roles('CARE')), db: Session = Depends(get_db)):
    criteria = [WarningHandleRecord.handler_id == user.id, WarningHandleRecord.warning_id.in_(select(HealthWarning.id).where(HealthWarning.profile_id.in_(visible_profile_ids(db, user))))]
    total = db.scalar(select(func.count()).select_from(WarningHandleRecord).where(*criteria))
    rows = db.scalars(select(WarningHandleRecord).where(*criteria).order_by(WarningHandleRecord.id.desc()).offset((page - 1) * page_size).limit(page_size))
    return ok({'list': [handle_data(db, row) for row in rows], 'total': total, 'page': page, 'page_size': page_size})
