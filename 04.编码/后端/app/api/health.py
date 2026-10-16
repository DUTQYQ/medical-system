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
from app.models import HealthRecord, HealthWarning, SysConfig, HealthRecordVoid, User
from app.services.serializers import record_data, value_text
from app.services.thresholds import validate_values, risk_level, INDICATORS, config_value, range_parts
from app.services.alerts import create_warning, generate_summary
from app.models.personal_threshold import HealthAssessment
from app.services.personal_threshold import assess, effective_rule, evidence_data
from .schemas import HealthInput, RecordVoidInput
from app.services.health_records import active_records, void_data

router = APIRouter(prefix='/health', tags=['健康指标'])


@router.get('/status')
def status(profile_id: int = Query(gt=0), user=Depends(get_current_user), db: Session = Depends(get_db)):
    from app.services.status import personal_status
    return ok(personal_status(db, get_profile(db, user, profile_id)))


def trend_data(db, profile_id, type, days):
    if type not in INDICATORS:
        raise APIError(2001, '不支持的指标类型')
    records = list(db.scalars(select(HealthRecord).where(active_records(), HealthRecord.profile_id == profile_id, HealthRecord.type == type,
                    HealthRecord.measured_at >= now() - timedelta(days=days)).order_by(HealthRecord.measured_at, HealthRecord.id)))
    names = {'BLOOD_PRESSURE': ['收缩压', '舒张压'], 'SLEEP': ['睡眠时长', '质量']}.get(type, [INDICATORS[type]['name']])
    series = [{'name': name, 'values': [float(getattr(record, f'val{i+1}')) if getattr(record, f'val{i+1}') is not None else None for record in records]} for i, name in enumerate(names)]
    rule = effective_rule(db, profile_id, INDICATORS[type]['keys'][0])
    raw = rule['raw']
    normal = json.loads(raw).get('level0') if raw else None
    normal_range = {'expression': normal}
    if normal:
        pieces = range_parts(normal)
        normal_range['min'] = min((piece[0] for piece in pieces if math.isfinite(piece[0])), default=None)
        normal_range['max'] = max((piece[1] for piece in pieces if math.isfinite(piece[1])), default=None)
    assessments = {row.record_id: row for row in db.scalars(select(HealthAssessment).where(HealthAssessment.record_id.in_([r.id for r in records])))}
    legacy_levels = {row.record_id: row.level for row in db.scalars(select(HealthWarning).where(HealthWarning.record_id.in_([r.id for r in records])).order_by(HealthWarning.id))}
    return {'dates': [record.measured_at.strftime('%Y-%m-%d %H:%M:%S') for record in records], 'series': series,
            'normal_range': normal_range, 'threshold_source': rule['source'], 'threshold_version_id': rule['version_id'],
            'current_thresholds': [effective_rule(db, profile_id, key) for key in INDICATORS[type]['keys']],
            'assessments': [evidence_data(assessments.get(record.id)) for record in records],
            'abnormal_points': [{'date': record.measured_at.strftime('%Y-%m-%d %H:%M:%S'), 'value': float(record.val1),
                'level': assessments[record.id].risk_level if record.id in assessments else legacy_levels.get(record.id),
                'assessment_source': 'SNAPSHOT' if record.id in assessments else 'LEGACY'} for record in records if record.is_abnormal]}


@router.post('/records')
def create(body: HealthInput, tasks: BackgroundTasks, user=Depends(require_roles('ELDER', 'FAMILY', 'CARE')), db: Session = Depends(get_db)):
    profile = get_profile(db, user, body.profile_id, lock=True)
    val1, val2 = validate_values(db, body.type, body.values)
    level, rules = assess(db, profile.id, body.type, val1, val2)
    record = HealthRecord(profile_id=profile.id, type=body.type, val1=val1, val2=val2, measured_at=body.measured_at,
                          remark=body.remark, recorder_id=user.id, is_abnormal=int(level > 0))
    db.add(record)
    db.flush()
    warning = create_warning(db, profile, record_id=record.id, type=body.type, value_text=value_text(body.type, val1, val2), level=level) if level else None
    assessment = HealthAssessment(profile_id=profile.id, record_id=record.id,
        warning_id=warning.id if warning else None, risk_level=level, thresholds=rules, values=body.values)
    db.add(assessment)
    db.commit()
    if warning and warning.summary_status == 'PENDING':
        tasks.add_task(generate_summary, warning.id)
    return ok({'record_id': record.id, 'is_abnormal': bool(level), 'risk_level': level,
               'warning_id': warning.id if warning else None, 'assessment': evidence_data(assessment)})


@router.get('/records')
def records(profile_id: int, type: str | None = None, page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), include_voided: bool = False, user=Depends(get_current_user), db: Session = Depends(get_db)):
    get_profile(db, user, profile_id)
    criteria = [HealthRecord.profile_id == profile_id]
    if not include_voided:
        criteria.append(active_records())
    if type:
        if type not in INDICATORS:
            raise APIError(2001, '不支持的指标类型')
        criteria.append(HealthRecord.type == type)
    total = db.scalar(select(func.count()).select_from(HealthRecord).where(*criteria))
    rows = db.scalars(select(HealthRecord).where(*criteria).order_by(HealthRecord.measured_at.desc(), HealthRecord.id.desc()).offset((page - 1) * page_size).limit(page_size))
    result = list(rows)
    assessments = {row.record_id: row for row in db.scalars(select(HealthAssessment).where(HealthAssessment.record_id.in_([r.id for r in result])))}
    voids = {row.record_id: row for row in db.scalars(select(HealthRecordVoid).where(HealthRecordVoid.record_id.in_([r.id for r in result])))}
    return ok({'list': [{**record_data(row), 'assessment': evidence_data(assessments.get(row.id)),
        'entered_by': db.get(User, row.recorder_id).name if row.recorder_id and db.get(User, row.recorder_id) else None,
        'is_voided': row.id in voids, 'void_audit': void_data(db, voids.get(row.id)),
        'can_void': row.id not in voids and (user.role == 'ADMIN' or row.recorder_id == user.id)} for row in result],
        'total': total, 'page': page, 'page_size': page_size})


@router.delete('/records/{record_id}')
def remove(record_id: int, body: RecordVoidInput, user=Depends(get_current_user), db: Session = Depends(get_db)):
    record = db.get(HealthRecord, record_id)
    if not record:
        raise APIError(2002, '记录不存在', 404)
    get_profile(db, user, record.profile_id, lock=True)
    record = db.scalar(select(HealthRecord).where(HealthRecord.id == record_id).with_for_update().execution_options(populate_existing=True))
    if user.role != 'ADMIN' and record.recorder_id != user.id:
        raise APIError(1002, '只能作废本人录入的指标；其他记录请联系管理员核验', 403)
    audit = db.scalar(select(HealthRecordVoid).where(HealthRecordVoid.record_id == record_id).with_for_update())
    if audit is None:
        audit = HealthRecordVoid(record_id=record_id, voided_by=user.id, reason=body.reason)
        db.add(audit)
    db.commit()
    return ok({'record_id': record_id, 'is_voided': True, 'void_audit': void_data(db, audit)}, message='记录已作废，原始测量、预警和处理记录保留')


@router.get('/trend')
def trend(profile_id: int, type: str, days: int = Query(30, ge=1, le=365), user=Depends(get_current_user), db: Session = Depends(get_db)):
    get_profile(db, user, profile_id)
    return ok(trend_data(db, profile_id, type, days))
