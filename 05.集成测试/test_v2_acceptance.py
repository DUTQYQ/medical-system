"""B-scope acceptance; MySQL races run only on disposable marked databases."""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from sqlalchemy import select, func
from conftest import login, expect
from app.core.database import SessionLocal, engine, now
from app.models import CareRelation, HealthAssessment, ConsultationIntake, User, ProfileThresholdVersion
from app.models.care_services import Activity, Equipment, EquipmentLoan, ServiceRequest


def request(client, elder, profile_id=2001):
    return expect(client.post('/api/services/requests', headers=elder, json={'profile_id': profile_id,
        'category': 'ENTERTAINMENT', 'title': '希望下午打牌', 'description': '请确认时间及活动名额', 'location': '一楼活动室'}))


def activity(client, admin, capacity=1):
    return expect(client.post('/api/services/activities', headers=admin, json={'title': '验收棋牌活动',
        'category': 'ENTERTAINMENT', 'start_at': (now()+timedelta(days=1)).isoformat(),
        'end_at': (now()+timedelta(days=1, hours=1)).isoformat(), 'location': '一楼活动室', 'capacity': capacity}))


def equipment(client, admin):
    return expect(client.post('/api/services/equipment', headers=admin,
        json={'name': '验收设备', 'total': 1, 'description': '临时库验收记录'}))


def test_first_intake_confirmed_facts_and_readable_rule_advice(client):
    elder = login(client, 2)
    started = expect(client.post('/api/ai/intake/start', headers=elder, json={'profile_id': 2001}))
    again = expect(client.post('/api/ai/intake/start', headers=elder, json={'profile_id': 2001}))
    assert started['intake_id'] == again['intake_id'] and started['next_question']
    values = ['丰富日常生活', '打牌', '需要陪同', '出行陪同', '清淡', '夜间易醒']
    current, entries = started, []
    for value in values:
        key = current['next_question']['key']
        current = expect(client.post(f"/api/ai/intake/{started['intake_id']}/answer", headers=elder,
            json={'key': key, 'value': value}))
        entries.append({'key': key, 'value': value})
    assert expect(client.get('/api/ai/facts?profile_id=2001', headers=elder)) == []
    facts = expect(client.post(f"/api/ai/intake/{started['intake_id']}/confirm", headers=elder, json={'entries': entries}))
    assert len(facts) == 6 and all(item['version'] == 1 for item in facts)
    card = expect(client.post('/api/ai/advice', headers=elder, json={'profile_id': 2001}))
    assert card['mode'] == 'RULE' and len(card['sections']) == 4
    assert card['actions'] and all(section['items'] for section in card['sections'])
    expect(client.get('/api/ai/facts?profile_id=2001', headers=login(client, 6)), 1002)


def test_individual_threshold_and_historical_snapshot(client):
    elder, care, admin = [login(client, i) for i in (2, 4, 1)]
    body = {'profile_id': 2001, 'type': 'BLOOD_PRESSURE', 'values': {'systolic': 185, 'diastolic': 80},
            'measured_at': (now()-timedelta(seconds=1)).isoformat()}
    old = expect(client.post('/api/health/records', headers=elder, json=body))
    proposal = expect(client.post('/api/profiles/2001/threshold-proposals', headers=care,
        json={'indicator': 'BLOOD_PRESSURE_SYSTOLIC', 'level0_range': '90~189', 'level1_range': '190~199',
              'level2_range': '200~209', 'level3_range': '<90 或 >=210', 'reason': '测试个体照护方案'}))
    assert expect(client.post('/api/health/records', headers=elder, json=body))['risk_level'] == 3
    expect(client.post(f"/api/threshold-proposals/{proposal['proposal_id']}/review", headers=admin,
        json={'approve': True, 'note': '核对照护方案后批准'}))
    assert expect(client.post('/api/health/records', headers=elder, json=body))['risk_level'] == 0
    body['profile_id'] = 2002
    assert expect(client.post('/api/health/records', headers=login(client, 6), json=body))['risk_level'] == 3
    trend = expect(client.get('/api/health/trend?profile_id=2001&type=BLOOD_PRESSURE', headers=elder))
    assert all(point['level'] == 3 for point in trend['abnormal_points'])
    warning = expect(client.get(f"/api/alerts/{old['warning_id']}", headers=elder))
    assert warning['assessment']['thresholds']['BLOOD_PRESSURE_SYSTOLIC']['source'] == 'DEFAULT'


