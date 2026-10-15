import request from '@/utils/request'
import { asList } from '@/utils/format'
export const listSessions = async ({ profile_id } = {}) => asList(await request.get('/ai/sessions', { params: { profile_id } }))
export const listMessages = async id => asList(await request.get(`/ai/sessions/${id}/messages`))
export async function sendMessage({ session_id, profile_id, content }) {
  const d = await request.post('/ai/chat', { session_id: session_id || null, profile_id, question: content })
  return { ...d, role: 'assistant', content: d.answer }
}
export const deleteSession = id => request.delete(`/ai/sessions/${id}`)
export const startIntake = profile_id => request.post('/ai/intake/start', { profile_id })
export const answerIntake = (id, body) => request.post(`/ai/intake/${id}/answer`, body)
export const confirmIntake = (id, entries) => request.post(`/ai/intake/${id}/confirm`, { entries })
export const listPersonalFacts = async profile_id => asList(await request.get('/ai/facts', { params: { profile_id } }))
export const createPersonalFact = body => request.post('/ai/facts', body)
export const updatePersonalFact = (id, value) => request.put(`/ai/facts/${id}`, { value })
export const revokePersonalFact = id => request.delete(`/ai/facts/${id}`)
export const generatePersonalAdvice = profile_id => request.post('/ai/advice', { profile_id })
export const listPersonalAdvice = async profile_id => asList(await request.get('/ai/advice', { params: { profile_id } }))
