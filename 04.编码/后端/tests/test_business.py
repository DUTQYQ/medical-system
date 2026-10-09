import json
import os
from datetime import timedelta

os.environ.setdefault('DATABASE_URL', 'sqlite://')
os.environ.setdefault('JWT_SECRET', 'unit-test-secret-' + 'x' * 32)
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest
from app.main import app
from app.core.database import Base, get_db, now
from app.core.security import hash_password
from app.models import User, ElderProfile, HealthWarning, HealthRecord, AlertReceiver, SysConfig, WarningHandleRecord
from app.services.thresholds import evaluate
from scripts.seed import seed_database, THRESHOLDS


@pytest.fixture()
def setup(monkeypatch, tmp_path):
    # AI tests can import settings before this file is collected.
    from app.core.config import settings
    monkeypatch.setattr(settings, 'database_url', 'sqlite://')
    monkeypatch.setattr(settings, 'jwt_secret', 'unit-test-secret-' + 'x' * 32)
    monkeypatch.setenv('CHROMA_PATH', str(tmp_path / 'chroma'))
    monkeypatch.setenv('EMBEDDING_PROVIDER', 'hash')
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    with sessions() as db:
        seed_database(db, demo=True)
    def dependency():
        with sessions() as db:
            try:
                yield db
            except BaseException:
                db.rollback()
                raise
    app.dependency_overrides[get_db] = dependency
    monkeypatch.setattr('app.api.health.generate_summary', lambda warning_id: None)
    monkeypatch.setattr('app.api.alerts.generate_summary', lambda warning_id: None)
    with TestClient(app) as client:
        yield client, sessions
    app.dependency_overrides.clear()
    engine.dispose()


def login(client, suffix):
    result = client.post('/api/auth/login', json={'phone': '1300000000' + str(suffix), 'password': 'Abc123456'})
    assert result.json()['code'] == 0, result.text
    headers = {'Authorization': 'Bearer ' + result.json()['data']['token']}
    assert client.post('/api/auth/privacy-consent', headers=headers, json={'accepted': True}).json()['code'] == 0
    return headers


def first_profile(client, headers):
    return client.get('/api/profiles', headers=headers).json()['data'][0]['profile_id']


def input_record(client, headers, profile_id, type='BLOOD_PRESSURE', values=None):
    return client.post('/api/health/records', headers=headers, json={'profile_id': profile_id, 'type': type,
        'values': values or {'systolic': 181, 'diastolic': 111}, 'measured_at': (now() - timedelta(seconds=1)).strftime('%Y-%m-%d %H:%M:%S')})


def test_abnormal_to_notifications_to_handling_and_independent_reads(setup):
    client, sessions = setup
    elder, family, care = [login(client, index) for index in (2, 3, 4)]
    profile_id = first_profile(client, elder)
    result = input_record(client, elder, profile_id).json()
    assert result['code'] == 0, result
    warning_id = result['data']['warning_id']
    assert result['data']['risk_level'] == 3
    assert client.get('/api/notifications/unread', headers=family).json()['data']['unread'] == 1
    assert client.get(f'/api/alerts/{warning_id}', headers=family).json()['data']['my_read_status'] == 'READ'
    assert client.get('/api/notifications/unread', headers=care).json()['data']['unread'] == 1
    handled = client.post(f'/api/alerts/{warning_id}/handle', headers=family, json={'result': '联系老人复核指标', 'action': 'CONTACTED'})
    assert handled.json()['data']['status'] == 'RESOLVED'
    assert client.get('/api/notifications/unread', headers=care).json()['data']['unread'] == 1
    duplicate = client.post(f'/api/alerts/{warning_id}/handle', headers=care, json={'result': '重复提交', 'action': 'OBSERVE'})
    assert duplicate.status_code == 409
    with sessions() as db:
        assert len(list(db.scalars(select(WarningHandleRecord)))) == 1
        assert len(list(db.scalars(select(AlertReceiver)))) == 3


