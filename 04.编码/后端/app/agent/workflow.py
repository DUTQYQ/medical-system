"""Four distinct, permission-checked data paths orchestrated by LangGraph."""
import json
import logging
import os
import re
from datetime import timedelta
from time import perf_counter
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langsmith import tracing_context
from sqlalchemy import select
from app.core.database import SessionLocal, now
from app.core.errors import APIError
from app.core.permissions import get_profile
from app.models import SysConfig, HealthRecord, HealthWarning, ElderProfile, AILog, AlertReceiver, User
from app.services.alerts import create_warning
from app.services.health_records import active_records
from .llm import complete, safe_answer, ModelUnavailable
from .rag import retrieve, embedding_info

DISCLAIMER = '健康建议不构成医疗诊断'
EMERGENCY_REPLY = '您描述的当前症状需要立即寻求现场帮助。请立即联系 120 或让身边人员协助求助，不要等待 AI 回答。'
DEFAULT_EMERGENCY_KEYWORDS = ['胸痛', '胸口很痛', '胸口疼', '呼吸困难', '喘不上气', '意识丧失', '昏厥', '无法起身', '大量出血', '言语不清']
# Existing MySQL seed configurations contain clinical keyword names rather than
# all colloquial expressions. Expand only configured names, preserving the
# administrator's choice of enabled emergency concepts.
EMERGENCY_ALIASES = {
    '胸痛': ['胸口很痛', '胸口疼', '胸口痛', '胸部疼痛'],
    '呼吸困难': ['喘不上气', '喘不过气', '透不过气', '呼吸很困难'],
    '意识丧失': ['没有意识', '失去意识', '叫不醒'],
    '昏厥': ['晕倒', '昏倒'],
    '无法起身': ['起不来', '不能起身'],
}


def config_value(db, key, default):
    row = db.scalar(select(SysConfig).where(SysConfig.config_key == key, SysConfig.enabled == 1))
    return row.config_value if row else default


def number_config(db, key, default, *, minimum=1, maximum=10000):
    environment_name = {'ai_question_max_chars': 'MAX_INPUT_CHARS', 'ai_daily_limit': 'DAILY_CALL_LIMIT'}.get(key)
    if environment_name:
        try:
            default = int(os.getenv(environment_name, str(default)))
        except ValueError:
            pass
    try:
        return max(minimum, min(maximum, int(config_value(db, key, default))))
    except (TypeError, ValueError):
        return default


def emergency_clauses(question, keywords):
    """Conservative deterministic triage; distinguish explicit denial/history/education.

    Ambiguous current symptom descriptions retain the immediate safety route.
    Each clause is checked independently, so a denied symptom cannot suppress
    a different current symptom after a comma or a contrast word.
    """
    text = re.sub(r'\s+', '', question)
    clauses = re.split(r'[，。！？；,.!?;]|但是|不过|然而|但', text)
    active = []
    for index, clause in enumerate(clauses):
        for word in keywords:
            for match in re.finditer(re.escape(word), clause):
                before, after = clause[:match.start()], clause[match.end():]
                current = bool(re.search(r'现在|正在|刚刚|此刻|突然|今天|仍然|仍|还在|持续|再次|又', clause))
                denial = re.search(r'(?:没有|并无|无|没|未出现|不伴|否认|不存在)(?:出现|发生|感到|感觉)?.{0,10}$', before)
                double_denial = re.search(r'(?:不是|并非|并不是|不代表|不能说).{0,6}(?:没有|无|没)', before)
                if denial and not double_denial:
                    continue
                if re.match(r'(?:已经|已)(?:完全消失|不再出现|消失)|(?:完全消失|没有了)', after):
                    continue
                if not current and re.search(r'以前|曾经|既往|过去|当年|去年|上个月|病史|历史', clause):
                    continue
                education = re.search(r'什么是|什么叫|科普|培训|请解释|知识|(?:如何|怎样|怎么|应该|应当).{0,12}(?:询问|问诊|识别|评估|预防)', clause)
                education = education or re.match(r'是什么|什么意思|有哪些原因|的原因是什么', after)
                if education and not current:
                    continue
                active.append((index, match.start()))
    return clauses, active


