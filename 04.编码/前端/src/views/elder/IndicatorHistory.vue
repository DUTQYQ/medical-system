<template>
  <div class="ky-page">
    <div class="ky-page-header">
      <h2 class="ky-page-title">指标历史</h2>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getUser } from '@/utils/auth'
import { fmtDate } from '@/api/mock'
import { listProfiles, getIndicators, listRecords } from '@/api'
import StatusTag from '@/components/common/StatusTag.vue'

const user = getUser()
const indicators = ref([])
const type = ref('BLOOD_PRESSURE')
const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 10
const loading = ref(false)
const profileId = ref(null)

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
    const res = await listRecords({ profile_id: profileId.value, type: type.value, page: page.value, page_size: pageSize })
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

onMounted(async () => {
  try {
    const [inds, profiles] = await Promise.all([getIndicators(), listProfiles(user.user_id, 'ELDER')])
    indicators.value = inds
    if (profiles.length) profileId.value = profiles[0].profile_id
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  }
})
</script>
