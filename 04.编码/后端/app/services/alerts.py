from sqlalchemy import select
from app.models import HealthWarning, AlertReceiver, FamilyBind, CareRelation, User


def create_warning(db, profile, *, type, value_text, level, record_id=None, trigger_source='DATA_INPUT'):
    """Flush warning and recipients in caller's transaction; never call the model."""
    warning = HealthWarning(profile_id=profile.id, record_id=record_id, type=type,
                            value_text=value_text, level=level, trigger_source=trigger_source,
                            summary_status='PENDING' if level >= 2 else 'SKIPPED', status='PENDING')
    db.add(warning)
    db.flush()
    ids = {profile.user_id}
    ids.update(db.scalars(select(FamilyBind.family_user_id).where(FamilyBind.profile_id == profile.id, FamilyBind.status == 'APPROVED').with_for_update()))
    ids.update(db.scalars(select(CareRelation.care_user_id).where(CareRelation.profile_id == profile.id, CareRelation.status == 1).with_for_update()))
    enabled_ids = set(db.scalars(select(User.id).where(User.id.in_(ids), User.status == 1).with_for_update()))
    db.add_all(AlertReceiver(warning_id=warning.id, user_id=user_id, read_status='UNREAD') for user_id in enabled_ids)
    db.flush()
    return warning


def generate_summary(warning_id):
    # Lazy import avoids loading the model runtime in the primary write path.
    from app.agent.workflow import generate_summary as run
    return run(warning_id)
