<template>
  <div class="ky-page" v-loading="loading">
    <div class="ky-page-header">
      <h2 class="ky-page-title">康养活动库</h2>
      <div style="display: flex; gap: 12px">
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="create">＋ 新增活动</el-button>
      </div>
    </div>
    <el-alert type="info" :closable="false" title="活动按规则引擎自动匹配老人（年龄/慢病/季节/健康指标），不依赖大模型；规则 JSON 支持 suitable/avoid/caution。" style="margin-bottom: 16px" />
    <div class="ky-card">
      <el-table :data="rows">
        <el-table-column prop="name" label="活动名称" />
        <el-table-column prop="code" label="编码" width="110" />
        <el-table-column prop="category" label="分类" width="90" />
        <el-table-column label="强度" width="90">
          <template #default="{ row }">{{ intensityText(row.intensity) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }"><el-tag :type="row.enabled ? 'success' : 'info'" size="small">{{ row.enabled ? '启用' : '停用' }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button link type="primary" @click="edit(row)">修改</el-button>
            <el-button link type="danger" @click="remove(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="dialog" :title="form.activity_id ? '编辑活动' : '新增活动'" width="min(640px,95vw)">
      <el-form label-position="top">
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0 16px">
          <el-form-item label="活动名称"><el-input v-model="form.name" /></el-form-item>
          <el-form-item label="编码（唯一，如 TAICHI）"><el-input v-model="form.code" :disabled="!!form.activity_id" /></el-form-item>
          <el-form-item label="分类"><el-input v-model="form.category" placeholder="户外/养生/有氧/康复" /></el-form-item>
          <el-form-item label="强度">
            <el-select v-model="form.intensity" style="width: 100%">
              <el-option label="低强度 LOW" value="LOW" />
              <el-option label="中强度 MODERATE" value="MODERATE" />
              <el-option label="高强度 HIGH" value="HIGH" />
            </el-select>
          </el-form-item>
        </div>
        <el-form-item label="活动说明"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="康养效果"><el-input v-model="form.benefits" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="建议时长/时段"><el-input v-model="form.duration_hint" /></el-form-item>
        <el-form-item label="推荐规则（JSON）">
          <el-input v-model="form.rulesText" type="textarea" :rows="5" placeholder='{"suitable":{"min_age":60,"chronic_in":["高血压"]},"avoid":{"seasons_in":["summer"]},"caution":{"max_risk_level":2}}' />
        </el-form-item>
        <el-form-item label="禁忌/注意事项"><el-input v-model="form.contraindications" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listActivities, createActivity, updateActivity, deleteActivity } from '@/api'
import { asList } from '@/utils/format'

const rows = ref([])
const loading = ref(false)
const saving = ref(false)
const dialog = ref(false)
const form = ref({})

const INTENSITY = { LOW: '低强度', MODERATE: '中强度', HIGH: '高强度' }
const intensityText = v => INTENSITY[v] || v || '—'

async function load() {
  loading.value = true
  try { rows.value = asList(await listActivities()) } catch (e) { ElMessage.error(e.message) } finally { loading.value = false }
}

function create() {
  form.value = { code: '', name: '', category: '', intensity: 'LOW', description: '', benefits: '', duration_hint: '', rulesText: '{}', contraindications: '', enabled: true }
  dialog.value = true
}

function edit(row) {
  form.value = { ...row, rulesText: JSON.stringify(row.rules || {}, null, 2) }
  dialog.value = true
}

async function save() {
  let rules
  try { rules = JSON.parse(form.value.rulesText || '{}') } catch { ElMessage.error('规则 JSON 格式不正确'); return }
  if (typeof rules !== 'object' || Array.isArray(rules)) { ElMessage.error('规则必须是 JSON 对象'); return }
  saving.value = true
  const payload = {
    code: form.value.code, name: form.value.name, category: form.value.category || '', intensity: form.value.intensity,
    description: form.value.description || '', benefits: form.value.benefits || '', duration_hint: form.value.duration_hint || '',
    rules, contraindications: form.value.contraindications || '', enabled: !!form.value.enabled,
  }
  try {
    if (form.value.activity_id) await updateActivity(form.value.activity_id, payload)
    else await createActivity(payload)
    dialog.value = false
    await load()
    ElMessage.success('活动已保存')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  try {
    await ElMessageBox.confirm(`确认删除活动「${row.name}」？`, '删除活动', { type: 'warning' })
    await deleteActivity(row.activity_id)
    await load()
    ElMessage.success('活动已删除')
  } catch (e) { if (!['cancel', 'close'].includes(e)) ElMessage.error(e.message) }
}

onMounted(load)
</script>
