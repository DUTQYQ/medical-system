// 健康预警模块 api（mock）
// 【临时 mock】待丘宇乾替换为真实实现
import { db, respond, uid, fail } from './mock'

// 当前用户相关的预警列表（含本人视角的已读状态；D-05 处理状态与已读状态分离）
export async function listAlerts({ user_id, status, page = 1, page_size = 10 }) {
  const myIds = new Set(db.receivers.filter((r) => r.user_id === user_id).map((r) => r.warning_id))
  let list = db.warnings.filter((w) => myIds.has(w.warning_id))
  if (status) list = list.filter((w) => w.status === status)
  list = [...list].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  const total = list.length
  const start = (page - 1) * page_size
  const data = list.slice(start, start + page_size).map((w) => {
    const rec = db.receivers.find((r) => r.warning_id === w.warning_id && r.user_id === user_id)
    return { ...w, my_read_status: rec ? rec.read_status : false }
  })
  return respond({ list: data, total, page, page_size })
}

export async function getAlert({ warning_id, user_id }) {
  const w = db.warnings.find((x) => x.warning_id === Number(warning_id))
  if (!w) throw new Error('预警不存在')
  const rec = db.receivers.find((r) => r.warning_id === w.warning_id && r.user_id === user_id)
  const handles = db.handleRecords.filter((h) => h.warning_id === w.warning_id)
  const profile = db.profiles.find((p) => p.profile_id === w.profile_id)
  return respond({ ...w, my_read_status: rec ? rec.read_status : false, handles, profile })
}

// 标记已读
export async function updateRead(warningId, userId) {
  const rec = db.receivers.find((r) => r.warning_id === Number(warningId) && r.user_id === userId)
  if (rec) rec.read_status = true
  return respond(null)
}

// 家属/本人处理预警
export async function handleAlert({ warning_id, user_id, handler_name, action, result }) {
  const w = db.warnings.find((x) => x.warning_id === Number(warning_id))
  if (!w) throw new Error('预警不存在')
  db.handleRecords.push({
    handle_id: Number(uid('5')),
    warning_id: Number(warning_id),
    handler_id: user_id,
    handler_name,
    action,
    result,
    created_at: new Date().toISOString(),
  })
  if (result && (result === '已处理' || result === '已就医')) {
    w.status = 'RESOLVED'
  } else {
    w.status = 'PROCESSING'
  }
  // 处理动作也会被记录为一条通知反馈给老人本人
  const owner = db.profiles.find((p) => p.profile_id === w.profile_id)
  db.notifications.unshift({
    notification_id: Number(uid('9')),
    user_id: owner ? owner.user_id : null,
    type: 'ALERT',
    ref_type: 'ALERT',
    ref_id: w.warning_id,
    title: '预警处理反馈',
    content: `${handler_name} 已处理预警「${w.title}」：${result || action}`,
    read_status: false,
    created_at: new Date().toISOString(),
  })
  return respond({ ...w, handles: db.handleRecords.filter((h) => h.warning_id === w.warning_id) })
}

// AI 摘要重试（D-04：摘要异步降级，失败后可由前端触发重试）
export async function retrySummary(warningId) {
  const w = db.warnings.find((x) => x.warning_id === Number(warningId))
  if (!w) throw new Error('预警不存在')
  if (w.summary_status === 'FAILED') {
    w.summary_status = 'COMPLETED'
    w.ai_summary = '（重试成功）结合近期趋势：该异常较既往基线有明显波动。建议保持静息后复测，若持续异常或伴不适症状，请及时就医，并保留测量记录供医生参考。'
  }
  return respond({ summary_status: w.summary_status, ai_summary: w.ai_summary })
}

// 预警统计（老人首页 / 家属首页仪表盘）
export async function summaryStats(userId) {
  const myIds = new Set(db.receivers.filter((r) => r.user_id === userId).map((r) => r.warning_id))
  const mine = db.warnings.filter((w) => myIds.has(w.warning_id))
  const unread = db.receivers.filter((r) => r.user_id === userId && !r.read_status).length
  return respond({
    total: mine.length,
    pending: mine.filter((w) => w.status === 'PENDING').length,
    processing: mine.filter((w) => w.status === 'PROCESSING').length,
    resolved: mine.filter((w) => w.status === 'RESOLVED').length,
    unread,
  })
}
