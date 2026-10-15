import request from '@/utils/request'
import { asList } from '@/utils/format'
export const getPersonalThresholds = id => request.get(`/profiles/${id}/thresholds`)
export const proposePersonalThreshold = (id, body) => request.post(`/profiles/${id}/threshold-proposals`, body)
export const listThresholdProposals = async params => asList(await request.get('/threshold-proposals', { params }))
export const reviewThresholdProposal = (id, body) => request.post(`/threshold-proposals/${id}/review`, body)
