"""Review regressions for dev-liang integration with the approved v2 workflows."""
import json
from datetime import timedelta, date
import pytest
from sqlalchemy import select
from test_business import setup, login, first_profile, input_record
from app.core.database import now
from app.models import Activity, ActivityTemplate, HealthRecord, SysConfig, ElderProfile
from app.services.recommend import _match


def status(client, headers, pid, metric='HEART_RATE'):
    response = client.get('/api/health/status', headers=headers, params={'profile_id': pid})
    assert response.status_code == 200, response.text
    return next(row for row in response.json()['data'] if row['type'] == metric)


def record(client, headers, pid, value, hours=0):
    response = client.post('/api/health/records', headers=headers, json={'profile_id': pid, 'type': 'HEART_RATE',
        'values': {'value': value}, 'measured_at': (now()-timedelta(hours=hours, seconds=1)).isoformat()})
    assert response.status_code == 200, response.text
    return response.json()['data']


def template(client, admin, **extra):
    payload = {'code': 'REVIEW_ACTIVITY', 'name': '审核测试活动', 'category': '娱乐', 'intensity': 'LOW', 'rules': {}}
    payload.update(extra)
    response = client.post('/api/activities', headers=admin, json=payload)
    assert response.status_code == 200, response.text
    return response.json()['data']


def test_activity_models_are_distinct_and_no_data_is_unknown(setup):
    client, _ = setup
    elder = login(client, 2)
    pid = first_profile(client, elder)
    assert Activity.__tablename__ == 'care_activity' and ActivityTemplate.__tablename__ == 'activity'
    rows = client.get('/api/health/status', headers=elder, params={'profile_id': pid}).json()['data']
    assert len(rows) == 5
    assert all(row['risk_level'] is None and row['fluctuation_flag'] is None and row['judgement'] == '未记录' for row in rows)
    recommendations = client.get('/api/activities/recommend', headers=elder, params={'profile_id': pid}).json()['data']
    assert len(recommendations) == 6 and all(row['suitability'] == '需确认' for row in recommendations)


def test_baseline_excludes_current_voided_and_future_samples(setup):
    client, sessions = setup
    elder = login(client, 2)
    pid = first_profile(client, elder)
    record(client, elder, pid, 60, 5)
    record(client, elder, pid, 60, 4)
    bad = record(client, elder, pid, 150, 3)
    latest = record(client, elder, pid, 90, 1)
    assert client.request('DELETE', f'/api/health/records/{bad["record_id"]}', headers=elder, json={'reason': '误录'}).status_code == 200
    with sessions() as db:
        db.add(HealthRecord(profile_id=pid, type='HEART_RATE', val1=999, measured_at=now()+timedelta(days=1), is_abnormal=1))
        db.commit()
    result = status(client, elder, pid)
    assert result['record_id'] == latest['record_id']
    assert result['baseline_count'] == 2 and result['baseline_mean'] == 60
    assert result['fluctuation_ratio'] == 0.5 and result['fluctuation_flag'] is True
    assert result['judgement'] == '需关注（波动）'
    assert client.request('DELETE', f'/api/health/records/{latest["record_id"]}', headers=elder, json={'reason': '再次复核误录'}).status_code == 200
    assert status(client, elder, pid)['latest']['value'] == 60


def test_pressure_baseline_compares_both_components(setup):
    client, _ = setup
    elder = login(client, 2)
    pid = first_profile(client, elder)
    for hours, diastolic in [(3, 70), (2, 70), (1, 95)]:
        assert client.post('/api/health/records', headers=elder, json={'profile_id': pid, 'type': 'BLOOD_PRESSURE',
            'values': {'systolic': 120, 'diastolic': diastolic}, 'measured_at': (now()-timedelta(hours=hours)).isoformat()}).status_code == 200
    result = status(client, elder, pid, 'BLOOD_PRESSURE')
    assert result['baseline_components'][0]['flag'] is False
    assert result['baseline_components'][1]['flag'] is True
    assert result['fluctuation_flag'] is True


def test_stale_disabled_and_insufficient_baselines_do_not_claim_healthy(setup):
    client, sessions = setup
    elder = login(client, 2)
    pid = first_profile(client, elder)
    record(client, elder, pid, 75, 96)
    result = status(client, elder, pid)
    assert result['risk_level'] is None and result['judgement'] == '数据待更新'
    assert result['fluctuation_flag'] is None
    record(client, elder, pid, 75, 1)
    result = status(client, elder, pid)
    assert result['baseline_mean'] is None and result['fluctuation_flag'] is None
    with sessions() as db:
        db.scalar(select(SysConfig).where(SysConfig.config_key == 'HEART_RATE')).enabled = 0
        db.commit()
    assert status(client, elder, pid)['judgement'] == '检测已停用'


