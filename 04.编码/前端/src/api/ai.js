// AI 健康咨询模块 api（mock）
// 【临时 mock】待丘宇乾替换为真实实现（后端 LangChain/LangGraph 智能体）
// 注意：真实实现中 API Key 由后端持有，前端绝不接触模型密钥。
import { db, respond, uid } from './mock'

export async function listSessions({ user_id, profile_id } = {}) {
  let list = db.sessions
  if (user_id) list = list.filter((s) => s.user_id === user_id)
  if (profile_id) list = list.filter((s) => s.profile_id === Number(profile_id))
  list = [...list].sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
  return respond(list)
}

export async function createSession({ user_id, profile_id, title }) {
  const session = {
    session_id: uid('s'),
    profile_id: Number(profile_id),
    user_id,
    title: title || '新的健康咨询',
    created_at: new Date().toISOString(),
  }
  db.sessions.unshift(session)
  return respond(session)
}

export async function listMessages(sessionId) {
  const list = db.messages.filter((m) => m.session_id === sessionId)
  return respond(list)
}

export async function sendMessage({ session_id, profile_id, content }) {
  const profile = db.profiles.find((p) => p.profile_id === Number(profile_id))
  const userMsg = {
    message_id: uid('m'),
    session_id,
    role: 'user',
    content,
    created_at: new Date().toISOString(),
  }
  db.messages.push(userMsg)

  // 模拟「模型繁忙」限流（真实实现对应 5001 / 4004 错误码，前端需优雅降级）
  if (/限流|繁忙/.test(String(content))) {
    const err = new Error('AI 服务繁忙，请稍后重试')
    err.code = 5001
    throw err
  }

  const reply = db.cannedReply(content, profile)
  const aiMsg = {
    message_id: uid('m'),
    session_id,
    role: 'assistant',
    content: reply.content,
    intent: reply.intent,
    agent: reply.agent,
    safety_level: reply.safety_level,
    sources: reply.sources,
    created_at: new Date().toISOString(),
  }
  db.messages.push(aiMsg)
  return respond(aiMsg)
}

export async function deleteSession(sessionId) {
  db.sessions = db.sessions.filter((s) => s.session_id !== sessionId)
  db.messages = db.messages.filter((m) => m.session_id !== sessionId)
  return respond(null)
}
