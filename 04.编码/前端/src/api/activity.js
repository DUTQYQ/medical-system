import request from '@/utils/request'
export const listActivities = () => request.get('/activities')
export const getRecommendations = profileId => request.get('/activities/recommend', { params: { profile_id: profileId } })
export const createActivity = p => request.post('/activities', p)
export const updateActivity = (id, p) => request.put(`/activities/${id}`, p)
export const deleteActivity = id => request.delete(`/activities/${id}`)
