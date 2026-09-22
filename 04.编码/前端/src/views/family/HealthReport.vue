<template>
  <div class="ky-page" style="max-width: 860px">
    <div class="ky-page-header">
      <h2 class="ky-page-title">健康日报 / 周报</h2>
    </div>

    <div class="ky-card">
      <div class="ky-card__title">选择报告对象与周期</div>
      <div style="display: flex; gap: 16px; flex-wrap: wrap">
        <el-select v-model="elderId" style="width: 200px" placeholder="选择老人">
          <el-option v-for="e in elders" :key="e.profile_id" :label="e.profile.name" :value="e.profile_id" />
        </el-select>
        <el-radio-group v-model="period">
          <el-radio-button label="DAY">日报</el-radio-button>
          <el-radio-button label="WEEK">周报</el-radio-button>
        </el-radio-group>
        <el-button type="primary" @click="loadReport">生成报告</el-button>
      </div>
    </div>

    <template v-if="report">
      <div class="ky-card">
        <div class="ky-card__title" style="display: flex; justify-content: space-between; align-items: center">
          <span>{{ report.title }}</span>
          <el-tag type="primary">{{ report.period_text }}</el-tag>
        </div>

        <div class="report-section">
          <div class="report-section__title">📊 指标概览</div>
          <div class="report-metrics">
            <div v-for="m in report.metrics" :key="m.label" class="report-metric">
              <div class="report-metric__label">{{ m.label }}</div>
              <div class="report-metric__value" :style="{ color: m.abnormal ? 'var(--color-danger)' : 'inherit' }">
                {{ m.value }}<span class="unit">{{ m.unit }}</span>
              </div>
              <el-tag v-if="m.abnormal" size="small" type="danger">异常</el-tag>
              <el-tag v-else size="small" type="success">正常</el-tag>
            </div>
          </div>
        </div>

        <div class="report-section">
          <div class="report-section__title">⚠️ 异常情况</div>
          <p v-if="report.anomalies.length" class="report-text">
            {{ report.anomalies.join('；') }}。
          </p>
          <p v-else class="report-text" style="color: var(--color-success)">本周期各项指标均处于正常范围，继续保持。</p>
        </div>

        <div class="report-section">
          <div class="report-section__title">🤖 AI 健康建议</div>
          <p class="report-text">{{ report.advice }}</p>
          <DisclaimerFooter />
        </div>
      </div>
    </template>
    <div v-else-if="!elders.length" class="ky-card">
      <div class="ky-empty">请先绑定老人后查看健康报告</div>
    </div>
    <div v-else class="ky-card">
      <div class="ky-empty">选择老人与周期后点击「生成报告」</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getUser } from '@/utils/auth'
import { listElders, getLatestIndicators, getElderOverview, getTrend } from '@/api'
import DisclaimerFooter from '@/components/common/DisclaimerFooter.vue'

const user = getUser()
const elders = ref([])
const elderId = ref(null)
const period = ref('DAY')
const report = ref(null)

function bpText(lat) {
  const b = lat?.BLOOD_PRESSURE
  return b ? `${b.values.systolic}/${b.values.diastolic}` : '—'
}

async function loadReport() {
  if (!elderId.value) return ElMessage.warning('请选择老人')
  try {
    const [lat, overview, trend] = await Promise.all([
      getLatestIndicators(elderId.value),
      getElderOverview(elderId.value, user.user_id),
      getTrend({ profile_id: elderId.value, type: 'BLOOD_PRESSURE', days: period.value === 'DAY' ? 7 : 14 }),
    ])
    const name = overview.profile.name
    const metrics = [
      { label: '血压', value: bpText(lat), unit: 'mmHg', abnormal: !!lat.BLOOD_PRESSURE?.is_abnormal },
      { label: '血糖', value: lat.BLOOD_SUGAR?.values.value ?? '—', unit: 'mmol/L', abnormal: !!lat.BLOOD_SUGAR?.is_abnormal },
      { label: '心率', value: lat.HEART_RATE?.values.value ?? '—', unit: '次/分', abnormal: !!lat.HEART_RATE?.is_abnormal },
      { label: '睡眠', value: lat.SLEEP?.values.hours ?? '—', unit: '小时', abnormal: !!lat.SLEEP?.is_abnormal },
      { label: '步数', value: lat.STEP?.values.count ?? '—', unit: '步', abnormal: !!lat.STEP?.is_abnormal },
    ]
    const anomalies = metrics.filter((m) => m.abnormal).map((m) => `${m.label}异常（${m.value}${m.unit}）`)

    report.value = {
      title: `${name}健康${period.value === 'DAY' ? '日报' : '周报'}`,
      period_text: period.value === 'DAY' ? '日报' : '周报',
      metrics,
      anomalies,
      advice: `结合${name}本周期（${period.value === 'DAY' ? '近 24 小时' : '近一周'}）的数据，${
        anomalies.length
          ? `存在 ${anomalies.length} 项异常指标，建议保持关注并复测；若持续异常或伴不适，请及时就医。`
          : '各项指标整体平稳，建议继续保持规律作息、均衡饮食与适量运动。'
      }`,
    }
  } catch (e) {
    ElMessage.error(e.message)
  }
}

onMounted(async () => {
  try {
    elders.value = await listElders(user.user_id)
    if (elders.value.length) elderId.value = elders.value[0].profile_id
  } catch (e) {
    ElMessage.error(e.message)
  }
})
</script>

<style scoped>
.report-section {
  margin-top: 20px;
}
.report-section__title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 10px;
}
.report-metrics {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 12px;
}
.report-metric {
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  padding: 14px;
  text-align: center;
}
.report-metric__label {
  color: var(--color-text-secondary);
  font-size: 14px;
}
.report-metric__value {
  font-size: 22px;
  font-weight: 600;
  margin: 6px 0;
}
.report-text {
  font-size: var(--fs-body);
  line-height: 1.9;
  color: var(--color-text-primary);
}
</style>