def current_emergency(question, keywords):
    return bool(emergency_clauses(question, keywords)[1])


def configured_emergency_keywords(db):
    raw = config_value(db, 'emergency_keywords', json.dumps(DEFAULT_EMERGENCY_KEYWORDS, ensure_ascii=False))
    try:
        keywords = json.loads(raw)
        if not isinstance(keywords, list):
            raise ValueError('invalid keyword list')
    except (ValueError, TypeError):
        raise APIError(5001, '紧急关键词配置无效，请联系管理员', 503)
    expanded = set()
    for keyword in keywords:
        if isinstance(keyword, str) and keyword:
            expanded.add(keyword)
            expanded.update(EMERGENCY_ALIASES.get(keyword, []))
    return expanded


def emergency_subject(db, user, profile, question):
    """Attribute active symptoms deterministically before any elder warning write.

    Use the nearest named subject before each symptom, carrying it across clauses.
    An unspecified subject in a family/care question needs clarification first.
    """
    clauses, active = emergency_clauses(question, configured_emergency_keywords(db))
    elders = [profile.name, '所选老人', '这位老人', '老人', '长者', '长辈', '被照护人']
    male_relatives = ['爸爸', '父亲', '爷爷', '外公', '我爸']
    female_relatives = ['妈妈', '母亲', '奶奶', '外婆', '我妈']
    others = ['儿子', '女儿', '孩子', '同事', '朋友', '邻居', '妻子', '丈夫', '老伴', '爱人',
              '旁边的人', '家属', '护工', '工作人员', '另一个老人', '其他老人', '另一位老人']
    unknown = []
    if user.role == 'FAMILY' and profile.gender in ('M', 'F'):
        from app.models import FamilyBind
        relation = db.scalar(select(FamilyBind.relation).where(FamilyBind.family_user_id == user.id,
            FamilyBind.profile_id == profile.id, FamilyBind.status == 'APPROVED')) or ''
        candidates = male_relatives if profile.gender == 'M' else female_relatives
        if relation in ('儿子', '女儿', '子女'):
            elders += candidates[:2] + [candidates[-1]]
            unknown += candidates[2:4]
        elif relation in ('孙子', '孙女', '外孙', '外孙女'):
            elders += candidates[2:4]
            unknown += candidates[:2] + [candidates[-1]]
        else:
            unknown += candidates
        others += female_relatives if profile.gender == 'M' else male_relatives
    elif user.role == 'FAMILY':
        unknown += male_relatives + female_relatives
    else:
        others += male_relatives + female_relatives
    # Naming another accessible elder must not attach that person's symptom to
    # the current selection; no data from that other profile enters the reply.
    from app.core.permissions import profile_scope
    others += list(db.scalars(select(ElderProfile.name).where(*profile_scope(user, db), ElderProfile.id != profile.id,
                                                             ElderProfile.name != profile.name)))
    pattern = re.compile('|'.join(re.escape(word) for word in sorted(set(elders + others + unknown + ['我本人', '我自己', '本人', '自己', '我']), key=len, reverse=True) if word))
    subjects = []
    for index, offset in active:
        prefix = '，'.join(clauses[:index] + [clauses[index][:offset]])
        mentions = list(pattern.finditer(prefix))
        if not mentions:
            subjects.append('PROFILE' if user.role == 'ELDER' else 'UNKNOWN')
        else:
            word = mentions[-1].group()
            subjects.append('UNKNOWN' if word in unknown else ('OTHER' if word in others else ('PROFILE' if word in elders or user.role == 'ELDER' else 'SELF')))
    if 'PROFILE' in subjects:
        return 'PROFILE'
    return 'SELF' if subjects and set(subjects) == {'SELF'} else ('OTHER' if subjects and set(subjects) == {'OTHER'} else 'UNKNOWN')


