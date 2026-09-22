// 家属绑定与老人健康概况模块 api（mock）
// 【临时 mock】待丘宇乾替换为真实实现
// D-02：绑定三段式 —— 申请 → 老人确认 → 生效（APPROVED 后才可查看健康数据）
import { db, respond, uid, fail } from './mock'

const STATUS_TEXT = { PENDING: '待确认', APPROVED: '已生效', REJECTED: '已拒绝', UNBOUND: '已解绑' }

export async function submitBind({ family_user_id, elder_phone, relation, note }) {
  const profile = db.profiles.find((p) => p.emergency_phone === elder_phone || p.backup_phone === elder_phone)
  if (!profile) throw fail(3001, '未找到该手机号对应的老人，请核实')
  const exists = db.binds.find((b) => b.family_user_id === family_user_id && b.profile_id === profile.profile_id && b.status === 'PENDING')
  if (exists) throw fail(3002, '已提交过该老人的绑定申请，请耐心等待确认')
  const bind = {
    bind_id: Number(uid('3')),
    family_user_id,
    profile_id: profile.profile_id,
    elder_name: profile.name,
    relation,
    note: note || '',
    status: 'PENDING',
    created_at: new Date().toISOString(),
    confirmed_at: null,
  }
  db.binds.unshift(bind)
  // 通知老人处理绑定申请
  db.notifications.unshift({
    notification_id: Number(uid('9')),
    user_id: profile.user_id,
    type: 'BIND',
    title: '家属绑定申请',
    content: `有人申请绑定为您关系为「${relation}」的家属，请前往「我的-绑定确认」处理。`,
    read_status: false,
    created_at: new Date().toISOString(),
  })
  return respond(bind)
}

export async function listMyBinds(familyUserId) {
  const list = db.binds
    .filter((b) => b.family_user_id === familyUserId)
    .map((b) => ({ ...b, status_text: STATUS_TEXT[b.status] }))
  return respond(list)
}

// 老人视角：待我确认 / 已授权 / 已拒绝
export async function listBindRequests(userId) {
  const myProfile = db.profiles.find((p) => p.user_id === userId)
  if (!myProfile) return respond({ pending: [], approved: [], rejected: [] })
  const mine = db.binds.filter((b) => b.profile_id === myProfile.profile_id)
  return respond({
    pending: mine.filter((b) => b.status === 'PENDING').map((b) => ({ ...b, status_text: '待确认' })),
    approved: mine.filter((b) => b.status === 'APPROVED').map((b) => ({ ...b, status_text: '已授权' })),
    rejected: mine.filter((b) => b.status === 'REJECTED').map((b) => ({ ...b, status_text: '已拒绝' })),
  })
}

export async function confirmBind({ bind_id, decision, reason }) {
  const b = db.binds.find((x) => x.bind_id === Number(bind_id))
  if (!b) throw new Error('申请不存在')
  if (decision === 'APPROVE') {
    b.status = 'APPROVED'
    b.confirmed_at = new Date().toISOString()
  } else {
    b.status = 'REJECTED'
    b.reject_reason = reason || ''
    b.confirmed_at = new Date().toISOString()
  }
  // 通知家属结果
  db.notifications.unshift({
    notification_id: Number(uid('9')),
    user_id: b.family_user_id,
    type: 'BIND',
    title: '绑定申请已处理',
    content: `您与「${b.elder_name}」的绑定申请已${decision === 'APPROVE' ? '通过' : '被拒绝'}。`,
    read_status: false,
    created_at: new Date().toISOString(),
  })
  return respond(b)
}

export async function unbind(bindId) {
  const b = db.binds.find((x) => x.bind_id === Number(bindId))
  if (b) b.status = 'UNBOUND'
  return respond(null)
}

// 家属首页：已绑定老人列表 + 概览
export async function listElders(familyUserId) {
  const approved = db.binds.filter((b) => b.family_user_id === familyUserId && b.status === 'APPROVED')
  const list = approved.map((b) => {
    const profile = db.profiles.find((p) => p.profile_id === b.profile_id)
    return { ...b, profile }
  })
  return respond(list)
}

// 单个老人健康概况：档案 + 今日指标 + 未处理预警 + 近 14 天趋势摘要
export async function getElderOverview(profileId, familyUserId) {
  const b = db.binds.find((x) => x.profile_id === Number(profileId) && x.family_user_id === familyUserId && x.status === 'APPROVED')
  if (!b) throw fail(3002, '未绑定该老人，无法查看健康数据')
  const profile = db.profiles.find((p) => p.profile_id === Number(profileId))
  const records = db.healthRecords.filter((r) => r.profile_id === Number(profileId))
  const alerts = db.warnings.filter((w) => w.profile_id === Number(profileId) && w.status !== 'RESOLVED')
  const latest = {}
  ;['BLOOD_PRESSURE', 'BLOOD_SUGAR', 'HEART_RATE', 'SLEEP', 'STEP'].forEach((t) => {
    const arr = records.filter((r) => r.type === t).sort((a, b) => new Date(b.measured_at) - new Date(a.measured_at))
    latest[t] = arr[0] || null
  })
  return respond({ profile, latest, open_alerts: alerts, relation: b.relation })
}
