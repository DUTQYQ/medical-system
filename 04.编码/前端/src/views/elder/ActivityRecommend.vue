<template>
  <div class="ky-page">
    <div class="ky-page-header">
      <h2 class="ky-page-title">活动推荐</h2>
      <div style="display: flex; gap: 12px">
        <el-select v-if="profiles.length > 1" v-model="profileId" style="width: 160px" @change="load">
          <el-option v-for="p in profiles" :key="p.profile_id" :label="p.name" :value="p.profile_id" />
        </el-select>
        <el-button @click="load">刷新</el-button>
      </div>
    </div>

    <el-alert type="info" :closable="false" title="推荐结合您的年龄、慢病情况、当前季节与最新健康指标，由系统规则自动匹配，仅供健康管理参考。" style="margin-bottom: 16px" />

    <div v-loading="loading">
      <div v-for="a in list" :key="a.activity_id" class="ky-card activity-card" :class="'is-' + suitClass(a.suitability)">
        <div class="activity-card__head">
          <span class="activity-card__name">{{ a.name }}</span>
          <el-tag v-if="a.category" size="small" effect="plain">{{ a.category }}</el-tag>
          <el-tag v-if="a.intensity" size="small" :type="intensityType(a.intensity)" effect="light">{{ intensityText(a.intensity) }}</el-tag>
          <StatusTag kind="suitability" :value="a.suitability" />
        </div>
        <div class="activity-card__desc">{{ a.description }}</div>
        <div class="activity-card__grid">
          <div class="activity-cell">
            <div class="activity-cell__label">康养效果</div>
            <div>{{ a.benefits || '—' }}</div>
          </div>
          <div class="activity-cell">
            <div class="activity-cell__label">建议时长</div>
            <div>{{ a.duration_hint || '—' }}</div>
          </div>
          <div class="activity-cell">
            <div class="activity-cell__label">推荐理由</div>
            <div>
              <el-tag v-for="r in a.reasons" :key="r" size="small" type="info" effect="plain" style="margin: 0 6px 4px 0">{{ r }}</el-tag>
              <span v-if="!a.reasons?.length">—</span>
            </div>
          </div>
          <div class="activity-cell">
            <div class="activity-cell__label">注意事项</div>
            <div>{{ a.contraindications || '无' }}</div>
          </div>
        </div>
      </div>
      <div v-if="!loading && !list.length" class="ky-empty">暂无活动推荐</div>
      <DisclaimerFooter />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { listProfiles, getRecommendations } from '@/api'
import StatusTag from '@/components/common/StatusTag.vue'
import DisclaimerFooter from '@/components/common/DisclaimerFooter.vue'

const INTENSITY = { LOW: { text: '低强度', type: 'success' }, MODERATE: { text: '中强度', type: 'warning' }, HIGH: { text: '高强度', type: 'danger' } }

const profiles = ref([])
const profileId = ref(null)
const list = ref([])
const loading = ref(false)

function intensityText(v) { return INTENSITY[v]?.text || v }
function intensityType(v) { return INTENSITY[v]?.type || 'info' }
function suitClass(v) { return ({ '适合': 'ok', '需谨慎': 'warn', '不建议': 'avoid' })[v] || '' }

async function load() {
  loading.value = true
  try {
    profiles.value = await listProfiles()
    if (!profiles.value.length) { list.value = []; return }
    if (!profiles.value.some(p => p.profile_id === profileId.value)) profileId.value = profiles.value[0].profile_id
    list.value = await getRecommendations(profileId.value)
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.activity-card {
  margin-bottom: 14px;
  border-left: 4px solid var(--color-primary);
}
.activity-card.is-warn { border-left-color: var(--color-warning); }
.activity-card.is-avoid { border-left-color: var(--color-danger); opacity: 0.85; }
.activity-card__head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.activity-card__name {
  font-size: 20px;
  font-weight: 700;
}
.activity-card__desc {
  color: var(--color-text-regular);
  line-height: 1.8;
  margin-bottom: 12px;
}
.activity-card__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}
.activity-cell__label {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}
</style>
