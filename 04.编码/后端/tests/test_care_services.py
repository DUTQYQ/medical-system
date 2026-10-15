"""独立 SQLite 验收院内服务状态、最小权限、名额和库存。"""
from datetime import timedelta
import pytest
from sqlalchemy import select
from test_business import setup, login, first_profile
from app.core.database import now
from app.models import User, ElderProfile, CareRelation, FamilyBind, SysConfig
from app.models.care_services import (ServiceRequest, ServiceEvent, Activity, ActivityRegistration,
                                      Equipment, EquipmentLoan, ServiceNotification)
from app.services.care_services import escalate_overdue_calls, get_service_profile, validate_assignee
from app.core.errors import APIError
from scripts.seed_services import seed_services


def data(response):
    payload = response.json()
    assert payload['code'] == 0, payload
    return payload['data']


def request(client, headers, profile_id, **extra):
    payload = {'profile_id': profile_id, 'category': 'ENTERTAINMENT', 'title': '下午想打牌',
               'description': '请帮助安排', 'location': 'A栋101室'}
    payload.update(extra)
    return client.post('/api/services/requests', headers=headers, json=payload)


def activity(client, headers, capacity=1):
    return data(client.post('/api/services/activities', headers=headers, json={
        'title': '棋类活动', 'category': 'ENTERTAINMENT', 'start_at': (now()+timedelta(days=1)).isoformat(),
        'end_at': (now()+timedelta(days=1, hours=1)).isoformat(), 'location': '活动室',
        'capacity': capacity, 'status': 'PUBLISHED'}))


def second_profile(sessions):
    with sessions() as db:
        elder = db.scalar(select(User).where(User.role == 'ELDER'))
        profile = ElderProfile(user_id=elder.id, name='第二份独立档案', deleted=0)
        db.add(profile)
        db.commit()
        return profile.id


def accept(client, headers, request_id):
    return client.post(f'/api/services/requests/{request_id}/transition', headers=headers, json={'status': 'ACCEPTED'})


def test_call_works_before_health_consent_and_repeated_click_is_same_request(setup):
    client, sessions = setup
    raw = data(client.post('/api/auth/login', json={'phone': '13000000002', 'password': 'Abc123456'}))
    elder = {'Authorization': 'Bearer '+raw['token']}
    profiles = data(client.get('/api/services/profiles', headers=elder))
    assert client.get('/api/profiles', headers=elder).status_code == 403
    body = {'profile_id': profiles[0]['profile_id'], 'location': '101室', 'description': '请来帮忙'}
    first = data(client.post('/api/services/calls', headers=elder, json=body))
    repeat = data(client.post('/api/services/calls', headers=elder, json=body))
    assert first['request_id'] == repeat['request_id'] and repeat['reused']
    assert first['priority'] == 3
    with sessions() as db:
        assert db.scalar(select(ServiceRequest).where(ServiceRequest.id == first['id'])).status == 'SUBMITTED'
        assert len(list(db.scalars(select(ServiceEvent).where(ServiceEvent.request_id == first['id'])))) == 1


def test_service_full_workflow_read_is_not_completion_and_requires_result(setup):
    client, sessions = setup
    elder, care = login(client, 2), login(client, 4)
    profile_id = first_profile(client, elder)
    created = data(request(client, elder, profile_id))
    notification = data(client.get('/api/services/notifications', headers=care))['list'][0]
    data(client.post(f'/api/services/notifications/{notification["id"]}/read', headers=care))
    assert data(client.get(f'/api/services/requests/{created["id"]}', headers=elder))['status'] == 'SUBMITTED'
    assert data(accept(client, care, created['id']))['status'] == 'ACCEPTED'
    assert accept(client, care, created['id']).status_code == 409
    path = f'/api/services/requests/{created["id"]}/transition'
    assert client.post(path, headers=elder, json={'status': 'IN_PROGRESS'}).status_code == 403
    data(client.post(path, headers=care, json={'status': 'IN_PROGRESS'}))
    assert client.post(path, headers=care, json={'status': 'COMPLETED'}).status_code == 400
    done = data(client.post(path, headers=care, json={'status': 'COMPLETED', 'result': '已安排棋牌活动并陪同前往'}))
    assert done['completed_at'] and done['result']
    assert client.post(path, headers=care, json={'status': 'COMPLETED', 'result': '重复'}).status_code == 409
    assert len(data(client.get(f'/api/services/requests/{created["id"]}', headers=elder))['events']) == 4


