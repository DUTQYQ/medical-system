<template>
  <div class="ky-page">
    <div class="ky-page-header">
      <h2 class="ky-page-title">指标历史</h2><el-select v-if="profiles.length>1" v-model="profileId" style="width:160px" @change="reload"><el-option v-for="p in profiles" :key="p.profile_id" :label="p.name" :value="p.profile_id" /></el-select>
      <div style="display: flex; gap: 12px">
        <el-button @click="$router.push('/elder/input')">＋ 录入指标</el-button>
        <el-button type="primary" @click="$router.push('/elder/trend')">查看趋势图</el-button>
      </div>
    </div>

    <div class="ky-card">
      <el-radio-group v-model="type" @change="reload">
        <el-radio-button v-for="ind in indicators" :key="ind.type" :label="ind.type">{{ ind.name }}</el-radio-button>
      </el-radio-group>
    </div>

    <div class="ky-card">
      <el-checkbox v-model="includeVoided" @change="reload">显示作废记录及原因</el-checkbox>
      <el-table :data="records" style="width: 100%" v-loading="loading">
        <el-table-column label="测量时间" min-width="160">
          <template #default="{ row }">{{ fmtDate(row.measured_at) }}</template>
        </el-table-column>
        <el-table-column label="数值" min-width="140">
          <template #default="{ row }">
            <strong :style="{ color: row.is_abnormal ? 'var(--color-danger)' : 'var(--color-text-primary)' }">{{ valueText(row) }}</strong>
            <span v-if="row.timing" class="ky-sub">（{{ row.timing }}）</span>
          </template>
        </el-table-column>
        <el-table-column label="是否异常" width="120">
          <template #default="{ row }">
            <StatusTag kind="abnormal" :value="row.is_abnormal" />
          </template>
        </el-table-column>
        <el-table-column prop="entered_by" label="录入人" width="120" />
        <el-table-column prop="remark" label="备注" min-width="140" />
        <el-table-column label="检测依据" min-width="160"><template #default="{row}"><el-button link type="primary" @click="selectedRecord=row;evidenceDialog=true">{{ row.assessment?'查看阈值版本':'旧记录无阈值版本' }}</el-button></template></el-table-column>
        <el-table-column label="记录状态" min-width="160"><template #default="{row}"><el-tag v-if="row.is_voided" type="info">已作废</el-tag><p v-if="row.void_audit" class="ky-sub">{{ row.void_audit.voided_by_name }}：{{ row.void_audit.reason }} · {{ fmtDate(row.void_audit.voided_at) }}</p><span v-else>有效记录</span></template></el-table-column>
        <el-table-column label="操作" width="90"><template #default="{row}"><el-button v-if="row.can_void" link type="danger" @click="remove(row)">作废</el-button></template></el-table-column>
      </el-table>

      <el-pagination
        v-if="total > pageSize"
        style="margin-top: 16px; justify-content: flex-end"
        layout="prev, pager, next, total"
        :total="total"
        :page-size="pageSize"
        :current-page="page"
        @current-change="onPage"
      />
    </div>
    <el-dialog v-model="evidenceDialog" title="历史指标检测依据" width="min(650px,95vw)"><ThresholdEvidence :assessment="selectedRecord?.assessment" /></el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUser } from '@/utils/auth'
import { fmtDate } from '@/utils/format'
import { listProfiles, getIndicators, listRecords, deleteRecord } from '@/api'
import StatusTag from '@/components/common/StatusTag.vue'
import ThresholdEvidence from '@/components/common/ThresholdEvidence.vue'

const user = getUser()
const indicators = ref([])
const type = ref('BLOOD_PRESSURE')
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const profiles = ref([])
const profileId = ref(null)
const selectedRecord=ref(null),evidenceDialog=ref(false)
const includeVoided=ref(false)

const UNIT = { BLOOD_PRESSURE: 'mmHg', BLOOD_SUGAR: 'mmol/L', HEART_RATE: '次/分', SLEEP: '小时', STEP: '步' }

function valueText(row) {
  const v = row.values
  if (row.type === 'BLOOD_PRESSURE') return `${v.systolic}/${v.diastolic}`
  if (row.type === 'BLOOD_SUGAR') return `${v.value}`
  if (row.type === 'HEART_RATE') return `${v.value}`
  if (row.type === 'SLEEP') return `${v.hours}（${v.quality}）`
  if (row.type === 'STEP') return `${v.count}`
  return ''
}

async function reload() {
  page.value = 1
  await load()
}

async function load() {
  if (!profileId.value) return
  loading.value = true
  try {
    const res = await listRecords({ profile_id: profileId.value, type: type.value, page: page.value, page_size: pageSize, include_voided: includeVoided.value })
    records.value = res.list
    total.value = res.total
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function onPage(p) {
  page.value = p
  load()
}

async function remove(row) { try { const {value}=await ElMessageBox.prompt('请填写实际作废原因。原始数值和既有预警会保留，作废不会自动关闭预警。', '作废误录指标', { type:'warning',inputValidator:v=>!!v?.trim() || '请填写原因',inputType:'textarea' }); await deleteRecord(row.record_id,value.trim()); await load(); ElMessage.success('记录已作废，原始数据与审计记录保留') } catch(e) { if (!['cancel','close'].includes(e)) ElMessage.error(e.message) } }

onMounted(async () => {
  try {
    const [inds, ps] = await Promise.all([getIndicators(), listProfiles(user.user_id, 'ELDER')])
    indicators.value = inds
    profiles.value = ps
    if (ps.length) profileId.value = ps[0].profile_id
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  }
})
</script>
