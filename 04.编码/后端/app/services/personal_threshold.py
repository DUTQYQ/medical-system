"""Resolve individual overrides; numeric rules remain in sys_config."""
import json
from sqlalchemy import select
from app.core.errors import APIError
from app.models import SysConfig
from app.models.personal_threshold import ProfileThresholdVersion, HealthAssessment
from app.services.thresholds import INDICATORS, evaluate, threshold_data, parse_threshold
from app.services.serializers import dt

RULE_KEYS = {key for item in INDICATORS.values() for key in item['keys']}


def effective_rule(db, profile_id, key, *, lock=False):
    if key not in RULE_KEYS:
        raise APIError(2001, '不支持的阈值指标')
    query = select(ProfileThresholdVersion).where(
        ProfileThresholdVersion.profile_id == profile_id,
        ProfileThresholdVersion.indicator == key,
        ProfileThresholdVersion.status == 'APPROVED').order_by(ProfileThresholdVersion.id.desc()).limit(1)
    # MySQL REPEATABLE READ ordinary SELECT may see a snapshot established by
    # authentication before waiting for the profile lock. Measurements require
    # a current locking read of the approved version and its immutable value.
    version = db.scalar(query.with_for_update().execution_options(populate_existing=True) if lock else query)
    personal = bool(version and not version.restore_default)
    config_query = select(SysConfig).where(SysConfig.id == version.config_id) if personal else select(SysConfig).where(SysConfig.config_key == key)
    row = db.scalar(config_query.with_for_update().execution_options(populate_existing=True) if lock else config_query)
    if row is None:
        raise APIError(5001, '有效阈值未配置：' + key, 503)
    try:
        parse_threshold(row.config_value)
    except (ValueError, TypeError, KeyError):
        raise APIError(5001, '有效阈值配置无效：' + key, 503)
    result = threshold_data(row)
    result.update(indicator=key, source='PERSONAL' if personal else 'DEFAULT',
                  version_id=version.id if version else None, raw=row.config_value,
                  config_updated_at=dt(row.update_time))
    meta = next(item for item in INDICATORS.values() if key in item['keys'])
    result.update(indicator_name=meta['name'] + (' 收缩压' if key.endswith('SYSTOLIC') else ' 舒张压' if key.endswith('DIASTOLIC') else ''), unit=meta['unit'])
    return result


def assess(db, profile_id, metric_type, val1, val2=None):
    if metric_type not in INDICATORS:
        raise APIError(2001, '不支持的指标类型')
    rules, levels = {}, []
    for key, value in zip(INDICATORS[metric_type]['keys'], [val1, val2]):
        rule = effective_rule(db, profile_id, key, lock=True)
        rules[key] = rule
        if rule['enabled']:
            levels.append(evaluate(rule['raw'], float(value)))
    return max(levels, default=0), rules


def evidence_data(evidence):
    if not evidence:
        return None
    return {'assessment_id': evidence.id, 'risk_level': evidence.risk_level,
            'thresholds': evidence.thresholds, 'values': evidence.values,
            'assessed_at': dt(evidence.create_time)}


def evidence_for_record(db, record_id):
    return db.scalar(select(HealthAssessment).where(HealthAssessment.record_id == record_id))


def validate_rule(raw):
    try:
        parse_threshold(raw)
        if len(raw) > 500:
            raise ValueError('too long')
        # Ensure the full permissible outer domain is covered. Internal decimal
        # gaps follow the existing adjacent-risk rule, preserving compatibility.
        evaluate(raw, 0)
        evaluate(raw, 99999999.99)
    except (ValueError, TypeError, KeyError, APIError):
        raise APIError(2001, '阈值须包含四个等级，范围不得倒置或交叠，并覆盖低值和高值区间')
