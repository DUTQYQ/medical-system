<template>
<div class="ky-page" style="max-width:760px" v-loading="loading">
  <div class="ky-page-header"><h2 class="ky-page-title">健康指标录入</h2></div>
  <el-alert v-if="error" type="error" :closable="false" :title="error" style="margin-bottom:16px"><el-button @click="load">重新加载</el-button></el-alert>
  <div v-if="!loading && !profiles.length && !error" class="ky-card ky-empty">暂无可管理的健康档案。老人请先创建档案；家属请等待绑定生效。</div>
  <div v-if="profiles.length" class="ky-card">
    <el-form label-position="top">
      <el-form-item label="健康档案"><el-select v-model="profileId" :disabled="!!props.fixedProfileId" style="width:100%"><el-option v-for="p in profiles" :key="p.profile_id" :label="p.name" :value="p.profile_id" /></el-select></el-form-item>
      <el-form-item label="指标类型"><el-radio-group v-model="type" @change="reset"><el-radio-button v-for="i in indicators" :key="i.type" :label="i.type">{{ i.name }}</el-radio-button></el-radio-group></el-form-item>
      <el-alert v-if="hint" type="info" :closable="false" :title="'当前档案参考范围：' + hint" style="margin-bottom:16px" />
      <el-button v-if="profileId" link @click="$router.push('/'+route.meta.scope+'/personal-thresholds?profile_id='+profileId)">查看个人健康阈值与审核记录</el-button>
      <el-form-item v-for="f in current?.fields || []" :key="f.key" :label="f.label + (f.unit ? '（' + f.unit + '）' : '')">
        <el-select v-if="f.options" v-model="values[f.key]" style="width:100%"><el-option v-for="o in f.options" :key="o.value ?? o" :label="String(o.label ?? o)" :value="o.value ?? o" /></el-select>
        <el-input-number v-else v-model="values[f.key]" :step="f.step || (f.key === 'hours' ? .5 : type === 'BLOOD_SUGAR' ? .1 : 1)" :min="current?.ranges?.[f.key]?.[0] ?? 0" :max="current?.ranges?.[f.key]?.[1] ?? (f.key==='hours'?24:99999999.99)" style="width:100%" />
      </el-form-item>
      <el-form-item label="测量时间"><el-date-picker v-model="measuredAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" /></el-form-item>
      <el-form-item label="备注（可选）"><el-input v-model="remark" maxlength="200" /></el-form-item>
      <el-button type="primary" size="large" :disabled="!current || !profileId" :loading="saving" @click="save">保存记录</el-button>
    </el-form>
  </div>
