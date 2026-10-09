import request from '@/utils/request'
import { asList } from '@/utils/format'
export const listProfiles = async () => asList(await request.get('/profiles'))
export const getProfile = id => request.get(`/profiles/${id}`)
export const createProfile = p => request.post('/profiles', p)
export const updateProfile = (id, p) => request.put(`/profiles/${id}`, p)
export const deleteProfile = id => request.delete(`/profiles/${id}`)
