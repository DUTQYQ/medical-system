import json
import math
import re
from sqlalchemy import select
from app.models import SysConfig
from app.core.errors import APIError

INDICATORS = {
    'BLOOD_PRESSURE': {'name': '血压', 'unit': 'mmHg', 'fields': ['systolic', 'diastolic'], 'keys': ['BLOOD_PRESSURE_SYSTOLIC', 'BLOOD_PRESSURE_DIASTOLIC'], 'integer': True},
    'BLOOD_SUGAR': {'name': '血糖', 'unit': 'mmol/L', 'fields': ['value'], 'keys': ['BLOOD_SUGAR'], 'integer': False},
    'HEART_RATE': {'name': '心率', 'unit': '次/分', 'fields': ['value'], 'keys': ['HEART_RATE'], 'integer': True},
    'SLEEP': {'name': '睡眠', 'unit': '小时', 'fields': ['hours', 'quality'], 'keys': ['SLEEP_HOURS'], 'integer': False},
    'STEP': {'name': '步数', 'unit': '步', 'fields': ['count'], 'keys': ['STEP_COUNT'], 'integer': True},
}


def config_value(db, key, default=None):
    item = db.scalar(select(SysConfig).where(SysConfig.config_key == key, SysConfig.enabled == 1))
    return item.config_value if item else default


def indicator(db, type):
    if type not in INDICATORS:
        raise APIError(2001, '不支持的指标类型')
    item = {'type': type, 'enabled': True, **INDICATORS[type]}
    extra = config_value(db, 'indicator:' + type)
    if extra:
        try:
            item.update(json.loads(extra))
        except (ValueError, TypeError):
            raise APIError(5001, '指标配置无效，请联系管理员', 503)
    return item


def validate_values(db, type, values):
    item = indicator(db, type)
    if not item['enabled']:
        raise APIError(2001, '该指标已停用')
    fields = INDICATORS[type]['fields']
    if set(values) != set(fields):
        raise APIError(2001, '指标字段必须为 ' + ', '.join(fields))
    numbers = []
    for field in fields:
        value = values[field]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise APIError(2001, field + ' 必须为有限数字')
        if value < 0 or value > 99999999.99:
            raise APIError(2001, field + ' 超出可记录范围')
        if item['integer'] and value != int(value):
            raise APIError(2001, field + ' 必须为整数')
        numbers.append(value)
    if type == 'BLOOD_PRESSURE' and (numbers[0] <= numbers[1] or min(numbers) <= 0):
        raise APIError(2001, '血压必须大于 0，收缩压必须高于舒张压')
    if type in ('BLOOD_SUGAR', 'HEART_RATE') and numbers[0] <= 0:
        raise APIError(2001, '指标值必须大于 0')
    if type == 'SLEEP' and (numbers[0] > 24 or numbers[1] != int(numbers[1]) or not 1 <= numbers[1] <= 5):
        raise APIError(2001, '睡眠时长为 0~24 小时，质量为 1~5 整数')
    if type in ('BLOOD_SUGAR', 'SLEEP') and round(numbers[0], 2) != numbers[0]:
        raise APIError(2001, '指标最多保留两位小数')
    limits = item.get('ranges', {})
    for field, value in zip(fields, numbers):
        if field in limits:
            minimum, maximum = limits[field]
            if not minimum <= value <= maximum:
                raise APIError(2001, f'{field} 须在 {minimum}~{maximum} 范围内')
    return numbers[0], numbers[1] if len(numbers) > 1 else None


NUMBER = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)'


def range_parts(expression):
    """Parse documented expressions, including commas and Chinese 或."""
    if not isinstance(expression, str) or not expression.strip():
        raise ValueError('empty threshold')
    result = []
    for part in re.split(r'\s*(?:,|，|或|\|)\s*', expression.strip()):
        part = part.strip().replace('≥', '>=').replace('≤', '<=')
        match = re.fullmatch(fr'({NUMBER})\s*[~～]\s*({NUMBER})', part)
        if match:
            low, high = map(float, match.groups())
            if low > high:
                raise ValueError('reversed threshold range')
            result.append((low, high, True, True))
            continue
        match = re.fullmatch(fr'(>=|<=|>|<)\s*({NUMBER})', part)
        if not match:
            raise ValueError('unsupported threshold expression')
        op, value = match.group(1), float(match.group(2))
        result.append((value, math.inf, op == '>=', False) if op.startswith('>') else (-math.inf, value, False, op == '<='))
    return result


def parse_threshold(raw):
    value = json.loads(raw)
    if set(value) != {'level0', 'level1', 'level2', 'level3'}:
        raise ValueError('four risk levels are required')
    ranges = {level: range_parts(value[f'level{level}']) for level in range(4)}
    # Shared endpoints are legal in the documented sleep ranges. Wider
    # intersections between levels are ambiguous and must not silently hide risk.
    for level in range(4):
        for other in range(level + 1, 4):
            for a in ranges[level]:
                for b in ranges[other]:
                    if max(a[0], b[0]) < min(a[1], b[1]):
                        raise ValueError('risk-level intervals overlap')
    return ranges


def evaluate(raw, value):
    ranges = parse_threshold(raw)
    # Normal ranges have priority at shared endpoints (sleep 7h, 6h).
    for level in range(4):
        for low, high, left, right in ranges[level]:
            if (value > low or (left and value == low)) and (value < high or (right and value == high)):
                return level
    # Decimal gaps (e.g. 6.1~6.2) inherit the more severe adjacent level.
    # This derives boundaries only from sys_config, never from hardcoded limits.
    below = [(high, level) for level, pieces in ranges.items() for low, high, _, _ in pieces if high < value]
    above = [(low, level) for level, pieces in ranges.items() for low, high, _, _ in pieces if low > value]
    if below and above:
        lower = max(below, key=lambda x: x[0])
        upper = min(above, key=lambda x: x[0])
        return max(lower[1], upper[1])
    # Missing one-sided abnormal intervals fail closed: never silently normal.
    raise APIError(5001, '预警阈值未覆盖此指标值，请联系管理员补全低值或高值区间', 503)


def risk_level(db, type, val1, val2=None):
    levels = []
    for key, value in zip(INDICATORS[type]['keys'], [val1, val2]):
        row = db.scalar(select(SysConfig).where(SysConfig.config_key == key))
        if not row:
            raise APIError(5001, '预警阈值尚未配置：' + key, 503)
        if not row.enabled:
            continue
        try:
            levels.append(evaluate(row.config_value, float(value)))
        except (ValueError, TypeError, KeyError):
            raise APIError(5001, '预警阈值配置无效：' + key, 503)
    return max(levels, default=0)


def threshold_data(row):
    try:
        values = json.loads(row.config_value)
    except ValueError:
        values = {}
    meta = next((v for v in INDICATORS.values() if row.config_key in v['keys']), {})
    return {'config_id': row.id, 'indicator': row.config_key, 'indicator_name': row.description or meta.get('name', row.config_key),
            'unit': meta.get('unit', ''), 'enabled': bool(row.enabled),
            **{f'level{i}_range': values.get(f'level{i}', '') for i in range(4)}}
