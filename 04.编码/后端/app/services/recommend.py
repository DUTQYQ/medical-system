"""Validated, deterministic suggestions; never promises medical fitness."""
import json
from sqlalchemy import select
from pydantic import ValidationError
from app.models import ActivityTemplate, HealthWarning, HealthRecordVoid
from app.api.schemas import ActivityRules
from app.core.database import now
from app.services.serializers import age
from app.services.status import personal_status

SEASON_TEXT = {'spring': '春季', 'summer': '夏季', 'autumn': '秋季', 'winter': '冬季'}


def current_season():
    month = now().month
    return 'spring' if 3 <= month <= 5 else 'summer' if 6 <= month <= 8 else 'autumn' if 9 <= month <= 11 else 'winter'


def _match(condition, ctx):
    """All configured constraints in one group must hold; None means unknown."""
    results, reasons = [], []
    for field, compare, text in [('min_age', lambda a, b: a >= b, '年龄达到最低要求'),
                                 ('max_age', lambda a, b: a <= b, '年龄未超过上限')]:
        if field in condition:
            results.append(None if ctx['age'] is None else compare(ctx['age'], condition[field]))
            reasons.append(text)
    if condition.get('chronic_in'):
        results.append(None if not ctx['tags_known'] else bool(set(ctx['chronic_tags']) & set(condition['chronic_in'])))
        reasons.append('匹配已记录的慢病标签（需工作人员核实）')
    if condition.get('seasons_in'):
        results.append(ctx['season'] in condition['seasons_in'])
        reasons.append('当前季节符合设置')
    if condition.get('seasons_not_in'):
        results.append(ctx['season'] not in condition['seasons_not_in'])
        reasons.append('当前季节属于排除设置之外')
    if not results:
        return None, []
    if False in results:
        return False, []
    if None in results:
        return None, ['匹配所需的档案信息不完整']
    return True, reasons


def recommend_activities(db, profile):
    status = personal_status(db, profile)
    try:
        tags = json.loads(profile.chronic_tags or '[]')
        tags_known = isinstance(tags, list) and all(isinstance(tag, str) for tag in tags)
    except (ValueError, TypeError):
        tags, tags_known = [], False
    ctx = {'age': age(profile.birthday), 'chronic_tags': tags if tags_known else [],
           'tags_known': tags_known and profile.chronic_tags is not None, 'season': current_season()}
    fresh = [row for row in status if row['data_status'] == 'FRESH' and row['risk_level'] is not None]
    pending = list(db.scalars(select(HealthWarning.level).where(HealthWarning.profile_id == profile.id,
        HealthWarning.status.in_(['PENDING', 'PROCESSING']),
        (HealthWarning.record_id.is_(None)) | (HealthWarning.record_id.not_in(select(HealthRecordVoid.record_id))))))
    max_risk = max([row['risk_level'] for row in fresh] + pending, default=None)
    result = []
    for row in db.scalars(select(ActivityTemplate).where(ActivityTemplate.enabled == 1).order_by(ActivityTemplate.id)):
        try:
            rules = ActivityRules.model_validate(json.loads(row.rules or '{}')).model_dump(exclude_none=True, exclude_defaults=True)
            invalid = False
        except (ValueError, TypeError, ValidationError):
            rules, invalid = {}, True
        avoid, avoid_reasons = _match(rules.get('avoid', {}), ctx)
        suitable, suitable_reasons = _match(rules.get('suitable', {}), ctx)
        caution = rules.get('caution', {}).get('max_risk_level')
        if invalid:
            suitability, score, reasons = '需确认', 10, ['推荐规则无效，请联系管理员修复']
        elif avoid is True:
            suitability, score, reasons = '不建议', 0, avoid_reasons
        elif max_risk == 3:
            suitability, score, reasons = '暂缓参与', 5, ['存在高风险记录或未结预警，请先由现场工作人员核验']
        elif not fresh:
            suitability, score, reasons = '需确认', 20, ['缺少近期有效健康记录，不能据此判断活动适宜性']
        elif max_risk is not None and (max_risk > 0 or (caution is not None and max_risk >= caution)):
            suitability, score, reasons = '需谨慎', 40, ['当前记录或待处理预警需要关注，请先联系工作人员']
        elif rules.get('suitable') and suitable is not True:
            suitability, score, reasons = '需确认', 30, suitable_reasons or ['未满足活动设置的全部匹配条件']
        elif rules.get('avoid') and avoid is None:
            suitability, score, reasons = '需确认', 30, ['缺少排除条件所需的档案信息']
        else:
            suitability, score, reasons = '可了解', 80, suitable_reasons or ['可了解此活动，实际参与须工作人员确认']
        result.append({'activity_id': row.id, 'code': row.code, 'name': row.name, 'category': row.category,
            'intensity': row.intensity, 'description': row.description, 'benefits': row.benefits,
            'duration_hint': row.duration_hint, 'contraindications': row.contraindications,
            'suitability': suitability, 'reasons': reasons, 'score': score, 'can_request': not invalid and score > 5,
            'season': SEASON_TEXT[ctx['season']], 'service_category': 'ENTERTAINMENT' if row.category in ('娱乐', '棋牌', 'ENTERTAINMENT') else
                'EXERCISE' if row.category in ('户外', '养生', '有氧', '康复', '锻炼', 'EXERCISE') else 'OTHER',
            'profile_id': profile.id, 'disclaimer': '健康建议不构成医疗诊断'})
    return sorted(result, key=lambda item: (-item['score'], item['activity_id']))
