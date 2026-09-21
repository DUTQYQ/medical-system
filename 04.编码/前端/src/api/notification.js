// 站内通知模块 api（mock）
// 【临时 mock】待丘宇乾替换为真实实现
// D-03：仅站内通知，不接短信 / 微信等外发渠道
import { db, respond } from './mock'

export async function listNotifications(userId) {
  const list = db.notifications
    .filter((n) => n.user_id === userId)
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  return respond(list)
}

export async function getUnreadCount(userId) {
  const count = db.notifications.filter((n) => n.user_id === userId && !n.read_status).length
  return respond({ count })
}

export async function markRead(userId, notificationId) {
  const n = db.notifications.find((x) => x.user_id === userId && (x.notification_id === Number(notificationId) || notificationId === 'all'))
  if (n) n.read_status = true
  return respond(null)
}

export async function markAllRead(userId) {
  db.notifications.forEach((n) => {
    if (n.user_id === userId) n.read_status = true
  })
  return respond(null)
}
