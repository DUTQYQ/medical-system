export const TYPES = ['BLOOD_PRESSURE', 'BLOOD_SUGAR', 'HEART_RATE', 'SLEEP', 'STEP']
export const NAME = { BLOOD_PRESSURE: '血压', BLOOD_SUGAR: '血糖', HEART_RATE: '心率', SLEEP: '睡眠', STEP: '步数' }
export const UNIT = { BLOOD_PRESSURE: 'mmHg', BLOOD_SUGAR: 'mmol/L', HEART_RATE: '次/分', SLEEP: '小时', STEP: '步' }
// 仅值结构定义；所有业务阈值由后端 sys_config 返回。
export const FIELD_SCHEMA = {
  BLOOD_PRESSURE: [{ key: 'systolic', label: '收缩压', unit: 'mmHg' }, { key: 'diastolic', label: '舒张压', unit: 'mmHg' }],
  BLOOD_SUGAR: [{ key: 'value', label: '血糖', unit: 'mmol/L', step: 0.1 }],
  HEART_RATE: [{ key: 'value', label: '心率', unit: '次/分' }],
  SLEEP: [{ key: 'hours', label: '睡眠时长', unit: '小时', step: 0.5 }, { key: 'quality', label: '睡眠质量（1差～5好）', options: [1, 2, 3, 4, 5] }],
  STEP: [{ key: 'count', label: '步数', unit: '步' }],
}
export const asList = d => Array.isArray(d) ? d : d?.list || d?.items || []
export function fmtDate(v) {
  if (!v) return '—'
  const d = new Date(String(v).replace(' ', 'T'))
  return Number.isNaN(d.getTime()) ? String(v) : d.toLocaleString('zh-CN', { hour12: false })
}
export function todayOnly() { const d = new Date(), pad = n => String(n).padStart(2, '0'); return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}` }
export function measuredNow() {
  const d = new Date(), pad = n => String(n).padStart(2, '0')
  return `${todayOnly()} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
export function thresholdHint(thresholds, type) {
  const list = asList(thresholds)
  if (list.length) return list.filter(t => (t.indicator || t.type || '').startsWith(type)).map(t => `${({BLOOD_PRESSURE_SYSTOLIC:'收缩压',BLOOD_PRESSURE_DIASTOLIC:'舒张压',BLOOD_SUGAR:'血糖',HEART_RATE:'心率',SLEEP_HOURS:'睡眠时长',STEP_COUNT:'步数'})[t.indicator] || t.indicator_name || t.indicator}: ${t.level0_range || '以后台配置为准'} ${t.unit || ''}`).join('；')
  const t = thresholds?.[type]
  if (!t) return ''
  if (t.level0_range) return t.level0_range
  return Object.entries(t).map(([key, r]) => `${({ systolic: '收缩压', diastolic: '舒张压', fasting: '空腹', postprandial: '餐后' })[key] || key}: ${r?.low ?? r?.min ?? ''}～${r?.high ?? r?.max ?? ''}`).join('；')
}
export function recordText(record) {
  const v = record.values || {}
  return record.type === 'BLOOD_PRESSURE' ? `${v.systolic}/${v.diastolic}` : record.type === 'SLEEP' ? `${v.hours} 小时 · 质量${v.quality ?? '—'}` : record.type === 'STEP' ? `${v.count}` : `${v.value}`
}
