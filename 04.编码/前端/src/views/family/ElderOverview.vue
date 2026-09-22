<template>
  <div class="ky-page">
    <div class="ky-page-header">
      <div style="display: flex; align-items: center; gap: 12px">
        <el-button @click="$router.push('/family/home')">← 返回</el-button>
        <h2 class="ky-page-title">{{ overview.profile?.name || '老人' }} 的健康概况</h2>
        <el-tag v-if="overview.relation" type="primary">{{ overview.relation }}</el-tag>
      </div>
      <div style="display: flex; gap: 12px">
        <el-button @click="dialogVisible = true">✍️ 代录指标</el-button>
        <el-button type="primary" @click="$router.push('/family/ai')">🤖 代发起 AI 咨询</el-button>
        <el-button @click="$router.push('/family/report')">📊 健康报告</el-button>
      </div>
    </div>

    <template v-if="overview.profile">
      <!-- 基本信息 -->
      <div class="ky-card">
        <div class="ky-card__title">基本信息</div>
        <div class="info-tags">
          <el-tag>{{ overview.profile.gender === 'M' ? '男' : '女' }}</el-tag>
          <el-tag type="info">{{ overview.profile.age }} 岁</el-tag>
          <el-tag v-for="t in overview.profile.chronic_tags || []" :key="t" type="warning">{{ t }}</el-tag>
        </div>
        <div class="ky-sub" style="margin-top: 12px">
          紧急联系人：{{ overview.profile.emergency_contact }}（{{ overview.profile.emergency_phone }}）
          <template v-if="overview.profile.allergy"> · 过敏史：{{ overview.profile.allergy }}</template>
        </div>
      </div>

      <!-- 今日指标 -->
      <div class="stat-grid">
        <div class="ky-stat">
          <div class="ky-stat__label">血压</div>
          <div class="ky-stat__value">{{ bpText }}<span class="unit">mmHg</span></div>
          <div class="ky-stat__extra"><StatusTag kind="abnormal" :value="!!overview.latest?.BLOOD_PRESSURE?.is_abnormal" /></div>
        </div>
        <div class="ky-stat">
          <div class="ky-stat__label">心率</div>
          <div class="ky-stat__value">{{ overview.latest?.HEART_RATE?.values.value ?? '—' }}<span class="unit">次/分</span></div>
        </div>
        <div class="ky-stat">
          <div class="ky-stat__label">血糖</div>
          <div class="ky-stat__value">{{ overview.latest?.BLOOD_SUGAR?.values.value ?? '—' }}<span class="unit">mmol/L</span></div>
        </div>
        <div class="ky-stat">
          <div class="ky-stat__label">睡眠</div>
          <div class="ky-stat__value">{{ overview.latest?.SLEEP?.values.hours ?? '—' }}<span class="unit">小时</span></div>
        </div>
      </div>

      <!-- 未处理预警 -->
      <div class="ky-card">
        <div class="ky-card__title" style="display: flex; justify-content: space-between; align-items: center">
          <span>未处理预警</span>
          <el-button link type="primary" @click="$router.push('/family/notifications')">全部预警 →</el-button>
        </div>
        <div v-if="overview.open_alerts?.length" class="alert-list">
          <div v-for="a in overview.open_alerts" :key="a.warning_id" class="alert-item" @click="$router.push(`/family/alert/${a.warning_id}`)">
            <StatusTag kind="level" :value="a.level" />
            <span class="alert-item__title">{{ a.title }}</span>
            <span class="alert-item__value">{{ a.value_text }}</span>
            <StatusTag kind="status" :value="a.status" />
          </div>
        </div>
        <div v-else class="ky-empty">暂无未处理预警</div>
      </div>

      <!-- 趋势 -->
      <div class="ky-card">
        <div class="ky-card__title" style="display: flex; justify-content: space-between; align-items: center">
          <span>近期趋势</span>
          <el-radio-group v-model="trendType" size="small" @change="loadTrend">
            <el-radio-button label="BLOOD_PRESSURE">血压</el-radio-button>
            <el-radio-button label="BLOOD_SUGAR">血糖</el-radio-button>
            <el-radio-button label="HEART_RATE">心率</el-radio-button>
          </el-radio-group>
        </div>
        <TrendChart :dates="trend.dates" :series="trend.series" :abnormal-indexes="trend.abnormalIndexes" :unit="trend.unit" />
      </div>
    </template>

    <!-- 代录指标对话框 -->
    <el-dialog v-model="dialogVisible" title="代录指标" width="560px">
      <el-form label-position="top">
        <el-form-item label="指标类型">
          <el-radio-group v-model="form.type" @change="resetValues">
            <el-radio-button v-for="ind in indicators" :key="ind.type" :label="ind.type">{{ ind.name }}</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="form.type === 'BLOOD_SUGAR'" label="测量时机">
          <el-radio-group v-model="form.timing">
            <el-radio-button label="空腹">空腹</el-radio-button>
            <el-radio-button label="餐后 2 小时">餐后 2 小时</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-for="f in currentFields" :key="f.key" :label="f.label">
          <el-input-number v-model="form.values[f.key]" :step="f.key === 'hours' ? 0.5 : 1" :min="0" style="width: 100%" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="onSubmitRecord">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUser } from '@/utils/auth'
