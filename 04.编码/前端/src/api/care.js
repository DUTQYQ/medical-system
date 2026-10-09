import request from '@/utils/request'
import { asList } from '@/utils/format'
export const listCareElders = async params => asList(await request.get('/care/elders', { params }))
export const getCareElder = id => request.get(`/care/elders/${id}`)
export const listCareHandles = params => request.get('/care/handles', { params })
