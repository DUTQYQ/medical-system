<template>
  <div class="ky-page" v-loading="loading">
    <div class="ky-page-header">
      <h2 class="ky-page-title">按人阈值覆盖</h2>
      <div style="display: flex; gap: 12px">
        <el-select v-model="profileId" placeholder="选择老人档案" style="width: 180px" @change="load">
          <el-option v-for="p in profiles" :key="p.profile_id" :label="p.name" :value="p.profile_id" />
        </el-select>
        <el-button @click="load">刷新</el-button>
        <el-button type="primary" :disabled="!profileId" :loading="saving" @click="save">保存覆盖</el-button>
      </div>
    </div>

    <el-alert type="info" :closable="false" title="开启「覆盖全局」后，该老人对应指标按此区间判定（不再叠加年龄放宽）；关闭则回退到全局阈值 + 年龄自动放宽。" style="margin-bottom: 16px" />

    <div v-if="profileId" class="ky-card">
      <el-table :data="rows">
        <el-table-column prop="name" label="指标" width="150" />
        <el-table-column prop="unit" label="单位" width="90" />
        <el-table-column label="正常范围"><template #default="{ row }"><el-input v-model="row.level0_range" size="small" /></template></el-table-column>
        <el-table-column label="Ⅰ级"><template #default="{ row }"><el-input v-model="row.level1_range" size="small" /></template></el-table-column>
        <el-table-column label="Ⅱ级"><template #default="{ row }"><el-input v-model="row.level2_range" size="small" /></template></el-table-column>
        <el-table-column label="Ⅲ级"><template #default="{ row }"><el-input v-model="row.level3_range" size="small" /></template></el-table-column>
        <el-table-column label="覆盖全局" width="100"><template #default="{ row }"><el-switch v-model="row.enabled" /></template></el-table-column>
        <el-table-column label="备注" width="180"><template #default="{ row }"><el-input v-model="row.remark" size="small" placeholder="覆盖原因" /></template></el-table-column>
      </el-table>
    </div>
    <div v-else class="ky-empty">请先选择老人档案</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listProfiles, listAdminThresholds, listProfileThresholds, saveProfileThresholds } from '@/api'
import { asList } from '@/utils/format'

const NAME = { BLOOD_PRESSURE_SYSTOLIC: '收缩压', BLOOD_PRESSURE_DIASTOLIC: '舒张压', BLOOD_SUGAR: '血糖', HEART_RATE: '心率', SLEEP_HOURS: '睡眠时长', STEP_COUNT: '步数' }

const profiles = ref([])
const profileId = ref(null)
const rows = ref([])
const loading = ref(false)
const saving = ref(false)

async function load() {
  loading.value = true
  try {
    profiles.value = await listProfiles()
    if (!profiles.value.length) { rows.value = []; return }
    if (!profiles.value.some(p => p.profile_id === profileId.value)) profileId.value = profiles.value[0].profile_id
    const globals = asList(await listAdminThresholds())
    const overrides = asList(await listProfileThresholds(profileId.value))
    const overrideMap = Object.fromEntries(overrides.map(o => [o.config_key, o]))
    rows.value = globals.map(g => {
      const o = overrideMap[g.indicator]
      return {
        config_key: g.indicator,
        name: NAME[g.indicator] || g.indicator_name || g.indicator,
        unit: g.unit,
        level0_range: o?.level0_range ?? g.level0_range ?? '',
        level1_range: o?.level1_range ?? g.level1_range ?? '',
        level2_range: o?.level2_range ?? g.level2_range ?? '',
        level3_range: o?.level3_range ?? g.level3_range ?? '',
        enabled: o ? !!o.enabled : false,
        remark: o?.remark ?? '',
      }
    })
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const payload = rows.value.map(r => ({
      config_key: r.config_key, level0_range: r.level0_range, level1_range: r.level1_range,
      level2_range: r.level2_range, level3_range: r.level3_range, enabled: !!r.enabled, remark: r.remark || '',
    }))
    await saveProfileThresholds(profileId.value, payload)
    ElMessage.success('按人阈值已保存，新录入即时生效')
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>