def emergency_response(db, warning, audience):
    roles = set(db.scalars(select(User.role).join(AlertReceiver, AlertReceiver.user_id == User.id)
                          .where(AlertReceiver.warning_id == warning.id)))
    labels = {'ELDER': '老人本人', 'FAMILY': '已绑定家属', 'CARE': '负责护工', 'ADMIN': '管理员'}
    recipients = '、'.join(labels[role] for role in labels if role in roles)
    lead = EMERGENCY_REPLY if audience == 'ELDER' else '请立即核实所选长者的现场情况，联系现场工作人员或 120，不要等待 AI 回答。'
    notice = f'系统已生成紧急预警，站内通知已创建给：{recipients}。' if recipients else '系统已生成紧急预警，但当前没有可通知的接收人。'
    if not roles.intersection({'FAMILY', 'CARE'}):
        notice += '当前没有可通知的已绑定家属或负责护工，请直接寻求现场帮助。'
    return lead + notice + '站内通知不代表接收人已读或已经到场。'


def classify(db, question):
    if current_emergency(question, configured_emergency_keywords(db)):
        return 'EMERGENCY'
    if re.search(r'预警|报警|异常|血压(?:很|偏)?高|血糖(?:很|偏)?高|心率(?:很|偏)?快', question):
        return 'ABNORMAL'
    if re.search(r'最近|近\d|历史|趋势|平均|记录|我的|我.{0,8}(?:血压|血糖|心率|睡眠|步数)', question):
        return 'DATA'
    return 'NORMAL'


def record_text(record):
    first = f'{float(record.val1):g}' if record.val1 is not None else '未记录'
    second = f'{float(record.val2):g}' if record.val2 is not None else '未记录'
    values = f'{first}/{second} mmHg' if record.type == 'BLOOD_PRESSURE' else f'{first} ' + {
        'BLOOD_SUGAR': 'mmol/L', 'HEART_RATE': '次/分', 'SLEEP': '小时', 'STEP': '步',
    }.get(record.type, '')
    return f'记录#{record.id} {record.measured_at:%Y-%m-%d %H:%M} {record.type}: {values}'


def history_context(db, profile_id, *, days=30, limit=50):
    records = list(db.scalars(select(HealthRecord).where(active_records(), HealthRecord.profile_id == profile_id,
        HealthRecord.measured_at >= now() - timedelta(days=days)).order_by(HealthRecord.measured_at.desc(), HealthRecord.id.desc()).limit(limit)))
    # All available historic demo records may predate the requested window.
    # Do not substitute them or relabel them as recent measurements.
    return records, '\n'.join(record_text(record) for record in records) or f'近 {days} 天没有已记录的指标，不能推断健康状况。'


class State(TypedDict, total=False):
    question: str
    intent: str
    agent: str
    context: str
    sources: list
    evidence: str
    safety_level: str
    risk_level: int
    warning_id: int | None
    answer: str
    model_status: str