def test_family_can_withdraw_only_own_pending_requests_and_activity_signups(setup):
    client, sessions = setup
    elder, family, care = login(client, 2), login(client, 3), login(client, 4)
    profile_id = first_profile(client, elder)
    elder_request = data(request(client, elder, profile_id))
    family_request = data(request(client, family, profile_id, title='家属申请陪同散步'))
    transition_path = lambda row: f'/api/services/requests/{row["id"]}/transition'
    assert client.post(transition_path(elder_request), headers=family, json={'status': 'CANCELLED'}).status_code == 403
    assert client.post(transition_path(elder_request), headers=family, json={'status': 'ACCEPTED'}).status_code == 403
    assert data(client.post(transition_path(family_request), headers=family, json={'status': 'CANCELLED'}))['status'] == 'CANCELLED'

    event = activity(client, care)
    register_path = f'/api/services/activities/{event["id"]}/register'
    registration = data(client.post(register_path, headers=family, json={'profile_id': profile_id}))
    cancel_path = f'/api/services/registrations/{registration["id"]}/transition'
    assert client.post(cancel_path, headers=elder, json={'status': 'CANCELLED'}).status_code == 403
    assert data(client.post(cancel_path, headers=family, json={'status': 'CANCELLED'}))['status'] == 'CANCELLED'
    other_profile = second_profile(sessions)
    assert client.post(register_path, headers=family, json={'profile_id': other_profile}).status_code == 403
    with sessions() as db:
        assert db.get(Activity, event['id']).reserved_count == 0


def test_revoke_care_hides_old_service_and_notifications(setup):
    client, sessions = setup
    elder, care = login(client, 2), login(client, 4)
    profile_id = first_profile(client, elder)
    created = data(request(client, elder, profile_id))
    notes = data(client.get('/api/services/notifications', headers=care))
    assert notes['total']
    with sessions() as db:
        relation = db.scalar(select(CareRelation).where(CareRelation.profile_id == profile_id))
        relation.status = 0
        db.commit()
    assert client.get(f'/api/services/requests/{created["id"]}', headers=care).status_code == 403
    assert data(client.get('/api/services/notifications', headers=care))['total'] == 0
    assert client.post(f'/api/services/notifications/{notes["list"][0]["id"]}/read', headers=care).status_code == 403
    assert data(client.get('/api/services/requests', headers=care))['total'] == 0


def test_unrelated_profile_staff_cannot_access_or_accept(setup):
    client, sessions = setup
    elder, care = login(client, 2), login(client, 4)
    other = second_profile(sessions)
    created = data(request(client, elder, other))
    assert accept(client, care, created['id']).status_code == 403
    assert client.post('/api/services/calls', headers=care, json={'profile_id': other, 'location': '其他老人房间'}).status_code == 403


def test_call_without_carer_defaults_to_admin_and_timeout_escalates_once(setup):
    client, sessions = setup
    elder, admin = login(client, 2), login(client, 1)
    other = second_profile(sessions)
    no_care = data(client.post('/api/services/calls', headers=elder, json={'profile_id': other, 'location': '102室'}))
    assert no_care['escalated_at'] and no_care['assigned_name'] == '系统管理员'
    profile = first_profile(client, elder)
    waiting = data(client.post('/api/services/calls', headers=elder, json={'profile_id': profile, 'location': '101室'}))
    with sessions() as db:
        db.get(ServiceRequest, waiting['id']).create_time = now()-timedelta(minutes=6)
        db.commit()
        assert escalate_overdue_calls(db) == 1
        db.commit()
        assert escalate_overdue_calls(db) == 0
        db.commit()
    overdue = data(client.get(f'/api/services/requests/{waiting["id"]}', headers=admin))
    assert overdue['escalated_at'] and overdue['assigned_name'] == '系统管理员'
    assert any('超时' in note['title'] for note in data(client.get('/api/services/notifications', headers=admin))['list'])


def test_activity_duplicate_full_cancel_frees_one_place_and_profile_acl(setup):
    client, sessions = setup
    elder, admin, care = login(client, 2), login(client, 1), login(client, 4)
    first, second = first_profile(client, elder), second_profile(sessions)
    item = activity(client, admin, 1)
    path = f'/api/services/activities/{item["id"]}/register'
    registered = data(client.post(path, headers=elder, json={'profile_id': first}))
    assert client.post(path, headers=elder, json={'profile_id': first}).status_code == 409
    assert client.post(path, headers=elder, json={'profile_id': second}).status_code == 409
    assert client.post(path, headers=care, json={'profile_id': second}).status_code == 403
    data(client.post(f'/api/services/registrations/{registered["id"]}/transition', headers=elder, json={'status': 'CANCELLED'}))
    data(client.post(path, headers=elder, json={'profile_id': second}))
    with sessions() as db:
        assert db.get(Activity, item['id']).reserved_count == 1


