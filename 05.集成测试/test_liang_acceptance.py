"""Contributed pages' API integration on the disposable acceptance database."""
from datetime import timedelta
from conftest import login, expect
from app.core.database import SessionLocal, now
from app.models import Activity, ActivityTemplate
from scripts.seed_services import seed_services


def test_activity_template_maintenance_recommendation_and_service_request(client):
    admin, elder, family, outsider = [login(client, i) for i in (1, 2, 3, 6)]
    with SessionLocal() as db:
        seed_services(db, demo=False)
        db.commit()
    item = expect(client.post('/api/activities', headers=admin,
        json={'code': 'CHESS_REVIEW', 'name': '棋牌交流', 'category': '棋牌', 'rules': {}}))
    unavailable = expect(client.get('/api/activities/recommend?profile_id=2001', headers=family))
    assert unavailable[0]['suitability'] == '需确认'
    expect(client.post('/api/health/records', headers=elder, json={'profile_id': 2001, 'type': 'HEART_RATE',
        'values': {'value': 75}, 'measured_at': (now()-timedelta(seconds=1)).isoformat()}))
    recommended = expect(client.get('/api/activities/recommend?profile_id=2001', headers=elder))[0]
    assert recommended['suitability'] == '可了解' and recommended['profile_id'] == 2001
    expect(client.get('/api/health/status?profile_id=2001', headers=outsider), 1002)
    expect(client.get('/api/activities/recommend?profile_id=2001', headers=outsider), 1002)
    request = expect(client.post('/api/services/requests', headers=elder, json={'profile_id': recommended['profile_id'],
        'category': recommended['service_category'], 'title': '申请了解棋牌活动', 'description': '请工作人员核验安排', 'location': '101室'}))
    assert request['status'] == 'SUBMITTED'
    expect(client.delete(f'/api/activities/{item["activity_id"]}', headers=admin))
    assert expect(client.get('/api/activities', headers=elder)) == []
    with SessionLocal() as db:
        assert db.get(ActivityTemplate, item['activity_id']).enabled == 0
        assert Activity.__tablename__ == 'care_activity'


def test_typed_activity_rules_and_disabled_templates_on_mysql(client):
    admin = login(client, 1)
    for rules in [[], {'suitable': {'min_age': True}}, {'suitable': {'min_age': 90, 'max_age': 30}}, {'caution': {'max_risk_level': 'bad'}}]:
        assert client.post('/api/activities', headers=admin, json={'code': 'INVALID', 'name': '错误规则', 'rules': rules}).status_code == 422
    status = expect(client.get('/api/health/status?profile_id=2001', headers=login(client, 3)))
    assert all(row['risk_level'] is None and row['judgement'] == '未记录' for row in status)
