import request from '@/utils/request'
import { asList, FIELD_SCHEMA } from '@/utils/format'
export async function getIndicators() {
  return asList(await request.get('/config/indicators')).filter(i => i.enabled !== false).map(i => {
    const type = i.type || i.indicator_type
    const schema = FIELD_SCHEMA[type] || []
    return { ...i, type, name: i.name || i.indicator_name, fields: Array.isArray(i.fields) && i.fields.every(f => typeof f === 'object') ? i.fields : schema }
  })
}
export const getThresholds = () => request.get('/config/thresholds')
