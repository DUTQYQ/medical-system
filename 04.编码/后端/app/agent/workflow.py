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
from app.models import SysConfig, HealthRecord, HealthWarning, ElderProfile, AILog
from app.services.alerts import create_warning
from .llm import complete, safe_answer, ModelUnavailable
from .rag import retrieve, embedding_info

DISCLAIMER = '健康建议不构成医疗诊断'
EMERGENCY_REPLY = '您描述的症状需要立即寻求现场帮助。请立即联系 120 或让身边人员协助求助，不要等待 AI 回答。系统已生成紧急预警并通知已授权家属和负责护工。'
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


def classify(db, question):
    raw = config_value(db, 'emergency_keywords', json.dumps(DEFAULT_EMERGENCY_KEYWORDS, ensure_ascii=False))
    try:
        keywords = json.loads(raw)
        if not isinstance(keywords, list):
            raise ValueError('invalid keyword list')
    except (ValueError, TypeError):
        raise APIError(5001, '紧急关键词配置无效，请联系管理员', 503)
    compact = re.sub(r'[\s，。！？,.!?]', '', question)
    expanded = set()
    for keyword in keywords:
        if isinstance(keyword, str) and keyword:
            expanded.add(keyword)
            expanded.update(EMERGENCY_ALIASES.get(keyword, []))
    if any(word in compact for word in expanded):
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
    records = list(db.scalars(select(HealthRecord).where(HealthRecord.profile_id == profile_id,
        HealthRecord.measured_at >= now() - timedelta(days=days)).order_by(HealthRecord.measured_at.desc()).limit(limit)))
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


def run_chat(db, user, profile, question):
    """Models get only strings, never the DB/permissions/create-warning tools."""
    profile = get_profile(db, user, profile.id)
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
        warnings_text = '\n'.join(f'预警#{warning.id} {warning.create_time:%Y-%m-%d %H:%M}: {warning.type} {warning.value_text}, 风险等级{warning.level}, 处理状态{warning.status}' for warning in warnings) or '没有已记录的预警，不能编造预警。'
        records, trend = history_context(db, profile.id, days=7)
        context = warnings_text + '\n近7天指标：\n' + trend
        return {'agent': 'RISK', 'context': context, 'sources': [], 'evidence': context,
                'safety_level': 'L3', 'risk_level': max((warning.level for warning in warnings), default=0)}

    def emergency(state):
        current_profile = get_profile(db, user, profile.id, lock=True)
        warning = create_warning(db, current_profile, type='EMERGENCY', value_text=question[:50], level=3, trigger_source='AI_CHAT')
        warning.summary_status = 'SKIPPED'
        warning.ai_summary = EMERGENCY_REPLY
        # Commit before any optional model work: an outage cannot roll back the warning.
        db.commit()
        return {'agent': 'EMERGENCY', 'context': '', 'sources': [], 'evidence': '', 'safety_level': 'L4',
                'risk_level': 3, 'warning_id': warning.id, 'answer': EMERGENCY_REPLY, 'model_status': 'BYPASSED_FOR_SAFETY'}

    def answer(state):
        if state['intent'] == 'EMERGENCY':
            return {}
        started = perf_counter()
        try:
            text = complete(state['question'], state['context'], timeout=number_config(db, 'ai_chat_timeout_sec', 8, maximum=30))
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
        _, trend = history_context(db, profile.id, days=7)
        context = f'预警#{warning.id}：{warning.type} {warning.value_text}，风险等级{warning.level}。\n近7天记录：\n{trend}'
        timeout = number_config(db, 'ai_summary_timeout_sec', 8, maximum=30)
        retries = number_config(db, 'ai_summary_retry', 1, minimum=0, maximum=2)
        started = perf_counter()
        for attempt in range(retries + 1):
            try:
                summary = safe_answer(complete('基于该预警及真实历史记录生成简短摘要，勿给诊断或调药指令。', context, timeout=timeout))
                warning.ai_summary = summary[:4000]
                warning.summary_status = 'SUCCESS'
                db.add(AILog(agent='ALERT', model='configured-provider', success=1, latency_ms=int((perf_counter() - started) * 1000)))
                db.commit()
                return
            except ModelUnavailable:
                continue
            except Exception as exc:
                # Only the exception class is logged; upstream details may contain credentials.
                logging.getLogger('kangyang').error('Summary failed: %s', type(exc).__name__)
                break
        warning.ai_summary = None
        warning.summary_status = 'FAILED'
        db.add(AILog(agent='ALERT', model='configured-provider', success=0, error_msg='摘要服务未配置、失败或超时', latency_ms=int((perf_counter() - started) * 1000)))
        db.commit()