def test_pending_binding_has_no_access_and_revoke_hides_existing_alert(setup):
    client, _ = setup
    elder = login(client, 2)
    profile_id = first_profile(client, elder)
    client.post('/api/auth/register', json={'phone': '13800000000', 'password': 'Abc123456', 'name': '新家属', 'role': 'FAMILY'})
    token = client.post('/api/auth/login', json={'phone': '13800000000', 'password': 'Abc123456'}).json()['data']['token']
    family = {'Authorization': 'Bearer ' + token}
    client.post('/api/auth/privacy-consent', headers=family, json={'accepted': True})
    result = client.post('/api/family/bind', headers=family, json={'phone': '13000000002', 'relation': '女儿'}).json()['data']
    bind_id = result['bind_id']
    assert client.get(f'/api/profiles/{profile_id}', headers=family).status_code == 403
    assert client.post('/api/family/bind', headers=family, json={'phone': '13000000002', 'relation': '女儿'}).json()['code'] == 4001
    assert client.put(f'/api/family/bind/{bind_id}/confirm', headers=elder, json={'action': 'APPROVE'}).json()['code'] == 0
    warning_id = input_record(client, elder, profile_id).json()['data']['warning_id']
    assert client.get('/api/notifications/unread', headers=family).json()['data']['unread'] == 1
    assert client.delete(f'/api/family/bind/{bind_id}', headers=family).json()['code'] == 0
    assert client.get(f'/api/alerts/{warning_id}', headers=family).status_code == 403
    assert client.get('/api/notifications/unread', headers=family).json()['data']['unread'] == 0
    assert client.get('/api/notifications', headers=family).json()['data']['total'] == 0


def test_logout_persists_disable_and_reenable_do_not_revive_old_tokens(setup):
    client, sessions = setup
    elder, admin = login(client, 2), login(client, 1)
    assert client.post('/api/auth/logout', headers=elder).json()['code'] == 0
    assert client.get('/api/auth/me', headers=elder).json()['code'] == 1001
    with sessions() as db:
        assert db.scalar(select(SysConfig).where(SysConfig.group_name == 'jwt_revocation'))
        elder_id = db.scalar(select(User.id).where(User.role == 'ELDER'))
    elder = login(client, 2)
    assert client.put(f'/api/admin/users/{elder_id}/status', headers=admin, json={'enabled': False}).json()['code'] == 0
    assert client.get('/api/auth/me', headers=elder).json()['code'] == 1003
    client.put(f'/api/admin/users/{elder_id}/status', headers=admin, json={'enabled': True})
    assert client.get('/api/auth/me', headers=elder).json()['code'] == 1001


def test_registration_role_guard_data_isolation_and_soft_delete(setup):
    client, _ = setup
    assert client.post('/api/auth/register', json={'phone': '13800000000', 'password': 'Abc123456', 'name': '越权', 'role': 'ADMIN'}).json()['code'] == 4003
    elder = login(client, 2)
    profile_id = first_profile(client, elder)
    client.post('/api/auth/register', json={'phone': '13800000001', 'password': 'Abc123456', 'name': '新老人'})
    token = client.post('/api/auth/login', json={'phone': '13800000001', 'password': 'Abc123456'}).json()['data']['token']
    other = {'Authorization': 'Bearer ' + token}
    client.post('/api/auth/privacy-consent', headers=other, json={'accepted': True})
    assert client.get(f'/api/profiles/{profile_id}', headers=other).status_code == 403
    assert client.get('/api/health/records', headers=other, params={'profile_id': profile_id}).status_code == 403
    assert client.get('/api/admin/users', headers=elder).status_code == 403
    client.delete(f'/api/profiles/{profile_id}', headers=elder)
    assert client.get(f'/api/profiles/{profile_id}', headers=elder).status_code == 404


def test_threshold_edit_immediately_affects_new_record_and_invalid_rolls_back(setup):
    client, sessions = setup
    elder, admin = login(client, 2), login(client, 1)
    profile_id = first_profile(client, elder)
    thresholds = client.get('/api/admin/thresholds', headers=admin).json()['data']
    row = next(item for item in thresholds if item['indicator'] == 'BLOOD_PRESSURE_SYSTOLIC')
    response = client.put(f'/api/admin/thresholds/{row["config_id"]}', headers=admin, json={'level0_range': '90~149', 'level1_range': '150~159', 'level2_range': '160~179', 'level3_range': '<90 或 >=180'})
    assert response.json()['code'] == 0
    assert input_record(client, elder, profile_id, values={'systolic': 145, 'diastolic': 80}).json()['data']['is_abnormal'] is False
    bad = input_record(client, elder, profile_id, values={'systolic': 80, 'diastolic': 120})
    assert bad.json()['code'] == 2001
    with sessions() as db:
        assert len(list(db.scalars(select(HealthRecord)))) == 1
        assert not list(db.scalars(select(HealthWarning)))