def test_status_uses_approved_rules_without_rewriting_historic_evidence(setup):
    client, _ = setup
    elder, care, admin = [login(client, i) for i in (2, 4, 1)]
    pid = first_profile(client, elder)
    original = input_record(client, elder, pid, values={'systolic': 185, 'diastolic': 80}).json()['data']
    body = {'indicator': 'BLOOD_PRESSURE_SYSTOLIC', 'level0_range': '90~189', 'level1_range': '190~199',
        'level2_range': '200~209', 'level3_range': '<90 或 >=210', 'reason': '测试已确认照护方案'}
    proposal = client.post(f'/api/profiles/{pid}/threshold-proposals', headers=care, json=body).json()['data']
    assert status(client, elder, pid, 'BLOOD_PRESSURE')['risk_level'] == 3
    assert client.post(f'/api/threshold-proposals/{proposal["proposal_id"]}/review', headers=admin,
        json={'approve': True, 'note': '核验后通过'}).status_code == 200
    result = status(client, elder, pid, 'BLOOD_PRESSURE')
    assert result['risk_level'] == 0 and result['recorded_assessment']['risk_level'] == 3
    assert result['normal_ranges'][0]['source'] == 'PERSONAL'
    trend = client.get('/api/health/trend', headers=elder, params={'profile_id': pid, 'type': 'BLOOD_PRESSURE'}).json()['data']
    assert trend['abnormal_points'][0]['level'] == 3
    assert client.get(f'/api/alerts/{original["warning_id"]}', headers=care).json()['data']['level'] == 3


def test_age_alone_does_not_change_the_configured_thresholds(setup):
    client, sessions = setup
    elder = login(client, 2)
    pid = first_profile(client, elder)
    original = input_record(client, elder, pid, values={'systolic': 145, 'diastolic': 85}).json()['data']
    assert original['risk_level'] == 1
    with sessions() as db:
        db.get(ElderProfile, pid).birthday = date(1990, 1, 1)
        db.commit()
    assert status(client, elder, pid, 'BLOOD_PRESSURE')['risk_level'] == 1


@pytest.mark.parametrize('rules', [None, [], {'unknown': True}, {'suitable': {'min_age': True}},
    {'suitable': {'min_age': 'old'}}, {'suitable': {'min_age': 90, 'max_age': 50}},
    {'avoid': {'seasons_in': ['invalid']}}, {'caution': {'max_risk_level': 'low'}},
    {'suitable': {'seasons_in': ['winter'], 'seasons_not_in': ['winter']}}])
def test_activity_rule_validation_rejects_bad_types_instead_of_500(setup, rules):
    client, _ = setup
    admin = login(client, 1)
    result = client.post('/api/activities', headers=admin,
        json={'code': 'BAD_RULE', 'name': '无效规则', 'rules': rules})
    assert result.status_code == 422


def test_rule_groups_use_and_and_season_exclusion_has_correct_direction():
    ctx = {'age': 78, 'chronic_tags': ['高血压'], 'tags_known': True, 'season': 'autumn'}
    assert _match({'min_age': 60, 'max_age': 70}, ctx)[0] is False
    assert _match({'min_age': 60, 'max_age': 90, 'chronic_in': ['糖尿病']}, ctx)[0] is False
    assert _match({'seasons_not_in': ['summer']}, ctx)[0] is True
    assert _match({'min_age': 60}, {**ctx, 'age': None})[0] is None


def test_template_roles_disabled_visibility_and_scheduled_events_are_independent(setup):
    client, sessions = setup
    elder, admin = login(client, 2), login(client, 1)
    created = template(client, admin)
    assert client.post('/api/activities', headers=elder, json={'code': 'DENIED', 'name': '越权'}).status_code == 403
    event = client.post('/api/services/activities', headers=admin, json={'title': '真实排期', 'category': 'ENTERTAINMENT',
        'start_at': (now()+timedelta(days=1)).isoformat(), 'end_at': (now()+timedelta(days=1, hours=1)).isoformat(),
        'location': '活动室', 'capacity': 5}).json()['data']
    assert client.delete(f'/api/activities/{created["activity_id"]}', headers=admin).status_code == 200
    assert created['activity_id'] not in [row['activity_id'] for row in client.get('/api/activities', headers=elder).json()['data']]
    assert any(row['activity_id'] == created['activity_id'] and not row['enabled'] for row in client.get('/api/activities', headers=admin).json()['data'])
    with sessions() as db:
        assert db.get(Activity, event['activity_id']).title == '真实排期'
        assert db.get(ActivityTemplate, created['activity_id']) is not None


def test_recommendation_checks_live_scope_conditions_and_high_risk(setup):
    client, sessions = setup
    elder, family, admin = [login(client, i) for i in (2, 3, 1)]
    pid = first_profile(client, elder)
    a = template(client, admin, category='阅读', rules={'suitable': {'min_age': 60, 'max_age': 70}})
    record(client, elder, pid, 75)
    def recommendation():
        response = client.get('/api/activities/recommend', headers=family, params={'profile_id': pid})
        assert response.status_code == 200, response.text
        return next(row for row in response.json()['data'] if row['activity_id'] == a['activity_id'])
    assert recommendation()['suitability'] == '需确认'
    assert recommendation()['service_category'] == 'OTHER'
    with sessions() as db:
        db.get(ActivityTemplate, a['activity_id']).rules = '{broken'
        db.commit()
    assert recommendation()['can_request'] is False
    with sessions() as db:
        db.get(ActivityTemplate, a['activity_id']).rules = '{}'
        db.commit()
    assert recommendation()['suitability'] == '可了解'
    client.post('/api/ai/chat', headers=elder, json={'profile_id': pid, 'question': '我现在胸痛'})
    assert recommendation()['suitability'] == '暂缓参与' and recommendation()['can_request'] is False
    from app.models import FamilyBind
    with sessions() as db:
        db.scalar(select(FamilyBind)).status = 'UNBOUND'
        db.commit()
    assert client.get('/api/health/status', headers=family, params={'profile_id': pid}).status_code == 403
    assert client.get('/api/activities/recommend', headers=family, params={'profile_id': pid}).status_code == 403
