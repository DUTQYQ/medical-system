<template>
<div class="ky-page" style="max-width:760px" v-loading="loading">
  <div class="ky-page-header"><h2 class="ky-page-title">健康指标录入</h2></div>
  <el-alert v-if="error" type="error" :closable="false" :title="error" style="margin-bottom:16px"><el-button @click="load">重新加载</el-button></el-alert>
  <div v-if="!loading && !profiles.length && !error" class="ky-card ky-empty">暂无可管理的健康档案。老人请先创建档案；家属请等待绑定生效。</div>
  <div v-if="profiles.length" class="ky-card">
    <el-form label-position="top">
      <el-form-item label="健康档案"><el-select v-model="profileId" style="width:100%"><el-option v-for="p in profiles" :key="p.profile_id" :label="p.name" :value="p.profile_id" /></el-select></el-form-item>
      <el-form-item label="指标类型"><el-radio-group v-model="type" @change="reset"><el-radio-button v-for="i in indicators" :key="i.type" :label="i.type">{{ i.name }}</el-radio-button></el-radio-group></el-form-item>
      <el-alert v-if="hint" type="info" :closable="false" :title="'后台参考范围：' + hint" style="margin-bottom:16px" />
      <el-form-item v-for="f in current?.fields || []" :key="f.key" :label="f.label + (f.unit ? '（' + f.unit + '）' : '')">
        <el-select v-if="f.options" v-model="values[f.key]" style="width:100%"><el-option v-for="o in f.options" :key="o.value ?? o" :label="String(o.label ?? o)" :value="o.value ?? o" /></el-select>
        <el-input-number v-else v-model="values[f.key]" :step="f.step || (f.key === 'hours' ? .5 : type === 'BLOOD_SUGAR' ? .1 : 1)" :min="0" style="width:100%" />
      </el-form-item>
      <el-form-item label="测量时间"><el-date-picker v-model="measuredAt" type="datetime" value-format="YYYY-MM-DD HH:mm:ss" style="width:100%" /></el-form-item>
      <el-form-item label="备注（可选）"><el-input v-model="remark" maxlength="200" /></el-form-item>
      <el-button type="primary" size="large" :disabled="!current || !profileId" :loading="saving" @click="save">保存记录</el-button>
    </el-form>
  </div>
</div>
</template>
<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listProfiles, getIndicators, getThresholds, addRecord } from '@/api'
import { measuredNow, thresholdHint } from '@/utils/format'
const props = defineProps({ fixedProfileId: { type: [Number,String], default: null } })
const emit = defineEmits(['saved'])
const route = useRoute(), profiles = ref([]), profileId = ref(null), indicators = ref([]), thresholds = ref({}), loading = ref(false), saving = ref(false), error = ref('')
const type = ref('BLOOD_PRESSURE'), values = reactive({}), measuredAt = ref(measuredNow()), remark = ref('')
const current = computed(() => indicators.value.find(i => i.type === type.value))
const hint = computed(() => thresholdHint(thresholds.value, type.value))
function reset() { Object.keys(values).forEach(k => delete values[k]); if (type.value === 'SLEEP') values.quality = 3 }
async function load() {
  loading.value = true; error.value = ''
  try {
    const [p, i, t] = await Promise.all([listProfiles(), getIndicators(), getThresholds()])
    profiles.value = p; indicators.value = i; thresholds.value = t
    const requested = Number(props.fixedProfileId || route.query.profile_id)
    profileId.value = p.find(x => x.profile_id === requested)?.profile_id || p[0]?.profile_id
    if (!i.some(x => x.type === type.value)) type.value = i[0]?.type
    reset()
  } catch (e) { error.value = e.message } finally { loading.value = false }
}
async function save() {
  if (saving.value || !current.value) return
  for (const f of current.value.fields) if (values[f.key] == null || values[f.key] === '') return ElMessage.warning('请填写' + f.label)
  if (!measuredAt.value) return ElMessage.warning('请选择测量时间')
  saving.value = true
  try {
    const v = Object.fromEntries(current.value.fields.map(f => [f.key, values[f.key]]))
    const r = await addRecord({ profile_id: profileId.value, type: type.value, values: v, measured_at: measuredAt.value, remark: remark.value })
    if (r.is_abnormal) await ElMessageBox.alert('记录已保存并触发健康预警。授权家属与负责护工可在站内查看并处理。请关注异常数据，必要时就医。', '指标异常', { type: 'warning' })
    else ElMessage.success('记录已保存，未触发阈值预警')
    reset(); remark.value = ''; measuredAt.value = measuredNow(); emit('saved', r)
  } catch (e) { ElMessage.error(e.message) } finally { saving.value = false }
}
onMounted(load)
</script>