def test_service_lifecycle_notice_read_and_revoke(client):
    elder, family, care = [login(client, i) for i in (2, 3, 4)]
    item = request(client, elder)
    notices = expect(client.get('/api/services/notifications', headers=family))
    expect(client.post(f"/api/services/notifications/{notices['list'][0]['id']}/read", headers=family))
    assert expect(client.get(f"/api/services/requests/{item['id']}", headers=family))['status'] == 'SUBMITTED'
    for status in ('ACCEPTED', 'IN_PROGRESS', 'COMPLETED'):
        expect(client.post(f"/api/services/requests/{item['id']}/transition", headers=care,
            json={'status': status, 'result': '已协助完成活动安排' if status == 'COMPLETED' else ''}))
    detail = expect(client.get(f"/api/services/requests/{item['id']}", headers=elder))
    assert detail['status'] == 'COMPLETED' and len(detail['events']) == 4
    expect(client.delete('/api/family/bind/9001', headers=family))
    expect(client.get(f"/api/services/requests/{item['id']}", headers=family), 1002)
    assert expect(client.get('/api/services/notifications', headers=family))['total'] == 0


def test_call_without_health_consent_idempotent_and_no_care_escalation(client):
    elder = login(client, 2, consent=False)
    expect(client.get('/api/health/records?profile_id=2001', headers=elder), 1002)
    with SessionLocal() as db:
        relation = db.get(CareRelation, 8001); relation.status = 0; db.commit()
    body = {'profile_id': 2001, 'location': '二楼房间', 'description': '需要工作人员协助'}
    first = expect(client.post('/api/services/calls', headers=elder, json=body))
    second = expect(client.post('/api/services/calls', headers=elder, json=body))
    assert first['id'] == second['id'] and second['reused']
    assert first['priority'] == 3 and first['escalated_at'] and first['assigned_to'] == 1
    admin_notices = expect(client.get('/api/services/notifications', headers=login(client, 1)))
    assert admin_notices['unread_count'] >= 1


def test_activity_capacity_cancel_and_reregister(client):
    elder, other, admin = [login(client, i) for i in (2, 6, 1)]
    item = activity(client, admin)
    registration = expect(client.post(f"/api/services/activities/{item['id']}/register", headers=elder, json={'profile_id': 2001}))
    expect(client.post(f"/api/services/activities/{item['id']}/register", headers=other, json={'profile_id': 2002}), 2001)
    expect(client.post(f"/api/services/registrations/{registration['id']}/transition", headers=elder, json={'status': 'CANCELLED'}))
    expect(client.post(f"/api/services/activities/{item['id']}/register", headers=other, json={'profile_id': 2002}))
    with SessionLocal() as db:
        assert db.get(Activity, item['id']).reserved_count == 1


def test_equipment_issued_returned_once_and_damaged_not_available(client):
    elder, care, admin = [login(client, i) for i in (2, 4, 1)]
    item = equipment(client, admin)
    borrowed = expect(client.post(f"/api/services/equipment/{item['id']}/request", headers=elder,
        json={'profile_id': 2001, 'quantity': 1, 'location': '二楼房间'}))
    expect(client.post(f"/api/services/requests/{borrowed['id']}/transition", headers=care, json={'status': 'ACCEPTED'}))
    loan = expect(client.get('/api/services/loans', headers=care))[0]
    for _ in range(2):
        expect(client.post(f"/api/services/loans/{loan['id']}/return", headers=care, json={'damaged': True, 'note': '转维修'}))
    with SessionLocal() as db:
        device = db.get(Equipment, item['id'])
        assert device.available == 0 and device.damaged == 1


