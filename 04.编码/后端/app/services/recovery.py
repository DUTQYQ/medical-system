"""Recover interrupted optional summaries without running a model.

This uses bounded request timeouts plus a 60-second margin rather than a new
queue table. Enable only with one process against this database. Multi-process
deployments need leases/a dedicated worker and must disable this sweep.
"""
import logging
import os
import threading
from contextlib import contextmanager
from datetime import timedelta
from sqlalchemy import update
from sqlalchemy.exc import SQLAlchemyError
from app.core.database import SessionLocal, now
from app.models import HealthWarning
from app.services.thresholds import config_value

logger = logging.getLogger('kangyang')
_jobs_lock = threading.RLock()
_active_jobs = set()


@contextmanager
def summary_job(warning_id):
    """Register a real running job; a duplicate invocation does no model work."""
    with _jobs_lock:
        claimed = warning_id not in _active_jobs
        if claimed:
            _active_jobs.add(warning_id)
    try:
        yield claimed
    finally:
        if claimed:
            with _jobs_lock:
                _active_jobs.discard(warning_id)


def recovery_enabled():
    if os.getenv('WEB_CONCURRENCY', '1') != '1':
        return False
    mode = os.getenv('SUMMARY_RECOVERY_ENABLED', 'auto').strip().lower()
    if mode in ('true', '1', 'yes'):
        return True
    if mode in ('false', '0', 'no'):
        return False
    return mode == 'auto' and os.getenv('DEMO_MODE', '').lower() in ('true', '1', 'yes')


def bounded_number(db, key, default, minimum, maximum):
    try:
        return max(minimum, min(maximum, int(config_value(db, key, str(default)))))
    except (ValueError, TypeError):
        return default


def recover_pending_summaries(db):
    timeout = bounded_number(db, 'ai_summary_timeout_sec', 8, 1, 30)
    retries = bounded_number(db, 'ai_summary_retry', 1, 0, 2)
    cutoff = now() - timedelta(seconds=timeout * (retries + 1) + 60)
    with _jobs_lock:
        criteria = [HealthWarning.summary_status == 'PENDING', HealthWarning.update_time < cutoff]
        if _active_jobs:
            criteria.append(HealthWarning.id.not_in(list(_active_jobs)))
        result = db.execute(update(HealthWarning).where(*criteria).values(summary_status='FAILED', ai_summary=None, update_time=now()))
        return result.rowcount


def recover_once():
    try:
        # Prevent a queued job from registering against the old state between
        # selecting a stale row and committing its recovery transition.
        with _jobs_lock:
            with SessionLocal() as db:
                count = recover_pending_summaries(db)
                db.commit()
        if count:
            logger.info('Recovered %d interrupted AI summaries as FAILED; original warnings remain available', count)
        return count
    except SQLAlchemyError:
        logger.warning('Summary recovery could not reach the database; business API reports availability independently')
        return 0
