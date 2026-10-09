import json
import sys
import types
from datetime import timedelta
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db, now
from app.core.errors import install_handlers
from app.core.errors import APIError
from app.core.security import get_current_user
from app.models import User, ElderProfile, FamilyBind, CareRelation, HealthRecord, HealthWarning, AlertReceiver, ChatSession, SysConfig, KnowledgeDocument
from app.api.ai import router
from app.agent import workflow, llm, rag
from scripts.import_knowledge import import_knowledge, load_corpus


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    engine = create_engine(f'sqlite:///{tmp_path / "ai-tests.db"}', connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setenv('CHROMA_PATH', str(tmp_path / 'chroma'))
    monkeypatch.setenv('EMBEDDING_PROVIDER', 'hash')
    for variable in ('LLM_API_KEY', 'DEEPSEEK_API_KEY', 'QWEN_API_KEY', 'DASHSCOPE_API_KEY', 'GLM_API_KEY', 'ZHIPU_API_KEY'):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv('LLM_PROVIDER', 'deepseek')
    monkeypatch.setattr(workflow, 'SessionLocal', factory)
    with factory() as db:
        db.add_all([User(id=1, phone='13000000002', name='老人', password_hash='unused', role='ELDER', status=1),
                    User(id=2, phone='13000000003', name='家属', password_hash='unused', role='FAMILY', status=1),
                    User(id=3, phone='13000000004', name='护工', password_hash='unused', role='CARE', status=1),
                    User(id=4, phone='13000000005', name='其他老人', password_hash='unused', role='ELDER', status=1)])
        db.flush()
        db.add_all([ElderProfile(id=10, user_id=1, name='老人', deleted=0), ElderProfile(id=11, user_id=1, name='另一档案', deleted=0), ElderProfile(id=20, user_id=4, name='其他老人', deleted=0)])
        db.flush()
        db.add_all([FamilyBind(family_user_id=2, profile_id=10, relation='家属', status='APPROVED'), CareRelation(care_user_id=3, profile_id=10, status=1),
                    HealthRecord(id=100, profile_id=10, type='BLOOD_PRESSURE', val1=185, val2=95, measured_at=now()-timedelta(hours=1), is_abnormal=1),
                    HealthRecord(id=101, profile_id=20, type='BLOOD_PRESSURE', val1=122, val2=81, measured_at=now(), is_abnormal=0),
                    HealthWarning(id=200, profile_id=10, record_id=100, type='BLOOD_PRESSURE', value_text='185/95', level=3, status='PENDING', summary_status='PENDING'),
                    SysConfig(config_key='emergency_keywords', config_value=json.dumps(workflow.DEFAULT_EMERGENCY_KEYWORDS, ensure_ascii=False), config_type='json', enabled=1)])
        # Explicit test authorization records: application registration never auto-consents.
        for user_id in (1, 2, 3, 4):
            db.add(SysConfig(config_key=f'privacy_consent:{user_id}', config_value=json.dumps({'accepted': True, 'version': '1.0', 'accepted_at': now().isoformat()}), config_type='json', enabled=1))
        import_knowledge(db, reindex=False)
        db.commit()
    app = FastAPI()
    install_handlers(app)
    app.include_router(router, prefix='/api')
    user_ref = {'id': 1}
    def db_override():
        with factory() as db:
            yield db
    def user_override():
        with factory() as db:
            return db.get(User, user_ref['id'])
    app.dependency_overrides[get_db] = db_override
    app.dependency_overrides[get_current_user] = user_override
    with TestClient(app) as client:
        yield client, factory, user_ref
    engine.dispose()


def stub(monkeypatch):
    contexts = []
    def complete(question, context, **kwargs):
        contexts.append(context)
        return '以下解释基于本次查询到的参考资料。'
    monkeypatch.setattr(workflow, 'complete', complete)
    return contexts


def test_normal_rag_does_not_query_private_health_data(fixture, monkeypatch):
    client, factory, _ = fixture
    contexts = stub(monkeypatch)
    result = client.post('/api/ai/chat', json={'profile_id': 10, 'question': '高血压老人能吃鸡蛋吗'}).json()
    assert result['code'] == 0
    assert result['data']['intent'] == 'NORMAL'
    assert result['data']['agent'] == 'HEALTH'
    assert '高血压：测量与日常管理' in result['data']['sources']
    assert result['data']['retrieval']['semantic_embedding'] is False
    assert all('185' not in context and '122' not in context for context in contexts)


def test_data_path_returns_real_records_and_excludes_other_elder(fixture, monkeypatch):
    client, _, _ = fixture
    contexts = stub(monkeypatch)
    result = client.post('/api/ai/chat', json={'profile_id': 10, 'question': '我最近血压怎么样'}).json()['data']
    assert result['intent'] == 'DATA' and result['agent'] == 'HEALTH_DATA'
    assert '185/95' in result['answer'] and '记录#100' in result['answer']
    assert '122/81' not in contexts[0]


def test_abnormal_path_references_specific_warning(fixture, monkeypatch):
    client, _, _ = fixture
    stub(monkeypatch)
    result = client.post('/api/ai/chat', json={'profile_id': 10, 'question': '这个预警是怎么回事'}).json()['data']
    assert result['intent'] == 'ABNORMAL' and result['agent'] == 'RISK'
    assert '预警#200' in result['answer'] and '185/95' in result['answer']


def test_emergency_without_key_creates_warning_and_all_recipients(fixture):
    client, factory, _ = fixture
    result = client.post('/api/ai/chat', json={'profile_id': 10, 'question': '我胸口很痛，喘不上气'}).json()
    assert result['code'] == 0 and result['data']['safety_level'] == 'L4'
    assert result['data']['model_status'] == 'BYPASSED_FOR_SAFETY'
    assert '120' in result['data']['answer']
    with factory() as db:
        warning = db.get(HealthWarning, result['data']['warning_id'])
        assert warning.trigger_source == 'AI_CHAT' and warning.level == 3
        ids = set(db.scalars(select(AlertReceiver.user_id).where(AlertReceiver.warning_id == warning.id)))
        assert ids == {1, 2, 3}


def test_original_mysql_keyword_configuration_understands_acceptance_example(fixture):
    client, factory, _ = fixture
    with factory() as db:
        row = db.scalar(select(SysConfig).where(SysConfig.config_key == 'emergency_keywords'))
        row.config_value = json.dumps(['胸痛', '呼吸困难', '意识丧失', '昏厥', '无法起身', '大量出血', '言语不清'], ensure_ascii=False)
        db.commit()
    result = client.post('/api/ai/chat', json={'profile_id': 10, 'question': '我胸口很痛，喘不上气'}).json()
    assert result['code'] == 0 and result['data']['intent'] == 'EMERGENCY'


def test_missing_key_returns_3001_without_fake_model_success(fixture):
    client, _, _ = fixture
    result = client.post('/api/ai/chat', json={'profile_id': 10, 'question': '我最近血压怎么样'})
    assert result.status_code == 503 and result.json()['code'] == 3001


def test_care_cannot_start_private_ai_consultations(fixture):
    client, _, user_ref = fixture
    user_ref['id'] = 3
    assert client.post('/api/ai/chat', json={'profile_id': 10, 'question': '最近记录'}).json()['code'] == 1002


def test_ai_requires_explicit_privacy_consent(fixture):
    client, factory, _ = fixture
    with factory() as db:
        db.delete(db.scalar(select(SysConfig).where(SysConfig.config_key == 'privacy_consent:1')))
        db.commit()
    response = client.post('/api/ai/chat', json={'profile_id': 10, 'question': '胸痛'})
    assert response.status_code == 403 and response.json()['code'] == 1002
    with factory() as db:
        assert db.scalar(select(func.count(HealthWarning.id))) == 1


def test_session_profile_mismatch_and_data_ownership_are_rejected(fixture, monkeypatch):
    client, _, user_ref = fixture
    stub(monkeypatch)
    session_id = client.post('/api/ai/chat', json={'profile_id': 10, 'question': '我最近血压怎么样'}).json()['data']['session_id']
    assert client.post('/api/ai/chat', json={'profile_id': 11, 'session_id': session_id, 'question': '最近记录'}).json()['code'] == 2001
    user_ref['id'] = 4
    assert client.get(f'/api/ai/sessions/{session_id}/messages').json()['code'] == 1002
    assert client.post('/api/ai/chat', json={'profile_id': 10, 'question': '最近记录'}).json()['code'] == 1002


def test_unbinding_immediately_revokes_consultation_access(fixture, monkeypatch):
    client, factory, user_ref = fixture
    stub(monkeypatch)
    result = client.post('/api/ai/chat', json={'profile_id': 10, 'question': '我最近血压怎么样'}).json()['data']
    user_ref['id'] = 2
    assert client.get(f"/api/ai/sessions/{result['session_id']}/messages").json()['code'] == 0
    with factory() as db:
        db.scalar(select(FamilyBind)).status = 'REVOKED'
        db.commit()
    assert client.get(f"/api/ai/sessions/{result['session_id']}/messages").json()['code'] == 1002


def test_summary_failure_and_success_use_independent_db_session(fixture, monkeypatch):
    _, factory, _ = fixture
    workflow.generate_summary(200)
    with factory() as db:
        warning = db.get(HealthWarning, 200)
        assert warning.summary_status == 'FAILED' and warning.status == 'PENDING'
        warning.summary_status = 'PENDING'
        db.commit()
    contexts = stub(monkeypatch)
    workflow.generate_summary(200)
    with factory() as db:
        assert db.get(HealthWarning, 200).summary_status == 'SUCCESS'
    assert '预警#200' in contexts[0] and '185/95' in contexts[0]


def test_active_summary_does_not_start_duplicate_model_job(fixture, monkeypatch):
    from app.services.recovery import summary_job
    _, factory, _ = fixture
    contexts = stub(monkeypatch)
    with summary_job(200) as claimed:
        assert claimed is True
        workflow.generate_summary(200)
        assert contexts == []
        with factory() as db:
            assert db.get(HealthWarning, 200).summary_status == 'PENDING'
    workflow.generate_summary(200)
    assert len(contexts) == 1
    with factory() as db:
        assert db.get(HealthWarning, 200).summary_status == 'SUCCESS'


def test_daily_limit_survives_deleting_chat_and_emergency_is_still_allowed(fixture, monkeypatch):
    client, factory, _ = fixture
    stub(monkeypatch)
    with factory() as db:
        db.add(SysConfig(config_key='ai_daily_limit', config_value='1', enabled=1))
        db.commit()
    result = client.post('/api/ai/chat', json={'profile_id': 10, 'question': '我最近血压怎么样'}).json()['data']
    assert client.delete(f"/api/ai/sessions/{result['session_id']}").json()['code'] == 0
    assert client.post('/api/ai/chat', json={'profile_id': 10, 'question': '最近记录'}).json()['code'] == 3002
    assert client.post('/api/ai/chat', json={'profile_id': 10, 'question': '胸痛'}).json()['data']['intent'] == 'EMERGENCY'


def test_chroma_rebuild_after_knowledge_changes(fixture):
    _, factory, _ = fixture
    with factory() as db:
        hits = rag.retrieve(db, '高血压')
        assert '高血压：测量与日常管理' in [hit['title'] for hit in hits]
        db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.category == '高血压')).enabled = 0
        db.commit()
        hits = rag.retrieve(db, '高血压')
        assert all(hit['title'] != '高血压：测量与日常管理' for hit in hits)


