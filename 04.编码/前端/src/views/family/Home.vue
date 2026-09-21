<template>
  <div class="ky-page">
    <div class="home-hero">
      <div>
        <div class="home-greet">{{ greeting }}，{{ user?.name }} 👋</div>
        <div class="ky-sub">{{ today }} · 关注家人健康，安心每一天</div>
      </div>
      <div style="display: flex; gap: 12px">
        <el-button @click="$router.push('/family/bind')">＋ 绑定老人</el-button>
        <el-button type="primary" @click="$router.push('/family/ai')">代发起 AI 咨询</el-button>
      </div>
    </div>

    <!-- 预警概览 -->
    <div class="stat-grid">
      <div class="ky-stat">
        <div class="ky-stat__label">未读预警</div>
        <div class="ky-stat__value" :style="{ color: stats.unread ? 'var(--color-danger)' : 'inherit' }">{{ stats.unread }}</div>
      </div>
      <div class="ky-stat">
        <div class="ky-stat__label">待处理预警</div>
        <div class="ky-stat__value" :style="{ color: stats.pending ? 'var(--color-warning)' : 'inherit' }">{{ stats.pending }}</div>
      </div>
      <div class="ky-stat">
        <div class="ky-stat__label">处理中</div>
        <div class="ky-stat__value">{{ stats.processing }}</div>
      </div>
      <div class="ky-stat">
        <div class="ky-stat__label">已处理</div>
        <div class="ky-stat__value" style="color: var(--color-success)">{{ stats.resolved }}</div>
      </div>
    </div>

    <!-- 已绑定老人 -->
    <div class="ky-card">
      <div class="ky-card__title">我的家人</div>
      <div v-if="elders.length" class="elder-grid">
        <div v-for="e in elders" :key="e.bind_id" class="elder-card" @click="$router.push(`/family/elder/${e.profile_id}`)">
          <div class="elder-card__head">
            <div class="elder-card__avatar">{{ (e.profile?.name || '老')[0] }}</div>
            <div>
              <div class="elder-card__name">{{ e.profile?.name }} <span class="ky-sub">（{{ e.relation }}）</span></div>
              <div class="ky-sub">{{ e.profile?.age }} 岁 · {{ e.profile?.chronic_tags?.join('、') || '无慢病标签' }}</div>
            </div>
          </div>
          <div class="elder-card__metrics">
            <div class="metric">
              <span class="metric__label">血压</span>
              <span class="metric__value" :style="{ color: latest[e.profile_id]?.BLOOD_PRESSURE?.is_abnormal ? 'var(--color-danger)' : 'inherit' }">
                {{ bpText(latest[e.profile_id]) }}
              </span>
            </div>
            <div class="metric">
              <span class="metric__label">血糖</span>
              <span class="metric__value" :style="{ color: latest[e.profile_id]?.BLOOD_SUGAR?.is_abnormal ? 'var(--color-danger)' : 'inherit' }">
                {{ latest[e.profile_id]?.BLOOD_SUGAR?.values.value ?? '—' }}
              </span>
            </div>
          </div>
          <div class="elder-card__alert">
            <span v-if="openAlertCount(e.profile_id)" style="color: var(--color-danger)">⚠ {{ openAlertCount(e.profile_id) }} 条未处理预警</span>
            <span v-else style="color: var(--color-success)">✓ 近期无未处理预警</span>
          </div>
        </div>
      </div>
      <div v-else class="ky-empty">
        尚未绑定老人。请先前往「绑定老人」发起绑定申请，待老人确认后即可查看健康数据。
        <div style="margin-top: 12px"><el-button type="primary" @click="$router.push('/family/bind')">去绑定</el-button></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getUser } from '@/utils/auth'
import { listElders, getLatestIndicators, summaryStats, getElderOverview } from '@/api'

const user = getUser()
const elders = ref([])
const latest = ref({})
const stats = ref({ unread: 0, pending: 0, processing: 0, resolved: 0 })
const openAlerts = ref({})

const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
})

function bpText(lat) {
  const b = lat?.BLOOD_PRESSURE
  return b ? `${b.values.systolic}/${b.values.diastolic}` : '—'
}

function openAlertCount(profileId) {
  return openAlerts.value[profileId] || 0
}

async function load() {
  try {
    elders.value = await listElders(user.user_id)
    stats.value = await summaryStats(user.user_id)
    for (const e of elders.value) {
      const [lat, overview] = await Promise.all([
        getLatestIndicators(e.profile_id),
        getElderOverview(e.profile_id, user.user_id),
      ])
      latest.value[e.profile_id] = lat
      openAlerts.value[e.profile_id] = overview.open_alerts.length
    }
  } catch (e) {
    ElMessage.error(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.home-hero {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 20px;
}
.home-greet {
  font-size: 28px;
  font-weight: 700;
  margin-bottom: 6px;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}
.elder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.elder-card {
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
}
.elder-card:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-card);
}
.elder-card__head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.elder-card__avatar {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.elder-card__name {
  font-size: 20px;
  font-weight: 600;
}
.elder-card__metrics {
  display: flex;
  gap: 24px;
  padding: 12px 0;
  border-top: 1px solid var(--color-border-light);
  border-bottom: 1px solid var(--color-border-light);
}
.metric__label {
  display: block;
  color: var(--color-text-secondary);
  font-size: 14px;
}
.metric__value {
  font-size: 22px;
  font-weight: 600;
}
.elder-card__alert {
  margin-top: 12px;
  font-size: 15px;
}
</style>