@pytest.mark.parametrize('type,values', [('BLOOD_SUGAR', {'value': 6.15}), ('HEART_RATE', {'value': 80}), ('SLEEP', {'hours': 7, 'quality': 3}), ('STEP', {'count': 5000})])
def test_all_indicator_shapes(setup, type, values):
    client, _ = setup
    elder = login(client, 2)
    result = input_record(client, elder, first_profile(client, elder), type, values)
    assert result.json()['code'] == 0, result.text


def test_decimal_gap_is_not_normal_and_uncovered_low_value_fails_closed():
    assert evaluate(json.dumps(THRESHOLDS['BLOOD_SUGAR']), 6.15) == 1
    assert evaluate(json.dumps(THRESHOLDS['SLEEP_HOURS']), 7) == 0
    assert evaluate(json.dumps(THRESHOLDS['BLOOD_PRESSURE_SYSTOLIC']), 80) == 3
    from app.core.errors import APIError
    broken = dict(THRESHOLDS['BLOOD_PRESSURE_SYSTOLIC'], level3='>=180')
    with pytest.raises(APIError):
        evaluate(json.dumps(broken), 80)


def test_privacy_consent_profile_edit_and_password_invalidate_sessions(setup):
    client, sessions = setup
    elder = login(client, 2)
    assert client.post('/api/auth/privacy-consent', headers=elder, json={'accepted': False}).json()['code'] == 2001
    assert client.post('/api/auth/privacy-consent', headers=elder, json={'accepted': True, 'version': '1.0'}).json()['code'] == 0
    result = client.get('/api/auth/me', headers=elder).json()['data']
    assert result['privacy_consent']['accepted'] is True
    assert result['privacy_consent']['accepted_at']
    assert client.put('/api/auth/me', headers=elder, json={'name': '老人新名称'}).json()['data']['name'] == '老人新名称'
    assert client.put('/api/auth/password', headers=elder, json={'old_password': 'wrongpass', 'new_password': 'Next@1234'}).json()['code'] == 2001
    assert client.put('/api/auth/password', headers=elder, json={'old_password': 'Abc123456', 'new_password': 'Next@1234'}).json()['code'] == 0
    assert client.get('/api/auth/me', headers=elder).json()['code'] == 1001
    assert client.post('/api/auth/login', json={'phone': '13000000002', 'password': 'Next@1234'}).json()['code'] == 0


def test_login_attempt_limit_is_persistent_and_blocks_correct_password(setup):
    client, sessions = setup
    for index in range(5):
        result = client.post('/api/auth/login', json={'phone': '13000000002', 'password': 'wrongpass'})
        assert result.json()['code'] == 1001
    assert client.post('/api/auth/login', json={'phone': '13000000002', 'password': 'Abc123456'}).status_code == 429
    with sessions() as db:
        count = db.scalar(select(SysConfig).where(SysConfig.config_key.like('login_fail:%')))
        assert json.loads(count.config_value)['count'] == 5


def test_bind_limit_and_care_assignment_revocation(setup):
    client, sessions = setup
    admin, elder, care = login(client, 1), login(client, 2), login(client, 4)
    profile_id = first_profile(client, elder)
    with sessions() as db:
        db.scalar(select(SysConfig).where(SysConfig.config_key == 'family_bind_max')).config_value = '1'
        care_id = db.scalar(select(User.id).where(User.role == 'CARE'))
        db.commit()
    client.post('/api/auth/register', json={'phone': '13800000000', 'password': 'Abc123456', 'name': '另一家属', 'role': 'FAMILY'})
    token = client.post('/api/auth/login', json={'phone': '13800000000', 'password': 'Abc123456'}).json()['data']['token']
    assert client.post('/api/family/bind', headers={'Authorization': 'Bearer ' + token}, json={'phone': '13000000002', 'relation': '女儿'}).json()['code'] == 4002
    warning_id = input_record(client, elder, profile_id).json()['data']['warning_id']
    assert client.get('/api/notifications/unread', headers=care).json()['data']['unread'] == 1
    response = client.post('/api/admin/care-assignments', headers=admin, json={'profile_id': profile_id, 'care_user_id': care_id, 'enabled': False})
    assert response.json()['code'] == 0
    assert client.get('/api/care/elders', headers=care).json()['data'] == []
    assert client.get('/api/notifications/unread', headers=care).json()['data']['unread'] == 0
    assert client.get(f'/api/alerts/{warning_id}', headers=care).status_code == 403


