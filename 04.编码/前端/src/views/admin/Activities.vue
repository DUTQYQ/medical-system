<template>
  <div class="ky-page" v-loading="loading">
    <div class="ky-page-header">
      <h2 class="ky-page-title">康养活动建议库</h2>
      <div style="display: flex; gap: 12px">
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" @click="create">＋ 新增活动</el-button>
      </div>
    </div>
    <el-alert type="info" :closable="false" title="这里维护可了解的活动类型及筛选条件。真实活动的时间、名额、报名与出席记录请在院内服务中管理；活动建议不会自动报名。" style="margin-bottom: 16px" />
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
            <el-button v-if="row.enabled" link type="danger" @click="remove(row)">停用</el-button>
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
        <p class="ky-sub">同组填写的条件须全部满足。年龄或慢病信息缺失时会提示确认，不直接判断适合。</p>
        <template v-for="group in ['suitable','avoid']" :key="group">
          <h3>{{ group==='suitable'?'建议了解的匹配条件':'不建议参与的排除条件' }}</h3>
          <template v-if="form[group]">
            <el-form-item label="年龄区间（留空则不限制）"><el-input-number v-model="form[group].min_age" :min="0" :max="150" :precision="0" placeholder="最小年龄" /><span> 至 </span><el-input-number v-model="form[group].max_age" :min="0" :max="150" :precision="0" placeholder="最大年龄" /></el-form-item>
            <el-form-item label="匹配已记录标签（可输入后回车，多标签任一命中）"><el-select v-model="form[group].chronic_in" multiple filterable allow-create default-first-option style="width:100%" /></el-form-item>
            <el-form-item label="符合以下季节"><el-select v-model="form[group].seasons_in" multiple style="width:100%"><el-option v-for="s in seasons" :key="s.value" :value="s.value" :label="s.label" /></el-select></el-form-item>
            <el-form-item label="符合以上条件且不在以下季节"><el-select v-model="form[group].seasons_not_in" multiple style="width:100%"><el-option v-for="s in seasons" :key="s.value" :value="s.value" :label="s.label" /></el-select></el-form-item>
          </template>
        </template>
        <el-form-item label="当健康风险等级达到以下等级时提示谨慎（可选）"><el-select v-model="form.cautionLevel" clearable style="width:100%"><el-option v-for="n in [1,2,3]" :key="n" :value="n" :label="String(n)+' 级'" /></el-select></el-form-item>
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
const seasons=[{value:'spring',label:'春季'},{value:'summer',label:'夏季'},{value:'autumn',label:'秋季'},{value:'winter',label:'冬季'}]

const INTENSITY = { LOW: '低强度', MODERATE: '中强度', HIGH: '高强度' }
const intensityText = v => INTENSITY[v] || v || '—'

async function load() {
  loading.value = true
  try { rows.value = asList(await listActivities()) } catch (e) { ElMessage.error(e.message) } finally { loading.value = false }
}

function create() {
  edit({code:'',name:'',category:'',intensity:'LOW',description:'',benefits:'',duration_hint:'',contraindications:'',enabled:true,rules:{}})
}

function edit(row) {
  form.value = { ...row, cautionLevel:row.rules?.caution?.max_risk_level ?? null }
  for(const group of ['suitable','avoid'])form.value[group]={min_age:null,max_age:null,chronic_in:[],seasons_in:[],seasons_not_in:[],...row.rules?.[group]}
  if(row.rules_error)ElMessage.warning(row.rules_error)
  dialog.value = true
}

function rulesFromForm(){
  const rules={}
  for(const group of ['suitable','avoid']){
    const condition={}
    for(const [key,value] of Object.entries(form.value[group]||{}))if(value!=null&&value!==''&&(!Array.isArray(value)||value.length))condition[key]=value
    if(Object.keys(condition).length)rules[group]=condition
  }
  if(form.value.cautionLevel!=null&&form.value.cautionLevel!=='')rules.caution={max_risk_level:form.value.cautionLevel}
  return rules
}

async function save() {
  if(saving.value)return
  if(!form.value.name?.trim()||!/^[A-Z][A-Z0-9_]{0,49}$/.test(form.value.code||''))return ElMessage.warning('请填写活动名称和正确编码（大写字母开头，可含数字和下划线）')
  const rules=rulesFromForm()
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
    await ElMessageBox.confirm(`确认停用活动建议「${row.name}」？已发布活动与报名记录会保留。`, '停用活动建议', { type: 'warning' })
    await deleteActivity(row.activity_id)
    await load()
    ElMessage.success('活动建议已停用')
  } catch (e) { if (!['cancel', 'close'].includes(e)) ElMessage.error(e.message) }
}

onMounted(load)
</script>
