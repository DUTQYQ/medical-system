"""Measurements are immutable; corrections retain an explicit void audit."""
from sqlalchemy import select
from app.models import HealthRecord, HealthRecordVoid, User
from app.services.serializers import dt


def active_records():
    return HealthRecord.id.not_in(select(HealthRecordVoid.record_id))


def void_data(db, row):
    if row is None:
        return None
    actor = db.get(User, row.voided_by)
    return {'voided_by': row.voided_by, 'voided_by_name': actor.name if actor else None,
            'reason': row.reason, 'voided_at': dt(row.create_time)}
