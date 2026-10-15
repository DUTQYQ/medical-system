"""Independent SQLite acceptance for life intake, facts, advice and chat memory."""
import json
from datetime import timedelta
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db, now
from app.core.errors import install_handlers
from app.core.security import get_current_user
from app.models import User, ElderProfile, FamilyBind, CareRelation, SysConfig, ChatSession, ChatMessage, AILog
from app.models.consultation import ConsultationIntake, ProfileFact, ProfileFactRevision, AdviceCard
from app.api.intake import router as intake_router
from app.api.ai import router as chat_router
from app.services import intake
from app.agent import workflow, llm


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "intake.db"}', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    for name in ['LLM_API_KEY', 'DEEPSEEK_API_KEY', 'QWEN_API_KEY', 'DASHSCOPE_API_KEY', 'GLM_API_KEY', 'ZHIPU_API_KEY']:
        monkeypatch.delenv(name, raising=False)
    with factory() as db:
        for user_id, role in [(1, 'ELDER'), (2, 'FAMILY'), (3, 'CARE'), (4, 'ELDER'), (5, 'ADMIN')]:
            db.add(User(id=user_id, phone=f'1310000000{user_id}', name=f'用户{user_id}', role=role, status=1, password_hash='unused'))
        db.flush()
        db.add_all([ElderProfile(id=10, user_id=1, name='老人甲'), ElderProfile(id=20, user_id=4, name='老人乙')])
        db.flush()
        db.add_all([FamilyBind(family_user_id=2, profile_id=10, status='APPROVED'), CareRelation(care_user_id=3, profile_id=10, status=1)])
        for user_id in range(1, 6):
            db.add(SysConfig(config_key=f'privacy_consent:{user_id}', config_value=json.dumps({'accepted': True}), enabled=1))
        db.commit()
    app = FastAPI()
    install_handlers(app)
    app.include_router(intake_router, prefix='/api')
    app.include_router(chat_router, prefix='/api')
    user_ref = {'id': 1}
    def db_override():
        with factory() as db:
            try:
                yield db
            except BaseException:
                db.rollback()
                raise
    def user_override():
        with factory() as db:
            return db.get(User, user_ref['id'])
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_current_user] = user_override
    with TestClient(app) as client:
        yield client, factory, user_ref
    engine.dispose()


def fill(client, *, values=None, skips=()):
    result = client.post('/api/ai/intake/start', json={'profile_id': 10}).json()['data']
    intake_id = result['intake_id']
    defaults = {'life_goal': '多交朋友', 'entertainment_preferences': ['象棋', '打牌'], 'movement_ability': '需要陪同',
                'assistance_needs': '出行陪同', 'food_preferences': '少辣', 'sleep_concerns': '夜间易醒'}
    defaults.update(values or {})
    for question in intake.QUESTIONS:
        key = question['key']
        response = client.post(f'/api/ai/intake/{intake_id}/answer', json={'key': key, 'value': defaults[key], 'skip': key in skips})
        assert response.json()['code'] == 0, response.text
        result = response.json()['data']
    return intake_id, [{'key': key, 'value': value} for key, value in defaults.items() if key not in skips], result


def confirmed(client, **kwargs):
    intake_id, entries, result = fill(client, **kwargs)
    response = client.post(f'/api/ai/intake/{intake_id}/confirm', json={'entries': entries})
    assert response.json()['code'] == 0, response.text
    return intake_id, entries, response.json()['data']


def test_start_resume_idempotent_and_skips_without_saving_facts(fixture):
    client, factory, _ = fixture
    first = client.post('/api/ai/intake/start', json={'profile_id': 10}).json()['data']
    assert first['next_question']['key'] == 'life_goal'
    assert client.post('/api/ai/intake/start', json={'profile_id': 10}).json()['data']['intake_id'] == first['intake_id']
    client.post(f'/api/ai/intake/{first["intake_id"]}/answer', json={'key': 'life_goal', 'skip': True})
    resumed = client.post('/api/ai/intake/start', json={'profile_id': 10}).json()['data']
    assert resumed['next_question']['key'] == 'entertainment_preferences'
    assert resumed['answers'][0]['skipped'] is True and resumed['answers'][0]['value'] is None
    assert client.get('/api/ai/facts?profile_id=10').json()['data'] == []
    with factory() as db:
        assert db.scalar(select(func.count(ConsultationIntake.id))) == 1


