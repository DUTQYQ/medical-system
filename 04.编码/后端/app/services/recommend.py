"""活动推荐规则引擎：按档案特征（年龄/慢病/季节/最新健康状态）匹配活动库。

规则定义在各活动 ``rules`` 字段（JSON），由本模块解释，不依赖 LLM，演示稳定。
"""
import json
from sqlalchemy import select
from app.models import Activity
from app.core.database import now
from app.services.serializers import age
from app.services.status import personal_status

SEASON_TEXT = {'spring': '春季', 'summer': '夏季', 'autumn': '秋季', 'winter': '冬季'}


def current_season():
    month = now().month
    if 3 <= month <= 5:
        return 'spring'
    if 6 <= month <= 8:
        return 'summer'
    if 9 <= month <= 11:
        return 'autumn'
    return 'winter'


def _in_list(value, wanted):
    if not wanted:
        return False
    if isinstance(value, (list, tuple, set)):
        return any(v in wanted for v in value)
    return value in wanted


def _match(cond, ctx):
    hit = False
    reasons = []
    if not cond:
        return False, []
    person_age = ctx['age']
    if person_age is not None and 'min_age' in cond and person_age >= cond['min_age']:
        hit = True
        reasons.append(f'{cond["min_age"]} 岁以上')
    if person_age is not None and 'max_age' in cond and person_age <= cond['max_age']:
        hit = True
        reasons.append(f'{cond["max_age"]} 岁以下')
    if 'chronic_in' in cond and _in_list(ctx['chronic_tags'], cond['chronic_in']):
        hit = True
        reasons.append('慢病/病史')
    if 'seasons_in' in cond and ctx['season'] in cond['seasons_in']:
        hit = True
        reasons.append('当前季节适宜')
    if 'seasons_not_in' in cond and ctx['season'] in cond['seasons_not_in']:
        hit = True
        reasons.append('当前季节不适宜')
    return hit, reasons


def recommend_activities(db, profile):
    status = personal_status(db, profile)
    ctx = {
        'age': age(profile.birthday),
        'chronic_tags': json.loads(profile.chronic_tags or '[]'),
        'season': current_season(),
        'latest_risk_levels': {item['type']: item['risk_level'] for item in status},
    }
    max_risk = max(ctx['latest_risk_levels'].values(), default=0)

    result = []
    for row in db.scalars(select(Activity).where(Activity.enabled == 1).order_by(Activity.id)):
        try:
            rules = json.loads(row.rules or '{}')
        except (ValueError, TypeError):
            rules = {}
        avoid_hit, avoid_reasons = _match(rules.get('avoid'), ctx)
        suitable_hit, suitable_reasons = _match(rules.get('suitable'), ctx)

        caution_hit = False
        caution = rules.get('caution') or {}
        if caution.get('max_risk_level') is not None and max_risk >= caution['max_risk_level']:
            caution_hit = True

        if avoid_hit:
            suitability, score, reasons = '不建议', 0, avoid_reasons or ['存在不适宜因素']
        elif caution_hit:
            suitability, score, reasons = '需谨慎', 50, ['当前健康指标需关注'] + suitable_reasons
        else:
            suitability, score, reasons = '适合', 100, suitable_reasons or ['适合日常进行']

        result.append({'activity_id': row.id, 'code': row.code, 'name': row.name, 'category': row.category,
                       'intensity': row.intensity, 'description': row.description, 'benefits': row.benefits,
                       'duration_hint': row.duration_hint, 'contraindications': row.contraindications,
                       'suitability': suitability, 'reasons': reasons, 'score': score,
                       'season': SEASON_TEXT.get(ctx['season'], ctx['season'])})

    result.sort(key=lambda x: -x['score'])
    return result
