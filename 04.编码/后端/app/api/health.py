import json
import math
from datetime import timedelta
from fastapi import APIRouter, BackgroundTasks, Depends, Query
from sqlalchemy import select, func, update
from sqlalchemy.orm import Session
from app.core.database import get_db, now
from app.core.security import get_current_user
from app.core.permissions import get_profile, require_roles
from app.core.errors import APIError, ok
from app.models import HealthRecord, HealthWarning, SysConfig
from app.services.serializers import record_data, value_text
from app.services.thresholds import validate_values, risk_level, INDICATORS, config_value, range_parts
from app.services.alerts import create_warning, generate_summary
from .schemas import HealthInput

router = APIRouter(prefix='/health', tags=['健康指标'])


def trend_data(db, profile_id, type, days):
    if type not in INDICATORS:
        raise APIError(2001, '不支持的指标类型')
    records = list(db.scalars(select(HealthRecord).where(HealthRecord.profile_id == profile_id, HealthRecord.type == type,
                    HealthRecord.measured_at >= now() - timedelta(days=days)).order_by(HealthRecord.measured_at, HealthRecord.id)))
    names = {'BLOOD_PRESSURE': ['收缩压', '舒张压'], 'SLEEP': ['睡眠时长', '质量']}.get(type, [INDICATORS[type]['name']])
    series = [{'name': name, 'values': [float(getattr(record, f'val{i+1}')) if getattr(record, f'val{i+1}') is not None else None for record in records]} for i, name in enumerate(names)]
    raw = config_value(db, INDICATORS[type]['keys'][0])
    normal = json.loads(raw).get('level0') if raw else None
    normal_range = {'expression': normal}
    if normal:
        pieces = range_parts(normal)
        normal_range['min'] = min((piece[0] for piece in pieces if math.isfinite(piece[0])), default=None)
        normal_range['max'] = max((piece[1] for piece in pieces if math.isfinite(piece[1])), default=None)
    return {'dates': [record.measured_at.strftime('%Y-%m-%d %H:%M:%S') for record in records], 'series': series,
            'normal_range': normal_range, 'abnormal_points': [{'date': record.measured_at.strftime('%Y-%m-%d %H:%M:%S'), 'value': float(record.val1), 'level': risk_level(db, type, record.val1, record.val2)} for record in records if record.is_abnormal]}


@router.post('/records')
def create(body: HealthInput, tasks: BackgroundTasks, user=Depends(require_roles('ELDER', 'FAMILY', 'CARE')), db: Session = Depends(get_db)):
    profile = get_profile(db, user, body.profile_id, lock=True)
    val1, val2 = validate_values(db, body.type, body.values)
    level = risk_level(db, body.type, val1, val2)
    record = HealthRecord(profile_id=profile.id, type=body.type, val1=val1, val2=val2, measured_at=body.measured_at,
                          remark=body.remark, recorder_id=user.id, is_abnormal=int(level > 0))
    db.add(record)
    db.flush()
    warning = create_warning(db, profile, record_id=record.id, type=body.type, value_text=value_text(body.type, val1, val2), level=level) if level else None
    db.commit()
    if warning and warning.summary_status == 'PENDING':
        tasks.add_task(generate_summary, warning.id)
    return ok({'record_id': record.id, 'is_abnormal': bool(level), 'risk_level': level, 'warning_id': warning.id if warning else None})


@router.get('/records')
def records(profile_id: int, type: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), user=Depends(get_current_user), db: Session = Depends(get_db)):
    get_profile(db, user, profile_id)
    criteria = [HealthRecord.profile_id == profile_id]
    if type:
        if type not in INDICATORS:
            raise APIError(2001, '不支持的指标类型')
        criteria.append(HealthRecord.type == type)
    total = db.scalar(select(func.count()).select_from(HealthRecord).where(*criteria))
    rows = db.scalars(select(HealthRecord).where(*criteria).order_by(HealthRecord.measured_at.desc(), HealthRecord.id.desc()).offset((page - 1) * page_size).limit(page_size))
    return ok({'list': [record_data(row) for row in rows], 'total': total, 'page': page, 'page_size': page_size})


@router.delete('/records/{record_id}')
def remove(record_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.get(HealthRecord, record_id)
    if not record:
        raise APIError(2002, '记录不存在', 404)
    get_profile(db, user, record.profile_id, lock=True)
    # Keep the alert and handling audit after correcting/deleting a measurement.
    db.execute(update(HealthWarning).where(HealthWarning.record_id == record_id).values(record_id=None))
    db.delete(record)
    db.commit()
    return ok()


@router.get('/trend')
def trend(profile_id: int, type: str, days: int = Query(30, ge=1, le=365), user=Depends(get_current_user), db: Session = Depends(get_db)):
    get_profile(db, user, profile_id)
    return ok(trend_data(db, profile_id, type, days))