def test_answer_validation_forbids_out_of_sequence_and_authoritative_fields(fixture):
    client, _, _ = fixture
    row = client.post('/api/ai/intake/start', json={'profile_id': 10}).json()['data']
    for body in [{'key': 'sleep_concerns', 'value': '尚可'}, {'key': 'threshold', 'value': '200'},
                 {'key': 'life_goal', 'value': ''}, {'key': 'life_goal', 'value': 'x' * 501}]:
        response = client.post(f'/api/ai/intake/{row["intake_id"]}/answer', json=body)
        assert response.json()['code'] == 2001
    assert client.post(f'/api/ai/intake/{row["intake_id"]}/confirm', json={'entries': []}).status_code == 400


def test_confirmation_is_explicit_idempotent_and_creates_versioned_facts(fixture):
    client, factory, _ = fixture
    intake_id, entries, result = fill(client, skips=('food_preferences',))
    assert result['status'] == 'READY_TO_CONFIRM'
    assert client.get('/api/ai/facts?profile_id=10').json()['data'] == []
    entries[0]['value'] = '多认识新朋友'
    first = client.post(f'/api/ai/intake/{intake_id}/confirm', json={'entries': entries}).json()['data']
    assert len(first) == 5 and first[0]['value'] == '多认识新朋友'
    repeated = client.post(f'/api/ai/intake/{intake_id}/confirm', json={'entries': entries}).json()['data']
    assert [f['fact_id'] for f in first] == [f['fact_id'] for f in repeated]
    with factory() as db:
        assert db.scalar(select(func.count(ProfileFactRevision.id))) == 5
    response = client.put(f'/api/ai/facts/{first[0]["fact_id"]}', json={'value': '阅读'})
    assert response.json()['data']['version'] == 2
    with factory() as db:
        revisions = list(db.scalars(select(ProfileFactRevision).where(ProfileFactRevision.fact_id == first[0]['fact_id']).order_by(ProfileFactRevision.version)))
        assert [r.value for r in revisions] == ['多认识新朋友', '阅读']
    assert client.post(f'/api/ai/intake/{intake_id}/answer', json={'key': 'life_goal', 'value': '修改'}).status_code == 409


def test_all_skips_can_confirm_but_do_not_invent_information(fixture):
    client, _, _ = fixture
    confirmed(client, skips=tuple(intake.QUESTION_MAP))
    assert client.get('/api/ai/facts?profile_id=10').json()['data'] == []
    result = client.post('/api/ai/advice', json={'profile_id': 10}).json()['data']
    assert result['mode'] == 'RULE' and '尚未确认' in result['sections'][0]['items'][0]
    assert result['sources'] == []


def test_short_term_expiry_and_revoke_are_excluded_from_advice(fixture):
    client, factory, _ = fixture
    _, _, facts = confirmed(client)
    sleep = next(f for f in facts if f['key'] == 'sleep_concerns')
    interest = next(f for f in facts if f['key'] == 'entertainment_preferences')
    with factory() as db:
        db.get(ProfileFact, sleep['fact_id']).valid_until = now() - timedelta(days=1)
        db.commit()
    assert client.delete(f'/api/ai/facts/{interest["fact_id"]}').json()['code'] == 0
    listed = client.get('/api/ai/facts?profile_id=10').json()['data']
    assert next(f for f in listed if f['key'] == 'sleep_concerns')['status'] == 'EXPIRED'
    result = client.post('/api/ai/advice', json={'profile_id': 10}).json()['data']
    assert not any(source['key'] in ['sleep_concerns', 'entertainment_preferences'] for source in result['sources'])
    assert not any(action['category'] == 'ENTERTAINMENT' for action in result['actions'])


