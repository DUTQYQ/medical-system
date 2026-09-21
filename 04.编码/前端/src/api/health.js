// 健康指标模块 api（mock）
// 【临时 mock】待丘宇乾替换为真实实现
import { db, respond, uid, fail } from './mock'

// 录入一条指标；异常时生成一条预警（D-04：录入即触发，站内通知接收人）
export async function addRecord(payload) {
  const { profile_id, type, values, timing, entered_by } = payload
  const abnormal = db.judgeAbnormal(type, values, timing)
  const record = {
    record_id: Number(uid('6')),
    profile_id: Number(profile_id),
    type,
    values,
    timing: timing || null,
    measured_at: new Date().toISOString(),
    entered_by: entered_by || '本人',
    is_abnormal: !!abnormal,
  }
  db.healthRecords.push(record)

  if (abnormal) {
    const indicator = { BLOOD_PRESSURE: '血压', BLOOD_SUGAR: '血糖', HEART_RATE: '心率', SLEEP: '睡眠', STEP: '步数' }[type]
    const valueText = type === 'BLOOD_PRESSURE'
      ? `${values.systolic}/${values.diastolic} mmHg`
      : type === 'BLOOD_SUGAR'
        ? `${values.value} mmol/L`
        : type === 'HEART_RATE'
          ? `${values.value} 次/分`
          : type === 'SLEEP'
            ? `${values.hours} 小时`
            : `${values.count} 步`
    const warning = {
      warning_id: Number(uid('4')),
      profile_id: Number(profile_id),
      type,
      value_text: valueText,
      unit: { BLOOD_PRESSURE: 'mmHg', BLOOD_SUGAR: 'mmol/L', HEART_RATE: '次/分', SLEEP: '小时', STEP: '步' }[type],
      level: 1,
      level_text: 'Ⅰ级（轻度）',
      title: `${indicator}异常提醒`,
      summary_status: 'COMPLETED',
      ai_summary: `检测到${indicator}异常（${valueText}）。建议保持静息后复测；若持续异常或伴不适，请及时就医。`,
      status: 'PENDING',
      trigger_source: 'MANUAL',
      created_at: new Date().toISOString(),
      measure_time: new Date().toISOString(),
    }
    db.warnings.unshift(warning)
    // 通知老人本人 + 已授权家属
    const prof = db.profiles.find((p) => p.profile_id === Number(profile_id))
    const receivers = new Set(prof ? [prof.user_id] : [])
    db.binds.filter((b) => b.profile_id === Number(profile_id) && b.status === 'APPROVED').forEach((b) => receivers.add(b.family_user_id))
    receivers.forEach((uid_) => {
      db.receivers.push({ warning_id: warning.warning_id, user_id: uid_, read_status: false })
      db.notifications.unshift({
        notification_id: Number(uid('9')),
        user_id: uid_,
        type: 'ALERT',
        ref_type: 'ALERT',
        ref_id: warning.warning_id,
        title: '您有一条新的健康预警',
        content: `${indicator}异常提醒（${valueText}），请及时查看。`,
        read_status: false,
        created_at: new Date().toISOString(),
      })
    })
  }

  return respond({ record, warning_created: !!abnormal })
}

// 记录列表（按档案 + 类型 + 分页）
export async function listRecords({ profile_id, type, page = 1, page_size = 10 }) {
  let list = db.healthRecords.filter((r) => r.profile_id === Number(profile_id))
  if (type) list = list.filter((r) => r.type === type)
  list = [...list].sort((a, b) => new Date(b.measured_at) - new Date(a.measured_at))
  const total = list.length
  const start = (page - 1) * page_size
  const data = list.slice(start, start + page_size)
  return respond({ list: data, total, page, page_size })
}

// 各指标最新一条记录（首页仪表盘用）
export async function getLatestIndicators(profileId) {
  const types = ['BLOOD_PRESSURE', 'BLOOD_SUGAR', 'HEART_RATE', 'SLEEP', 'STEP']
  const result = {}
  types.forEach((t) => {
    const arr = db.healthRecords
      .filter((r) => r.profile_id === Number(profileId) && r.type === t)
      .sort((a, b) => new Date(b.measured_at) - new Date(a.measured_at))
    result[t] = arr[0] || null
  })
  return respond(result)
}

// 趋势数据（近 14 天，多类型序列 + 异常点标记）
export async function getTrend({ profile_id, type, days = 14 }) {
  const list = db.healthRecords
    .filter((r) => r.profile_id === Number(profile_id) && r.type === type)
    .sort((a, b) => new Date(a.measured_at) - new Date(b.measured_at))
    .slice(-days)

  const dates = list.map((r) => r.measured_at.slice(0, 10))

  let series = []
  if (type === 'BLOOD_PRESSURE') {
    series = [
      { name: '收缩压', key: 'systolic', values: list.map((r) => r.values.systolic) },
      { name: '舒张压', key: 'diastolic', values: list.map((r) => r.values.diastolic) },
    ]
  } else if (type === 'BLOOD_SUGAR') {
    series = [{ name: '血糖', key: 'value', values: list.map((r) => r.values.value) }]
  } else if (type === 'HEART_RATE') {
    series = [{ name: '心率', key: 'value', values: list.map((r) => r.values.value) }]
  } else if (type === 'SLEEP') {
    series = [{ name: '睡眠时长', key: 'hours', values: list.map((r) => r.values.hours) }]
  } else if (type === 'STEP') {
    series = [{ name: '步数', key: 'count', values: list.map((r) => r.values.count) }]
  }

  // 异常点索引
  const abnormalIndexes = []
  list.forEach((r, i) => {
    if (r.is_abnormal) abnormalIndexes.push(i)
  })

  return respond({ dates, series, abnormalIndexes, unit: indicators_unit(type) })
}

function indicators_unit(type) {
  return { BLOOD_PRESSURE: 'mmHg', BLOOD_SUGAR: 'mmol/L', HEART_RATE: '次/分', SLEEP: '小时', STEP: '步' }[type]
}
