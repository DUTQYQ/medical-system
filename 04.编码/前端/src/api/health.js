import request from '@/utils/request'
import { TYPES, UNIT } from '@/utils/format'
export async function addRecord(p) {
  const r = await request.post('/health/records', p)
  return { ...r, warning_created: r.is_abnormal }
}
export const listRecords = params => request.get('/health/records', { params })
export const deleteRecord = id => request.delete(`/health/records/${id}`)
export async function getLatestIndicators(profileId) {
  return Object.fromEntries(await Promise.all(TYPES.map(async type => {
    const r = await listRecords({ profile_id: profileId, type, page: 1, page_size: 1 })
    return [type, r.list[0] || null]
  })))
}
export async function getTrend(params) {
  const d = await request.get('/health/trend', { params })
  return { ...d, unit: d.unit || UNIT[params.type], abnormalIndexes: d.abnormalIndexes || d.abnormal_indexes || [...new Set((d.abnormal_points || []).map(p => d.dates.indexOf(p.date)).filter(i => i >= 0))] }
}
