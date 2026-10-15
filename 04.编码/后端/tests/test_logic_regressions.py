"""Regression scenarios from the role and workflow audit; isolated SQLite only."""
from datetime import timedelta
from sqlalchemy import select, func
from test_business import setup, login, first_profile, input_record
from app.core.database import now
from app.models import HealthRecord, HealthRecordVoid, HealthWarning, SysConfig
from app.agent.workflow import history_context


def test_family_follow_up_does_not_close_processing_warning(setup):
    client, _ = setup
    elder, family, care = [login(client, n) for n in (2, 3, 4)]
    pid = first_profile(client, elder)
    wid = input_record(client, elder, pid).json()['data']['warning_id']
    assert client.put(f'/api/alerts/{wid}/status', headers=care, json={'status': 'PROCESSING'}).status_code == 200
    for result in ['电话联系，等待现场复核', '已安排家属探访']:
        response = client.post(f'/api/alerts/{wid}/handle', headers=family, json={'action': 'CONTACTED', 'result': result})
        assert response.json()['data']['status'] == 'PROCESSING'
        assert response.json()['data']['handle']['record_type'] == 'FOLLOW_UP'
    assert client.post(f'/api/alerts/{wid}/handle', headers=care, json={'action': 'OBSERVE', 'result': '工作人员完成复核'}).json()['data']['status'] == 'RESOLVED'


def test_void_is_authorized_audited_idempotent_and_excluded_from_current_data(setup):
    client, sessions = setup
    elder, family, care, admin = [login(client, n) for n in (2, 3, 4, 1)]
    pid = first_profile(client, elder)
    item = input_record(client, care, pid).json()['data']
    rid, wid = item['record_id'], item['warning_id']
    path = f'/api/health/records/{rid}'
    assert client.request('DELETE', path, headers=family, json={'reason': '家属尝试删除护工数据'}).status_code == 403
    assert client.delete(path, headers=care).status_code == 422
    for _ in range(2):
        response = client.request('DELETE', path, headers=care, json={'reason': '复核确认输入错误'})
        assert response.json()['data']['is_voided'] is True
    assert client.get('/api/health/records', headers=elder, params={'profile_id': pid}).json()['data']['total'] == 0
    audited = client.get('/api/health/records', headers=family, params={'profile_id': pid, 'include_voided': True}).json()['data']['list'][0]
    assert audited['values']['systolic'] == 181 and audited['void_audit']['reason'] == '复核确认输入错误'
    assert audited['can_void'] is False
    assert client.get('/api/health/trend', headers=elder, params={'profile_id': pid, 'type': 'BLOOD_PRESSURE'}).json()['data']['dates'] == []
    warning = client.get(f'/api/alerts/{wid}', headers=care).json()['data']
    assert warning['status'] == 'PENDING' and warning['record_void_audit']['reason'] == '复核确认输入错误'
    with sessions() as db:
        assert db.get(HealthRecord, rid) is not None
        assert db.get(HealthWarning, wid).record_id == rid
        assert db.scalar(select(func.count(HealthRecordVoid.id))) == 1
        assert history_context(db, pid)[0] == []
    # Administrators can void records authored by another user after recording why.
    normal = input_record(client, elder, pid, values={'systolic': 120, 'diastolic': 80}).json()['data']
    assert client.request('DELETE', f'/api/health/records/{normal["record_id"]}', headers=admin,
                          json={'reason': '管理员核验重复测量'}).status_code == 200


def test_default_threshold_rejects_uncovered_domain_without_breaking_entry(setup):
    client, _ = setup
    elder, admin = [login(client, n) for n in (2, 1)]
    pid = first_profile(client, elder)
    old = next(r for r in client.get('/api/admin/thresholds', headers=admin).json()['data'] if r['indicator'] == 'HEART_RATE')
    bad = {'level0_range': '60~80', 'level1_range': '81~90', 'level2_range': '91~100', 'level3_range': '101~110'}
    assert client.put(f'/api/admin/thresholds/{old["config_id"]}', headers=admin, json=bad).status_code == 400
    unchanged = next(r for r in client.get('/api/admin/thresholds', headers=admin).json()['data'] if r['indicator'] == 'HEART_RATE')
    assert unchanged == old
    assert input_record(client, elder, pid, type='HEART_RATE', values={'value': 50}).status_code == 200


def test_care_status_distinguishes_no_data_stale_and_no_pending_alert(setup):
    client, sessions = setup
    elder, care = [login(client, n) for n in (2, 4)]
    pid = first_profile(client, elder)
    def state():
        return client.get('/api/care/elders', headers=care).json()['data'][0]
    assert state()['status'] == 'UNKNOWN' and state()['data_status'] == 'NO_DATA'
    result = client.post('/api/health/records', headers=elder, json={'profile_id': pid, 'type': 'HEART_RATE',
        'values': {'value': 75}, 'measured_at': (now()-timedelta(days=4)).isoformat()}).json()['data']
    assert state()['status'] == 'STALE'
    with sessions() as db:
        db.get(HealthRecord, result['record_id']).measured_at = now()-timedelta(hours=2)
        db.commit()
    assert state()['status'] == 'NO_PENDING_ALERT'
    with sessions() as db:
        db.scalar(select(SysConfig).where(SysConfig.config_key == 'care_health_data_fresh_hours')).config_value = '1'
        db.commit()
    assert state()['status'] == 'STALE'
    assert client.get('/api/care/elders', headers=care, params={'status': 'STALE'}).json()['data'][0]['profile_id'] == pid
