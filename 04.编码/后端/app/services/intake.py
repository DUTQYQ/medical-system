"""Deterministic intake, confirmed facts, and readable, evidence-bound advice."""
import json
import re
from datetime import timedelta
from sqlalchemy import select, func
from app.core.database import now
from app.core.errors import APIError
from app.services.serializers import dt
from app.models.consultation import ProfileFact, ProfileFactRevision, AdviceCard
from app.models import User, AILog
from app.agent import llm

TEMPLATE_VERSION = 'life-v1'
DISCLAIMER = '健康建议不构成医疗诊断'
QUESTIONS = [
    {'key': 'life_goal', 'label': '您希望在院里过怎样的生活，最想改善什么？', 'type': 'text', 'options': ['丰富日常生活', '多交朋友', '改善睡眠', '保持活动', '暂时没有']},
    {'key': 'entertainment_preferences', 'label': '您喜欢哪些娱乐活动？', 'type': 'text', 'options': ['打牌', '象棋', '唱歌', '阅读', '书画', '聊天', '暂无偏好']},
    {'key': 'movement_ability', 'label': '您平时走动方便吗，是否需要陪同或辅助设备？', 'type': 'text', 'options': ['可以独立走动', '需要陪同', '使用拐杖', '使用轮椅', '暂时不清楚']},
    {'key': 'assistance_needs', 'label': '您希望工作人员在哪些日常事情上帮助您？', 'type': 'text', 'options': ['日常照护', '出行陪同', '联系家属', '设备协助', '暂无需求']},
    {'key': 'food_preferences', 'label': '您有什么饮食偏好或需要工作人员注意的事情？', 'type': 'text', 'options': ['清淡', '软食', '少辣', '无特别偏好', '需要向工作人员说明']},
    {'key': 'sleep_concerns', 'label': '最近几天睡眠如何，有没有想告诉我们的困扰？', 'type': 'text', 'options': ['睡眠尚可', '入睡困难', '夜间易醒', '白天困倦', '暂时不清楚']},
]
QUESTION_MAP = {q['key']: q for q in QUESTIONS}
FACT_LABELS = dict(zip(QUESTION_MAP, ['生活目标', '娱乐偏好', '行动能力', '协助需求', '饮食偏好', '近期睡眠']))


def clean_value(value):
    if isinstance(value, str):
        value = value.strip()
        if value and len(value) <= 500:
            return value
    elif isinstance(value, list) and 0 < len(value) <= 12:
        if all(isinstance(item, str) and 0 < len(item.strip()) <= 80 for item in value):
            return list(dict.fromkeys(item.strip() for item in value))
    raise APIError(2001, '词条内容须为 1 至 500 字文本，或最多 12 个简短选项')


def check_key(key):
    if key not in QUESTION_MAP:
        raise APIError(2001, '不支持的信息词条；不能通过咨询修改病史、药物或阈值')
    return key


def intake_data(row):
    answered = {a['key'] for a in (row.answers or [])}
    next_question = next((dict(q) for q in QUESTIONS if q['key'] not in answered), None)
    return {'intake_id': row.id, 'profile_id': row.profile_id, 'template_version': row.template_version,
            'status': row.status, 'next_question': next_question if row.status == 'IN_PROGRESS' else None,
            'answers': row.answers or [], 'progress': len(answered), 'total_questions': len(QUESTIONS),
            'confirmed_at': dt(row.confirmed_at), 'disclaimer': DISCLAIMER}


def fact_origin(db, row):
    reporter = db.get(User, row.reported_by) if db else None
    confirmer = db.get(User, row.confirmed_by) if db else None
    labels = {'ELDER': '老人', 'FAMILY': '家属', 'CARE': '护工', 'ADMIN': '管理员'}
    reported_role = reporter.role if reporter else None
    confirmed_role = confirmer.role if confirmer else None
    origin = '老人自述' if reported_role == 'ELDER' else '家属观察' if reported_role == 'FAMILY' else '用户报告'
    return {'reported_role': reported_role, 'confirmed_role': confirmed_role,
            'reported_by_name': reporter.name if reporter else None,
            'confirmed_by_name': confirmer.name if confirmer else None,
            'origin_label': origin + '，' + labels.get(confirmed_role, '用户') + '确认，未经医护核实'}


