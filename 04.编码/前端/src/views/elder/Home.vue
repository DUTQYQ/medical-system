<template>
  <div class="ky-page">
    <div class="home-hero">
      <div>
        <div class="home-greet">{{ greeting }}，{{ user?.name }} 👋</div>
        <div class="ky-sub">{{ today }} · 今天是美好的一天，记得按时测量健康指标</div>
      </div>
      <el-button type="primary" size="large" @click="$router.push('/elder/input')">＋ 录入健康指标</el-button>
    </div>

    <!-- 今日健康速览 -->
    <div class="stat-grid">
      <div class="ky-stat">
        <div class="ky-stat__label">血压</div>
        <div class="ky-stat__value">
          {{ bpText }}<span class="unit">mmHg</span>
        </div>
        <div class="ky-stat__extra">
          <StatusTag kind="abnormal" :value="!!latest.BLOOD_PRESSURE?.is_abnormal" />
          <span v-if="latest.BLOOD_PRESSURE" style="margin-left: 6px">{{ fmtTime(latest.BLOOD_PRESSURE.measured_at) }}</span>
        </div>
      </div>
      <div class="ky-stat">
        <div class="ky-stat__label">心率</div>
        <div class="ky-stat__value">{{ latest.HEART_RATE?.values.value ?? '—' }}<span class="unit">次/分</span></div>
        <div class="ky-stat__extra">
          <StatusTag kind="abnormal" :value="!!latest.HEART_RATE?.is_abnormal" />
        </div>
      </div>
      <div class="ky-stat">
        <div class="ky-stat__label">空腹血糖</div>
        <div class="ky-stat__value">{{ latest.BLOOD_SUGAR?.values.value ?? '—' }}<span class="unit">mmol/L</span></div>
        <div class="ky-stat__extra">
          <StatusTag kind="abnormal" :value="!!latest.BLOOD_SUGAR?.is_abnormal" />
        </div>
      </div>
      <div class="ky-stat">
        <div class="ky-stat__label">睡眠时长</div>
        <div class="ky-stat__value">{{ latest.SLEEP?.values.hours ?? '—' }}<span class="unit">小时</span></div>
        <div class="ky-stat__extra">
          <StatusTag kind="abnormal" :value="!!latest.SLEEP?.is_abnormal" />
        </div>
      </div>
    </div>

    <!-- 今日提醒 / 未读预警 -->
    <div class="ky-card">
      <div class="ky-card__title" style="display: flex; justify-content: space-between; align-items: center">
        <span>健康提醒</span>
        <el-button link type="primary" @click="$router.push('/elder/notifications')">
          查看全部{{ stats.unread ? `（${stats.unread} 条未读）` : '' }}
        </el-button>
      </div>
      <div v-if="alerts.length" class="alert-list">
        <div v-for="a in alerts" :key="a.warning_id" class="alert-item" @click="$router.push(`/elder/alert/${a.warning_id}`)">
          <div class="alert-item__main">
            <StatusTag kind="level" :value="a.level" />
            <span class="alert-item__title">{{ a.title }}</span>
          </div>
          <div class="alert-item__value">{{ a.value_text }}</div>
          <StatusTag kind="status" :value="a.status" />
        </div>
      </div>
      <div v-else class="ky-empty">暂无待处理的健康提醒，继续保持 👍</div>
    </div>

    <!-- 快捷服务 -->
    <div class="ky-card">
      <div class="ky-card__title">快捷服务</div>
      <div class="service-grid">
        <div v-for="s in services" :key="s.path" class="service-item" @click="$router.push(s.path)">
          <div class="service-item__icon">{{ s.icon }}</div>
          <div class="service-item__name">{{ s.name }}</div>
          <div class="ky-sub">{{ s.desc }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getUser } from '@/utils/auth'
import { listProfiles, getLatestIndicators, listAlerts, summaryStats } from '@/api'
import StatusTag from '@/components/common/StatusTag.vue'

const user = getUser()
const profileId = ref(null)
const latest = ref({})
const alerts = ref([])
const stats = ref({ unread: 0 })

const today = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: 'long', day: 'numeric', weekday: 'long' })
const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 12) return '早上好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const bpText = computed(() => {
  const b = latest.value.BLOOD_PRESSURE
  return b ? `${b.values.systolic}/${b.values.diastolic}` : '—'
})

const services = [
  { name: '健康档案', icon: '📋', desc: '查看基本信息与慢病标签', path: '/elder/profile' },
  { name: '指标录入', icon: '✍️', desc: '录入血压、血糖等指标', path: '/elder/input' },
  { name: '指标历史', icon: '📈', desc: '查看历史与趋势图', path: '/elder/history' },
  { name: 'AI 健康咨询', icon: '🤖', desc: 'AI 助手随时答疑', path: '/elder/ai' },
  { name: '健康打卡', icon: '✅', desc: '每日健康习惯打卡', path: '/elder/checkin' },
  { name: '用药信息', icon: '💊', desc: '管理常用药物', path: '/elder/medication' },
]

function fmtTime(iso) {
  const d = new Date(iso)
  return `${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
}

async function load() {
  try {
    const profiles = await listProfiles(user.user_id, 'ELDER')
    if (!profiles.length) return
    profileId.value = profiles[0].profile_id

    const [lat, alertRes, statRes] = await Promise.all([
      getLatestIndicators(profileId.value),
      listAlerts({ user_id: user.user_id, page: 1, page_size: 5 }),
      summaryStats(user.user_id),
    ])
    latest.value = lat
    alerts.value = alertRes.list
    stats.value = statRes
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
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 16px;
}
.alert-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.alert-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 16px;
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  flex-wrap: wrap;
}
.alert-item:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-card);
}
.alert-item__main {
  display: flex;
  align-items: center;
  gap: 10px;
}
.alert-item__title {
  font-weight: 600;
}
.alert-item__value {
  color: var(--color-danger);
  font-weight: 600;
}
.service-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}
.service-item {
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}
.service-item:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-card);
}
.service-item__icon {
  font-size: 34px;
  margin-bottom: 8px;
}
.service-item__name {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
}
</style>
