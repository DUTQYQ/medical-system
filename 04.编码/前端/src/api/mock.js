// ============================================================
// 【临时 mock 数据层】 —— 待丘宇乾替换为真实后端实现
// ============================================================
// 说明：
//   1. 本文件仅用于「后端尚未完成」阶段的联调与页面验收，前端不依赖后端。
//   2. 数据为内存态（刷新页面即重置），仅演示用。
//   3. 真实实现完成后，请将 src/api/*.js 中的 mock 调用替换为
//      `request.get/post`（见 src/utils/request.js），本文件可整体删除。
//   4. 约定：所有 api 函数「成功时 resolve 出 data，失败时 throw { code, message }」，
//      页面侧统一 try/catch 并 ElMessage.error(e.message)。
//
// 硬性约束（严格遵守，勿在真实实现中违反）：
//   - API Key / 模型密钥绝不落前端（真实实现中由后端持有）
//   - 阈值不硬编码到页面，统一从 /api/config/thresholds 读取
//   - AI 相关页面必须展示免责声明（见 03.概要设计/设计决策记录 D-02、R-01~R-05）
// ============================================================

// ---------- 工具 ----------
export function delay(ms = 260) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// 业务失败：throw 一个带 code 的 Error
export function fail(code, message) {
  const err = new Error(message || '操作失败')
  err.code = code
  return err
}

// 成功：resolve 出 data
export async function respond(data) {
  await delay()
  return data
}

let _seq = 100000
export function uid(prefix = 'id') {
  _seq += 1
  return `${prefix}_${_seq}`
}

function pad(n) {
  return String(n).padStart(2, '0')
}

