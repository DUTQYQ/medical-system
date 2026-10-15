"""Workflow boundaries on a disposable database, including real MySQL locks."""
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import select, func
import pytest
from conftest import login, expect
from app.core.database import SessionLocal, engine
from app.core.errors import APIError
from app.models import User, ElderProfile, FamilyBind, AILog, HealthWarning
from app.models.consultation import AdviceCard
from app.api.profiles import remove
from app.services.summary_budget import reserve
from scripts.seed_services import seed_services
from app.agent import llm
from app.agent import workflow


def test_phone_and_password_change_reauthenticates_atomically(client):
    user, other = login(client, 2), login(client, 2)
    body = {'name': '验收更新', 'phone': '13800000008', 'new_password': 'Newpass1234'}
    assert client.put('/api/auth/me', headers=user, json=body).status_code == 400
    updated = expect(client.put('/api/auth/me', headers=user, json={**body, 'current_password': 'Abc123456'}))
    assert updated['reauth_required'] and updated['phone'] == body['phone']
    assert client.get('/api/auth/me', headers=other).status_code == 401
    expect(client.post('/api/auth/login', json={'phone': body['phone'], 'password': body['new_password']}))


def test_caregiver_self_emergency_does_not_notify_for_elder(client):
    care = login(client, 4)
    result = expect(client.post('/api/ai/chat', headers=care, json={'profile_id': 2001, 'question': '我自己现在胸痛'}))
    assert result['warning_id'] is None and '120' in result['answer']
    with SessionLocal() as db:
        assert db.scalar(select(func.count(HealthWarning.id))) == 0
    elder = expect(client.post('/api/ai/chat', headers=care, json={'profile_id': 2001, 'question': '老人现在胸痛'}))
    assert elder['warning_id'] is not None


@pytest.mark.skipif(engine.dialect.name != 'mysql', reason='requires MySQL repeatable-read semantics')
def test_profile_archive_current_read_sees_services_after_old_snapshot(client):
    elder = login(client, 2)
    with SessionLocal() as old:
        user = old.get(User, 2)
        old.get(ElderProfile, 2001)  # Establish a consistent snapshot before creation.
        expect(client.post('/api/services/requests', headers=elder, json={'profile_id': 2001,
            'category': 'OTHER', 'title': '归档并发验收', 'description': '必须先完成', 'location': '101室'}))
        with pytest.raises(APIError) as blocked:
            remove(2001, user=user, db=old)
        assert blocked.value.status == 409
        old.rollback()
    assert client.get('/api/profiles/2001', headers=elder).status_code == 200


@pytest.mark.skipif(engine.dialect.name != 'mysql', reason='requires independent InnoDB transactions')
def test_summary_budget_is_atomic_across_different_warning_jobs(client):
    with SessionLocal() as db:
        seed_services(db)
        from app.models import SysConfig
        db.scalar(select(SysConfig).where(SysConfig.config_key == 'ai_summary_daily_limit')).config_value = '1'
        db.commit()
    def attempt(wid):
        with SessionLocal() as db:
            # Both transactions deliberately start snapshots before contending.
            db.get(User, 2)
            result, _ = reserve(db, wid)
            db.commit()
            return result is not None
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, [991, 992]))
    assert sum(results) == 1
    with SessionLocal() as db:
        assert db.scalar(select(func.count(AILog.id)).where(AILog.agent == 'ALERT_ATTEMPT')) == 1


def test_advice_rechecks_binding_after_model_response(client, monkeypatch):
    family = login(client, 3)
    expect(client.post('/api/ai/facts', headers=family, json={'profile_id': 2001, 'key': 'life_goal', 'value': '参加院内活动'}))
    def revoked_during_generation(*args, **kwargs):
        with SessionLocal() as db:
            db.scalar(select(ElderProfile).where(ElderProfile.id == 2001).with_for_update())
            relation = db.scalar(select(FamilyBind).where(FamilyBind.id == 9001).with_for_update())
            relation.status = 'UNBOUND'
            db.commit()
        return 'invalid json, fall back to rules'
    monkeypatch.setattr(llm, 'complete', revoked_during_generation)
    assert client.post('/api/ai/advice', headers=family, json={'profile_id': 2001}).status_code == 403
    with SessionLocal() as db:
        assert db.scalar(select(func.count(AdviceCard.id))) == 0
        assert db.scalar(select(func.count(AILog.id)).where(AILog.agent == 'CONSULT_ATTEMPT')) == 1


def test_measurement_voided_during_model_cannot_publish_stale_summary(client, monkeypatch):
    from datetime import timedelta
    from app.core.database import now
    monkeypatch.setattr('app.api.health.generate_summary', lambda wid: None)
    elder, care = login(client, 2), login(client, 4)
    with SessionLocal() as db:
        seed_services(db)
        db.commit()
    item = expect(client.post('/api/health/records', headers=elder, json={'profile_id': 2001,
        'type': 'BLOOD_PRESSURE', 'values': {'systolic': 185, 'diastolic': 95},
        'measured_at': (now()-timedelta(seconds=1)).isoformat()}))
    def model(*args, **kwargs):
        expect(client.request('DELETE', f'/api/health/records/{item["record_id"]}', headers=elder,
            json={'reason': '模型生成期间复核为错误测量'}))
        return '应丢弃的旧分析'
    monkeypatch.setattr(workflow, 'complete', model)
    workflow.generate_summary(item['warning_id'])
    warning = expect(client.get(f'/api/alerts/{item["warning_id"]}', headers=care))
    assert warning['summary_status'] == 'SKIPPED' and warning['ai_summary'] is None
    assert warning['status'] == 'PENDING' and '作废' in warning['summary_message']
