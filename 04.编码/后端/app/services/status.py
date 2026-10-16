"""Descriptive measurements using approved thresholds and prior valid samples."""
import math
from datetime import timedelta
from sqlalchemy import select
from app.core.database import now
from app.core.errors import APIError
from app.models import HealthRecord
from app.services.thresholds import INDICATORS, config_value, evaluate
from app.services.personal_threshold import effective_rule, evidence_for_record, evidence_data
from app.services.health_records import active_records
from app.services.serializers import record_values, dt
from app.services.recovery import bounded_number

LEVEL_TEXT = ['参考范围内', '轻度异常', '较高异常', '高风险异常']


def fluctuation_threshold(db):
    raw = config_value(db, 'FLUCTUATION_THRESHOLD')
    if raw is None:
        return None
    try:
        value = float(raw)
        if math.isfinite(value) and 0 < value <= 10:
            return value
    except (ValueError, TypeError):
        pass
    raise APIError(5001, '波动提醒参数无效，请联系管理员核验配置', 503)


def prior_baseline(db, profile_id, metric_type, latest, column):
    # Exclude this reading and all later measurements; never dilute a deviation.
    rows = list(db.scalars(select(column).where(active_records(),
        HealthRecord.profile_id == profile_id, HealthRecord.type == metric_type,
        HealthRecord.measured_at >= latest.measured_at-timedelta(days=7),
        (HealthRecord.measured_at < latest.measured_at) |
        ((HealthRecord.measured_at == latest.measured_at) & (HealthRecord.id < latest.id)),
        column.is_not(None)).order_by(HealthRecord.measured_at.desc(), HealthRecord.id.desc()).limit(500)))
    return (sum(map(float, rows))/len(rows) if len(rows) >= 2 else None), len(rows)


def personal_status(db, profile):
    cutoff = now()-timedelta(hours=bounded_number(db, 'care_health_data_fresh_hours', 72, 1, 8760))
    fluctuation_limit = fluctuation_threshold(db)
    items = []
    for metric_type, meta in INDICATORS.items():
        latest = db.scalar(select(HealthRecord).where(active_records(), HealthRecord.profile_id == profile.id,
            HealthRecord.type == metric_type, HealthRecord.measured_at <= now())
            .order_by(HealthRecord.measured_at.desc(), HealthRecord.id.desc()).limit(1))
        rules = [effective_rule(db, profile.id, key) for key in meta['keys']]
        base = {'type': metric_type, 'name': meta['name'], 'unit': meta['unit'], 'latest': None,
            'measured_at': None, 'is_abnormal': None, 'risk_level': None, 'data_status': 'NO_DATA',
            'normal_ranges': [{'key': rule['indicator'], 'range': rule['level0_range'],
                'source': rule['source'], 'version_id': rule['version_id'], 'enabled': rule['enabled']} for rule in rules],
            'baseline_mean': None, 'baseline_count': 0, 'baseline_components': [],
            'fluctuation_ratio': None, 'fluctuation_flag': None, 'fluctuation_enabled': fluctuation_limit is not None,
            'fluctuation_threshold': fluctuation_limit, 'judgement': '未记录', 'recorded_assessment': None}
        if latest is None:
            items.append(base)
            continue
        fresh = latest.measured_at >= cutoff
        values = [latest.val1, latest.val2]
        enabled = [evaluate(rule['raw'], float(value)) for rule, value in zip(rules, values) if rule['enabled']]
        risk = max(enabled) if enabled else None
        components = []
        for index, key in enumerate(meta['keys']):
            mean, count = prior_baseline(db, profile.id, metric_type, latest, getattr(HealthRecord, f'val{index+1}'))
            ratio = (float(values[index])-mean)/mean if mean is not None and mean > 0 else None
            flag = abs(ratio) >= fluctuation_limit if fresh and ratio is not None and fluctuation_limit is not None else None
            components.append({'key': key, 'mean': round(mean, 2) if mean is not None else None,
                'count': count, 'ratio': round(ratio, 3) if ratio is not None else None, 'flag': flag})
        available = [row['flag'] for row in components if row['flag'] is not None]
        flag = any(available) if available else None
        judgement = '数据待更新' if not fresh else ('检测已停用' if risk is None else
            LEVEL_TEXT[risk] if risk else '需关注（波动）' if flag else '参考范围内')
        base.update(latest=record_values(latest), record_id=latest.id, measured_at=dt(latest.measured_at),
            is_abnormal=bool(risk) if fresh and risk is not None else None, risk_level=risk if fresh else None,
            data_status='FRESH' if fresh else 'STALE', judgement=judgement,
            baseline_mean=components[0]['mean'], baseline_count=components[0]['count'],
            baseline_components=components, fluctuation_ratio=components[0]['ratio'], fluctuation_flag=flag,
            recorded_assessment=evidence_data(evidence_for_record(db, latest.id)))
        items.append(base)
    return items