export function fmtDate(input) {
  if (!input) return ''
  const d = new Date(input)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export function fmtDateOnly(input) {
  if (!input) return ''
  const d = new Date(input)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

export function todayOnly() {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

function isoDaysAgo(n) {
  const d = new Date()
  d.setDate(d.getDate() - n)
  d.setHours(8, 0, 0, 0)
  return d.toISOString()
}

// ---------- 用户 ----------
const users = {
  13000000002: { user_id: 10001, name: '张桂兰', role: 'ELDER', phone: '13000000002', avatar: '' },
  13000000003: { user_id: 10002, name: '李强', role: 'FAMILY', phone: '13000000003', avatar: '' },
  13000000007: { user_id: 10003, name: '张敏', role: 'FAMILY', phone: '13000000007', avatar: '' },
  13000000004: { user_id: 10004, name: '王护工', role: 'CARE', phone: '13000000004', avatar: '' },
  13000000001: { user_id: 10000, name: '管理员', role: 'ADMIN', phone: '13000000001', avatar: '' },
}

// token 映射（mock 用）
const tokens = {}

// ---------- 指标与阈值配置 ----------
export const indicators = [
  {
    type: 'BLOOD_PRESSURE',
    name: '血压',
    unit: 'mmHg',
    desc: '收缩压/舒张压，静息状态下测量',
    fields: [
      { key: 'systolic', label: '收缩压（高压）', unit: 'mmHg', placeholder: '如 128' },
      { key: 'diastolic', label: '舒张压（低压）', unit: 'mmHg', placeholder: '如 82' },
    ],
  },
  {
    type: 'BLOOD_SUGAR',
    name: '血糖',
    unit: 'mmol/L',
    desc: '空腹或餐后 2 小时血糖',
    meta: { timing: ['空腹', '餐后 2 小时'] },
    fields: [{ key: 'value', label: '血糖值', unit: 'mmol/L', placeholder: '如 5.6' }],
  },
  {
    type: 'HEART_RATE',
    name: '心率',
    unit: '次/分',
    desc: '静息心率',
    fields: [{ key: 'value', label: '心率', unit: '次/分', placeholder: '如 72' }],
  },
  {
    type: 'SLEEP',
    name: '睡眠',
    unit: '小时',
    desc: '夜间睡眠时长与主观质量',
    meta: { quality: ['优', '良', '差'] },
    fields: [
      { key: 'hours', label: '睡眠时长', unit: '小时', placeholder: '如 7.5' },
      { key: 'quality', label: '睡眠质量', options: ['优', '良', '差'] },
    ],
  },
  {
    type: 'STEP',
    name: '步数',
    unit: '步',
    desc: '当日累计步数',
    fields: [{ key: 'count', label: '步数', unit: '步', placeholder: '如 6800' }],
  },
]

// 阈值（对应 /api/config/thresholds）。真实实现从后端读取，前端绝不硬编码业务规则。
export const thresholds = {
  BLOOD_PRESSURE: { systolic: { low: 90, high: 139 }, diastolic: { low: 60, high: 89 } },
  BLOOD_SUGAR: { fasting: { low: 3.9, high: 6.1 }, postprandial: { high: 7.8 } },
  HEART_RATE: { low: 60, high: 100 },
  SLEEP: { low: 6, high: 9 },
  STEP: { low: 3000, high: 15000 },
}

// 判断一条指标记录是否异常（返回描述文本或 null）
function judgeAbnormal(type, values, timing = '空腹') {
  const t = thresholds[type]
  if (!t) return null
  if (type === 'BLOOD_PRESSURE') {
    const sys = Number(values.systolic)
    const dia = Number(values.diastolic)
    if (sys >= 140 || dia >= 90) return `血压偏高（${sys}/${dia} mmHg）`
    if (sys < 90 || dia < 60) return `血压偏低（${sys}/${dia} mmHg）`
    return null
  }
  if (type === 'BLOOD_SUGAR') {
    const v = Number(values.value)
    const high = timing === '餐后 2 小时' ? t.postprandial.high : t.fasting.high
    if (v > high) return `血糖偏高（${v} mmol/L）`
    if (v < t.fasting.low) return `血糖偏低（${v} mmol/L）`
    return null
  }
  if (type === 'HEART_RATE') {
    const v = Number(values.value)
    if (v > t.high) return `心率偏快（${v} 次/分）`
    if (v < t.low) return `心率偏慢（${v} 次/分）`
    return null
  }
  if (type === 'SLEEP') {
    const v = Number(values.hours)
    if (v < t.low) return `睡眠不足（${v} 小时）`
    return null
  }
  if (type === 'STEP') {
    const v = Number(values.count)
    if (v < t.low) return `活动量偏低（${v} 步）`
    return null
  }
  return null
}

// ---------- 老人档案 ----------
const profiles = [
  {
    profile_id: 2001,
    user_id: 10001,
    name: '张桂兰',
    gender: 'F',
    birthday: '1954-03-12',
    age: 72,
    height: 158,
    weight: 62,
    blood_type: 'A',
    allergy: '青霉素（皮肤试验阳性）',
    medical_history: '2018 年脑梗，恢复良好，无肢体功能障碍；近两年血压控制欠佳',
    chronic_tags: ['高血压', '2 型糖尿病', '失眠'],
    emergency_contact: '李强',
    emergency_phone: '13000000003',
    backup_contact: '张敏',
    backup_phone: '13000000007',
    care_worker: '王护工',
    care_phone: '13000000004',
    created_at: isoDaysAgo(120),
  },
  {
    profile_id: 2002,
    user_id: 10005,
    name: '王秀英',
    gender: 'F',
    birthday: '1958-07-02',
    age: 68,
    height: 160,
    weight: 58,
    blood_type: 'B',
    allergy: '无',
    medical_history: '轻度骨质疏松',
    chronic_tags: ['高血压'],
    emergency_contact: '李强',
    emergency_phone: '13000000003',
    backup_contact: '',
    backup_phone: '',
    care_worker: '',
    care_phone: '',
    created_at: isoDaysAgo(60),
  },
  {
    profile_id: 2003,
    user_id: 10006,
    name: '刘建国',
    gender: 'M',
    birthday: '1951-11-28',
    age: 74,
    height: 172,
    weight: 75,
    blood_type: 'O',
    allergy: '磺胺类药物',
    medical_history: '冠心病，支架术后',
    chronic_tags: ['冠心病', '高血压'],
    emergency_contact: '李强',
    emergency_phone: '13000000003',
    backup_contact: '',
    backup_phone: '',
    care_worker: '',
    care_phone: '',
    created_at: isoDaysAgo(80),
  },
]

// ---------- 健康记录（为 2001 生成近 14 天数据，含 2 处异常） ----------
const healthRecords = []
;(function seedRecords() {
  let rid = 1
  for (let i = 13; i >= 0; i--) {
    const iso = isoDaysAgo(i)
    const rec = (type, values, timing) => {
      healthRecords.push({
        record_id: rid++,
        profile_id: 2001,
        type,
        values,
        timing: timing || null,
        measured_at: iso,
        entered_by: '张桂兰',
        is_abnormal: !!judgeAbnormal(type, values, timing),
      })
    }
    const sys = i === 4 ? 165 : i === 9 ? 152 : 126 + ((i * 7) % 9) - 3
    const dia = i === 4 ? 95 : i === 9 ? 90 : 82 + ((i * 5) % 6) - 2
    rec('BLOOD_PRESSURE', { systolic: sys, diastolic: dia })

    const sugar = i === 2 ? 9.8 : +(5.6 + ((i * 3) % 10) / 10 - 0.4).toFixed(1)
    rec('BLOOD_SUGAR', { value: sugar }, '空腹')

    rec('HEART_RATE', { value: 72 + ((i * 11) % 15) - 6 })

    const sleep = i === 5 ? 4.2 : +(7.1 + ((i * 13) % 20) / 10 - 0.8).toFixed(1)
    rec('SLEEP', { hours: sleep, quality: sleep < 6 ? '差' : sleep < 7 ? '良' : '优' })

    rec('STEP', { count: 5200 + ((i * 17) % 40) * 100 })
  }
})()

// ---------- 健康预警 ----------
const warnings = [
  {
    warning_id: 4001,
    profile_id: 2001,
    type: 'BLOOD_PRESSURE',
    value_text: '165/95 mmHg',
    unit: 'mmHg',
    level: 1,
    level_text: 'Ⅰ级（轻度）',
    title: '血压偏高提醒',
    summary_status: 'COMPLETED',
    ai_summary: '近 3 天收缩压均值 158 mmHg，较既往基线（约 128 mmHg）明显升高。建议：① 保持静息 5 分钟后复测；② 若连续两日收缩压 ≥160 mmHg 或伴头晕、胸闷，请及时就医；③ 规律服药、低盐饮食、避免情绪激动。',
    status: 'PENDING',
    trigger_source: 'MANUAL',
    created_at: isoDaysAgo(0),
    measure_time: isoDaysAgo(0),
  },
  {
    warning_id: 4002,
    profile_id: 2001,
    type: 'BLOOD_SUGAR',
    value_text: '9.8 mmol/L',
    unit: 'mmol/L',
    level: 2,
    level_text: 'Ⅱ级（中度）',
    title: '空腹血糖偏高提醒',
    summary_status: 'FAILED',
    ai_summary: null,
    status: 'PROCESSING',
    trigger_source: 'MANUAL',
    created_at: isoDaysAgo(2),
    measure_time: isoDaysAgo(2),
  },
  {
    warning_id: 4003,
    profile_id: 2001,
    type: 'SLEEP',
    value_text: '4.2 小时',
    unit: '小时',
    level: 1,
    level_text: 'Ⅰ级（轻度）',
    title: '睡眠不足提醒',
    summary_status: 'COMPLETED',
    ai_summary: '近一周平均睡眠 6.3 小时，昨日仅 4.2 小时，睡眠不足可能影响血压与血糖稳定。建议：① 固定就寝时间；② 睡前避免咖啡、浓茶；③ 午间小憩不超过 30 分钟。',
    status: 'RESOLVED',
    trigger_source: 'MANUAL',
    created_at: isoDaysAgo(5),
    measure_time: isoDaysAgo(5),
  },
  {
    warning_id: 4004,
    profile_id: 2002,
    type: 'HEART_RATE',
    value_text: '118 次/分',
    unit: '次/分',
    level: 2,
    level_text: 'Ⅱ级（中度）',
    title: '心率偏快提醒',
    summary_status: 'COMPLETED',
    ai_summary: '静息心率 118 次/分，明显高于正常范围（60–100 次/分）。若伴心悸、胸闷，建议尽快就医并做心电图检查。',
    status: 'PENDING',
    trigger_source: 'MANUAL',
    created_at: isoDaysAgo(1),
    measure_time: isoDaysAgo(1),
  },
]

// 预警接收人（每一条预警对应多个接收者，read_status 分离）
const receivers = [
  { warning_id: 4001, user_id: 10001, read_status: false },
  { warning_id: 4001, user_id: 10002, read_status: false },
  { warning_id: 4002, user_id: 10001, read_status: false },
  { warning_id: 4002, user_id: 10002, read_status: true },
  { warning_id: 4003, user_id: 10001, read_status: true },
  { warning_id: 4003, user_id: 10002, read_status: true },
  { warning_id: 4004, user_id: 10002, read_status: false },
]

// 处理记录
const handleRecords = [
  { handle_id: 1, warning_id: 4003, handler_id: 10001, handler_name: '张桂兰', action: '我已了解并调整作息', result: '已知晓', created_at: isoDaysAgo(5) },
  { handle_id: 2, warning_id: 4002, handler_id: 10002, handler_name: '李强', action: '已电话提醒母亲测餐后血糖', result: '跟进中', created_at: isoDaysAgo(1) },
]

// ---------- 家属绑定 ----------
const binds = [
  { bind_id: 3001, family_user_id: 10002, profile_id: 2001, elder_name: '张桂兰', relation: '儿子', note: '日常照护', status: 'APPROVED', created_at: isoDaysAgo(30), confirmed_at: isoDaysAgo(29) },
  { bind_id: 3002, family_user_id: 10003, profile_id: 2001, elder_name: '张桂兰', relation: '女儿', note: '', status: 'PENDING', created_at: isoDaysAgo(1), confirmed_at: null },
  { bind_id: 3003, family_user_id: 10002, profile_id: 2002, elder_name: '王秀英', relation: '女婿', note: '', status: 'PENDING', created_at: isoDaysAgo(2), confirmed_at: null },
  { bind_id: 3004, family_user_id: 10007, profile_id: 2001, elder_name: '张桂兰', relation: '邻居', note: '非亲属', status: 'REJECTED', created_at: isoDaysAgo(10), confirmed_at: isoDaysAgo(9) },
]

// ---------- AI 咨询会话与消息 ----------
const sessions = [
  { session_id: 's1001', profile_id: 2001, user_id: 10001, title: '高血压日常注意事项', created_at: isoDaysAgo(3) },
  { session_id: 's1002', profile_id: 2001, user_id: 10002, title: '母亲血糖偏高怎么吃', created_at: isoDaysAgo(1) },
]

const messages = [
  { message_id: 'm1', session_id: 's1001', role: 'user', content: '我血压有点高，平时要注意什么？', intent: 'HEALTH_CONSULT', agent: 'health_assistant', safety_level: 'SAFE', sources: [], created_at: isoDaysAgo(3) },
  {
    message_id: 'm2',
    session_id: 's1001',
    role: 'assistant',
    content: '结合您的健康档案（高血压、2 型糖尿病），建议：① 每日定时测量血压并记录；② 低盐低脂饮食，每日食盐 <5g；③ 规律服药，勿自行停药；④ 每周 150 分钟中等强度运动（如快走）。如血压持续 ≥160/100 mmHg，请及时就医。',
    intent: 'HEALTH_CONSULT',
    agent: 'health_assistant',
    safety_level: 'SAFE',
    sources: ['《中国高血压防治指南》'],
    created_at: isoDaysAgo(3),
  },
  { message_id: 'm3', session_id: 's1002', role: 'user', content: '我妈空腹血糖 9.8，吃饭要注意什么？', intent: 'HEALTH_CONSULT', agent: 'health_assistant', safety_level: 'SAFE', sources: [], created_at: isoDaysAgo(1) },
  {
    message_id: 'm4',
    session_id: 's1002',
    role: 'assistant',
    content: '空腹血糖 9.8 mmol/L 已明显偏高，建议：① 控制主食总量，粗细搭配；② 少食多餐，先菜后饭；③ 避免含糖饮料与糕点；④ 连续监测 3 天空腹及餐后血糖并记录。若持续偏高，需就医调整降糖方案。',
    intent: 'HEALTH_CONSULT',
    agent: 'health_assistant',
    safety_level: 'SAFE',
    sources: ['《中国 2 型糖尿病防治指南》'],
    created_at: isoDaysAgo(1),
  },
]

// AI 关键词回复模板（mock 用；真实实现由后端 LangChain 智能体完成）
function cannedReply(content, profile) {
  const text = String(content)
  const name = profile ? profile.name : '您'
  if (/血压/.test(text)) {
    return {
      intent: 'HEALTH_CONSULT',
      agent: 'health_assistant',
      safety_level: 'SAFE',
      sources: ['《中国高血压防治指南》'],
      content: `结合${name}的档案，高血压日常注意：① 每日固定时间测血压并记录；② 低盐饮食（每日 <5g 盐）；③ 规律服药、勿自行停药；④ 情绪平稳、保证睡眠。若血压持续 ≥160/100 mmHg 或伴头晕胸闷，请及时就医。`,
    }
  }
  if (/血糖|糖尿病|吃/.test(text)) {
    return {
      intent: 'HEALTH_CONSULT',
      agent: 'health_assistant',
      safety_level: 'SAFE',
      sources: ['《中国 2 型糖尿病防治指南》'],
      content: `关于血糖：① 控制主食总量、粗细搭配；② 先吃菜后吃饭、少食多餐；③ 避免含糖饮料与糕点；④ 连续监测空腹与餐后血糖。若空腹 ≥7 mmol/L 或餐后 ≥11.1 mmol/L 反复出现，建议就医调整方案。`,
    }
  }
  if (/睡眠|失眠|睡不着/.test(text)) {
    return {
      intent: 'HEALTH_CONSULT',
      agent: 'health_assistant',
      safety_level: 'SAFE',
      sources: [],
      content: '改善睡眠建议：① 固定就寝与起床时间；② 睡前 1 小时远离手机；③ 午后避免浓茶咖啡；④ 卧室保持安静、温度适宜。若长期失眠影响日间精神，建议就医评估。',
    }
  }
  if (/用药|吃什么药|药怎么/.test(text)) {
    return {
      intent: 'MEDICATION_CONSULT',
      agent: 'medication_assistant',
      safety_level: 'NEED_CONFIRM',
      sources: [],
      content: '用药问题涉及专业判断，我不能替代医生。建议：① 严格按医嘱服药，勿自行增减或停药；② 记录药名、剂量、服药时间；③ 有疑问请咨询主治医生或药师。您可把具体药名发给我，我帮您整理注意事项。',
    }
  }
  if (/跌倒|摔|头晕|胸痛|胸闷|急救|救命/.test(text)) {
    return {
      intent: 'EMERGENCY',
      agent: 'triage_assistant',
      safety_level: 'ESCALATE',
      sources: [],
      content: '您描述的情况可能属于紧急情况，请立即拨打 120 或就近就医。如意识不清、胸痛持续、呼吸困难，请勿自行移动患者，保持呼吸道通畅并等待急救人员。',
    }
  }
  return {
    intent: 'HEALTH_CONSULT',
    agent: 'health_assistant',
    safety_level: 'SAFE',
    sources: [],
    content: '已收到您的问题。作为健康管理助手，我会基于您的健康档案提供一般性建议。您想了解血压、血糖、睡眠、运动还是用药方面的内容？',
  }
}

// ---------- 通知（站内通知，D-03：仅站内，不接短信/微信） ----------
const notifications = [
  { notification_id: 1, user_id: 10001, type: 'ALERT', ref_type: 'ALERT', ref_id: 4001, title: '您有一条新的健康预警', content: '血压偏高提醒（165/95 mmHg），请及时查看。', read_status: false, created_at: isoDaysAgo(0) },
  { notification_id: 2, user_id: 10001, type: 'BIND', ref_type: 'BIND', title: '家属绑定申请', content: '张敏 申请绑定为您的家属，请前往「我的-绑定确认」处理。', read_status: false, created_at: isoDaysAgo(1) },
  { notification_id: 3, user_id: 10001, type: 'SYSTEM', title: '本周健康周报已生成', content: '请前往「健康档案」查看。', read_status: true, created_at: isoDaysAgo(4) },
  { notification_id: 4, user_id: 10002, type: 'ALERT', ref_type: 'ALERT', ref_id: 4001, title: '家人健康预警', content: '张桂兰 出现血压偏高（165/95 mmHg），请及时查看并处理。', read_status: false, created_at: isoDaysAgo(0) },
  { notification_id: 5, user_id: 10002, type: 'ALERT', ref_type: 'ALERT', ref_id: 4004, title: '家人健康预警', content: '王秀英 出现心率偏快（118 次/分），请及时查看并处理。', read_status: false, created_at: isoDaysAgo(1) },
]

// 导出 store（供各 domain api 使用）
export const db = {
  users,
  tokens,
  profiles,
  healthRecords,
  warnings,
  receivers,
  handleRecords,
  binds,
  sessions,
  messages,
  notifications,
  judgeAbnormal,
  cannedReply,
  uid,
  isoDaysAgo,
}