def test_only_staff_can_record_attendance_after_activity_starts(setup):
    client, sessions = setup
    elder, admin, care = login(client, 2), login(client, 1), login(client, 4)
    profile = first_profile(client, elder)
    item = activity(client, admin)
    registered = data(client.post(f'/api/services/activities/{item["id"]}/register', headers=elder, json={'profile_id': profile}))
    path = f'/api/services/registrations/{registered["id"]}/transition'
    assert client.post(path, headers=elder, json={'status': 'ATTENDED'}).status_code == 403
    assert client.post(path, headers=care, json={'status': 'ATTENDED'}).status_code == 409
    with sessions() as db:
        db.get(Activity, item['id']).start_at = now()-timedelta(minutes=1)
        db.commit()
    assert data(client.post(path, headers=care, json={'status': 'ATTENDED'}))['status'] == 'ATTENDED'


def borrow(client, admin, elder, care, profile):
    item = data(client.post('/api/services/equipment', headers=admin, json={'name': '轮椅', 'total': 1}))
    created = data(client.post(f'/api/services/equipment/{item["id"]}/request', headers=elder,
        json={'profile_id': profile, 'quantity': 1, 'location': '101室'}))
    data(accept(client, care, created['id']))
    loan = next(row for row in data(client.get('/api/services/loans', headers=care)) if row['request_id'] == created['id'])
    return item, created, loan


def test_equipment_acceptance_out_of_stock_rolls_back_no_second_loan(setup):
    client, sessions = setup
    elder, admin, care = login(client, 2), login(client, 1), login(client, 4)
    profile = first_profile(client, elder)
    item = data(client.post('/api/services/equipment', headers=admin, json={'name': '唯一轮椅', 'total': 1}))
    path = f'/api/services/equipment/{item["id"]}/request'
    body = {'profile_id': profile, 'quantity': 1, 'location': '101室'}
    first, second = data(client.post(path, headers=elder, json=body)), data(client.post(path, headers=elder, json=body))
    data(accept(client, care, first['id']))
    assert accept(client, care, second['id']).status_code == 409
    assert data(client.get(f'/api/services/requests/{second["id"]}', headers=care))['status'] == 'SUBMITTED'
    with sessions() as db:
        assert db.get(Equipment, item['id']).available == 0
        assert len(list(db.scalars(select(EquipmentLoan).where(EquipmentLoan.equipment_id == item['id'])))) == 1


def test_equipment_return_is_idempotent_and_damaged_does_not_restore_available(setup):
    client, sessions = setup
    elder, admin, care = login(client, 2), login(client, 1), login(client, 4)
    item, request_row, loan = borrow(client, admin, elder, care, first_profile(client, elder))
    path = f'/api/services/loans/{loan["id"]}/return'
    assert client.post(path, headers=elder, json={'damaged': False}).status_code == 403
    data(client.post(path, headers=care, json={'damaged': True, 'note': '车轮损坏'}))
    data(client.post(path, headers=care, json={'damaged': False}))
    with sessions() as db:
        equipment = db.get(Equipment, item['id'])
        assert equipment.available == 0 and equipment.damaged == 1
        assert db.get(EquipmentLoan, loan['id']).status == 'RETURNED_DAMAGED'


def test_undamaged_return_restores_stock_once(setup):
    client, sessions = setup
    elder, admin, care = login(client, 2), login(client, 1), login(client, 4)
    item, _, loan = borrow(client, admin, elder, care, first_profile(client, elder))
    for _ in range(2):
        data(client.post(f'/api/services/loans/{loan["id"]}/return', headers=care, json={'damaged': False}))
    with sessions() as db:
        assert db.get(Equipment, item['id']).available == 1


