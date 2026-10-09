import request from '@/utils/request'
import { asList } from '@/utils/format'
export async function listNotifications() {
  const l = asList(await request.get('/notifications', { params: { page_size: 100 } }))
  return l.map(n => ({ ...n, notification_id: n.notification_id || n.warning_id, type: n.warning_id ? 'ALERT' : n.type, title: n.title || `${n.elder_name || ''}健康预警`, content: n.content || `${n.value_text || ''} ${n.unit || ''} · ${n.level_text || ''}`, read_status: [true, 1, 'READ'].includes(n.read_status ?? n.my_read_status), ref_type: n.ref_type || (n.warning_id ? 'ALERT' : n.type === 'BIND' ? 'BIND' : undefined), ref_id: n.ref_id || n.warning_id }))
}
export async function getUnreadCount() { const d = await request.get('/notifications/unread'); return { ...d, count: d.unread } }
export const markRead = (_userId, id) => request.post(`/notifications/${id}/read`)
export const markAllRead = () => request.post('/notifications/read-all')
