import json
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.database import get_db, now
from app.core.security import get_current_user
from app.core.permissions import get_profile, require_roles, visible_profile_ids
from app.core.errors import APIError, ok
from app.models import SysConfig, User, ElderProfile
from app.models.personal_threshold import ProfileThresholdVersion
from app.services.personal_threshold import RULE_KEYS, effective_rule, validate_rule
from app.services.serializers import dt

router = APIRouter(tags=['个体阈值'])


class Proposal(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    indicator: str = Field(min_length=1, max_length=30)
    level0_range: str = Field(default='', max_length=100)
    level1_range: str = Field(default='', max_length=100)
    level2_range: str = Field(default='', max_length=100)
    level3_range: str = Field(default='', max_length=100)
    reason: str = Field(min_length=1, max_length=500)
    restore_default: bool = False


class Review(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    approve: bool
    note: str = Field(min_length=1, max_length=500)


def proposal_data(db, item):
    row = db.get(SysConfig, item.config_id) if item.config_id else None
    rules = json.loads(row.config_value) if row else {}
    proposer = db.get(User, item.proposed_by)
    profile = db.get(ElderProfile, item.profile_id)
    from app.services.thresholds import INDICATORS
    meta = next(value for value in INDICATORS.values() if item.indicator in value['keys'])
    return {'proposal_id': item.id, 'version_id': item.id, 'profile_id': item.profile_id,
            'indicator': item.indicator, 'status': item.status, 'reason': item.reason,
            'elder_name': profile.name if profile else '', 'indicator_name': meta['name'] + (' 收缩压' if item.indicator.endswith('SYSTOLIC') else ' 舒张压' if item.indicator.endswith('DIASTOLIC') else ''),
            'restore_default': bool(item.restore_default), 'proposed_by': item.proposed_by,
            'proposer_name': proposer.name if proposer else '', 'reviewed_by': item.reviewed_by,
            'review_note': item.review_note, 'created_at': dt(item.create_time),
            'reviewed_at': dt(item.reviewed_at),
            **{f'level{i}_range': rules.get(f'level{i}', '') for i in range(4)}}


@router.get('/profiles/{profile_id}/thresholds')
def thresholds(profile_id: int, user=Depends(get_current_user), db: Session = Depends(get_db)):
    get_profile(db, user, profile_id)
    versions = list(db.scalars(select(ProfileThresholdVersion).where(ProfileThresholdVersion.profile_id == profile_id).order_by(ProfileThresholdVersion.id.desc())))
    return ok({'profile_id': profile_id, 'rules': [effective_rule(db, profile_id, key) for key in sorted(RULE_KEYS)],
               'pending': [proposal_data(db, row) for row in versions if row.status == 'PENDING'],
               'history': [proposal_data(db, row) for row in versions]})


@router.post('/profiles/{profile_id}/threshold-proposals')
def propose(profile_id: int, body: Proposal, user=Depends(require_roles('CARE', 'ADMIN')), db: Session = Depends(get_db)):
    get_profile(db, user, profile_id, lock=True)
    if body.indicator not in RULE_KEYS:
        raise APIError(2001, '不支持的阈值指标')
    if db.scalar(select(ProfileThresholdVersion.id).where(ProfileThresholdVersion.profile_id == profile_id,
          ProfileThresholdVersion.indicator == body.indicator, ProfileThresholdVersion.status == 'PENDING').with_for_update()):
        raise APIError(2001, '该指标已有待审核申请', 409)
    raw = json.dumps({f'level{i}': getattr(body, f'level{i}_range') for i in range(4)}, ensure_ascii=False, separators=(',', ':'))
    if not body.restore_default:
        validate_rule(raw)
    item = ProfileThresholdVersion(profile_id=profile_id, indicator=body.indicator,
        proposed_by=user.id, reason=body.reason, restore_default=int(body.restore_default), status='PENDING')
    db.add(item)
    db.flush()
    if not body.restore_default:
        row = SysConfig(config_key='pt:' + str(item.id), config_value=raw, config_type='threshold',
                        group_name='personal_threshold', enabled=1, description='个体阈值版本 ' + str(item.id))
        db.add(row)
        db.flush()
        item.config_id = row.id
    db.commit()
    return ok(proposal_data(db, item))


@router.get('/threshold-proposals')
def proposals(status: str | None = Query(default=None), user=Depends(require_roles('CARE', 'ADMIN')), db: Session = Depends(get_db)):
    ids = visible_profile_ids(db, user)
    conditions = [ProfileThresholdVersion.profile_id.in_(ids)]
    if status:
        if status not in ('PENDING', 'APPROVED', 'REJECTED', 'SUPERSEDED'):
            raise APIError(2001, '审核状态无效')
        conditions.append(ProfileThresholdVersion.status == status)
    rows = db.scalars(select(ProfileThresholdVersion).where(*conditions).order_by(ProfileThresholdVersion.id.desc()).limit(300))
    return ok([proposal_data(db, row) for row in rows])


@router.post('/threshold-proposals/{proposal_id}/review')
def review(proposal_id: int, body: Review, user=Depends(require_roles('ADMIN')), db: Session = Depends(get_db)):
    item = db.get(ProfileThresholdVersion, proposal_id)
    if not item:
        raise APIError(2002, '阈值申请不存在', 404)
    # The same profile lock is held by measurement entry, serialising approvals
    # with full blood-pressure evaluations across both component rules.
    get_profile(db, user, item.profile_id, lock=True)
    item = db.scalar(select(ProfileThresholdVersion).where(ProfileThresholdVersion.id == proposal_id).with_for_update().execution_options(populate_existing=True))
    if item.status != 'PENDING':
        raise APIError(2001, '该申请已审核，不能重复操作', 409)
    if body.approve:
        if item.restore_default:
            row = db.scalar(select(SysConfig).where(SysConfig.config_key == item.indicator).with_for_update().execution_options(populate_existing=True))
            if not row:
                raise APIError(5001, '院内默认阈值不存在', 503)
            validate_rule(row.config_value)
        else:
            row = db.scalar(select(SysConfig).where(SysConfig.id == item.config_id).with_for_update().execution_options(populate_existing=True))
            if not row:
                raise APIError(5001, '个体配置不存在', 503)
            validate_rule(row.config_value)
        # Recheck the proposer still has responsibility at approval time.
        proposer = db.scalar(select(User).where(User.id == item.proposed_by).with_for_update().execution_options(populate_existing=True))
        if not proposer or not proposer.status or proposer.role not in ('CARE', 'ADMIN'):
            raise APIError(2001, '申请人已停用或失去配置权限，请重新提交', 409)
        get_profile(db, proposer, item.profile_id, lock=True)
        current = list(db.scalars(select(ProfileThresholdVersion).where(ProfileThresholdVersion.profile_id == item.profile_id,
            ProfileThresholdVersion.indicator == item.indicator, ProfileThresholdVersion.status == 'APPROVED').with_for_update()))
        for previous in current:
            previous.status = 'SUPERSEDED'
    item.status = 'APPROVED' if body.approve else 'REJECTED'
    item.reviewed_by, item.review_note, item.reviewed_at = user.id, body.note, now()
    db.commit()
    return ok(proposal_data(db, item))