</div>
</template>
<script setup>
import { ref, reactive, computed, onMounted, watch, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listProfiles, getIndicators, getPersonalThresholds, addRecord } from '@/api'
import { measuredNow, thresholdHint } from '@/utils/format'
const props = defineProps({ fixedProfileId: { type: [Number,String], default: null } })
const emit = defineEmits(['saved'])
const route = useRoute(), profiles = ref([]), profileId = ref(null), indicators = ref([]), thresholds = ref({}), loading = ref(false), saving = ref(false), error = ref('')
const type = ref('BLOOD_PRESSURE'), values = reactive({}), measuredAt = ref(measuredNow()), remark = ref('')
const current = computed(() => indicators.value.find(i => i.type === type.value))
const hint = computed(() => thresholdHint(thresholds.value, type.value))
let viewVersion=0,thresholdVersion=0
function profileChanged(){viewVersion++;reset();remark.value='';measuredAt.value=measuredNow();loadThresholds()}
watch(profileId,profileChanged,{flush:'sync'})
watch(()=>props.fixedProfileId,id=>{if(!id)return;profileId.value=profiles.value.find(p=>p.profile_id===Number(id))?.profile_id || null},{flush:'sync'})
onBeforeUnmount(()=>{viewVersion++;thresholdVersion++})
function reset() { Object.keys(values).forEach(k => delete values[k]); if (type.value === 'SLEEP') values.quality = 3 }
async function load() {
  loading.value = true; error.value = ''
  try {
    const [p, i] = await Promise.all([listProfiles(), getIndicators()])
    profiles.value = p; indicators.value = i
    const requested = Number(props.fixedProfileId || route.query.profile_id)
    profileId.value = p.find(x => x.profile_id === requested)?.profile_id || (props.fixedProfileId?null:p[0]?.profile_id)
    await loadThresholds()
    if (!i.some(x => x.type === type.value)) type.value = i[0]?.type
    reset()
  } catch (e) { error.value = e.message } finally { loading.value = false }
}
async function loadThresholds(){const id=profileId.value,version=viewVersion,ticket=++thresholdVersion;thresholds.value=[];if(!id)return;try{const data=await getPersonalThresholds(id);if(profileId.value===id&&version===viewVersion&&ticket===thresholdVersion)thresholds.value=data.rules || []}catch(e){if(profileId.value===id&&version===viewVersion&&ticket===thresholdVersion)error.value=e.message}}
function validateInput(){
  if(!profileId.value)return '请选择可管理的健康档案'
  for(const f of current.value.fields){
    const value=values[f.key]
    if(value==null||value==='')return '请填写'+f.label
    if(typeof value!=='number'||!Number.isFinite(value)||value<0||value>99999999.99)return f.label+'须为可记录的有限数字'
    if(current.value.integer&&!Number.isInteger(value))return f.label+'须为整数'
    const limits=current.value.ranges?.[f.key]
    if(limits&&(value<limits[0]||value>limits[1]))return f.label+'须在 '+limits[0]+' 至 '+limits[1]+' 范围内'
  }
  if(type.value==='BLOOD_PRESSURE'&&(values.systolic<=values.diastolic||values.diastolic<=0))return '血压须大于 0，收缩压须高于舒张压'
  if(['HEART_RATE','BLOOD_SUGAR'].includes(type.value)&&values.value<=0)return '指标值须大于 0'
  if(type.value==='SLEEP'&&(values.hours>24||!Number.isInteger(values.quality)||values.quality<1||values.quality>5))return '睡眠时长为 0 至 24 小时，质量为 1 至 5 整数'
  if(['BLOOD_SUGAR','SLEEP'].includes(type.value)){const value=values[type.value==='SLEEP'?'hours':'value'];if(Math.round(value*100)/100!==value)return '指标最多保留两位小数'}
  const time=new Date(measuredAt.value)
  if(!measuredAt.value||Number.isNaN(time.getTime()))return '请选择有效的测量时间'
  if(time>new Date())return '测量时间不能在未来'
  return ''
}
async function save() {
  if (saving.value || !current.value) return
  const message=validateInput();if(message)return ElMessage.warning(message)
  const id=profileId.value,version=viewVersion,indicatorType=type.value
  saving.value = true
  try {
    const v = Object.fromEntries(current.value.fields.map(f => [f.key, values[f.key]]))
    const r = await addRecord({ profile_id: id, type: indicatorType, values: v, measured_at: measuredAt.value, remark: remark.value })
    if(profileId.value!==id||viewVersion!==version||type.value!==indicatorType)return
    if (r.is_abnormal) await ElMessageBox.alert('记录已保存并触发健康预警。授权家属与负责护工可在站内查看并处理。请关注异常数据，必要时就医。', '指标异常', { type: 'warning' })
    else ElMessage.success('记录已保存，未触发阈值预警')
    if(profileId.value!==id||viewVersion!==version||type.value!==indicatorType)return
    reset(); remark.value = ''; measuredAt.value = measuredNow(); emit('saved', {...r,profile_id:id})
  } catch (e) { ElMessage.error(e.message) } finally { saving.value = false }
}
onMounted(load)
</script>