def test_catalog_config_reserved_categories_and_input_validation(setup):
    client, _ = setup
    admin, elder = login(client, 1), login(client, 2)
    assert client.post('/api/services/catalog', headers=elder, json={'category': 'READING', 'name': '读书'}).status_code == 403
    data(client.post('/api/services/catalog', headers=admin, json={'category': 'READING', 'name': '读书陪伴'}))
    data(client.put('/api/services/catalog/READING', headers=admin, json={'name': '读书陪伴', 'enabled': False}))
    assert not any(row['category'] == 'READING' for row in data(client.get('/api/services/catalog', headers=elder)))
    assert client.put('/api/services/catalog/CALL', headers=admin, json={'name': '呼叫', 'enabled': False}).status_code == 400
    profile = first_profile(client, elder)
    assert request(client, elder, profile, category='CALL').status_code == 400
    assert request(client, elder, profile, category='READING').status_code == 400
    assert request(client, elder, profile, location='').status_code == 422
    assert request(client, elder, profile, requested_at='2026-10-13T10:00:00Z').status_code == 422


def test_seed_existing_deployment_never_invents_equipment_or_activity(setup):
    _, sessions = setup
    with sessions() as db:
        before = (len(list(db.scalars(select(Activity)))), len(list(db.scalars(select(Equipment)))))
        seed_services(db, demo=False)
        db.commit()
        seed_services(db, demo=False)
        db.commit()
        after = (len(list(db.scalars(select(Activity)))), len(list(db.scalars(select(Equipment)))))
        assert before == after


def test_disabled_assignee_is_reassigned_and_call_escalated_immediately(setup):
    client, sessions = setup
    elder, admin = login(client, 2), login(client, 1)
    profile = first_profile(client, elder)
    call = data(client.post('/api/services/calls', headers=elder, json={'profile_id': profile, 'location': '101室'}))
    with sessions() as db:
        carer = db.scalar(select(User).where(User.role == 'CARE'))
        carer.status = 0
        db.commit()
        assert escalate_overdue_calls(db) >= 1
        db.commit()
    result = data(client.get(f'/api/services/requests/{call["id"]}', headers=admin))
    assert result['assigned_name'] == '系统管理员' and result['escalated_at']
    assert any('重新分派' in item['note'] for item in result['events'])


def test_activity_draft_publish_close_cancel_releases_places_and_notifies(setup):
    client, sessions = setup
    elder, admin, care = login(client, 2), login(client, 1), login(client, 4)
    profile = first_profile(client, elder)
    item = data(client.post('/api/services/activities', headers=care, json={
        'title': '可变更棋牌活动', 'category': 'ENTERTAINMENT',
        'start_at': (now()+timedelta(days=1)).isoformat(), 'end_at': (now()+timedelta(days=1, hours=1)).isoformat(),
        'location': '活动室', 'capacity': 2, 'status': 'DRAFT'}))
    registration_path = f'/api/services/activities/{item["id"]}/register'
    assert client.post(registration_path, headers=elder, json={'profile_id': profile}).status_code == 409
    transition_path = f'/api/services/activities/{item["id"]}/transition'
    assert client.post(transition_path, headers=elder, json={'status': 'PUBLISHED'}).status_code == 403
    assert data(client.post(transition_path, headers=care, json={'status': 'PUBLISHED'}))['status'] == 'PUBLISHED'
    registration = data(client.post(registration_path, headers=elder, json={'profile_id': profile}))
    assert data(client.post(transition_path, headers=care, json={'status': 'CLOSED'}))['status'] == 'CLOSED'
    assert client.post(registration_path, headers=elder, json={'profile_id': second_profile(sessions)}).status_code == 409
    cancelled = data(client.post(transition_path, headers=admin, json={'status': 'CANCELLED'}))
    assert cancelled['registered_count'] == 0 and cancelled['status'] == 'CANCELLED'
    with sessions() as db:
        assert db.get(ActivityRegistration, registration['id']).status == 'CANCELLED'
    notes = data(client.get('/api/services/notifications', headers=elder))['list']
    assert any(note['title'] == '活动已取消' and note['ref_id'] == item['id'] for note in notes)
    assert client.post(transition_path, headers=admin, json={'status': 'PUBLISHED'}).status_code == 409
    assert client.post(f'/api/services/registrations/{registration["id"]}/transition', headers=care,
                       json={'status': 'ATTENDED'}).status_code == 409


def test_caregiver_cannot_cancel_activity_created_by_other_staff(setup):
    client, _ = setup
    admin, care = login(client, 1), login(client, 4)
    item = activity(client, admin)
    assert client.post(f'/api/services/activities/{item["id"]}/transition', headers=care,
                       json={'status': 'CANCELLED'}).status_code == 403