def run_chat(db, user, profile, question, *, history=None):
    """Models get only strings, never the DB/permissions/create-warning tools."""
    profile = get_profile(db, user, profile.id)
    # Only confirmed, current personal facts reach generation; interview drafts do not.
    from app.services.intake import facts_context
    personal_facts = facts_context(db, profile.id)
    profile_context = f'本次咨询档案：{profile.name}。基础档案由用户提供，不能当作医疗诊断。'
    for field, label in [('allergy', '记录的过敏信息'), ('medical_history', '记录的病史'), ('chronic_tags', '记录的慢病标签')]:
        if getattr(profile, field, None):
            profile_context += f'\n{label}：{str(getattr(profile, field))[:500]}'
    if personal_facts:
        profile_context += '\n已确认的康养生活词条：\n' + personal_facts
    def route(state):
        return {'intent': classify(db, state['question'])}

    def knowledge(state):
        hits = retrieve(db, state['question'])
        context = '\n\n'.join(f"来源：{hit['title']}\n{hit['text']}" for hit in hits)
        return {'agent': 'HEALTH', 'context': context or '知识库没有相关资料，请明确说明资料不足。',
                'sources': list(dict.fromkeys(hit['title'] for hit in hits)), 'evidence': '', 'safety_level': 'L1', 'risk_level': 0}

    def data(state):
        records, text = history_context(db, profile.id)
        return {'agent': 'HEALTH_DATA', 'context': text, 'sources': [], 'evidence': text,
                'safety_level': 'L2', 'risk_level': 0}

    def abnormal(state):
        warnings = list(db.scalars(select(HealthWarning).where(HealthWarning.profile_id == profile.id).order_by(HealthWarning.create_time.desc()).limit(5)))
        current = list(db.scalars(select(HealthWarning).where(HealthWarning.profile_id == profile.id,
            HealthWarning.status.in_(['PENDING', 'PROCESSING']))))
        from app.models import HealthRecordVoid
        voided_ids = set(db.scalars(select(HealthRecordVoid.record_id).join(HealthRecord,
            HealthRecord.id == HealthRecordVoid.record_id).where(HealthRecord.profile_id == profile.id)))
        current = [w for w in current if w.record_id not in voided_ids]
        warnings_text = '\n'.join(f'预警#{warning.id} {warning.create_time:%Y-%m-%d %H:%M}: {warning.type} {warning.value_text}, 历史判定等级{warning.level}, 处理状态{warning.status}'
            + ('；关联测量已作废，不能作为当前指标依据，预警仍需人工核验' if warning.record_id in voided_ids else '') for warning in warnings) or '没有已记录的预警，不能编造预警。'
        warnings_text = f'当前有效且未处理完的预警 {len(current)} 条；历史已处理或已作废记录不能代表当前风险。\n' + warnings_text
        records, trend = history_context(db, profile.id, days=7)
        context = warnings_text + '\n近7天指标：\n' + trend
        return {'agent': 'RISK', 'context': context, 'sources': [], 'evidence': context,
                'safety_level': 'L3', 'risk_level': max((warning.level for warning in current), default=0)}

    def emergency(state):
        subject = emergency_subject(db, user, profile, question)
        if subject != 'PROFILE':
            if subject == 'SELF':
                reply = EMERGENCY_REPLY + f'本次症状指向您本人，未为所选老人 {profile.name} 创建预警。'
            else:
                reply = '如有人正在出现这些症状，请立即联系现场工作人员或 120，不要等待 AI 回答。'
                reply += f'请明确有症状的人是否为所选老人 {profile.name}；当前未给该老人创建预警。'
            return {'agent': 'EMERGENCY', 'context': '', 'sources': [], 'evidence': '', 'safety_level': 'L4',
                'risk_level': 3, 'warning_id': None, 'answer': reply, 'model_status': 'BYPASSED_FOR_SAFETY'}
        current_profile = get_profile(db, user, profile.id, lock=True)
        warning = create_warning(db, current_profile, type='EMERGENCY', value_text=question[:50], level=3, trigger_source='AI_CHAT')
        warning.summary_status = 'SKIPPED'
        reply = emergency_response(db, warning, user.role)
        warning.ai_summary = reply
        # Commit before any optional model work: an outage cannot roll back the warning.
        db.commit()
        return {'agent': 'EMERGENCY', 'context': '', 'sources': [], 'evidence': '', 'safety_level': 'L4',
                'risk_level': 3, 'warning_id': warning.id, 'answer': reply, 'model_status': 'BYPASSED_FOR_SAFETY'}

    def answer(state):
        if state['intent'] == 'EMERGENCY':
            return {}
        started = perf_counter()
        try:
            text = complete(state['question'], state['context'] + '\n\n' + profile_context,
                            timeout=number_config(db, 'ai_chat_timeout_sec', 8, maximum=30), history=history,
                            audience=user.role)
            text = safe_answer(text)
            if state.get('evidence'):
                text += '\n\n本次查询依据：\n' + state['evidence']
            db.add(AILog(user_id=user.id, agent=state['agent'], model='configured-provider', success=1,
                         latency_ms=int((perf_counter() - started) * 1000)))
            return {'answer': text[:8000], 'model_status': 'SUCCESS'}
        except ModelUnavailable:
            db.add(AILog(user_id=user.id, agent=state['agent'], model='configured-provider', success=0,
                         latency_ms=int((perf_counter() - started) * 1000), error_msg='模型未配置或调用失败'))
            db.commit()
            raise APIError(3001, 'AI 助手暂时不可用，请稍后再试。数据录入、预警通知与处理仍可使用。', 503)

    graph = StateGraph(State)
    graph.add_node('route', route)
    for name, node in [('NORMAL', knowledge), ('DATA', data), ('ABNORMAL', abnormal), ('EMERGENCY', emergency)]:
        graph.add_node(name, node)
        graph.add_edge(name, 'answer')
    graph.add_node('answer', answer)
    graph.add_edge(START, 'route')
    graph.add_conditional_edges('route', lambda state: state['intent'], {name: name for name in ('NORMAL', 'DATA', 'ABNORMAL', 'EMERGENCY')})
    graph.add_edge('answer', END)
    # Health records must not be exported to an inherited tracing service.
    with tracing_context(enabled=False):
        result = graph.compile().invoke({'question': question, 'warning_id': None})
    result['disclaimer'] = DISCLAIMER
    if result['intent'] == 'NORMAL':
        result['retrieval'] = embedding_info()
    return result


