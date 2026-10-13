<template>
  <div class="ky-page">
    <div class="ky-page-header">
      <h2 class="ky-page-title">个人健康判断</h2>
      <div style="display: flex; gap: 12px">
        <el-select v-if="profiles.length > 1" v-model="profileId" style="width: 160px" @change="load">
          <el-option v-for="p in profiles" :key="p.profile_id" :label="p.name" :value="p.profile_id" />
        </el-select>
        <el-button @click="load">刷新</el-button>
      </div>
    </div>

    <el-alert type="info" :closable="false" title="健康判断结合「我的正常范围（随年龄/个人情况调整）」与「个人近 7 天基线波动」，同一数值对不同人可能得出不同结论。" style="margin-bottom: 16px" />

    <div v-loading="loading">
      <div v-for="item in items" :key="item.type" class="ky-card status-card">
        <div class="status-card__head">
          <span class="status-card__name">{{ item.name }}</span>
          <span class="status-card__unit">{{ item.unit }}</span>
          <StatusTag kind="judgement" :value="item.judgement" />
        </div>
        <div class="status-card__body">
          <div class="status-cell">
            <div class="status-cell__label">本次测量</div>
            <div class="status-cell__value">{{ valueText(item) }}<span v-if="item.measured_at" class="status-cell__time">{{ fmtTime(item.measured_at) }}</span></div>
          </div>
          <div class="status-cell">
            <div class="status-cell__label">我的正常范围</div>
            <div class="status-cell__value range-value">{{ normalRanges(item) }}</div>
          </div>
          <div class="status-cell">
            <div class="status-cell__label">风险等级</div>
            <div class="status-cell__value"><StatusTag v-if="item.latest" kind="level" :value="item.risk_level" /><span v-else>—</span></div>
          </div>
          <div class="status-cell">
            <div class="status-cell__label">个人基线（近 7 天）</div>
            <div class="status-cell__value">{{ item.baseline_mean ?? '—' }}<span v-if="item.baseline_mean" class="status-cell__time">共 {{ item.baseline_count }} 条</span></div>
          </div>
          <div class="status-cell">
            <div class="status-cell__label">较基线波动</div>
            <div class="status-cell__value"><template v-if="item.fluctuation_ratio !== null && item.fluctuation_ratio !== undefined">{{ (item.fluctuation_ratio * 100).toFixed(0) }}%</template><span v-else>—</span></div>
          </div>
          <div class="status-cell">
            <div class="status-cell__label">波动标记</div>
            <div class="status-cell__value"><StatusTag v-if="item.latest" kind="fluctuation" :value="!!item.fluctuation_flag" /><span v-else>—</span></div>
          </div>
        </div>
      </div>
      <div v-if="!loading && !items.length" class="ky-empty">暂无健康判断数据</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listProfiles, getHealthStatus } from '@/api'
import StatusTag from '@/components/common/StatusTag.vue'

const RANGE_LABEL = { BLOOD_PRESSURE_SYSTOLIC: '收缩压', BLOOD_PRESSURE_DIASTOLIC: '舒张压', BLOOD_SUGAR: '血糖', HEART_RATE: '心率', SLEEP_HOURS: '睡眠时长', STEP_COUNT: '步数' }

const profiles = ref([])
const profileId = ref(null)
const items = ref([])
const loading = ref(false)

function valueText(item) {
  const v = item.latest
  if (!v) return '未记录'
  if (item.type === 'BLOOD_PRESSURE') return `${v.systolic}/${v.diastolic}`
  if (item.type === 'SLEEP') return `${v.hours} 小时 · 质量 ${v.quality}`
  return `${v.value ?? v.count}`
}

function normalRanges(item) {
  if (!item.normal_ranges?.length) return '—'
  return item.normal_ranges.map(r => `${RANGE_LABEL[r.key] || r.key}: ${r.range || '未配置'}`).join('　')
}

function fmtTime(iso) {
  const d = new Date(String(iso).replace(' ', 'T'))
  if (Number.isNaN(d.getTime())) return ''
  return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function load() {
  loading.value = true
  try {
    profiles.value = await listProfiles()
    if (!profiles.value.length) { items.value = []; return }
    if (!profiles.value.some(p => p.profile_id === profileId.value)) profileId.value = profiles.value[0].profile_id
    items.value = await getHealthStatus(profileId.value)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

onMounted(load)
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