def test_equipment_admin_maintenance_preserves_borrowed_damaged_and_total(setup):
    client, sessions = setup
    elder, admin, care = login(client, 2), login(client, 1), login(client, 4)
    profile = first_profile(client, elder)
    item, _, loan = borrow(client, admin, elder, care, profile)
    path = f'/api/services/equipment/{item["id"]}'
    assert client.put(path, headers=care, json={'enabled': False}).status_code == 403
    assert client.put(path, headers=admin, json={'total': 0}).status_code == 409
    updated = data(client.put(path, headers=admin, json={'total': 3, 'description': '实际新增两台'}))
    assert updated['total'] == 3 and updated['available'] == 2
    data(client.put(path, headers=admin, json={'enabled': False}))
    assert not any(row['id'] == item['id'] for row in data(client.get('/api/services/equipment', headers=elder)))
    assert client.post(path+'/request', headers=elder, json={'profile_id': profile, 'quantity': 1, 'location': '101室'}).status_code == 404
    # Disabled devices can still be returned; stock does not become publicly loanable.
    data(client.post(f'/api/services/loans/{loan["id"]}/return', headers=care, json={'damaged': True}))
    assert client.put(path, headers=admin, json={'total': 0}).status_code == 409
    maintained = data(client.put(path, headers=admin, json={'total': 1, 'enabled': True}))
    assert maintained['available'] == 0 and maintained['damaged'] == 1 and maintained['total'] == 1


def test_call_timeout_can_be_configured_by_admin_and_is_used_immediately(setup):
    client, sessions = setup
    elder, admin, care = login(client, 2), login(client, 1), login(client, 4)
    assert data(client.get('/api/services/settings', headers=elder))['call_timeout_seconds'] == 300
    assert client.put('/api/services/settings', headers=care, json={'call_timeout_seconds': 15}).status_code == 403
    for value in (14, 3601):
        assert client.put('/api/services/settings', headers=admin, json={'call_timeout_seconds': value}).status_code == 422
    data(client.put('/api/services/settings', headers=admin, json={'call_timeout_seconds': 15}))
    assert data(client.get('/api/services/settings', headers=admin))['call_timeout_seconds'] == 15
    created = data(client.post('/api/services/calls', headers=elder,
        json={'profile_id': first_profile(client, elder), 'location': '101室'}))
    with sessions() as db:
        db.get(ServiceRequest, created['id']).create_time = now()-timedelta(seconds=20)
        db.commit()
        assert escalate_overdue_calls(db) == 1
        db.commit()
    assert data(client.get(f'/api/services/requests/{created["id"]}', headers=admin))['escalated_at']


@pytest.mark.parametrize('role', ['CARE', 'FAMILY'])
def test_write_acl_rechecks_revoked_relation_despite_cached_identity(setup, role):
    _, sessions = setup
    with sessions() as reader:
        user = reader.scalar(select(User).where(User.role == role))
        profile = reader.scalar(select(ElderProfile))
        model = CareRelation if role == 'CARE' else FamilyBind
        relation = reader.scalar(select(model).where(model.profile_id == profile.id))
        assert relation.status == (1 if role == 'CARE' else 'APPROVED')
        with sessions() as writer:
            changed = writer.get(model, relation.id)
            changed.status = 0 if role == 'CARE' else 'REVOKED'
            writer.commit()
        # The reader deliberately still holds the formerly authorized object.
        assert relation.status == (1 if role == 'CARE' else 'APPROVED')
        with pytest.raises(APIError) as error:
            get_service_profile(reader, user, profile.id, lock=True)
        assert error.value.status == 403


def test_locked_profile_refreshes_changed_owner_before_elder_permission(setup):
    _, sessions = setup
    with sessions() as reader:
        elder = reader.scalar(select(User).where(User.role == 'ELDER'))
        profile = reader.scalar(select(ElderProfile))
        original_owner = profile.user_id
        with sessions() as writer:
            admin = writer.scalar(select(User).where(User.role == 'ADMIN'))
            writer.get(ElderProfile, profile.id).user_id = admin.id
            writer.commit()
        assert profile.user_id == original_owner
        with pytest.raises(APIError) as error:
            get_service_profile(reader, elder, profile.id, lock=True)
        assert error.value.status == 403 and profile.user_id != original_owner


def test_assignee_validation_refreshes_disabled_cached_user(setup):
    _, sessions = setup
    with sessions() as reader:
        care = reader.scalar(select(User).where(User.role == 'CARE'))
        profile = reader.scalar(select(ElderProfile))
        assert care.status == 1
        with sessions() as writer:
            writer.get(User, care.id).status = 0
            writer.commit()
        with pytest.raises(APIError) as error:
            validate_assignee(reader, profile.id, care.id)
        assert error.value.code == 2001 and care.status == 0