def test_advice_without_key_persists_rule_cards_without_creating_requests(fixture):
    client, factory, _ = fixture
    confirmed(client)
    result = client.post('/api/ai/advice', json={'profile_id': 10}).json()['data']
    assert result['mode'] == 'RULE' and result['model_status'] == 'RULE_FALLBACK'
    assert '规则生成' in result['generation_note']
    assert len(result['sections']) == 4 and len(result['sources']) == 6
    assert {action['category'] for action in result['actions']} == {'ENTERTAINMENT', 'EQUIPMENT', 'DAILY_LIVING', 'MEAL'}
    assert client.get('/api/ai/advice?profile_id=10').json()['data'][0]['advice_id'] == result['advice_id']
    with factory() as db:
        assert db.scalar(select(func.count(AdviceCard.id))) == 1


def test_role_specific_advice_is_private_and_admin_uses_management_tools(fixture):
    client, _, user_ref = fixture
    confirmed(client)
    elder_advice = client.post('/api/ai/advice', json={'profile_id': 10}).json()['data']
    assert elder_advice['title'] == '我的康养生活建议'
    user_ref['id'] = 2
    assert client.get('/api/ai/advice?profile_id=10').json()['data'] == []
    family_advice = client.post('/api/ai/advice', json={'profile_id': 10}).json()['data']
    assert family_advice['title'] == '家属照护建议'
    assert family_advice['sections'][0]['title'] == '已确认的生活信息与来源'
    assert [row['advice_id'] for row in client.get('/api/ai/advice?profile_id=10').json()['data']] == [family_advice['advice_id']]
    user_ref['id'] = 3
    assert client.get('/api/ai/facts?profile_id=10').status_code == 200
    assert client.post('/api/ai/intake/start', json={'profile_id': 10}).status_code == 403
    assert client.post('/api/ai/facts', json={'profile_id': 10, 'key': 'life_goal', 'value': '修改'}).status_code == 403
    care_advice = client.post('/api/ai/advice', json={'profile_id': 10}).json()['data']
    assert care_advice['title'] == '护理工作建议'
    assert [row['advice_id'] for row in client.get('/api/ai/advice?profile_id=10').json()['data']] == [care_advice['advice_id']]
    user_ref['id'] = 5
    assert client.post('/api/ai/chat', json={'profile_id': 10, 'question': '老人的生活情况'}).status_code == 403
    assert client.get('/api/ai/facts?profile_id=10').status_code == 403
    assert client.post('/api/ai/advice', json={'profile_id': 10}).status_code == 403


def test_family_observation_keeps_its_source_in_facts_advice_and_model_context(fixture, monkeypatch):
    client, _, user_ref = fixture
    user_ref['id'] = 2
    fact = client.post('/api/ai/facts', json={'profile_id': 10, 'key': 'movement_ability', 'value': '需要陪同'}).json()['data']
    assert fact['reported_role'] == 'FAMILY' and fact['confirmed_role'] == 'FAMILY'
    assert '家属观察' in fact['source'] and '老人自述' not in fact['source']
    user_ref['id'] = 3
    advice = client.post('/api/ai/advice', json={'profile_id': 10}).json()['data']
    assert advice['sections'][0]['title'] == '已确认的生活信息与来源'
    assert '家属观察，家属确认' in advice['sections'][0]['items'][0]
    assert advice['sources'][0]['reported_role'] == 'FAMILY'
    contexts = []
    monkeypatch.setattr(workflow, 'complete', lambda question, context, **kwargs: contexts.append(context) or '请先核实家属观察。')
    assert client.post('/api/ai/chat', json={'profile_id': 10, 'question': '老人最近的生活情况'}).status_code == 200
    assert '家属观察，家属确认' in contexts[-1]
    assert '需要陪同（用户已确认，自述信息' not in contexts[-1]


def test_invalid_or_unsafe_model_json_falls_back(fixture, monkeypatch):
    client, _, _ = fixture
    confirmed(client)
    for output in ['not json', '[]', '{"sections":[]}', '您确诊为高血压，需要停药', '已预约您的活动，不用工作人员确认']:
        monkeypatch.setattr(llm, 'complete', lambda *args, **kwargs: output)
        assert client.post('/api/ai/advice', json={'profile_id': 10}).json()['data']['mode'] == 'RULE'


