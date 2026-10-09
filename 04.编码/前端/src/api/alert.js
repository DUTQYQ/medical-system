import request from '@/utils/request'
import { NAME } from '@/utils/format'
const normalize = w => ({ ...w, title: w.title || `${NAME[w.type] || w.type || '健康'}预警`, my_read_status: ['READ', true, 1].includes(w.my_read_status) })
export async function listAlerts({ user_id, ...params } = {}) {
  const d = await request.get('/alerts', { params })
  return { ...d, list: d.list.map(normalize) }
}
export async function getAlert({ warning_id }) { return normalize(await request.get(`/alerts/${warning_id}`)) }
export const updateRead = id => request.post(`/alerts/${id}/read`)
export const handleAlert = ({ warning_id, action, result }) => request.post(`/alerts/${warning_id}/handle`, { action, result })
export const setAlertStatus = (id, status) => request.put(`/alerts/${id}/status`, { status })
export const retrySummary = id => request.post(`/alerts/${id}/summary/retry`)
export async function summaryStats() {
  const s = await request.get('/alerts/statistics')
  return { ...s, resolved: s.resolved ?? s.handled, processing: s.processing ?? 0 }
}
