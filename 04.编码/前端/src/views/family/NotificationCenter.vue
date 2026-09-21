<template>
  <div class="ky-page" style="max-width: 860px">
    <div class="ky-page-header">
      <h2 class="ky-page-title">通知中心</h2>
      <el-button @click="onMarkAll">全部标为已读</el-button>
    </div>

    <div class="ky-card">
      <div v-if="notifications.length" class="notice-list">
        <div
          v-for="n in notifications"
          :key="n.notification_id"
          class="notice-item"
          :class="{ 'notice-item--unread': !n.read_status }"
          @click="onClick(n)"
        >
          <div class="notice-item__icon">{{ typeIcon(n.type) }}</div>
          <div class="notice-item__body">
            <div class="notice-item__title">
              {{ n.title }}
              <span v-if="!n.read_status" class="ky-dot" />
            </div>
            <div class="notice-item__content">{{ n.content }}</div>
            <div class="ky-sub">{{ fmtDate(n.created_at) }}</div>
          </div>
          <el-tag v-if="n.read_status" size="small" type="info">已读</el-tag>
          <el-tag v-else size="small" type="danger">未读</el-tag>
        </div>
      </div>
      <div v-else class="ky-empty">暂无通知</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getUser } from '@/utils/auth'
import { fmtDate } from '@/api/mock'
import { listNotifications, markRead, markAllRead } from '@/api'

const router = useRouter()
const user = getUser()
const notifications = ref([])

function typeIcon(type) {
  return { ALERT: '⚠️', BIND: '🔗', SYSTEM: '📋' }[type] || '🔔'
}

async function load() {
  try {
    notifications.value = await listNotifications(user.user_id)
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function onClick(n) {
  if (!n.read_status) {
    await markRead(user.user_id, n.notification_id)
    n.read_status = true
  }
  if (n.ref_type === 'ALERT' && n.ref_id) {
    router.push(`/family/alert/${n.ref_id}`)
  } else if (n.ref_type === 'BIND') {
    router.push('/family/bind')
  }
}

async function onMarkAll() {
  try {
    await markAllRead(user.user_id)
    notifications.value.forEach((n) => (n.read_status = true))
    ElMessage.success('已全部标为已读')
  } catch (e) {
    ElMessage.error(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.notice-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.notice-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  padding: 16px;
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}
.notice-item--unread {
  background: var(--color-primary-light);
  border-color: #b3d8ff;
}
.notice-item:hover {
  box-shadow: var(--shadow-card);
}
.notice-item__icon {
  font-size: 24px;
}
.notice-item__body {
  flex: 1;
}
.notice-item__title {
  font-weight: 600;
  margin-bottom: 4px;
}
.notice-item__content {
  color: var(--color-text-regular);
  margin-bottom: 4px;
}
</style>