def test_admin_role_change_and_indicator_limits(setup):
    client, sessions = setup
    admin, care, elder = login(client, 1), login(client, 4), login(client, 2)
    profile_id = first_profile(client, elder)
    with sessions() as db:
        care_id = db.scalar(select(User.id).where(User.role == 'CARE'))
    assert client.put(f'/api/admin/users/{care_id}/role', headers=admin, json={'role': 'ADMIN'}).json()['code'] == 0
    assert client.get('/api/auth/me', headers=care).json()['code'] == 1001
    assert client.put('/api/admin/indicators/HEART_RATE', headers=admin, json={'name': '心率', 'unit': '次/分', 'ranges': {'value': [1, 300]}}).json()['code'] == 0
    assert input_record(client, elder, profile_id, 'HEART_RATE', {'value': 301}).json()['code'] == 2001
    assert client.get('/api/admin/statistics', headers=admin, params={'range': 'month'}).json()['data']['users'] == 4


def test_consent_is_enforced_by_backend_before_health_access(setup):
    client, sessions = setup
    token = client.post('/api/auth/login', json={'phone': '13000000002', 'password': 'Abc123456'}).json()['data']['token']
    headers = {'Authorization': 'Bearer ' + token}
    assert client.get('/api/auth/me', headers=headers).json()['data']['privacy_consent'] is None
    assert client.get('/api/profiles', headers=headers).status_code == 403
    assert client.post('/api/profiles', headers=headers, json={'name': '未授权档案'}).status_code == 403
    assert client.post('/api/auth/privacy-consent', headers=headers, json={'accepted': False}).json()['code'] == 2001
    assert client.get('/api/profiles', headers=headers).status_code == 403
    client.post('/api/auth/privacy-consent', headers=headers, json={'accepted': True})
    assert client.get('/api/profiles', headers=headers).json()['code'] == 0


def test_phone_update_unique_validation_and_new_login(setup):
    client, _ = setup
    elder = login(client, 2)
    assert client.put('/api/auth/me', headers=elder, json={'name': '张桂兰', 'phone': '13000000003'}).json()['code'] == 2001
    assert client.put('/api/auth/me', headers=elder, json={'name': '张桂兰', 'phone': 'bad'}).json()['code'] == 2001
    assert client.put('/api/auth/me', headers=elder, json={'name': '张桂兰', 'phone': '13800000001'}).json()['data']['phone'] == '13800000001'
    assert client.post('/api/auth/login', json={'phone': '13800000001', 'password': 'Abc123456'}).json()['code'] == 0


def test_statistics_range_matches_real_counts(setup):
    client, _ = setup
    elder, admin, family = login(client, 2), login(client, 1), login(client, 3)
    warning_id = input_record(client, elder, first_profile(client, elder)).json()['data']['warning_id']
    client.post(f'/api/alerts/{warning_id}/handle', headers=family, json={'result': '今日联系确认', 'action': 'CONTACTED'})
    result = client.get('/api/admin/statistics', headers=admin, params={'range': '1d'}).json()['data']
    assert result['registered_users'] == 4
    assert result['warnings'] == 1
    assert result['pending'] == 0
    assert result['handled'] == 1
    assert result['module_totals']['health_records'] == 1
    assert result['module_totals']['family_binds'] == 1
    assert sum(result['chart']['warnings']) == result['warnings']
    assert sum(result['chart']['users']) == result['registered_users']