def fact_data(row, db=None):
    expired = row.valid_until is not None and row.valid_until <= now()
    return {'fact_id': row.id, 'profile_id': row.profile_id, 'key': row.fact_key, 'label': row.label, 'value': row.value,
            'version': row.version, 'status': 'EXPIRED' if expired and row.status == 'CONFIRMED' else row.status,
            'source': fact_origin(db, row)['origin_label'], **fact_origin(db, row),
            'source_intake_id': row.source_intake_id, 'reported_by': row.reported_by,
            'confirmed_by': row.confirmed_by, 'confirmed_at': dt(row.confirmed_at), 'valid_until': dt(row.valid_until),
            'is_current': row.status == 'CONFIRMED' and not expired}


def facts_for(db, profile_id, *, current_only=False):
    rows = list(db.scalars(select(ProfileFact).where(ProfileFact.profile_id == profile_id,
               ProfileFact.status != 'REVOKED').order_by(ProfileFact.id)))
    return [row for row in rows if not current_only or (row.status == 'CONFIRMED' and (row.valid_until is None or row.valid_until > now()))]


def save_fact(db, profile_id, key, value, user, *, source_intake_id=None, reported_by=None, change_reason=None):
    check_key(key)
    value = clean_value(value)
    row = db.scalar(select(ProfileFact).where(ProfileFact.profile_id == profile_id, ProfileFact.fact_key == key)
                    .with_for_update().execution_options(populate_existing=True))
    if row is None:
        row = ProfileFact(profile_id=profile_id, fact_key=key, label=FACT_LABELS[key], value=value,
                          version=1, reported_by=reported_by or user.id, confirmed_by=user.id,
                          source_intake_id=source_intake_id)
        db.add(row)
    else:
        row.version += 1
        row.value = value
        row.status = 'CONFIRMED'
        row.reported_by = reported_by or user.id
        row.confirmed_by = user.id
        row.source_intake_id = source_intake_id
    row.confirmed_at = now()
    row.valid_until = now() + timedelta(days=7) if key == 'sleep_concerns' else None
    db.flush()
    db.add(ProfileFactRevision(fact_id=row.id, version=row.version, value=value, status='CONFIRMED', changed_by=user.id,
                              source_intake_id=row.source_intake_id, reported_by=row.reported_by, valid_until=row.valid_until,
                              change_reason=change_reason or ('问询确认' if source_intake_id else '用户修改并确认')))
    return row


def facts_context(db, profile_id):
    rows = facts_for(db, profile_id, current_only=True)
    return '\n'.join(f'{row.label}：{display_value(row.value)}（{fact_origin(db, row)["origin_label"]}，非诊断）' for row in rows)


def display_value(value):
    return '、'.join(value) if isinstance(value, list) else str(value)


def advice_data(row):
    return {'advice_id': row.id, 'profile_id': row.profile_id, 'title': row.title, 'mode': row.mode,
            'created_at': dt(row.create_time), **row.content}


