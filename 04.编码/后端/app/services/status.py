"""个人健康判断：个性化阈值 + 个人基线波动。"""
from datetime import timedelta
from sqlalchemy import select
from app.core.database import now
from app.models import HealthRecord
from app.services.thresholds import INDICATORS, effective_threshold, personal_level, config_value
from app.services.serializers import record_values, dt

LEVEL_TEXT = ['健康', '轻度异常', '较高异常', '高风险异常']


def fluctuation_threshold(db):
    raw = config_value(db, 'FLUCTUATION_THRESHOLD', '0.2')
    try:
        return float(raw)
    except (ValueError, TypeError):
        return 0.2


def baseline(db, profile_id, type, days=7):
    rows = list(db.scalars(select(HealthRecord.val1).where(
        HealthRecord.profile_id == profile_id, HealthRecord.type == type,
        HealthRecord.measured_at >= now() - timedelta(days=days), HealthRecord.val1.isnot(None))))
    if len(rows) < 2:
        return None, len(rows)
    values = [float(v) for v in rows]
    return sum(values) / len(values), len(values)


def personal_status(db, profile):
    """返回每个指标的个性化健康判断，供「个人健康判断」页与推荐引擎使用。"""
    items = []
    for type in INDICATORS:
        latest = db.scalar(select(HealthRecord).where(
            HealthRecord.profile_id == profile.id, HealthRecord.type == type)
            .order_by(HealthRecord.measured_at.desc(), HealthRecord.id.desc()).limit(1))
        normal_ranges = []
        for key in INDICATORS[type]['keys']:
            eff = effective_threshold(db, profile, key)
            normal_ranges.append({'key': key, 'range': eff.get('level0', '') if eff else ''})

        if latest is None or latest.val1 is None:
            items.append({'type': type, 'name': INDICATORS[type]['name'], 'unit': INDICATORS[type]['unit'],
                          'latest': None, 'measured_at': None, 'is_abnormal': False, 'risk_level': 0,
                          'normal_ranges': normal_ranges, 'baseline_mean': None, 'baseline_count': 0,
                          'fluctuation_ratio': None, 'fluctuation_flag': False, 'judgement': '未记录'})
            continue

        val1 = float(latest.val1)
        val2 = float(latest.val2) if latest.val2 is not None else None
        risk = personal_level(db, profile, type, val1, val2)
        base, count = baseline(db, profile.id, type)
        ratio = (val1 - base) / base if base else None
        flag = ratio is not None and abs(ratio) >= fluctuation_threshold(db)
        judgement = LEVEL_TEXT[risk] if risk else ('需关注（波动）' if flag else '健康')
        items.append({'type': type, 'name': INDICATORS[type]['name'], 'unit': INDICATORS[type]['unit'],
                      'latest': record_values(latest), 'measured_at': dt(latest.measured_at),
                      'is_abnormal': bool(latest.is_abnormal), 'risk_level': risk,
                      'normal_ranges': normal_ranges, 'baseline_mean': round(base, 2) if base else None,
                      'baseline_count': count, 'fluctuation_ratio': round(ratio, 3) if ratio is not None else None,
                      'fluctuation_flag': bool(flag), 'judgement': judgement})
    return items
