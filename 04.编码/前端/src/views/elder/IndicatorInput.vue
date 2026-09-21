<template>
  <div class="ky-page" style="max-width: 760px">
    <div class="ky-page-header">
      <h2 class="ky-page-title">指标录入</h2>
      <el-button link type="primary" @click="$router.push('/elder/history')">查看历史记录 →</el-button>
    </div>

    <!-- 指标类型选择 -->
    <div class="ky-card">
      <div class="ky-card__title">选择指标类型</div>
      <el-radio-group v-model="type" @change="onTypeChange">
        <el-radio-button v-for="ind in indicators" :key="ind.type" :label="ind.type">{{ ind.name }}</el-radio-button>
      </el-radio-group>
      <div class="ky-sub" style="margin-top: 10px">{{ currentIndicator?.desc }}</div>
      <el-alert v-if="rangeHint" type="info" :closable="false" style="margin-top: 10px" :title="'参考范围：' + rangeHint" />
    </div>

    <!-- 录入表单 -->
    <div class="ky-card">
      <div class="ky-card__title">录入数值</div>

      <el-form label-position="top">
        <el-form-item v-if="currentIndicator?.meta?.timing" label="测量时机">
          <el-radio-group v-model="timing">
            <el-radio-button v-for="t in currentIndicator.meta.timing" :key="t" :label="t">{{ t }}</el-radio-button>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-for="f in currentIndicator?.fields || []" :key="f.key" :label="f.label">
          <el-select v-if="f.options" v-model="values[f.key]" style="width: 100%">
            <el-option v-for="o in f.options" :key="o" :label="o" :value="o" />
          </el-select>
          <el-input-number v-else v-model="values[f.key]" :step="f.key === 'hours' ? 0.5 : 1" :min="0" style="width: 100%" :placeholder="f.placeholder" />
          <span v-if="f.unit" class="ky-sub" style="margin-left: 8px">{{ f.unit }}</span>
        </el-form-item>

        <el-form-item label="备注（可选）">
          <el-input v-model="remark" placeholder="如：晨起空腹测量" maxlength="50" />
        </el-form-item>

        <el-button type="primary" size="large" :loading="saving" @click="onSave">保存记录</el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUser } from '@/utils/auth'
import { listProfiles, getIndicators, getThresholds, addRecord } from '@/api'

const user = getUser()
const indicators = ref([])
const thresholds = ref({})
const type = ref('BLOOD_PRESSURE')
const timing = ref('空腹')
const remark = ref('')
const values = reactive({})
const saving = ref(false)
const profileId = ref(null)

const currentIndicator = computed(() => indicators.value.find((i) => i.type === type.value))

const rangeHint = computed(() => {
  const t = thresholds.value[type.value]
  if (!t) return ''
  if (type.value === 'BLOOD_PRESSURE') return `收缩压 ${t.systolic.low}–${t.systolic.high} / 舒张压 ${t.diastolic.low}–${t.diastolic.high} mmHg`
  if (type.value === 'BLOOD_SUGAR') return `空腹 ${t.fasting.low}–${t.fasting.high} mmol/L，餐后 <${t.postprandial.high} mmol/L`
  if (type.value === 'HEART_RATE') return `${t.low}–${t.high} 次/分`
  if (type.value === 'SLEEP') return `建议 ${t.low}–${t.high} 小时`
  if (type.value === 'STEP') return `建议 ≥${t.low} 步`
  return ''
})

function onTypeChange() {
  values.systolic = null
  values.diastolic = null
  values.value = null
  values.hours = null
  values.count = null
  values.quality = '优'
}

async function onSave() {
  if (!profileId.value) return ElMessage.warning('请先完善健康档案')
  const ind = currentIndicator.value
  // 必填校验
  for (const f of ind.fields) {
    if (f.options) continue
    if (values[f.key] === null || values[f.key] === undefined || values[f.key] === '') {
      return ElMessage.warning(`请填写${f.label}`)
    }
  }
  const payload = {
    profile_id: profileId.value,
    type: type.value,
    values: { ...values },
    timing: ind.meta?.timing ? timing.value : null,
    entered_by: user.name,
    remark: remark.value,
  }
  saving.value = true
  try {
    const res = await addRecord(payload)
    if (res.warning_created) {
      await ElMessageBox.alert(
        '本次录入的指标超出正常范围，系统已自动生成一条健康预警，并通知您的授权家属。请保持静息后复测，如持续异常请及时就医。',
        '指标异常提醒',
        { confirmButtonText: '我知道了', type: 'warning' }
      )
    } else {
      ElMessage.success('记录已保存，指标正常')
    }
    onTypeChange()
    remark.value = ''
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

onMounted(async () => {
  try {
    const [inds, ths, profiles] = await Promise.all([getIndicators(), getThresholds(), listProfiles(user.user_id, 'ELDER')])
    indicators.value = inds
    thresholds.value = ths
    if (profiles.length) profileId.value = profiles[0].profile_id
    onTypeChange()
  } catch (e) {
    ElMessage.error(e.message)
  }
})
</script>