def test_local_semantic_embedding_never_downloads_and_has_separate_collection(fixture, tmp_path, monkeypatch):
    _, factory, _ = fixture
    with factory() as db:
        assert rag.rebuild_index(db)['semantic_embedding'] is False
    model_path = tmp_path / 'existing-local-model'
    model_path.mkdir()
    (model_path / 'modules.json').write_text('[]', encoding='utf-8')
    calls = []
    class LocalModelStub:
        def __init__(self, path, **kwargs):
            calls.append((path, kwargs))
        def encode(self, texts, **kwargs):
            return [[1.0, 0.0, 0.0] if '血压' in text else [0.0, 1.0, 0.0] for text in texts]
    module = types.ModuleType('sentence_transformers')
    module.SentenceTransformer = LocalModelStub
    monkeypatch.setitem(sys.modules, 'sentence_transformers', module)
    monkeypatch.setenv('EMBEDDING_PROVIDER', 'sentence-transformers')
    monkeypatch.setenv('EMBEDDING_MODEL_PATH', str(model_path))
    with factory() as db:
        result = rag.rebuild_index(db)
        assert result['semantic_embedding'] is True
        assert '血压' in rag.retrieve(db, '高血压')[0]['title']
    assert calls[0][1] == {'device': 'cpu', 'local_files_only': True, 'trust_remote_code': False}


