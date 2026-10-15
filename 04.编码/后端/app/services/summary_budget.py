"""Persisted cost reservations for optional summaries; never gate alert creation."""
from datetime import timedelta
from sqlalchemy import select
from app.core.database import now
from app.models import AILog, SysConfig
from app.agent.workflow import number_config


def allowance(db, warning_id, *, lock=False, check_cooldown=True):
    gate = select(SysConfig).where(SysConfig.config_key == 'ai_summary_daily_limit', SysConfig.enabled == 1)
    if lock:
        gate = gate.with_for_update().execution_options(populate_existing=True)
    if db.scalar(gate) is None:
        return False, '摘要预算尚未初始化，请联系管理员；预警与通知不受影响'
    today = now().replace(hour=0, minute=0, second=0, microsecond=0)
    query = select(AILog).where(AILog.agent == 'ALERT_ATTEMPT', AILog.create_time >= today)
    rows = list(db.scalars(query.with_for_update() if lock else query))
    if len(rows) >= number_config(db, 'ai_summary_daily_limit', 100, minimum=0):
        return False, '今日摘要额度已用完；预警与通知仍可使用'
    per_warning = [row for row in rows if row.model == f'warning:{warning_id}']
    if len(per_warning) >= number_config(db, 'ai_summary_warning_daily_limit', 3):
        return False, '此预警今日摘要尝试次数已达上限'
    cooldown = number_config(db, 'ai_summary_cooldown_seconds', 60, maximum=3600)
    recent = select(AILog.id).where(AILog.agent == 'ALERT_ATTEMPT', AILog.model == f'warning:{warning_id}',
                                    AILog.create_time > now()-timedelta(seconds=cooldown))
    if lock:
        recent = recent.with_for_update()
    if check_cooldown and db.scalar(recent) is not None:
        return False, f'请等待至少 {cooldown} 秒后重试摘要'
    return True, ''


def reserve(db, warning_id, *, check_cooldown=True):
    allowed, reason = allowance(db, warning_id, lock=True, check_cooldown=check_cooldown)
    if not allowed:
        return None, reason
    row = AILog(agent='ALERT_ATTEMPT', model=f'warning:{warning_id}', success=0)
    db.add(row)
    # The reservation survives timeouts/crashes and releases the budget lock
    # before optional network work. Each HTTP attempt consumes one reservation.
    db.commit()
    return row, ''
