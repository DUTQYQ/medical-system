<template>
  <div class="ky-page">
    <div class="ky-page-header">
      <h2 class="ky-page-title">个人健康参考</h2>
      <div style="display: flex; gap: 12px">
        <el-select v-if="profiles.length > 1" v-model="profileId" style="width: 160px">
          <el-option v-for="p in profiles" :key="p.profile_id" :label="p.name" :value="p.profile_id" />
        </el-select>
        <el-button @click="load">刷新</el-button>
      </div>
    </div>

    <el-alert type="info" :closable="false" title="采用院内默认或已审核的个体阈值。波动与本次之前 7 天的至少两条有效记录比较；结果仅供参考，不等于医疗诊断。" style="margin-bottom: 16px" />

    <el-alert v-if="error" type="error" :closable="false" :title="error" style="margin-bottom:16px" />
    <div v-loading="loading">
      <div v-for="item in items" :key="item.type" class="ky-card status-card">
        <div class="status-card__head">
          <span class="status-card__name">{{ item.name }}</span>
          <span class="status-card__unit">{{ item.unit }}</span>
          <StatusTag kind="judgement" :value="item.judgement" />
        </div>
        <div class="status-card__body">
          <div class="status-cell">
            <div class="status-cell__label">最近有效测量</div>
            <div class="status-cell__value">{{ valueText(item) }}<span v-if="item.measured_at" class="status-cell__time">{{ fmtTime(item.measured_at) }}</span></div>
          </div>
          <div class="status-cell">
            <div class="status-cell__label">当前有效参考范围</div>
            <div class="status-cell__value range-value">{{ normalRanges(item) }}</div>
          </div>
          <div class="status-cell">
            <div class="status-cell__label">风险等级</div>
            <div class="status-cell__value"><StatusTag v-if="item.risk_level!=null" kind="level" :value="item.risk_level" /><span v-else>—</span></div>
          </div>
          <div class="status-cell">
            <div class="status-cell__label">此前 7 天基线</div>
            <div class="status-cell__value"><div v-for="c in item.baseline_components" :key="c.key">{{ RANGE_LABEL[c.key] }}：{{ c.mean ?? '样本不足' }}<span class="status-cell__time"> 共 {{ c.count }} 条</span></div></div>
          </div>
          <div class="status-cell">
            <div class="status-cell__label">较基线波动</div>
            <div class="status-cell__value"><div v-for="c in item.baseline_components" :key="c.key">{{ RANGE_LABEL[c.key] }}：{{ c.ratio==null?'无法计算':(c.ratio*100).toFixed(1)+'%' }}</div></div>
          </div>
          <div class="status-cell">
            <div class="status-cell__label">波动标记</div>
            <div class="status-cell__value"><StatusTag v-if="item.fluctuation_flag!=null" kind="fluctuation" :value="item.fluctuation_flag" /><span v-else>数据不足、待更新或未启用提醒</span></div>
          </div>
        </div>
      </div>
      <div v-if="!loading && !items.length" class="ky-empty">暂无健康判断数据</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listProfiles, getHealthStatus } from '@/api'
import StatusTag from '@/components/common/StatusTag.vue'

const RANGE_LABEL = { BLOOD_PRESSURE_SYSTOLIC: '收缩压', BLOOD_PRESSURE_DIASTOLIC: '舒张压', BLOOD_SUGAR: '血糖', HEART_RATE: '心率', SLEEP_HOURS: '睡眠时长', STEP_COUNT: '步数' }

const profiles = ref([])
const profileId = ref(null)
const items = ref([])
const loading = ref(false), error=ref('')
const route=useRoute(),router=useRouter()
let requestVersion=0
watch(profileId,load,{flush:'sync'})
onBeforeUnmount(()=>{requestVersion++})

function valueText(item) {
  const v = item.latest
  if (!v) return '未记录'
  if (item.type === 'BLOOD_PRESSURE') return `${v.systolic}/${v.diastolic}`
  if (item.type === 'SLEEP') return `${v.hours} 小时 · 质量 ${v.quality}`
  return `${v.value ?? v.count}`
}

function normalRanges(item) {
  if (!item.normal_ranges?.length) return '—'
  return item.normal_ranges.map(r => `${RANGE_LABEL[r.key] || r.key}: ${r.enabled?r.range || '未配置':'检测已停用'}（${r.source==='PERSONAL'?'已审核个体':'院内默认'}）`).join('　')
}

function fmtTime(iso) {
  const d = new Date(String(iso).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function load() {
  const id=profileId.value,ticket=++requestVersion
  items.value=[];error.value=''
  if(!id){loading.value=false;return;}
  loading.value=true
  try {
    const response=await getHealthStatus(id)
    if(ticket===requestVersion&&id===profileId.value)items.value=response
  } catch(e) {if(ticket===requestVersion&&id===profileId.value)error.value=e.message}
  finally {if(ticket===requestVersion)loading.value=false}
}
async function initialize(){
  loading.value=true
  try{profiles.value=await listProfiles();const requested=Number(route.query.profile_id);profileId.value=profiles.value.find(p=>p.profile_id===requested)?.profile_id || profiles.value[0]?.profile_id || null;if(!profileId.value)loading.value=false}
  catch(e){error.value=e.message;loading.value=false}
}
onMounted(initialize)
</script>

<style scoped>
.status-card {
  margin-bottom: 14px;
}
.status-card__head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
}
.status-card__name {
  font-size: 20px;
  font-weight: 700;
}
.status-card__unit {
  color: var(--color-text-secondary);
  font-size: 14px;
}
.status-card__body {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
}
.status-cell__label {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}
.status-cell__value {
  font-size: 18px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.status-cell__time {
  font-size: 13px;
  font-weight: 400;
  color: var(--color-text-secondary);
}
.range-value {
  font-size: 15px;
  font-weight: 500;
}
</style>
