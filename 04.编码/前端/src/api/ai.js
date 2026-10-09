import request from '@/utils/request'
import { asList } from '@/utils/format'
export const listSessions = async ({ profile_id } = {}) => asList(await request.get('/ai/sessions', { params: { profile_id } }))
export const listMessages = async id => asList(await request.get(`/ai/sessions/${id}/messages`))
export async function sendMessage({ session_id, profile_id, content }) {
  const d = await request.post('/ai/chat', { session_id: session_id || null, profile_id, question: content })
  return { ...d, role: 'assistant', content: d.answer }
}
export const deleteSession = id => request.delete(`/ai/sessions/${id}`)