def rule_advice(rows, db=None):
    values = {r.fact_key: display_value(r.value) for r in rows}
    facts = [f'{r.label}：{display_value(r.value)}（{fact_origin(db, r)["origin_label"]}）。' for r in rows] or ['尚未确认生活信息。您可以先完成问询，再与工作人员讨论安排。']
    today, help_items, actions = [], [], []
    interests = values.get('entertainment_preferences')
    if interests and not any(word in interests for word in ['暂无', '没有', '不喜欢']):
        today.append(f'记录中的娱乐偏好是“{interests}”。请核实本人意愿，再查看院内相应活动。')
        actions.append({'category': 'ENTERTAINMENT', 'title': '申请娱乐活动', 'description': f'希望参加与“{interests[:160]}”有关的活动，请工作人员确认时间和名额。'})
    ability = values.get('movement_ability', '')
    if any(word in ability for word in ['陪同', '轮椅', '拐杖', '不便', '不能', '困难']):
        today.append('生活信息记录了走动时需要帮助。活动前请工作人员核实陪同和所需辅助设备。')
        help_items.append('请工作人员核实活动能力，再安排陪同或辅助设备。')
        actions.append({'category': 'EQUIPMENT', 'title': '申请辅助设备', 'description': '请工作人员核实实际需要与适用性，并确认库存和使用安排。'})
    elif ability:
        today.append('若今天感觉舒适，可以和工作人员商量适合您的轻松活动；出现不适请停止并寻求帮助。')
    if '活动' in values.get('life_goal', '') or '锻炼' in values.get('life_goal', ''):
        actions.append({'category': 'EXERCISE', 'title': '申请活动与锻炼协助',
                        'description': '希望工作人员结合本人实际活动能力，确认合适的院内活动与是否需要陪同。'})
    if values.get('assistance_needs') and not any(word in values['assistance_needs'] for word in ['暂无', '没有']):
        help_items.append(f'请工作人员核实记录中的这些需求：“{values["assistance_needs"]}”。')
        actions.append({'category': 'DAILY_LIVING', 'title': '申请日常协助', 'description': values['assistance_needs'][:300]})
    if values.get('food_preferences'):
        help_items.append(f'可向餐饮人员说明饮食偏好“{values["food_preferences"]}”；过敏和特殊饮食要求应另经工作人员核实。')
        if not any(word in values['food_preferences'] for word in ['无特别', '没有', '暂无']):
            actions.append({'category': 'MEAL', 'title': '申请餐饮协助',
                            'description': f'请工作人员确认饮食偏好“{values["food_preferences"][:160]}”，特殊饮食或过敏信息应另行核实。'})
    if values.get('sleep_concerns') and not any(word in values['sleep_concerns'] for word in ['尚可', '没有', '不清楚']):
        today.append('可记录今晚的睡眠感受，保持自己舒适的作息。若困扰持续或影响白天生活，请告诉工作人员。')
    return {'sections': [{'title': '已确认的生活信息与来源', 'items': facts},
                         {'title': '今天可以做什么', 'items': today or ['先选择一项自己愿意参加的日常活动，与工作人员确认安排。']},
                         {'title': '需要工作人员协助', 'items': help_items or ['如有新需求，可直接呼叫工作人员或提交服务申请。']},
                         {'title': '依据与注意事项', 'items': ['依据您确认的生活信息生成。自述信息不等于医护评估。',
                          '活动、设备与护理安排须经工作人员确认；建议不会自动提交申请。', DISCLAIMER]}],
            'sources': [{'fact_id': r.id, 'key': r.fact_key, 'version': r.version, 'confirmed_at': dt(r.confirmed_at),
                        'reported_by': r.reported_by, 'confirmed_by': r.confirmed_by, **fact_origin(db, r)} for r in rows],
            'actions': actions, 'disclaimer': DISCLAIMER, 'model_status': 'RULE_FALLBACK',
            'generation_note': '规则生成，AI 模型未启用或不可用；请与工作人员确认安排。'}


