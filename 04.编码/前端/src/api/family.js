import request from '@/utils/request'
import { asList } from '@/utils/format'
import { getProfile } from './profile'
import { getLatestIndicators } from './health'
import { listAlerts } from './alert'
export const submitBind = ({ elder_phone, phone, relation, note, profile_id }) => request.post('/family/bind', { phone: phone || elder_phone, relation, note, ...(profile_id ? { profile_id: Number(profile_id) } : {}) })
export const listMyBinds = async () => asList(await request.get('/family/binds'))
export async function listBindRequests() {
  const d = await request.get('/family/binds')
  if (d.pending) return d
  const l = asList(d).map(b => ({ ...b, confirmed_at: b.approved_at || b.confirmed_at, reject_reason: b.approve_note || b.reject_reason }))
  return { pending: l.filter(b => b.status === 'PENDING'), approved: l.filter(b => b.status === 'APPROVED'), rejected: l.filter(b => b.status === 'REJECTED'), revoked: l.filter(b => b.status === 'REVOKED') }
}
export const confirmBind = ({ bind_id, decision, reason }) => request.put(`/family/bind/${bind_id}/confirm`, { action: decision, note: reason || '' })
export const unbind = id => request.delete(`/family/bind/${id}`)
export async function listElders() {
  const l = asList(await request.get('/family/elders'))
  return Promise.all(l.map(async e => ({ ...e, profile: e.profile || await getProfile(e.profile_id) })))
}
export async function getElderOverview(id) {
  const [profile, latest, alerts, elders] = await Promise.all([getProfile(id), getLatestIndicators(id), listAlerts({ profile_id: id, page_size: 100 }), listElders()])
  return { profile, latest, open_alerts: alerts.list.filter(a => ['PENDING', 'PROCESSING'].includes(a.status)), relation: elders.find(e => Number(e.profile_id) === Number(id))?.relation }
}