def test_missing_local_semantic_files_fail_instead_of_downloading(fixture, tmp_path, monkeypatch):
    monkeypatch.setenv('EMBEDDING_PROVIDER', 'sentence-transformers')
    monkeypatch.setenv('EMBEDDING_MODEL_PATH', str(tmp_path / 'missing-model'))
    with pytest.raises(APIError) as exc:
        rag.embed('测试问题')
    assert exc.value.code == 3001


def test_missing_semantic_dependency_does_not_fake_hash_success(fixture, tmp_path, monkeypatch):
    model_path = tmp_path / 'existing-local-model'
    model_path.mkdir()
    (model_path / 'modules.json').write_text('[]', encoding='utf-8')
    monkeypatch.setenv('EMBEDDING_PROVIDER', 'sentence-transformers')
    monkeypatch.setenv('EMBEDDING_MODEL_PATH', str(model_path))
    monkeypatch.setitem(sys.modules, 'sentence_transformers', None)
    with pytest.raises(APIError) as exc:
        rag.embed('测试问题')
    assert exc.value.code == 3001


@pytest.mark.parametrize('category,question', [
    ('高血压', '高血压没有症状也要测量血压吗'),
    ('糖尿病', '糖尿病平时除了测血糖还要注意什么'),
    ('心率异常', '心跳过快或乱跳，心悸什么时候需要就医'),
    ('睡眠', '失眠时怎样调整睡眠习惯'),
    ('老年运动', '老年人总坐着，日常步行和家务算运动吗'),
    ('老年饮食', '老年人吃饭怎样做到少盐和饮食均衡'),
    ('常见问题', '一次血压升高能判断疾病吗'),
])
def test_official_corpus_wording_queries_retrieve_each_category(fixture, category, question):
    """Seven concrete lexical queries; this is not a semantic-recall benchmark."""
    _, factory, _ = fixture
    expected = next(entry['title'] for entry in load_corpus()['documents'] if entry['category'] == category)
    with factory() as db:
        hits = rag.retrieve(db, question, top_k=3)
    assert expected in [hit['title'] for hit in hits]
    assert all(hit['provider'] == 'hash' and hit['semantic_embedding'] is False for hit in hits)
    assert any('官方来源' in hit['text'] and 'https://' in hit['text'] for hit in hits)