def test_multiple_profiles_self_and_delegated_are_isolated(setup):
    client, sessions = setup
    elder, family, care, admin = [login(client, index) for index in (2, 3, 4, 1)]
    source_id = first_profile(client, elder)
    own = client.post('/api/profiles', headers=elder, json={'name': '本人第二档案'}).json()
    assert own['code'] == 0
    own_id = own['data']['profile_id']
    assert len(client.get('/api/profiles', headers=elder).json()['data']) == 2
    assert client.get(f'/api/profiles/{own_id}', headers=family).status_code == 403
    assert client.post('/api/profiles', headers=family, json={'name': '任意代建'}).json()['code'] == 2001
    family_created = client.post('/api/profiles', headers=family, json={'name': '家属代建档案', 'source_profile_id': source_id}).json()
    assert family_created['code'] == 0, family_created
    family_id = family_created['data']['profile_id']
    assert client.get(f'/api/profiles/{family_id}', headers=family).json()['code'] == 0
    assert client.get(f'/api/profiles/{family_id}', headers=elder).json()['code'] == 0
    assert client.get(f'/api/profiles/{family_id}', headers=care).status_code == 403
    care_created = client.post('/api/profiles', headers=care, json={'name': '护工代建档案', 'source_profile_id': source_id}).json()
    assert care_created['code'] == 0
    care_id = care_created['data']['profile_id']
    assert client.get(f'/api/profiles/{care_id}', headers=care).json()['code'] == 0
    assert client.get(f'/api/profiles/{care_id}', headers=family).status_code == 403
    # Supplying an unrelated owner must never override the authorized source.
    with sessions() as db:
        admin_id = db.scalar(select(User.id).where(User.role == 'ADMIN'))
    assert client.post('/api/profiles', headers=family, json={'name': '跨户攻击', 'source_profile_id': source_id, 'user_id': admin_id}).status_code == 403
    assert client.post('/api/profiles', headers=admin, json={'name': '管理员本人档案', 'user_id': admin_id}).json()['code'] == 2001


def test_binding_specific_profile_requires_matching_elder_phone(setup):
    client, _ = setup
    elder, family = login(client, 2), login(client, 3)
    second_id = client.post('/api/profiles', headers=elder, json={'name': '待确认第二档案'}).json()['data']['profile_id']
    wrong = client.post('/api/family/bind', headers=family, json={'phone': '13000000001', 'profile_id': second_id, 'relation': '儿子'})
    assert wrong.json()['code'] == 2002
    result = client.post('/api/family/bind', headers=family, json={'phone': '13000000002', 'profile_id': second_id, 'relation': '儿子'}).json()
    assert result['code'] == 0
    assert result['data']['profile_id'] == second_id
    assert client.get(f'/api/profiles/{second_id}', headers=family).status_code == 403
    client.put(f'/api/family/bind/{result["data"]["bind_id"]}/confirm', headers=elder, json={'action': 'APPROVE'})
    assert client.get(f'/api/profiles/{second_id}', headers=family).json()['code'] == 0


def test_new_binding_can_read_existing_warning_without_historic_unread_blast(setup):
    client, _ = setup
    elder = login(client, 2)
    profile_id = first_profile(client, elder)
    warning_id = input_record(client, elder, profile_id).json()['data']['warning_id']
    client.post('/api/auth/register', json={'phone': '13800000000', 'password': 'Abc123456', 'name': '新授权家属', 'role': 'FAMILY'})
    token = client.post('/api/auth/login', json={'phone': '13800000000', 'password': 'Abc123456'}).json()['data']['token']
    family = {'Authorization': 'Bearer ' + token}
    client.post('/api/auth/privacy-consent', headers=family, json={'accepted': True})
    bind = client.post('/api/family/bind', headers=family, json={'phone': '13000000002', 'relation': '女儿'}).json()['data']
    client.put(f'/api/family/bind/{bind["bind_id"]}/confirm', headers=elder, json={'action': 'APPROVE'})
    assert client.get('/api/alerts', headers=family).json()['data']['total'] == 1
    assert client.get('/api/notifications/unread', headers=family).json()['data']['unread'] == 0
    assert client.get(f'/api/alerts/{warning_id}', headers=family).json()['data']['my_read_status'] == 'READ'
    assert client.get('/api/notifications/unread', headers=family).json()['data']['unread'] == 0


