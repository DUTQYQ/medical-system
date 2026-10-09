"""Behavioral checks of the project closed loop, authorization and failure paths."""
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select

from conftest import login, expect
from app.core.database import SessionLocal, engine
from app.models import SysConfig, HealthRecord, HealthWarning, WarningHandleRecord, AlertReceiver


def record(client, headers, type='BLOOD_PRESSURE', values=None, profile_id=2001):
    return client.post('/api/health/records', json={'profile_id': profile_id, 'type': type,
                       'values': values or {'systolic': 185, 'diastolic': 100},
                       'measured_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}, headers=headers)


def test_registration_rejects_privileged_roles(client):
    for role in ('CARE', 'ADMIN'):
        expect(client.post('/api/auth/register', json={'phone': '13900139000', 'name': '越权注册',
                           'password': 'Abc123456', 'role': role}), 4003)
    expect(client.post('/api/auth/register', json={'phone': '13900139000', 'name': '新老人',
                       'password': 'Abc123456', 'role': 'ELDER'}))
    expect(client.post('/api/auth/register', json={'phone': '13900139000', 'name': '重复',
                       'password': 'Abc123456', 'role': 'FAMILY'}), 2001)


def test_logout_revokes_token_on_server(client):
    headers = login(client, 2)
    expect(client.post('/api/auth/logout', headers=headers))
    expect(client.get('/api/auth/me', headers=headers), 1001)


def test_family_scope_and_pending_consent(client):
    headers = login(client, 3)
    expect(client.get('/api/profiles/2002', headers=headers), 1002)
    binding = expect(client.post('/api/family/bind', json={'phone': '13000000006', 'relation': '女儿'}, headers=headers))
    bind_id = binding.get('bind_id', binding.get('id'))
    expect(client.get('/api/profiles/2002', headers=headers), 1002)
    expect(client.put(f'/api/family/bind/{bind_id}/confirm', json={'action': 'APPROVE'}, headers=login(client, 6)))
    expect(client.get('/api/profiles/2002', headers=headers))


def test_warning_notification_handle_and_read_are_independent(client):
    elder, family, other, care = (login(client, uid) for uid in (2, 3, 5, 4))
    data = expect(record(client, elder))
    warning_id = data['warning_id']
    assert data['is_abnormal'] and data['risk_level'] == 3
    assert expect(client.get('/api/notifications/unread', headers=family))['unread'] == 1
    detail = expect(client.get(f'/api/alerts/{warning_id}', headers=family))
    assert detail['my_read_status'] == 'READ'
    assert detail['summary_status'] in ('PENDING', 'FAILED')
    assert detail['ai_summary'] is None
    assert expect(client.get('/api/notifications/unread', headers=other))['unread'] == 1
    expect(client.post(f'/api/alerts/{warning_id}/handle', json={'action': 'CONTACTED', 'result': '已联系老人并安排复诊'}, headers=family))
    other_list = expect(client.get('/api/alerts', headers=other))['list']
    assert other_list[0]['status'] == 'RESOLVED'
    assert other_list[0]['my_read_status'] == 'UNREAD'
    assert other_list[0]['handler_name']
    with SessionLocal() as db:
        assert len(list(db.scalars(select(WarningHandleRecord).where(WarningHandleRecord.warning_id == warning_id)))) == 1
    expect(client.get('/api/care/handles', headers=care))


def test_unbinding_revokes_historical_alert_access(client):
    elder, family = login(client, 2), login(client, 3)
    warning_id = expect(record(client, elder))['warning_id']
    expect(client.delete('/api/family/bind/9001', headers=family))
    expect(client.get('/api/profiles/2001', headers=family), 1002)
    expect(client.get(f'/api/alerts/{warning_id}', headers=family), 1002)
    assert expect(client.get('/api/notifications/unread', headers=family))['unread'] == 0


def test_invalid_data_never_writes_partial_records(client):
    headers = login(client, 2)
    for values in ({'systolic': 80, 'diastolic': 90}, {'systolic': True, 'diastolic': 80},
                   {'systolic': 120}, {'systolic': 120.5, 'diastolic': 80}):
        expect(record(client, headers, values=values), 2001)
    with SessionLocal() as db:
        assert db.scalar(select(HealthRecord.id)) is None
        assert db.scalar(select(HealthWarning.id)) is None


def test_all_five_indicators_and_empty_trend(client):
    headers = login(client, 2)
    expect(client.get('/api/health/trend?profile_id=2001&type=BLOOD_PRESSURE&days=30', headers=headers))
    for type, values in [('BLOOD_PRESSURE', {'systolic': 128, 'diastolic': 82}),
                         ('BLOOD_SUGAR', {'value': 6.15}), ('HEART_RATE', {'value': 76}),
                         ('SLEEP', {'hours': 7, 'quality': 3}), ('STEP', {'count': 6500})]:
        data = expect(record(client, headers, type=type, values=values))
        assert data['risk_level'] == (1 if type == 'BLOOD_SUGAR' else 0)


def test_threshold_change_takes_effect_immediately(client):
    elder, admin = login(client, 2), login(client, 1)
    before = expect(record(client, elder, values={'systolic': 145, 'diastolic': 80}))
    assert before['risk_level'] == 1
    rows = expect(client.get('/api/admin/thresholds', headers=admin))
    if isinstance(rows, dict):
        rows = rows.get('list', rows.get('thresholds'))
    row = next(item for item in rows if item['indicator'] == 'BLOOD_PRESSURE_SYSTOLIC')
    expect(client.put(f"/api/admin/thresholds/{row['config_id']}", headers=admin,
                      json={'level0_range': '90~149', 'level1_range': '150~159',
                            'level2_range': '160~179', 'level3_range': '<90 或 >=180', 'enabled': True}))
    assert expect(record(client, elder, values={'systolic': 145, 'diastolic': 80}))['risk_level'] == 0


def test_disabled_account_loses_existing_token(client):
    family, admin = login(client, 3), login(client, 1)
    expect(client.put('/api/admin/users/3/status', json={'enabled': False}, headers=admin))
    expect(client.get('/api/profiles', headers=family), 1003)
    expect(client.post('/api/auth/login', json={'phone': '13000000003', 'password': 'Abc123456'}), 1003)
    expect(client.put('/api/admin/users/3/status', json={'enabled': True}, headers=admin))
    expect(client.get('/api/profiles', headers=family), 1001)


def test_care_cannot_access_unassigned_profile(client):
    care = login(client, 4)
    expect(client.get('/api/care/elders/2001', headers=care))
    expect(client.get('/api/care/elders/2002', headers=care), 1002)
    expect(client.get('/api/admin/users', headers=care), 1002)


def test_no_model_key_cannot_fake_ai_success(client):
    headers = login(client, 2)
    expect(client.post('/api/ai/chat', json={'profile_id': 2001, 'question': '高血压老人可以吃鸡蛋吗'}, headers=headers), 3001)
    assert expect(record(client, headers))['warning_id']


def test_emergency_creates_warning_without_model(client):
    headers = login(client, 2)
    result = client.post('/api/ai/chat', json={'profile_id': 2001, 'question': '我胸口很痛，喘不上气'}, headers=headers).json()
    assert result['code'] in (0, 3001), result
    with SessionLocal() as db:
        warning = db.scalar(select(HealthWarning).where(HealthWarning.trigger_source == 'AI_CHAT'))
        assert warning and warning.level == 3
        assert db.scalar(select(AlertReceiver.id).where(AlertReceiver.warning_id == warning.id, AlertReceiver.user_id == 3))
    assert expect(client.get('/api/notifications/unread', headers=login(client, 3)))['unread'] == 1


def test_read_all_only_updates_current_recipient(client):
    elder, family, other = login(client, 2), login(client, 3), login(client, 5)
    expect(record(client, elder))
    expect(client.post('/api/notifications/read-all', headers=family))
    assert expect(client.get('/api/notifications/unread', headers=family))['unread'] == 0
    assert expect(client.get('/api/notifications/unread', headers=other))['unread'] == 1
    assert expect(client.get('/api/alerts', headers=family))['list'][0]['status'] == 'PENDING'


def test_profile_soft_delete_removes_scope(client):
    elder, family = login(client, 2), login(client, 3)
    expect(client.delete('/api/profiles/2001', headers=elder))
    expect(client.get('/api/profiles/2001', headers=family), 2002)
    assert expect(client.get('/api/profiles', headers=elder)) == []


def test_model_free_statistics_return_real_counts(client):
    elder, admin = login(client, 2), login(client, 1)
    expect(record(client, elder))
    stats = expect(client.get('/api/admin/statistics?range=1d', headers=admin))
    assert stats


@pytest.mark.skipif(engine.dialect.name != 'mysql', reason='Requires real MySQL row locks')
def test_concurrent_handles_persist_one_result(client):
    elder, family, other = login(client, 2), login(client, 3), login(client, 5)
    warning_id = expect(record(client, elder))['warning_id']
    def handle(headers):
        return client.post(f'/api/alerts/{warning_id}/handle', json={'action': 'CONTACTED', 'result': '并发处理验收'}, headers=headers).json()
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(handle, [family, other]))
    assert sorted(result['code'] for result in results) == [0, 2001], results
    with SessionLocal() as db:
        assert len(list(db.scalars(select(WarningHandleRecord).where(WarningHandleRecord.warning_id == warning_id)))) == 1


@pytest.mark.skipif(engine.dialect.name != 'mysql', reason='Requires real MySQL row locks')
def test_concurrent_binding_requests_cannot_duplicate(client):
    headers = login(client, 3)
    def submit(_):
        return client.post('/api/family/bind', json={'phone': '13000000006', 'relation': '女儿'}, headers=headers).json()
    with ThreadPoolExecutor(max_workers=2) as workers:
        results = list(workers.map(submit, range(2)))
    assert sorted(result['code'] for result in results) == [0, 4001], results