def test_official_import_preserves_edited_disabled_entries_and_is_idempotent(fixture):
    _, factory, _ = fixture
    with factory() as db:
        assert db.scalar(select(func.count(KnowledgeDocument.id))) == 7
        row = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.category == '高血压'))
        row.content = '管理员已经复核并编辑的现有条目'
        row.enabled = 0
        db.commit()
        result = import_knowledge(db, reindex=False)
        assert result['added'] == 0 and result['preserved'] == 7
        assert row.content == '管理员已经复核并编辑的现有条目' and row.enabled == 0
        assert db.scalar(select(func.count(KnowledgeDocument.id))) == 7


def test_official_import_preview_does_not_write_to_database(fixture):
    _, factory, _ = fixture
    with factory() as db:
        row = db.scalar(select(KnowledgeDocument).where(KnowledgeDocument.category == '睡眠'))
        db.delete(row)
        db.commit()
        result = import_knowledge(db, dry_run=True)
        assert result['dry_run'] is True and result['added'] == 1
        assert db.scalar(select(func.count(KnowledgeDocument.id))) == 6


def test_output_gate_blocks_diagnosis_and_dose_changes():
    assert '系统已拦截' in llm.safe_answer('您确诊为高血压，请把药加倍。')
    assert '系统已拦截' in llm.safe_answer('建议增加剂量为每日两片。')
    assert '系统已拦截' in llm.safe_answer('口服氨氯地平5mg每日一次。')


@pytest.mark.parametrize('provider,key,url,model', [('deepseek', 'DEEPSEEK_API_KEY', 'https://api.deepseek.com/v1', 'deepseek-chat'),
    ('qwen', 'QWEN_API_KEY', 'https://dashscope.aliyuncs.com/compatible-mode/v1', 'qwen-plus'),
    ('glm', 'GLM_API_KEY', 'https://open.bigmodel.cn/api/paas/v4', 'glm-4-flash')])
def test_domestic_provider_switch_uses_environment_only(monkeypatch, provider, key, url, model):
    for variable in ('LLM_BASE_URL', 'LLM_MODEL', f'{provider.upper()}_BASE_URL', f'{provider.upper()}_MODEL'):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setenv('LLM_PROVIDER', provider)
    monkeypatch.setenv(key, 'test-key-not-real')
    assert llm.provider_config() == (provider, 'test-key-not-real', url, model)
