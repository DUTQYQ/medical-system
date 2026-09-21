<template>
  <div class="ky-page">
    <div class="ky-page-header">
      <h2 class="ky-page-title">健康趋势图</h2>
      <el-radio-group v-model="type" @change="load">
        <el-radio-button v-for="ind in indicators" :key="ind.type" :label="ind.type">{{ ind.name }}</el-radio-button>
      </el-radio-group>
    </div>

    <div class="ky-card">
      <div class="ky-card__title">{{ typeName }} 近 14 天趋势</div>
      <TrendChart :dates="dates" :series="series" :abnormal-indexes="abnormalIndexes" :unit="unit" @point-click="onPointClick" />
      <div class="ky-sub" style="margin-top: 8px">
        红点标记为异常值，点击可查看详情。{{ rangeHint }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getUser } from '@/utils/auth'
import { listProfiles, getIndicators, getThresholds, getTrend } from '@/api'
import TrendChart from '@/components/common/TrendChart.vue'

const user = getUser()
const indicators = ref([])
const thresholds = ref({})
const type = ref('BLOOD_PRESSURE')
const dates = ref([])
const series = ref([])
const abnormalIndexes = ref([])
const unit = ref('')
const profileId = ref(null)

const UNIT = { BLOOD_PRESSURE: 'mmHg', BLOOD_SUGAR: 'mmol/L', HEART_RATE: '次/分', SLEEP: '小时', STEP: '步' }
const NAME = { BLOOD_PRESSURE: '血压', BLOOD_SUGAR: '血糖', HEART_RATE: '心率', SLEEP: '睡眠', STEP: '步数' }
const typeName = computed(() => NAME[type.value] || '')

const rangeHint = computed(() => {
  const t = thresholds.value[type.value]
  if (!t) return ''
  if (type.value === 'BLOOD_PRESSURE') return `正常范围：收缩压 ${t.systolic.low}–${t.systolic.high}、舒张压 ${t.diastolic.low}–${t.diastolic.high} mmHg`
  if (type.value === 'BLOOD_SUGAR') return `空腹正常 ${t.fasting.low}–${t.fasting.high} mmol/L`
  if (type.value === 'HEART_RATE') return `正常 ${t.low}–${t.high} 次/分`
  if (type.value === 'SLEEP') return `建议 ${t.low}–${t.high} 小时`
  if (type.value === 'STEP') return `建议 ≥${t.low} 步`
  return ''
})

async function load() {
  if (!profileId.value) return
  try {
    const d = await getTrend({ profile_id: profileId.value, type: type.value, days: 14 })
    dates.value = d.dates
    series.value = d.series
    abnormalIndexes.value = d.abnormalIndexes
    unit.value = UNIT[type.value] || ''
  } catch (e) {
    ElMessage.error(e.message)
  }
}

function onPointClick({ date }) {
  ElMessage.info(`${date} 存在异常值，可前往「通知中心」查看对应预警`)
}

onMounted(async () => {
  try {
    const [inds, ths, profiles] = await Promise.all([getIndicators(), getThresholds(), listProfiles(user.user_id, 'ELDER')])
    indicators.value = inds
    thresholds.value = ths
    if (profiles.length) profileId.value = profiles[0].profile_id
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  }
})
</script>