def build_advice(db, profile, user):
    rows = facts_for(db, profile.id, current_only=True)
    content = rule_advice(rows, db)
    card_title = '我的康养生活建议'
    if user.role in ('FAMILY', 'CARE'):
        titles = {'FAMILY': ['已确认的生活信息与来源', '家属今天可以做什么', '建议联系工作人员', '依据与注意事项'],
                  'CARE': ['已确认的生活信息与来源', '今日照护协助', '需要团队协同', '依据与注意事项']}[user.role]
        for section, title in zip(content['sections'], titles):
            section['title'] = title
            section['items'] = [item.replace('您提到', '长者提到').replace('您报告', '长者报告')
                .replace('适合您的', '适合长者的').replace('与您确认', '与长者确认')
                .replace('您确认的', '长者确认的').replace('请告诉我们', '请告诉工作人员')
                .replace('自己愿意参加', '长者愿意参加') for item in section['items']]
        if user.role == 'FAMILY':
            card_title = '家属照护建议'
            if not rows:
                content['sections'][0]['items'] = ['尚未有已确认生活信息。家属观察可先与长者或负责护工核实。']
        else:
            card_title = '护理工作建议'
            if not rows:
                content['sections'][0]['items'] = ['尚未有已确认生活信息。请在照护沟通中核实后再形成安排。']
    mode = 'RULE'
    # The model may rewrite presentation, never alter the fact snapshot, actions or authority.
    reservation = None
    if rows:
        from app.agent.workflow import number_config
        db.scalar(select(User).where(User.id == user.id).with_for_update())
        today = now().replace(hour=0, minute=0, second=0, microsecond=0)
        attempts = db.scalar(select(func.count(AILog.id)).where(AILog.user_id == user.id,
                             AILog.agent == 'CONSULT_ATTEMPT', AILog.create_time >= today))
        if attempts < number_config(db, 'ai_daily_limit', 50):
            reservation = AILog(user_id=user.id, agent='CONSULT_ATTEMPT', model='advice-reservation', success=0)
            db.add(reservation)
            db.commit()
        else:
            content['model_status'] = 'RULE_DAILY_LIMIT'
            content['generation_note'] = '今日 AI 生成额度已用完，本卡由规则生成；服务申请仍可使用。'
    if reservation is not None:
        try:
            role_name = {'ELDER': '老人本人', 'FAMILY': '长者家属', 'CARE': '负责护工'}[user.role]
            titles = [section['title'] for section in content['sections']]
            raw = llm.complete(f'面向{role_name}，依据确认信息生成康养生活建议。仅返回 JSON {{"sections":[{{"title":"...","items":["..."]}}]}}。'
                               f'保留四个分区：{json.dumps(titles, ensure_ascii=False)}。每区 1 至 5 条短句，'
                               '不编造疾病、指标、活动名额、设备库存或已完成服务。',
                               json.dumps(content, ensure_ascii=False), timeout=8, audience=user.role)
            if llm.safe_answer(raw) != raw:
                raise ValueError('unsafe answer')
            if re.search(r'已(?:预约|安排|提交|通知|分配|批准|完成)|(?:无需|不用).{0,8}(?:工作人员|确认)', raw):
                raise ValueError('unsupported service execution claim')
            if raw.startswith('```'):
                raw = raw.split('\n', 1)[1].rsplit('```', 1)[0].strip()
            parsed = json.loads(raw)
            if not isinstance(parsed, dict):
                raise ValueError('invalid advice object')
            sections = parsed.get('sections')
            expected = [section['title'] for section in content['sections']]
            if not isinstance(sections, list) or len(sections) != 4:
                raise ValueError('invalid sections')
            for section, title in zip(sections, expected):
                if not isinstance(section, dict) or section.get('title') != title:
                    raise ValueError('invalid section title')
                items = section.get('items')
                if not isinstance(items, list) or not 1 <= len(items) <= 5 or not all(isinstance(i, str) and 0 < len(i.strip()) <= 220 for i in items):
                    raise ValueError('invalid items')
            # Facts and caveats stay deterministic; only suggestions may be rewritten.
            content['sections'][1:3] = sections[1:3]
            content['model_status'] = 'SUCCESS'
            content['generation_note'] = 'AI 生成建议，依据已确认词条；需工作人员确认安排。'
            mode = 'MODEL'
        except (llm.ModelUnavailable, ValueError, TypeError, KeyError):
            pass
        reservation.success = int(mode == 'MODEL')
        reservation.error_msg = None if mode == 'MODEL' else '建议模型不可用、输出无效或安全校验失败'
    # A relationship may have been revoked while the model was responding.
    from app.core.permissions import get_profile
    db.flush()
    db.expire_all()
    get_profile(db, user, profile.id, lock=True)
    row = AdviceCard(profile_id=profile.id, created_by=user.id, title=card_title, mode=mode, content=content)
    db.add(row)
    db.commit()
    return row