def test_care_time_filter_uses_measurement_time_combines_state_and_keeps_scope(setup):
    client, sessions = setup
    elder, care = login(client, 2), login(client, 4)
    first_id = first_profile(client, elder)
    input_record(client, elder, first_id)
    old_id = client.post('/api/profiles', headers=care, json={'name': '历史测量老人', 'source_profile_id': first_id}).json()['data']['profile_id']
    hidden_id = client.post('/api/profiles', headers=elder, json={'name': '未分配护工档案'}).json()['data']['profile_id']
    with sessions() as db:
        db.add(HealthRecord(profile_id=old_id, type='BLOOD_PRESSURE', val1=120, val2=80, measured_at=now()-timedelta(days=10), is_abnormal=0))
        db.add(HealthRecord(profile_id=hidden_id, type='BLOOD_PRESSURE', val1=120, val2=80, measured_at=now()-timedelta(minutes=1), is_abnormal=0))
        db.commit()
    recent = {'start_at': (now()-timedelta(days=1)).isoformat(timespec='seconds'), 'end_at': now().isoformat(timespec='seconds')}
    rows = client.get('/api/care/elders', headers=care, params=recent).json()['data']
    assert [row['profile_id'] for row in rows] == [first_id]
    older = {'start_at': (now()-timedelta(days=11)).isoformat(timespec='seconds'), 'end_at': (now()-timedelta(days=9)).isoformat(timespec='seconds')}
    assert [row['profile_id'] for row in client.get('/api/care/elders', headers=care, params=older).json()['data']] == [old_id]
    assert client.get('/api/care/elders', headers=care, params=dict(older, status='ABNORMAL')).json()['data'] == []
    assert client.get('/api/care/elders', headers=care, params={'start_at': recent['end_at'], 'end_at': recent['start_at']}).json()['code'] == 2001
    assert client.get('/api/care/elders', headers=care, params={'start_at': '2026-01-01T00:00:00Z'}).json()['code'] == 2001
    assert client.get('/api/care/elders', headers=care).json()['data'][0]['profile_id'] == first_id


def test_recovery_only_changes_expired_pending_summaries(setup):
    client, sessions = setup
    from app.services.recovery import recover_pending_summaries, summary_job
    elder = login(client, 2)
    profile_id = first_profile(client, elder)
    recent_id = input_record(client, elder, profile_id).json()['data']['warning_id']
    with sessions() as db:
        rows = []
        for state in ('PENDING', 'FAILED', 'SUCCESS', 'SKIPPED'):
            row = HealthWarning(profile_id=profile_id, type='BLOOD_PRESSURE', value_text='190/110', level=3,
                                status='PROCESSING', summary_status=state, ai_summary='原摘要' if state != 'PENDING' else None,
                                create_time=now()-timedelta(days=1), update_time=now()-timedelta(days=1))
            db.add(row)
            rows.append(row)
        db.commit()
        ids = [row.id for row in rows]
        with summary_job(ids[0]) as claimed:
            assert claimed is True
            assert recover_pending_summaries(db) == 0
            db.commit()
        assert recover_pending_summaries(db) == 1
        db.commit()
        db.expire_all()
        assert db.get(HealthWarning, recent_id).summary_status == 'PENDING'
        assert db.get(HealthWarning, ids[0]).summary_status == 'FAILED'
        assert db.get(HealthWarning, ids[0]).status == 'PROCESSING'
        for identifier, state in zip(ids[1:], ('FAILED', 'SUCCESS', 'SKIPPED')):
            assert db.get(HealthWarning, identifier).summary_status == state
            assert db.get(HealthWarning, identifier).ai_summary == '原摘要'


def test_recovery_is_opt_in_in_production_and_disabled_for_multiple_workers(monkeypatch):
    from app.services.recovery import recovery_enabled
    monkeypatch.setenv('DEMO_MODE', 'false')
    monkeypatch.setenv('WEB_CONCURRENCY', '1')
    monkeypatch.setenv('SUMMARY_RECOVERY_ENABLED', 'auto')
    assert recovery_enabled() is False
    monkeypatch.setenv('DEMO_MODE', 'true')
    assert recovery_enabled() is True
    monkeypatch.setenv('WEB_CONCURRENCY', '2')
    monkeypatch.setenv('SUMMARY_RECOVERY_ENABLED', 'true')
    assert recovery_enabled() is False
    monkeypatch.setenv('WEB_CONCURRENCY', '1')
    assert recovery_enabled() is True
