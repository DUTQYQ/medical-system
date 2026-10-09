import request from '@/utils/request'
import { asList } from '@/utils/format'
export const listUsers = params => request.get('/admin/users', { params })
export const createUser = p => request.post('/admin/users', p)
export const setUserEnabled = (id, enabled) => request.put(`/admin/users/${id}/status`, { enabled })
export const setUserRole = (id, role) => request.put(`/admin/users/${id}/role`, { role })
export const listAdminThresholds = () => request.get('/admin/thresholds')
export const saveThreshold = (id, p) => request.put(`/admin/thresholds/${id}`, p)
export const listAdminIndicators = () => request.get('/admin/indicators')
export const saveIndicator = (type, p) => request.put(`/admin/indicators/${type}`, p)
export async function listKnowledge(params = {}) {
 const data = await request.get('/admin/knowledge', { params })
 if (!Array.isArray(data)) return data
 const keyword = (params.keyword || '').toLowerCase()
 const list = data.filter(d => !keyword || (d.title + ' ' + d.content + ' ' + d.category).toLowerCase().includes(keyword))
 const size = params.page_size || 20, page = params.page || 1
 return { list: list.slice((page-1)*size, page*size), total: list.length, page, page_size: size }
}
export const addKnowledge = p => request.post('/admin/knowledge', p)
export const saveKnowledge = (id, p) => request.put(`/admin/knowledge/${id}`, p)
export const deleteKnowledge = id => request.delete(`/admin/knowledge/${id}`)
export const reindexKnowledge = () => request.post('/admin/knowledge/reindex')
export const adminStatistics = range => request.get('/admin/statistics', { params: { range } })
