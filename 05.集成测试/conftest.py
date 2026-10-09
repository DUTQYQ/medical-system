"""Independent API acceptance tests use a temporary SQLite database only."""
import os
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1] / '04.编码' / '后端'
sys.path.insert(0, str(BACKEND))
TEST_ROOT = Path(tempfile.mkdtemp(prefix='kangyang-acceptance-'))
TEST_URL = os.environ.get('KANGYANG_TEST_DATABASE_URL')
if TEST_URL:
    import re
    from sqlalchemy.engine import make_url
    test_name = make_url(TEST_URL).database
    if not re.fullmatch(r'kangyang_codex_test_[0-9a-f]{8}', test_name or '') or test_name != os.environ.get('KANGYANG_TEMP_DB_NAME'):
        raise RuntimeError('Acceptance tests refuse to reset a non-disposable database')
os.environ['DATABASE_URL'] = TEST_URL or 'sqlite:///' + str(TEST_ROOT / 'test.db').replace('\\', '/')
os.environ['SECRET_KEY'] = 'independent-test-secret-never-use-for-deployment'
os.environ['JWT_SECRET'] = os.environ['SECRET_KEY']
os.environ['LLM_PROVIDER'] = 'deepseek'
os.environ['DEEPSEEK_API_KEY'] = ''
os.environ['DASHSCOPE_API_KEY'] = ''
os.environ['ZHIPU_API_KEY'] = ''
os.environ['VECTOR_STORE_PATH'] = str(TEST_ROOT / 'vectors')
os.environ['ANONYMIZED_TELEMETRY'] = 'False'

from fastapi.testclient import TestClient
from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models import User, ElderProfile, FamilyBind, CareRelation, SysConfig
from app.main import app

PASSWORD = 'Abc123456'
PASSWORD_HASH = hash_password(PASSWORD)


@pytest.fixture
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        for uid, role in enumerate(['ADMIN', 'ELDER', 'FAMILY', 'CARE', 'FAMILY', 'ELDER'], 1):
            db.add(User(id=uid, phone=f'1300000000{uid}', name=role + str(uid),
                        password_hash=PASSWORD_HASH, role=role, status=1))
        db.flush()
        db.add_all([ElderProfile(id=2001, user_id=2, name='测试老人一', deleted=0),
                    ElderProfile(id=2002, user_id=6, name='测试老人二', deleted=0)])
        db.flush()
        db.add_all([FamilyBind(id=9001, family_user_id=3, profile_id=2001, status='APPROVED'),
                    FamilyBind(id=9002, family_user_id=5, profile_id=2001, status='APPROVED'),
                    CareRelation(id=8001, care_user_id=4, profile_id=2001, status=1)])
        thresholds = {
            'BLOOD_PRESSURE_SYSTOLIC': '{"level0":"90~139","level1":"140~159","level2":"160~179","level3":"<90 或 >=180"}',
            'BLOOD_PRESSURE_DIASTOLIC': '{"level0":"60~89","level1":"90~99","level2":"100~109","level3":"<60 或 >=110"}',
            'BLOOD_SUGAR': '{"level0":"3.9~6.1","level1":"6.2~7.0","level2":"7.1~11.1","level3":"<3.9 或 >=11.2"}',
            'HEART_RATE': '{"level0":"60~100","level1":"50~59,101~110","level2":"40~49,111~130","level3":"<40 或 >130"}',
            'SLEEP_HOURS': '{"level0":">=7","level1":"6~7","level2":"5~6","level3":"<5"}',
            'STEP_COUNT': '{"level0":">=6000","level1":"4000~5999","level2":"2000~3999","level3":"<2000"}',
        }
        for key, value in thresholds.items():
            db.add(SysConfig(config_key=key, config_value=value, config_type='threshold', group_name='threshold', enabled=1))
        for key, value in {'family_bind_max': '5', 'ai_summary_timeout_sec': '1',
                           'emergency_keywords': '["胸痛","胸口很痛","喘不上气","呼吸困难"]'}.items():
            db.add(SysConfig(config_key=key, config_value=value, config_type='string', group_name='system', enabled=1))
        db.commit()
    with TestClient(app) as active:
        yield active


def login(client, uid, consent=True):
    result = client.post('/api/auth/login', json={'phone': f'1300000000{uid}', 'password': PASSWORD}).json()
    assert result['code'] == 0, result
    headers = {'Authorization': 'Bearer ' + result['data']['token']}
    if consent:
        answer = client.post('/api/auth/privacy-consent', json={'accepted': True}, headers=headers).json()
        assert answer['code'] == 0, answer
    return headers


def expect(response, code=0):
    body = response.json()
    assert body['code'] == code, body
    return body.get('data')
