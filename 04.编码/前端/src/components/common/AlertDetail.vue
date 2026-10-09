<template>
<div class="ky-page" v-loading="loading"><div class="ky-page-header"><h2 class="ky-page-title">预警详情</h2><el-button @click="load">刷新</el-button></div>
<el-alert v-if="error" type="error" :closable="false" :title="error" />
<template v-if="alert">
<div class="ky-card"><div class="ky-card__title">{{ alert.title }}</div><el-descriptions :column="2" border>
<el-descriptions-item label="老人">{{ alert.elder_name || alert.profile?.name || '—' }}</el-descriptions-item><el-descriptions-item label="指标">{{ NAME[alert.type] || alert.type }}</el-descriptions-item>
<el-descriptions-item label="异常值">{{ alert.value_text }} {{ alert.unit }}</el-descriptions-item><el-descriptions-item label="风险等级"><StatusTag kind="level" :value="alert.level" /></el-descriptions-item>
<el-descriptions-item label="处理状态"><StatusTag :value="alert.status" /></el-descriptions-item><el-descriptions-item label="我的已读状态"><StatusTag kind="read" :value="alert.my_read_status" /></el-descriptions-item>
<el-descriptions-item label="触发来源">{{ sources[alert.trigger_source] || alert.trigger_source }}</el-descriptions-item><el-descriptions-item label="触发时间">{{ fmtDate(alert.created_at) }}</el-descriptions-item>
</el-descriptions><p v-if="hint" class="ky-sub">当前后台参考范围：{{ hint }}。历史预警保留触发当时的风险结果。</p><p class="ky-sub">打开详情仅标记本人已读。处理结论与已读状态独立保存。</p></div>
<div class="ky-card"><div class="ky-card__title">AI 分析摘要 <StatusTag kind="summary" :value="alert.summary_status" /></div><p v-if="alert.ai_summary" style="white-space:pre-wrap;line-height:1.8">{{ alert.ai_summary }}</p><p v-else class="ky-sub">{{ summaryHint }}</p><el-button v-if="alert.summary_status==='FAILED'" :loading="retrying" @click="retry">重试摘要</el-button></div>
<div class="ky-card"><div class="ky-card__title">近 7 天指标趋势</div><el-alert v-if="trendError" type="warning" :closable="false" title="趋势暂时无法加载，请稍后刷新；仍可处理预警。" /><TrendChart v-else :dates="trend.dates" :series="trend.series" :abnormal-indexes="trend.abnormalIndexes" :unit="trend.unit" /></div>
<div class="ky-card"><div class="ky-card__title">处理记录</div><el-empty v-if="!alert.handles?.length" description="暂无处理记录" /><el-timeline v-else><el-timeline-item v-for="h in alert.handles" :key="h.handle_id" :timestamp="fmtDate(h.created_at || h.handled_at)"><strong>{{ h.handler_name }} · {{ actions[h.action] || h.action }}</strong><p>{{ h.result }}</p></el-timeline-item></el-timeline></div>
<div v-if="canHandle && ['PENDING','PROCESSING'].includes(alert.status)" class="ky-card"><div class="ky-card__title">处理预警</div><el-form label-position="top"><el-form-item label="处理方式"><el-select v-model="form.action"><el-option v-for="(label,value) in actions" :key="value" :label="label" :value="value" /></el-select></el-form-item><el-form-item label="处理结论"><el-input v-model="form.result" type="textarea" :rows="3" maxlength="500" show-word-limit placeholder="填写实际处理结果，保留联系、安排或观察记录" /></el-form-item><el-button type="primary" :loading="saving" @click="handle">提交处理结论</el-button><el-button v-if="alert.status==='PENDING'" :disabled="saving" @click="change('PROCESSING')">开始跟进</el-button><el-button :disabled="saving" @click="change('IGNORED')">忽略预警</el-button></el-form></div>
<el-alert v-else-if="!canHandle" type="info" :closable="false" title="您可查看预警及处理记录；家属、负责护工或管理员提交处理结论。" />
</template></div>
</template>
<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUser } from '@/utils/auth'
import { NAME, TYPES, fmtDate, thresholdHint } from '@/utils/format'
import { getAlert, handleAlert, setAlertStatus, retrySummary, getTrend, getThresholds } from '@/api'
import StatusTag from './StatusTag.vue'
import TrendChart from './TrendChart.vue'
const route=useRoute(), user=getUser(), alert=ref(null), trend=ref({dates:[],series:[],abnormalIndexes:[]}), error=ref(''), trendError=ref(false), loading=ref(false), saving=ref(false), retrying=ref(false)
const thresholds=ref([]),hint=computed(()=>thresholdHint(thresholds.value,alert.value?.type))
const canHandle=['FAMILY','CARE','ADMIN'].includes(user?.role)
const form=ref({action:'CONTACTED',result:''})
const actions={CONTACTED:'已联系',ARRANGED_VISIT:'安排探访',SENT_HOSPITAL:'送医',OBSERVE:'持续观察'}
const sources={DATA_INPUT:'指标录入',AI_CHAT:'健康咨询',MANUAL:'人工创建'}
const summaryHint=computed(()=>({PENDING:'AI 摘要生成中，原始预警与处理功能已可使用。',FAILED:'AI 摘要失败，可查看原始指标并直接处理预警。',SKIPPED:'本条预警未生成 AI 摘要。'}[alert.value?.summary_status]||'暂无 AI 摘要。'))
async function load(quiet=false) {
  if(!quiet)loading.value=true
  error.value=''
  try {
    alert.value=await getAlert({warning_id:route.params.id})
    alert.value.my_read_status=true
    try{thresholds.value=await getThresholds();if(TYPES.includes(alert.value.type))trend.value=await getTrend({profile_id:alert.value.profile_id,type:alert.value.type,days:7});trendError.value=false}catch{trendError.value=true}
  } catch(e){error.value=e.message} finally{loading.value=false}
}
async function handle(){if(!form.value.result.trim())return ElMessage.warning('请填写实际处理结论');saving.value=true;try{await handleAlert({warning_id:route.params.id,...form.value});form.value.result='';await load(true);ElMessage.success('处理结论已保存')}catch(e){ElMessage.error(e.message)}finally{saving.value=false}}
async function change(status){try{if(status==='IGNORED')await ElMessageBox.confirm('确定忽略此预警？操作将保留记录。','确认忽略',{type:'warning'});await setAlertStatus(route.params.id,status);await load(true)}catch(e){if(e!=='cancel'&&e!=='close')ElMessage.error(e.message)}}
async function retry(){retrying.value=true;try{await retrySummary(route.params.id);await load(true);ElMessage.success('已提交摘要重试，请等待状态更新')}catch(e){ElMessage.error(e.message)}finally{retrying.value=false}}
let timer
onMounted(()=>{load();timer=setInterval(()=>{if(alert.value?.summary_status==='PENDING')load(true)},10000)})
onBeforeUnmount(()=>clearInterval(timer))
</script>