import { getElderOverview, getTrend, getIndicators, addRecord } from '@/api'
import StatusTag from '@/components/common/StatusTag.vue'
import TrendChart from '@/components/common/TrendChart.vue'

const route = useRoute()
const user = getUser()
const profileId = route.params.id

const overview = ref({})
const trendType = ref('BLOOD_PRESSURE')
const trend = ref({ dates: [], series: [], abnormalIndexes: [], unit: '' })
const indicators = ref([])
const dialogVisible = ref(false)
const form = reactive({ type: 'BLOOD_PRESSURE', timing: '空腹', values: {} })

const UNIT = { BLOOD_PRESSURE: 'mmHg', BLOOD_SUGAR: 'mmol/L', HEART_RATE: '次/分', SLEEP: '小时', STEP: '步' }

const bpText = computed(() => {
  const b = overview.value.latest?.BLOOD_PRESSURE
  return b ? `${b.values.systolic}/${b.values.diastolic}` : '—'
})

const currentFields = computed(() => indicators.value.find((i) => i.type === form.type)?.fields || [])

function resetValues() {
  form.values = {}
}

async function load() {
  try {
    overview.value = await getElderOverview(profileId, user.user_id)
    await loadTrend()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function loadTrend() {
  try {
    const d = await getTrend({ profile_id: profileId, type: trendType.value, days: 14 })
    trend.value = { ...d, unit: UNIT[trendType.value] || '' }
  } catch (e) {
    /* 忽略 */
  }
}

async function onSubmitRecord() {
  for (const f of currentFields.value) {
    if (form.values[f.key] === null || form.values[f.key] === undefined) return ElMessage.warning(`请填写${f.label}`)
  }
  try {
    const res = await addRecord({
      profile_id: profileId,
      type: form.type,
      values: { ...form.values },
      timing: form.type === 'BLOOD_SUGAR' ? form.timing : null,
      entered_by: user.name,
    })
    dialogVisible.value = false
    if (res.warning_created) {
      await ElMessageBox.alert('代录的指标超出正常范围，系统已生成健康预警。', '指标异常', { type: 'warning' })
    } else {
      ElMessage.success('代录成功')
    }
    resetValues()
    load()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

onMounted(async () => {
  try {
    indicators.value = await getIndicators()
  } catch (e) {
    /* 忽略 */
  }
  load()
})
</script>

<style scoped>
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}
.info-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.alert-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.alert-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  cursor: pointer;
  flex-wrap: wrap;
}
.alert-item:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-card);
}
.alert-item__title {
  font-weight: 600;
}
.alert-item__value {
  color: var(--color-danger);
  font-weight: 600;
}
</style>