def test_model_may_rewrite_advice_but_not_facts_or_actions(fixture, monkeypatch):
    client, factory, _ = fixture
    confirmed(client)
    sections = [{'title': title, 'items': ['工作人员确认后，可参加您感兴趣的活动。']} for title in ['已确认的生活信息与来源', '今天可以做什么', '需要工作人员协助', '依据与注意事项']]
    monkeypatch.setattr(llm, 'complete', lambda *args, **kwargs: json.dumps({'sections': sections}, ensure_ascii=False))
    result = client.post('/api/ai/advice', json={'profile_id': 10}).json()['data']
    assert result['mode'] == 'MODEL' and result['model_status'] == 'SUCCESS'
    assert '娱乐偏好：象棋、打牌' in '\n'.join(result['sections'][0]['items'])
    assert '不会自动提交申请' in '\n'.join(result['sections'][3]['items'])
    with factory() as db:
        assert db.scalar(select(AILog).where(AILog.model == 'advice-reservation')).success == 1


def test_live_relation_permission_is_checked_for_every_intake_fact_advice_endpoint(fixture):
    client, factory, user_ref = fixture
    intake_id, _, facts = confirmed(client)
    user_ref['id'] = 4
    assert client.get('/api/ai/facts?profile_id=10').status_code == 403
    assert client.post('/api/ai/intake/start', json={'profile_id': 10}).status_code == 403
    user_ref['id'] = 2
    assert client.get('/api/ai/facts?profile_id=10').status_code == 200
    with factory() as db:
        db.scalar(select(FamilyBind)).status = 'UNBOUND'
        db.commit()
    for method, url, body in [('get', '/api/ai/facts?profile_id=10', None), ('get', '/api/ai/advice?profile_id=10', None),
                              ('post', f'/api/ai/intake/{intake_id}/confirm', {'entries': []}),
                              ('put', f'/api/ai/facts/{facts[0]["fact_id"]}', {'value': '阅读'}),
                              ('post', '/api/ai/advice', {'profile_id': 10})]:
        response = getattr(client, method)(url, **({'json': body} if body is not None else {}))
        assert response.status_code == 403


def test_true_same_session_history_and_confirmed_facts_only(fixture, monkeypatch):
    client, factory, _ = fixture
    confirmed(client)
    captured = []
    monkeypatch.setattr(workflow, 'retrieve', lambda *args: [])
    def generate(question, context, **kwargs):
        captured.append((question, context, kwargs.get('history')))
        return '可与工作人员讨论参加感兴趣的活动。'
    monkeypatch.setattr(workflow, 'complete', generate)
    first = client.post('/api/ai/chat', json={'profile_id': 10, 'question': '我喜欢什么娱乐'}).json()['data']
    second = client.post('/api/ai/chat', json={'profile_id': 10, 'session_id': first['session_id'], 'question': '那具体怎样参加'}).json()['data']
    assert second['session_id'] == first['session_id']
    assert '象棋、打牌' in captured[1][1]
    assert [m['role'] for m in captured[1][2]] == ['user', 'assistant']
    assert captured[1][2][0]['content'] == '我喜欢什么娱乐'
    client.post('/api/ai/chat', json={'profile_id': 10, 'question': '另一个新话题'})
    assert captured[2][2] == []


def test_daily_model_limit_keeps_rule_advice_available(fixture, monkeypatch):
    client, factory, _ = fixture
    confirmed(client)
    with factory() as db:
        db.add(SysConfig(config_key='ai_daily_limit', config_value='1', enabled=1))
        db.add(AILog(user_id=1, agent='CONSULT_ATTEMPT', model='quota', success=0))
        db.commit()
    def unexpected(*args, **kwargs):
        raise AssertionError('Model must not be called after daily allowance')
    monkeypatch.setattr(llm, 'complete', unexpected)
    result = client.post('/api/ai/advice', json={'profile_id': 10}).json()['data']
    assert result['mode'] == 'RULE' and result['model_status'] == 'RULE_DAILY_LIMIT'


