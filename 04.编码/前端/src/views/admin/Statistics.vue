<template><div class="ky-page" v-loading="loading"><div class="ky-page-header"><h2 class="ky-page-title">系统统计</h2><el-select style="width:180px" v-model="range" @change="load"><el-option label="近 24 小时" value="1d" /><el-option label="近 7 天" value="7d" /><el-option label="近 30 天" value="30d" /></el-select></div><el-alert v-if="error" type="error" :closable="false" :title="error" /><div class="ky-card"><p class="ky-sub">统计周期：{{ fmtDate(data.start_at || data.period_start || data.start) }} ～ {{ fmtDate(data.end_at || data.period_end || data.end) }}</p><p class="ky-sub">{{ data.statistic_basis }}</p><div class="stats-grid"><div v-for="s in summaries" :key="s.label" class="ky-stat"><div class="ky-stat__label">{{ s.label }}</div><div class="ky-stat__value">{{ s.value ?? '—' }}</div></div></div></div><div class="ky-card"><div class="ky-card__title">周期咨询与预警</div><TrendChart :dates="dates" :series="series" :height="360" /></div><div class="ky-card"><div class="ky-card__title">各模块实际数据总量</div><el-descriptions :column="3" border><el-descriptions-item v-for="(v,k) in data.module_totals || data.totals || {}" :key="k" :label="moduleLabels[k] || k">{{ v }}</el-descriptions-item></el-descriptions></div></div></template>
<script setup>
import {ref,computed,onMounted} from 'vue'
import {adminStatistics} from '@/api'
import {fmtDate,asList} from '@/utils/format'
import TrendChart from '@/components/common/TrendChart.vue'
const range=ref('7d'),data=ref({}),loading=ref(false),error=ref('')
const summaries=computed(()=>[{label:'用户总数',value:data.value.total_users??data.value.user_count??data.value.users},{label:'周期新增用户',value:data.value.registered_users??data.value.new_users??data.value.registrations},{label:'周期活跃用户',value:data.value.active_users},{label:'周期咨询次数',value:data.value.consultations??data.value.consult_count??data.value.consultation_count},{label:'周期预警次数',value:data.value.warnings??data.value.alert_count??data.value.warning_count},{label:'周期待处理',value:data.value.pending??data.value.pending_warnings},{label:'周期已处理',value:data.value.handled??data.value.handled_warnings??data.value.resolved}])
const chart=computed(()=>asList(data.value.chart||data.value.daily||data.value.daily_counts||data.value.trends)),dates=computed(()=>data.value.dates||data.value.chart?.dates||chart.value.map(d=>d.date))
const series=computed(()=>data.value.series||(data.value.chart?.dates ? [{name:'咨询',values:data.value.chart.consultations||[]},{name:'预警',values:data.value.chart.warnings||[]}] : [{name:'咨询',values:chart.value.map(d=>d.consultations??d.consult_count??d.chat_count??0)},{name:'预警',values:chart.value.map(d=>d.warnings??d.warning_count??d.alert_count??0)}]))
const moduleLabels={users:'用户账号',health_records:'健康指标',chat_sessions:'咨询会话',chat_messages:'咨询消息',knowledge_documents:'知识条目',knowledge_chunks:'知识分段',family_binds:'有效家属绑定',care_relations:'有效护工责任关系',profiles:'健康档案',records:'健康指标',warnings:'预警',sessions:'咨询会话',messages:'咨询消息',knowledge:'知识条目',bindings:'绑定关系',handles:'处理记录'}
async function load(){loading.value=true;error.value='';try{data.value=await adminStatistics(range.value)}catch(e){error.value=e.message}finally{loading.value=false}}
onMounted(load)
</script>


<style scoped>.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:16px}.stats-grid .ky-stat{box-shadow:none;border:1px solid var(--color-border-light)}</style>
