import json
from datetime import date
from app.core.database import now


def dt(value):
    return value.strftime('%Y-%m-%d %H:%M:%S') if value else None


def age(birthday):
    today = now().date()
    return today.year - birthday.year - ((today.month, today.day) < (birthday.month, birthday.day)) if birthday else None


def user_data(user):
    return {'user_id': user.id, 'name': user.name, 'phone': user.phone, 'role': user.role, 'avatar': user.avatar or '', 'enabled': bool(user.status), 'last_login_time': dt(user.last_login_time)}


def profile_data(profile):
    result = {name: getattr(profile, name) for name in ('name', 'gender', 'blood_type', 'allergy', 'medical_history', 'emergency_contact', 'emergency_phone')}
    result.update({'profile_id': profile.id, 'user_id': profile.user_id, 'birthday': profile.birthday.isoformat() if profile.birthday else None,
                   'height': float(profile.height) if profile.height is not None else None, 'weight': float(profile.weight) if profile.weight is not None else None,
                   'age': age(profile.birthday), 'chronic_tags': json.loads(profile.chronic_tags or '[]'), 'created_at': dt(profile.create_time), 'updated_at': dt(profile.update_time)})
    return result


def record_values(record):
    first = float(record.val1) if record.val1 is not None else None
    second = float(record.val2) if record.val2 is not None else None
    if record.type == 'BLOOD_PRESSURE':
        return {'systolic': first, 'diastolic': second}
    if record.type == 'SLEEP':
        return {'hours': first, 'quality': second}
    return {'count' if record.type == 'STEP' else 'value': first}


def record_data(record):
    return {'record_id': record.id, 'profile_id': record.profile_id, 'type': record.type, 'values': record_values(record),
            'measured_at': dt(record.measured_at), 'is_abnormal': bool(record.is_abnormal), 'remark': record.remark or '', 'recorder_id': record.recorder_id, 'created_at': dt(record.create_time)}


def value_text(type, val1, val2=None):
    return f'{float(val1):g}/{float(val2):g}' if type == 'BLOOD_PRESSURE' else f'{float(val1):g}'
