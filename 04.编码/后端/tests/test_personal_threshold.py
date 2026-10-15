from sqlalchemy import select
from test_business import setup, login, first_profile, input_record
from app.models import ElderProfile, CareRelation, SysConfig, HealthWarning
from app.models.personal_threshold import HealthAssessment


def rule(reason='依据本次已确认的个体照护方案调整'):
    return {'indicator': 'BLOOD_PRESSURE_SYSTOLIC', 'level0_range': '90~189',
            'level1_range': '190~199', 'level2_range': '200~209', 'level3_range': '<90 或 >=210', 'reason': reason}


def proposal(client, headers, profile_id, body=None):
    response = client.post(f'/api/profiles/{profile_id}/threshold-proposals', headers=headers, json=body or rule())
    assert response.json()['code'] == 0, response.text
    return response.json()['data']['proposal_id']


def approve(client, admin, pid, accepted=True):
    response = client.post(f'/api/threshold-proposals/{pid}/review', headers=admin,
        json={'approve': accepted, 'note': '已核对个体照护记录及调整依据'})
    assert response.json()['code'] == 0, response.text
    return response.json()['data']


def test_personal_rule_pending_then_approved_and_other_profile_unchanged(setup):
    client, sessions = setup
    elder, care, admin = [login(client, n) for n in (2, 4, 1)]
    profile_id = first_profile(client, elder)
    with sessions() as db:
        current = db.get(ElderProfile, profile_id)
        other = ElderProfile(user_id=current.user_id, name='第二个独立档案')
        db.add(other); db.commit(); other_id = other.id
    pid = proposal(client, care, profile_id)
    measurement = {'systolic': 185, 'diastolic': 80}
    assert input_record(client, elder, profile_id, values=measurement).json()['data']['risk_level'] == 3
    approve(client, admin, pid)
    response = input_record(client, elder, profile_id, values=measurement).json()['data']
    assert response['risk_level'] == 0
    assert response['assessment']['thresholds']['BLOOD_PRESSURE_SYSTOLIC']['source'] == 'PERSONAL'
    assert input_record(client, elder, other_id, values=measurement).json()['data']['risk_level'] == 3
    effective = client.get(f'/api/profiles/{profile_id}/thresholds', headers=elder).json()['data']
    assert any(item['source'] == 'PERSONAL' and item['version_id'] == pid for item in effective['rules'])


def test_old_warning_and_trend_keep_original_threshold_after_change(setup):
    client, _ = setup
    elder, care, admin = [login(client, n) for n in (2, 4, 1)]
    profile_id = first_profile(client, elder)
    old = input_record(client, elder, profile_id, values={'systolic': 185, 'diastolic': 80}).json()['data']
    approve(client, admin, proposal(client, care, profile_id))
    trend = client.get('/api/health/trend', params={'profile_id': profile_id, 'type': 'BLOOD_PRESSURE'}, headers=elder).json()['data']
    assert trend['threshold_source'] == 'PERSONAL'
    assert trend['abnormal_points'][0]['level'] == 3
    assert trend['assessments'][0]['thresholds']['BLOOD_PRESSURE_SYSTOLIC']['source'] == 'DEFAULT'
    detail = client.get(f"/api/alerts/{old['warning_id']}", headers=care).json()['data']
    assert detail['level'] == 3 and detail['assessment']['risk_level'] == 3


def test_restore_default_keeps_personal_measurement_audit(setup):
    client, _ = setup
    elder, care, admin = [login(client, n) for n in (2, 4, 1)]
    profile_id = first_profile(client, elder)
    approve(client, admin, proposal(client, care, profile_id))
    measurement = {'systolic': 185, 'diastolic': 80}
    personal = input_record(client, elder, profile_id, values=measurement).json()['data']
    body = {'indicator': 'BLOOD_PRESSURE_SYSTOLIC', 'restore_default': True, 'reason': '个体方案复核后恢复院内默认'}
    approve(client, admin, proposal(client, care, profile_id, body))
    assert input_record(client, elder, profile_id, values=measurement).json()['data']['risk_level'] == 3
    records = client.get('/api/health/records', headers=elder, params={'profile_id': profile_id}).json()['data']['list']
    saved = next(item for item in records if item['record_id'] == personal['record_id'])
    assert saved['assessment']['risk_level'] == 0
    assert saved['assessment']['thresholds']['BLOOD_PRESSURE_SYSTOLIC']['source'] == 'PERSONAL'


def test_invalid_pending_rejection_and_duplicate_review(setup):
    client, _ = setup
    elder, care, admin = [login(client, n) for n in (2, 4, 1)]
    profile_id = first_profile(client, elder)
    invalid = rule(); invalid['level3_range'] = '>=210'
    assert client.post(f'/api/profiles/{profile_id}/threshold-proposals', headers=care, json=invalid).json()['code'] == 2001
    pid = proposal(client, care, profile_id)
    assert client.post(f'/api/profiles/{profile_id}/threshold-proposals', headers=care, json=rule()).status_code == 409
    approve(client, admin, pid, accepted=False)
    assert input_record(client, elder, profile_id, values={'systolic': 185, 'diastolic': 80}).json()['data']['risk_level'] == 3
    assert client.post(f'/api/threshold-proposals/{pid}/review', headers=admin,
        json={'approve': True, 'note': '重复审核'}).status_code == 409


def test_elder_cannot_set_and_revoked_caregiver_proposal_cannot_be_approved(setup):
    client, sessions = setup
    elder, care, admin = [login(client, n) for n in (2, 4, 1)]
    profile_id = first_profile(client, elder)
    assert client.post(f'/api/profiles/{profile_id}/threshold-proposals', headers=elder, json=rule()).status_code == 403
    pid = proposal(client, care, profile_id)
    with sessions() as db:
        relation = db.scalar(select(CareRelation).where(CareRelation.profile_id == profile_id))
        relation.status = 0; db.commit()
    assert client.get(f'/api/profiles/{profile_id}/thresholds', headers=care).status_code == 403
    assert client.post(f'/api/threshold-proposals/{pid}/review', headers=admin,
        json={'approve': True, 'note': '申请人已撤销负责关系'}).status_code == 403


def test_deleting_measurement_retains_warning_assessment(setup):
    client, sessions = setup
    elder = login(client, 2)
    profile_id = first_profile(client, elder)
    item = input_record(client, elder, profile_id).json()['data']
    assert client.request('DELETE', f"/api/health/records/{item['record_id']}", headers=elder, json={'reason': '复核发现误录，保留原始证据'}).json()['code'] == 0
    with sessions() as db:
        evidence = db.scalar(select(HealthAssessment).where(HealthAssessment.warning_id == item['warning_id']))
        assert evidence.record_id == item['record_id'] and evidence.risk_level == 3
        assert db.get(HealthWarning, item['warning_id']).record_id == item['record_id']


def test_nonfinite_and_overlapping_rule_rejected(setup):
    client, _ = setup
    elder, care = [login(client, n) for n in (2, 4)]
    profile_id = first_profile(client, elder)
    invalid = rule(); invalid['level3_range'] = '>=' + '9' * 95
    # Finite numbers without low coverage are rejected too.
    assert client.post(f'/api/profiles/{profile_id}/threshold-proposals', headers=care, json=invalid).json()['code'] == 2001
    invalid = rule(); invalid['level1_range'] = '180~199'
    assert client.post(f'/api/profiles/{profile_id}/threshold-proposals', headers=care, json=invalid).json()['code'] == 2001
