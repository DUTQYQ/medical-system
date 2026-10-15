"""Additional role attribution, archival obligations and optional AI cost tests."""
from datetime import timedelta
import pytest
from sqlalchemy import select, func
from test_business import setup, login, first_profile, input_record
from test_care_services import request, activity, data
from app.core.database import now
from app.models import User, ElderProfile, HealthWarning, AILog, SysConfig, CareRelation
from app.models.care_services import EquipmentLoan, ServiceEvent
from app.agent import workflow


@pytest.mark.parametrize('role,question,creates_warning', [
    (3, '我现在胸痛', False), (4, '我自己突然胸痛', False),
    (3, '妈妈现在胸痛', True), (3, '爸爸现在胸痛', False), (4, '老人现在呼吸困难', True),
    (3, '胸痛，呼吸困难', False), (2, '我的女儿胸痛', False),
    (3, '爸爸没有胸痛，我现在胸痛', False),
    (3, '我现在胸痛，妈妈也胸痛', True), (4, '其他老人胸痛', False),
    (3, '我妈身体不舒服，胸痛', True), (2, '我胸痛', True), (2, '我老伴胸痛', False),
])
def test_emergency_warning_belongs_to_the_symptomatic_person(setup, monkeypatch, role, question, creates_warning):
    client, sessions = setup
    headers = login(client, role)
    pid = first_profile(client, headers)
    calls = []
    monkeypatch.setattr(workflow, 'complete', lambda *args, **kwargs: calls.append(True))
    result = client.post('/api/ai/chat', headers=headers, json={'profile_id': pid, 'question': question}).json()['data']
    assert result['intent'] == 'EMERGENCY' and result['safety_level'] == 'L4' and not calls
    assert bool(result['warning_id']) is creates_warning
    assert '120' in result['answer']
    with sessions() as db:
        assert db.scalar(select(func.count(HealthWarning.id))) == int(creates_warning)


def test_resolved_or_voided_warning_does_not_claim_current_risk(setup, monkeypatch):
    client, _ = setup
    elder, care = login(client, 2), login(client, 4)
    pid = first_profile(client, elder)
    first = input_record(client, elder, pid).json()['data']
    client.post(f'/api/alerts/{first["warning_id"]}/handle', headers=care,
                json={'action': 'OBSERVE', 'result': '复核并完成处理'})
    second = input_record(client, elder, pid).json()['data']
    client.request('DELETE', f'/api/health/records/{second["record_id"]}', headers=elder,
                   json={'reason': '错误录入，已作废'})
    contexts = []
    monkeypatch.setattr(workflow, 'complete', lambda q, context, **kw: contexts.append(context) or '请依据有效测量复核。')
    result = client.post('/api/ai/chat', headers=elder, json={'profile_id': pid, 'question': '当前预警异常情况'}).json()['data']
    assert result['risk_level'] == 0
    assert '历史判定等级3' in contexts[0] and '关联测量已作废' in contexts[0]
    assert '当前有效且未处理完的预警 0 条' in result['answer']


def test_delete_profile_requires_service_completion_and_equipment_return(setup):
    client, sessions = setup
    elder, care, admin = [login(client, i) for i in (2, 4, 1)]
    pid = first_profile(client, elder)
    service = data(request(client, elder, pid))
    path = f'/api/profiles/{pid}'
    blocked = client.delete(path, headers=elder)
    assert blocked.status_code == 409 and '未完成服务 1 项' in blocked.json()['message']
    data(client.post(f'/api/services/requests/{service["id"]}/transition', headers=elder, json={'status': 'CANCELLED'}))
    equipment = data(client.post('/api/services/equipment', headers=admin, json={'name': '待归还轮椅', 'total': 1}))
    borrow = data(client.post(f'/api/services/equipment/{equipment["id"]}/request', headers=elder,
        json={'profile_id': pid, 'quantity': 1, 'location': '101室'}))
    task = f'/api/services/requests/{borrow["id"]}/transition'
    for status in ['ACCEPTED', 'IN_PROGRESS', 'COMPLETED']:
        data(client.post(task, headers=care, json={'status': status, 'result': '已交付设备'}))
    assert '未归还设备 1 项' in client.delete(path, headers=admin).json()['message']
    with sessions() as db:
        loan_id = db.scalar(select(EquipmentLoan.id))
    data(client.post(f'/api/services/loans/{loan_id}/return', headers=care, json={'damaged': False, 'note': '已收回'}))
    assert client.delete(path, headers=elder).status_code == 200
    with sessions() as db:
        assert db.get(ElderProfile, pid).deleted == 1


def test_delete_profile_requires_registration_and_alert_closure(setup):
    client, _ = setup
    elder, care, admin = [login(client, i) for i in (2, 4, 1)]
    pid = first_profile(client, elder)
    event = activity(client, admin)
    registered = data(client.post(f'/api/services/activities/{event["id"]}/register', headers=elder, json={'profile_id': pid}))
    path = f'/api/profiles/{pid}'
    assert '未结束报名 1 项' in client.delete(path, headers=elder).json()['message']
    data(client.post(f'/api/services/registrations/{registered["id"]}/transition', headers=elder, json={'status': 'CANCELLED'}))
    wid = input_record(client, elder, pid).json()['data']['warning_id']
    assert '待处理预警 1 条' in client.delete(path, headers=elder).json()['message']
    client.post(f'/api/alerts/{wid}/handle', headers=care, json={'action': 'OBSERVE', 'result': '复核后结案'})
    assert client.delete(path, headers=elder).status_code == 200


