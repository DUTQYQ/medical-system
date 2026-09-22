<template>
  <div class="ky-page">
    <div class="ky-page-header">
      <h2 class="ky-page-title">个人中心</h2>
    </div>

    <div class="ky-card">
      <div class="profile-head">
        <div class="profile-avatar">{{ (user?.name || '康')[0] }}</div>
        <div>
          <div class="profile-name">{{ user?.name || '未登录' }} <el-tag size="small" type="primary">{{ roleText }}</el-tag></div>
          <div class="ky-sub">手机号：{{ user?.phone || '—' }}</div>
        </div>
      </div>

      <el-descriptions :column="1" border style="margin-top: 20px">
        <el-descriptions-item label="姓名">{{ user?.name || '—' }}</el-descriptions-item>
        <el-descriptions-item label="手机号">{{ user?.phone || '—' }}</el-descriptions-item>
        <el-descriptions-item label="角色">{{ roleText }}</el-descriptions-item>
        <el-descriptions-item label="账号 ID">{{ user?.user_id || '—' }}</el-descriptions-item>
      </el-descriptions>
    </div>

    <div class="ky-card">
      <div class="ky-card__title">快捷入口</div>
      <div class="quick-grid">
        <div v-for="l in links" :key="l.path" class="quick-item" @click="$router.push(l.path)">
          <div class="quick-icon">{{ l.icon }}</div>
          <div>{{ l.label }}</div>
        </div>
      </div>
    </div>

    <div class="ky-card">
      <div class="ky-card__title">关于系统</div>
      <p class="ky-sub" style="line-height: 1.8">
        基于 AI 智能体的康养系统（大工软院 2026 秋季实训 · 第 17 组）。<br />
        本系统面向老人提供健康档案管理、指标监测、AI 健康咨询与异常预警；面向家属提供远程照护与健康概况查看。<br />
        适老化设计：大字号（正文 ≥18px）、大触控热区、主流程 ≤3 步。
      </p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { getUser } from '@/utils/auth'

const router = useRouter()
const user = getUser()

const ROLE_TEXT = { ELDER: '老人', FAMILY: '家属', CARE: '照护人员', ADMIN: '管理员' }
const roleText = computed(() => ROLE_TEXT[user?.role] || user?.role || '—')

const links = computed(() => {
  if (user?.role === 'FAMILY') {
    return [
      { label: '绑定老人', path: '/family/bind', icon: '👨‍👩‍👧' },
      { label: '健康日报周报', path: '/family/report', icon: '📊' },
    ]
  }
  return [
    { label: '绑定确认', path: '/elder/bind', icon: '🔗' },
    { label: '健康打卡', path: '/elder/checkin', icon: '✅' },
    { label: '用药信息', path: '/elder/medication', icon: '💊' },
  ]
})
</script>

<style scoped>
.profile-head {
  display: flex;
  align-items: center;
  gap: 20px;
}
.profile-avatar {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: var(--color-primary);
  color: #fff;
  font-size: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.profile-name {
  font-size: 22px;
  font-weight: 600;
  margin-bottom: 6px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.quick-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}
.quick-item {
  border: 1px solid var(--color-border-light);
  border-radius: 12px;
  padding: 20px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s;
}
.quick-item:hover {
  border-color: var(--color-primary);
  box-shadow: var(--shadow-card);
}
.quick-icon {
  font-size: 32px;
  margin-bottom: 8px;
}
</style>