def test_confirmed_skipped_intake_allows_later_explicit_fact(client):
    elder = login(client, 2)
    current = expect(client.post('/api/ai/intake/start', headers=elder, json={'profile_id': 2001}))
    intake_id = current['intake_id']
    while current['next_question']:
        current = expect(client.post(f'/api/ai/intake/{intake_id}/answer', headers=elder,
            json={'key': current['next_question']['key'], 'skip': True}))
    expect(client.post(f'/api/ai/intake/{intake_id}/confirm', headers=elder, json={'entries': []}))
    fact = expect(client.post('/api/ai/facts', headers=elder,
        json={'profile_id': 2001, 'key': 'entertainment_preferences', 'value': '打牌与阅读'}))
    assert fact['version'] == 1 and fact['value'] == '打牌与阅读'
    updated = expect(client.post('/api/ai/facts', headers=elder,
        json={'profile_id': 2001, 'key': 'entertainment_preferences', 'value': '阅读'}))
    assert updated['fact_id'] == fact['fact_id'] and updated['version'] == 2


def test_activity_cancel_closes_registration_and_notifies(client):
    elder, admin, care = [login(client, i) for i in (2, 1, 4)]
    item = activity(client, admin)
    registered = expect(client.post(f"/api/services/activities/{item['id']}/register", headers=elder, json={'profile_id': 2001}))
    expect(client.post(f"/api/services/activities/{item['id']}/transition", headers=care,
        json={'status': 'CANCELLED'}), 1002)
    expect(client.post(f"/api/services/activities/{item['id']}/transition", headers=admin, json={'status': 'CANCELLED'}))
    expect(client.post(f"/api/services/activities/{item['id']}/register", headers=elder, json={'profile_id': 2001}), 2001)
    with SessionLocal() as db:
        assert db.get(Activity, item['id']).reserved_count == 0
    registrations = expect(client.get(f"/api/services/activities/{item['id']}/registrations", headers=elder))
    assert registrations[0]['status'] == 'CANCELLED'


def test_equipment_maintenance_and_configured_call_timeout(client):
    elder, care, admin = [login(client, i) for i in (2, 4, 1)]
    device = equipment(client, admin)
    requested = expect(client.post(f"/api/services/equipment/{device['id']}/request", headers=elder,
        json={'profile_id': 2001, 'quantity': 1, 'location': '二楼房间'}))
    expect(client.post(f"/api/services/requests/{requested['id']}/transition", headers=care, json={'status': 'ACCEPTED'}))
    expect(client.put(f"/api/services/equipment/{device['id']}", headers=admin, json={'total': 0}), 2001)
    expect(client.put(f"/api/services/equipment/{device['id']}", headers=admin, json={'enabled': False}))
    loan = expect(client.get('/api/services/loans', headers=care))[0]
    expect(client.post(f"/api/services/loans/{loan['id']}/return", headers=care, json={'damaged': False}))
    expect(client.put(f"/api/services/equipment/{device['id']}", headers=admin, json={'total': 2, 'enabled': True}))
    with SessionLocal() as db:
        assert db.get(Equipment, device['id']).available == 2
    assert expect(client.put('/api/services/settings', headers=admin, json={'call_timeout_seconds': 30}))['call_timeout_seconds'] == 30
    expect(client.put('/api/services/settings', headers=care, json={'call_timeout_seconds': 60}), 1002)


@pytest.mark.skipif(engine.dialect.name != 'mysql', reason='Requires MySQL row locks')
def test_concurrent_first_intake_only_one_instance(client):
    headers = [login(client, 2), login(client, 3)]
    def start(header):
        return expect(client.post('/api/ai/intake/start', headers=header, json={'profile_id': 2001}))
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(start, headers))
    assert results[0]['intake_id'] == results[1]['intake_id']
    with SessionLocal() as db:
        assert db.scalar(select(func.count()).select_from(ConsultationIntake)) == 1


@pytest.mark.skipif(engine.dialect.name != 'mysql', reason='Requires MySQL row locks')
def test_concurrent_activity_last_place_never_overbooks(client):
    admin, elder, other = [login(client, i) for i in (1, 2, 6)]
    item = activity(client, admin)
    def register(pair):
        header, profile_id = pair
        return client.post(f"/api/services/activities/{item['id']}/register", headers=header, json={'profile_id': profile_id}).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(register, [(elder, 2001), (other, 2002)]))
    assert sorted(result['code'] for result in results) == [0, 2001], results
    with SessionLocal() as db:
        assert db.get(Activity, item['id']).reserved_count == 1