def generate_summary(warning_id):
    """BackgroundTasks entry: only scalar ID crosses the request boundary."""
    from app.services.recovery import summary_job
    with summary_job(warning_id) as claimed:
        if not claimed:
            return
        _generate_summary(warning_id)


def skip_voided_summary(db, warning):
    from app.models import HealthRecordVoid
    if not warning.record_id or db.scalar(select(HealthRecordVoid.id).where(
        HealthRecordVoid.record_id == warning.record_id).with_for_update()) is None:
        return False
    warning.summary_status = 'SKIPPED'
    warning.ai_summary = None
    db.add(AILog(agent='ALERT_SKIP', model=f'warning:{warning.id}', success=0,
                 error_msg='关联测量已作废，停止 AI 分析；原预警仍需工作人员核验'))
    db.commit()
    return True


def _generate_summary(warning_id):
    """Use an independent session while this worker tracks the active job."""
    with SessionLocal() as db:
        warning = db.get(HealthWarning, warning_id)
        if warning is None or warning.summary_status != 'PENDING':
            return
        profile = db.get(ElderProfile, warning.profile_id)
        if profile is None or profile.deleted:
            warning.summary_status = 'FAILED'
            db.commit()
            return
        if skip_voided_summary(db, warning):
            return
        _, trend = history_context(db, profile.id, days=7)
        context = f'预警#{warning.id}：{warning.type} {warning.value_text}，风险等级{warning.level}。\n近7天记录：\n{trend}'
        timeout = number_config(db, 'ai_summary_timeout_sec', 8, maximum=30)
        retries = number_config(db, 'ai_summary_retry', 1, minimum=0, maximum=2)
        started = perf_counter()
        for attempt in range(retries + 1):
            from app.services.summary_budget import reserve
            reservation, reason = reserve(db, warning.id, check_cooldown=attempt == 0)
            if reservation is None:
                warning.summary_status = 'FAILED'
                warning.ai_summary = None
                db.add(AILog(agent='ALERT_QUOTA', model=f'warning:{warning.id}', success=0, error_msg=reason))
                db.commit()
                return
            try:
                summary = safe_answer(complete('基于该预警及真实历史记录生成简短摘要，勿给诊断或调药指令。', context, timeout=timeout))
                # A measurement can be voided while the optional model is running.
                # Follow the same profile-first lock order as measurement writes,
                # and check current data before publishing the returned summary.
                db.scalar(select(ElderProfile).where(ElderProfile.id == warning.profile_id).with_for_update())
                if skip_voided_summary(db, warning):
                    return
                warning.ai_summary = summary[:4000]
                warning.summary_status = 'SUCCESS'
                reservation.success = 1
                db.add(AILog(agent='ALERT', model='configured-provider', success=1, latency_ms=int((perf_counter() - started) * 1000)))
                db.commit()
                return
            except ModelUnavailable:
                reservation.error_msg = '摘要模型不可用或超时'
                db.commit()
                continue
            except Exception as exc:
                # Only the exception class is logged; upstream details may contain credentials.
                logging.getLogger('kangyang').error('Summary failed: %s', type(exc).__name__)
                break
        warning.ai_summary = None
        warning.summary_status = 'FAILED'
        db.add(AILog(agent='ALERT', model='configured-provider', success=0, error_msg='摘要服务未配置、失败或超时', latency_ms=int((perf_counter() - started) * 1000)))
        db.commit()