def test_sensitive_account_changes_are_verified_atomic_and_revoke_other_sessions(setup):
    client, _ = setup
    elder, other_session = login(client, 2), login(client, 2)
    before = client.get('/api/auth/me', headers=elder).json()['data']
    change = {'name': '同步修改', 'phone': '13800000008', 'new_password': 'Newpass1234'}
    for credential in ({}, {'current_password': 'wrong'}):
        assert client.put('/api/auth/me', headers=elder, json={**change, **credential}).status_code == 400
        assert client.get('/api/auth/me', headers=elder).json()['data']['name'] == before['name']
    updated = client.put('/api/auth/me', headers=elder, json={**change, 'current_password': 'Abc123456'}).json()['data']
    assert updated['reauth_required'] is True and updated['phone'] == change['phone']
    assert client.get('/api/auth/me', headers=other_session).status_code == 401
    assert client.post('/api/auth/login', json={'phone': change['phone'], 'password': 'Abc123456'}).status_code == 401
    assert client.post('/api/auth/login', json={'phone': change['phone'], 'password': change['new_password']}).status_code == 200


def test_summary_quota_and_retry_cooldown_preserve_business_alerts(setup, monkeypatch):
    client, sessions = setup
    elder, care = login(client, 2), login(client, 4)
    pid = first_profile(client, elder)
    with sessions() as db:
        db.scalar(select(SysConfig).where(SysConfig.config_key == 'ai_summary_daily_limit')).config_value = '1'
        db.commit()
    monkeypatch.setattr(workflow, 'SessionLocal', sessions)
    calls = []
    monkeypatch.setattr(workflow, 'complete', lambda *a, **kw: calls.append(True) or '建议由工作人员复核。')
    first = input_record(client, elder, pid).json()['data']['warning_id']
    workflow.generate_summary(first)
    second = input_record(client, elder, pid).json()['data']['warning_id']
    workflow.generate_summary(second)
    assert len(calls) == 1
    with sessions() as db:
        assert db.get(HealthWarning, first).summary_status == 'SUCCESS'
        assert db.get(HealthWarning, second).status == 'PENDING'
        assert db.get(HealthWarning, second).summary_status == 'FAILED'
        assert db.get(HealthWarning, second).ai_summary is None
        assert db.scalar(select(func.count(AILog.id)).where(AILog.agent == 'ALERT_ATTEMPT')) == 1
    assert client.post(f'/api/alerts/{second}/summary/retry', headers=care).status_code == 429
    assert client.get('/api/notifications/unread', headers=care).json()['data']['unread'] == 2
    assert '额度已用完' in client.get(f'/api/alerts/{second}', headers=care).json()['data']['summary_message']
    assert client.get('/api/notifications/unread', headers=care).json()['data']['unread'] == 1


def test_summary_attempt_limit_and_cooldown_survive_failure(setup):
    from app.services.summary_budget import reserve
    _, sessions = setup
    with sessions() as db:
        first, _ = reserve(db, 999)
        assert first is not None
        assert reserve(db, 999)[0] is None
        assert reserve(db, 999, check_cooldown=False)[0] is not None
        assert reserve(db, 999, check_cooldown=False)[0] is not None
        assert reserve(db, 999, check_cooldown=False)[0] is None
        assert db.scalar(select(func.count(AILog.id)).where(AILog.agent == 'ALERT_ATTEMPT')) == 3


@pytest.mark.parametrize('during_model', [False, True])
def test_voided_measurement_does_not_publish_model_summary(setup, monkeypatch, during_model):
    client, sessions = setup
    elder, care = login(client, 2), login(client, 4)
    item = input_record(client, elder, first_profile(client, elder)).json()['data']
    monkeypatch.setattr(workflow, 'SessionLocal', sessions)
    calls = []
    def void():
        assert client.request('DELETE', f'/api/health/records/{item["record_id"]}', headers=elder,
            json={'reason': '复核为错误测量'}).status_code == 200
    def model(*args, **kwargs):
        calls.append(True)
        void()
        return '应丢弃的旧测量分析'
    monkeypatch.setattr(workflow, 'complete', model)
    if not during_model:
        void()
    workflow.generate_summary(item['warning_id'])
    assert len(calls) == int(during_model)
    result = client.get(f'/api/alerts/{item["warning_id"]}', headers=care).json()['data']
    assert result['summary_status'] == 'SKIPPED' and result['ai_summary'] is None
    assert result['status'] == 'PENDING' and '测量已作废' in result['summary_message']


def test_call_without_recipients_is_not_reported_as_escalated(setup):
    from app.services.care_services import escalate_overdue_calls
    client, sessions = setup
    elder = login(client, 2)
    pid = first_profile(client, elder)
    with sessions() as db:
        for user in db.scalars(select(User).where(User.role.in_(['ADMIN', 'CARE']))):
            user.status = 0
        db.commit()
    call = data(client.post('/api/services/calls', headers=elder, json={'profile_id': pid, 'location': '101室'}))
    assert call['escalated_at'] is None and call['assigned_to'] is None
    with sessions() as db:
        escalate_overdue_calls(db)
        db.commit()
        assert '暂无有效护工或管理员' in list(db.scalars(select(ServiceEvent.note)))[-1]
        assert db.get(HealthWarning, 1) is None