@pytest.mark.skipif(engine.dialect.name != 'mysql', reason='Requires MySQL row locks')
def test_concurrent_equipment_last_unit_never_overissues(client):
    admin, elder, other = [login(client, i) for i in (1, 2, 6)]
    item = equipment(client, admin)
    requests = [expect(client.post(f"/api/services/equipment/{item['id']}/request", headers=header,
        json={'profile_id': profile_id, 'quantity': 1, 'location': '验收位置'})) for header, profile_id in [(elder, 2001), (other, 2002)]]
    def issue(request):
        return client.post(f"/api/services/requests/{request['id']}/transition", headers=admin, json={'status': 'ACCEPTED'}).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(issue, requests))
    assert sorted(result['code'] for result in results) == [0, 2001], results
    with SessionLocal() as db:
        assert db.get(Equipment, item['id']).available == 0
        assert db.scalar(select(func.count()).select_from(EquipmentLoan)) == 1


@pytest.mark.skipif(engine.dialect.name != 'mysql', reason='Requires MySQL row locks')
def test_concurrent_staff_accept_one_event(client):
    elder, care, admin = [login(client, i) for i in (2, 4, 1)]
    item = request(client, elder)
    def accept(header):
        return client.post(f"/api/services/requests/{item['id']}/transition", headers=header, json={'status': 'ACCEPTED'}).json()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(accept, [care, admin]))
    assert sorted(result['code'] for result in results) == [0, 2001], results
    detail = expect(client.get(f"/api/services/requests/{item['id']}", headers=elder))
    assert len(detail['events']) == 2


@pytest.mark.skipif(engine.dialect.name != 'mysql', reason='Requires MySQL REPEATABLE READ snapshots')
def test_measurement_sees_approved_threshold_after_earlier_auth_snapshot(client):
    from app.services.personal_threshold import assess
    from app.core.permissions import get_profile
    elder, care, admin = [login(client, i) for i in (2, 4, 1)]
    proposal = expect(client.post('/api/profiles/2001/threshold-proposals', headers=care,
        json={'indicator': 'BLOOD_PRESSURE_SYSTOLIC', 'level0_range': '90~189', 'level1_range': '190~199',
              'level2_range': '200~209', 'level3_range': '<90 或 >=210', 'reason': '验证旧快照后的实时审核'}))
    with SessionLocal() as delayed_measurement:
        user = delayed_measurement.get(User, 2)
        assert delayed_measurement.scalar(select(ProfileThresholdVersion.id).where(ProfileThresholdVersion.status == 'APPROVED')) is None
        expect(client.post(f"/api/threshold-proposals/{proposal['proposal_id']}/review", headers=admin,
            json={'approve': True, 'note': '批准后录入必须按当前配置'}))
        get_profile(delayed_measurement, user, 2001, lock=True)
        level, rules = assess(delayed_measurement, 2001, 'BLOOD_PRESSURE', 185, 80)
        assert level == 0 and rules['BLOOD_PRESSURE_SYSTOLIC']['version_id'] == proposal['proposal_id']


@pytest.mark.skipif(engine.dialect.name != 'mysql', reason='Requires MySQL REPEATABLE READ snapshots')
def test_service_write_rechecks_binding_after_earlier_auth_snapshot(client):
    from app.services.care_services import get_service_profile
    from app.core.errors import APIError
    family = login(client, 3)
    with SessionLocal() as delayed_request:
        user = delayed_request.get(User, 3)
        # Authentication's consistent read establishes the earlier snapshot.
        assert delayed_request.scalar(select(func.count()).select_from(User)) == 6
        expect(client.delete('/api/family/bind/9001', headers=family))
        with pytest.raises(APIError) as rejected:
            get_service_profile(delayed_request, user, 2001, lock=True)
        assert rejected.value.code == 1002