def test_model_response_cannot_keep_access_after_binding_is_revoked(fixture, monkeypatch):
    client, factory, user_ref = fixture
    confirmed(client)
    user_ref['id'] = 2
    def generation(*args, **kwargs):
        with factory() as db:
            db.scalar(select(FamilyBind)).status = 'UNBOUND'
            db.commit()
        raise llm.ModelUnavailable('model down')
    monkeypatch.setattr(llm, 'complete', generation)
    result = client.post('/api/ai/advice', json={'profile_id': 10})
    assert result.status_code == 403
    with factory() as db:
        assert db.scalar(select(func.count(AdviceCard.id))) == 0


def test_skipped_fact_can_be_explicitly_added_and_updated_after_confirmation(fixture):
    client, factory, _ = fixture
    confirmed(client, skips=('entertainment_preferences',))
    existing = client.get('/api/ai/facts?profile_id=10').json()['data']
    assert not any(f['key'] == 'entertainment_preferences' for f in existing)
    body = {'profile_id': 10, 'key': 'entertainment_preferences', 'value': '象棋'}
    result = client.post('/api/ai/facts', json=body).json()['data']
    assert result['value'] == '象棋' and result['version'] == 1
    body['value'] = ['象棋', '阅读']
    updated = client.post('/api/ai/facts', json=body).json()['data']
    assert updated['fact_id'] == result['fact_id'] and updated['version'] == 2
    with factory() as db:
        versions = list(db.scalars(select(ProfileFactRevision).where(ProfileFactRevision.fact_id == result['fact_id']).order_by(ProfileFactRevision.version)))
        assert [v.value for v in versions] == ['象棋', ['象棋', '阅读']]
        assert versions[0].change_reason == '用户添加并确认个人词条'
    assert client.post('/api/ai/facts', json={'profile_id': 10, 'key': 'medical_history', 'value': '诊断'}).status_code == 400


def source_message(factory, profile_id, owner_id=1):
    with factory() as db:
        session = ChatSession(user_id=owner_id, profile_id=profile_id, title='测试咨询')
        db.add(session)
        db.flush()
        message = ChatMessage(session_id=session.id, role='user', content='我喜欢象棋')
        db.add(message)
        db.commit()
        return message.id


def test_confirm_conversation_fact_keeps_source_and_requires_same_profile(fixture):
    client, factory, _ = fixture
    message_id = source_message(factory, 10)
    result = client.post('/api/ai/facts', json={'profile_id': 10, 'key': 'entertainment_preferences',
                          'value': '象棋', 'source_message_id': message_id}).json()['data']
    with factory() as db:
        revision = db.scalar(select(ProfileFactRevision).where(ProfileFactRevision.fact_id == result['fact_id']))
        assert revision.change_reason == f'用户确认会话信息 message#{message_id}'
        db.add(ElderProfile(id=11, user_id=1, name='另一本人档案'))
        db.commit()
    other_message_id = source_message(factory, 11)
    response = client.post('/api/ai/facts', json={'profile_id': 10, 'key': 'life_goal',
                           'value': '多交朋友', 'source_message_id': other_message_id})
    assert response.status_code == 400 and response.json()['code'] == 2001
    assert client.post('/api/ai/facts', json={'profile_id': 10, 'key': 'life_goal', 'value': '阅读', 'source_message_id': 999999}).status_code == 404


def test_fact_creation_requires_live_profile_and_source_permissions(fixture):
    client, factory, user_ref = fixture
    other_message_id = source_message(factory, 20, owner_id=4)
    response = client.post('/api/ai/facts', json={'profile_id': 10, 'key': 'life_goal',
                           'value': '阅读', 'source_message_id': other_message_id})
    assert response.status_code == 403
    user_ref['id'] = 2
    assert client.post('/api/ai/facts', json={'profile_id': 10, 'key': 'life_goal', 'value': '阅读'}).status_code == 200
    with factory() as db:
        db.scalar(select(FamilyBind)).status = 'UNBOUND'
        db.commit()
    assert client.post('/api/ai/facts', json={'profile_id': 10, 'key': 'life_goal', 'value': '唱歌'}).status_code == 403
    with factory() as db:
        assert db.scalar(select(ProfileFact).where(ProfileFact.fact_key == 'life_goal')).value == '阅读'
