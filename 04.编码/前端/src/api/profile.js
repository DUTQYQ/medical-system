// 健康档案模块 api（mock）
// 【临时 mock】待丘宇乾替换为真实实现
import { db, respond, uid } from './mock'

// 当前用户可管理的档案：老人本人 → 自己的档案；家属 → 已绑定老人的档案
export async function listProfiles(userId, role) {
  if (role === 'FAMILY') {
    const approved = db.binds.filter((b) => b.family_user_id === userId && b.status === 'APPROVED')
    const ids = approved.map((b) => b.profile_id)
    return respond(db.profiles.filter((p) => ids.includes(p.profile_id)))
  }
  return respond(db.profiles.filter((p) => p.user_id === userId))
}

export async function getProfile(profileId) {
  const p = db.profiles.find((x) => x.profile_id === Number(profileId))
  if (!p) throw new Error('档案不存在')
  return respond({ ...p })
}

export async function createProfile(payload) {
  const profile = { profile_id: Number(uid('2')), ...payload }
  db.profiles.unshift(profile)
  return respond({ ...profile })
}

export async function updateProfile(profileId, payload) {
  const p = db.profiles.find((x) => x.profile_id === Number(profileId))
  if (!p) throw new Error('档案不存在')
  Object.assign(p, payload)
  return respond({ ...p })
}

export async function deleteProfile(profileId) {
  const idx = db.profiles.findIndex((x) => x.profile_id === Number(profileId))
  if (idx > -1) db.profiles.splice(idx, 1)
  return respond(null)
}
