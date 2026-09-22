<template>
  <div class="ky-page">
    <div class="ky-page-header">
      <div style="display: flex; align-items: center; gap: 12px">
        <el-button @click="$router.back()">← 返回</el-button>
        <h2 class="ky-page-title">预警详情</h2>
      </div>
      <div v-if="alert" style="display: flex; gap: 8px">
        <StatusTag kind="level" :value="alert.level" />
        <StatusTag kind="status" :value="alert.status" />
      </div>
    </div>

    <template v-if="alert">
      <!-- 预警基本信息 -->
      <div class="ky-card">
        <div class="ky-card__title">{{ alert.title }}</div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="预警对象">{{ alert.profile?.name || '—' }}</el-descriptions-item>
          <el-descriptions-item label="预警指标">{{ typeName }}（{{ alert.type }}）</el-descriptions-item>
          <el-descriptions-item label="异常值">
            <span class="alert-value">{{ alert.value_text }}</span>
          </el-descriptions-item>
          <el-descriptions-item label="预警等级">{{ alert.level_text }}</el-descriptions-item>
          <el-descriptions-item label="触发方式">{{ triggerText }}</el-descriptions-item>
          <el-descriptions-item label="预警时间">{{ fmtDate(alert.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="处理状态">{{ statusText }}</el-descriptions-item>
          <el-descriptions-item label="AI 摘要">
            <StatusTag kind="summary" :value="alert.summary_status" />
          </el-descriptions-item>
        </el-descriptions>
      </div>

      <!-- AI 摘要 -->
      <div class="ky-card">
        <div class="ky-card__title" style="display: flex; align-items: center; justify-content: space-between">
          <span>AI 健康分析摘要</span>
          <el-button v-if="alert.summary_status === 'FAILED'" type="warning" size="small" @click="onRetrySummary">
            重新生成摘要
          </el-button>
        </div>
        <template v-if="alert.summary_status === 'COMPLETED'">
          <p class="ai-summary">{{ alert.ai_summary }}</p>
          <DisclaimerFooter />
        </template>
        <div v-else-if="alert.summary_status === 'FAILED'" class="ky-empty">
          AI 摘要生成失败（服务繁忙或超时）。您可点击右上角「重新生成摘要」重试，或直接查看指标趋势自行判断。
        </div>
        <div v-else class="ky-empty">AI 摘要生成中，请稍后刷新查看…</div>
      </div>

      <!-- 近期趋势 -->
      <div class="ky-card">
        <div class="ky-card__title">近期指标趋势（近 14 天，红点标记为异常）</div>
        <TrendChart
          :dates="trend.dates"
          :series="trend.series"
          :abnormal-indexes="trend.abnormalIndexes"
          :unit="trend.unit"
          @point-click="() => {}"
        />
      </div>

      <!-- 处理记录 -->
      <div class="ky-card">
        <div class="ky-card__title">处理记录</div>
        <div v-if="alert.handles && alert.handles.length" class="ky-timeline">
          <div v-for="h in alert.handles" :key="h.handle_id" class="ky-timeline__item">
            <div><strong>{{ h.handler_name }}</strong>（{{ h.action }}）</div>
            <div class="ky-sub">{{ h.result }} · {{ fmtDate(h.created_at) }}</div>
          </div>
        </div>
        <div v-else class="ky-empty">暂无处理记录</div>
      </div>

      <!-- 我要处理 -->
      <div class="ky-card">
        <div class="ky-card__title">我要处理</div>
        <el-form label-position="top">
          <el-form-item label="处理动作">
            <el-input v-model="handleForm.action" type="textarea" :rows="2" placeholder="如：已提醒老人按时服药 / 已陪同就医" />
          </el-form-item>
          <el-form-item label="处理结果">
            <el-radio-group v-model="handleForm.result">
              <el-radio-button label="已知晓" />
              <el-radio-button label="跟进中" />
              <el-radio-button label="已处理" />
              <el-radio-button label="已就医" />
            </el-radio-group>
          </el-form-item>
          <el-button type="primary" size="large" @click="onHandle">提交处理</el-button>
        </el-form>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getUser } from '@/utils/auth'
import { fmtDate } from '@/api/mock'
import { getAlert, updateRead, handleAlert, retrySummary, getTrend } from '@/api'
import StatusTag from './StatusTag.vue'
import TrendChart from './TrendChart.vue'
import DisclaimerFooter from './DisclaimerFooter.vue'

const route = useRoute()
const user = getUser()
const warningId = route.params.id

const alert = ref(null)
const trend = ref({ dates: [], series: [], abnormalIndexes: [], unit: '' })
const handleForm = ref({ action: '', result: '跟进中' })

const TYPE_NAME = { BLOOD_PRESSURE: '血压', BLOOD_SUGAR: '血糖', HEART_RATE: '心率', SLEEP: '睡眠', STEP: '步数' }
const UNIT = { BLOOD_PRESSURE: 'mmHg', BLOOD_SUGAR: 'mmol/L', HEART_RATE: '次/分', SLEEP: '小时', STEP: '步' }

const typeName = computed(() => TYPE_NAME[alert.value?.type] || alert.value?.type || '')
const triggerText = computed(() => (alert.value?.trigger_source === 'AI' ? 'AI 自动识别' : '指标录入触发'))
const statusText = computed(() => ({ PENDING: '待处理', PROCESSING: '处理中', RESOLVED: '已处理' }[alert.value?.status] || '—'))

async function load() {
  try {
    alert.value = await getAlert({ warning_id: warningId, user_id: user.user_id })
    // 进入即标记已读
    if (!alert.value.my_read_status) {
      await updateRead(warningId, user.user_id)
      alert.value.my_read_status = true
    }
    await loadTrend(alert.value.profile_id, alert.value.type)
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function loadTrend(profileId, type) {
  try {
    const d = await getTrend({ profile_id: profileId, type, days: 14 })
    trend.value = { ...d, unit: UNIT[type] || '' }
  } catch (e) {
    /* 趋势加载失败不影响主信息 */
  }
}

async function onRetrySummary() {
  try {
    const d = await retrySummary(warningId)
    alert.value.summary_status = d.summary_status
    alert.value.ai_summary = d.ai_summary
    ElMessage.success('摘要已重新生成')
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function onHandle() {
  if (!handleForm.value.action.trim()) {
    ElMessage.warning('请填写处理动作')
    return
  }
  try {
    const updated = await handleAlert({
      warning_id: warningId,
      user_id: user.user_id,
      handler_name: user.name,
      action: handleForm.value.action,
      result: handleForm.value.result,
    })
    alert.value.status = updated.status
    alert.value.handles = updated.handles
    handleForm.value.action = ''
    ElMessage.success('处理已提交')
  } catch (e) {
    ElMessage.error(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.alert-value {
  font-size: 22px;
  font-weight: 600;
  color: var(--color-danger);
}
.ai-summary {
  font-size: var(--fs-body);
  line-height: 1.9;
  color: var(--color-text-primary);
  white-space: pre-wrap;
}
</style>
