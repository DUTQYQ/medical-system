<template>
  <div class="ky-layout ky-elder" :class="fontClass" :style="{ '--fs-body': fontSize + 'px' }">
    <header class="ky-topbar">
      <div class="ky-topbar__left">
        <span class="ky-logo">智能康养系统</span>
        <span class="ky-role-tag">老人端</span>
      </div>
      <div class="ky-topbar__right">
        <el-button-group>
          <el-button @click="fontScale = Math.max(0, fontScale - 1)" aria-label="缩小字号">A−</el-button>
          <el-button @click="fontScale = Math.min(2, fontScale + 1)" aria-label="放大字号">A+</el-button>
        </el-button-group>
        <span class="ky-topbar__user">{{ user?.name || '未登录' }}</span>
        <el-button link type="primary" @click="onLogout">退出登录</el-button>
      </div>
    </header>

    <nav class="ky-nav">
      <ul class="ky-nav__list">
        <li
          v-for="item in navs"
          :key="item.path"
          class="ky-nav__item"
          :class="{ 'ky-nav__item--active': isActive(item) }"
          @click="$router.push(item.path)"
        >
          {{ item.label }}
          <span v-if="item.badge && unread > 0" class="ky-dot" />
        </li>
      </ul>
    </nav>

    <main class="ky-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUser, clearAuth } from '@/utils/auth'
import { getUnreadCount } from '@/api'

const route = useRoute()
const router = useRouter()
const user = getUser()
const unread = ref(0)
const fontScale = ref(0)
const fontSize = computed(() => 19 + fontScale.value * 2)
const fontClass = computed(() => ({ 'ky-font-lg': fontScale.value === 1, 'ky-font-xl': fontScale.value === 2 }))

const navs = [
  { label: '首页', path: '/elder/home', prefixes: ['/elder/home'] },
  { label: '健康档案', path: '/elder/profile', prefixes: ['/elder/profile'] },
  { label: '指标录入', path: '/elder/input', prefixes: ['/elder/input', '/elder/history', '/elder/trend'] },
  { label: 'AI 健康咨询', path: '/elder/ai', prefixes: ['/elder/ai', '/elder/consult-history'] },
  { label: '通知中心', path: '/elder/notifications', prefixes: ['/elder/notifications', '/elder/alert'], badge: true },
  { label: '我的', path: '/elder/mine', prefixes: ['/elder/mine', '/elder/bind', '/elder/checkin', '/elder/medication'] },
]

function isActive(item) {
  return item.prefixes.some((p) => route.path.startsWith(p))
}

async function refreshUnread() {
  if (!user) return
  try {
    const d = await getUnreadCount(user.user_id)
    unread.value = d.count
  } catch {
    /* 忽略轮询错误 */
  }
}

function onLogout() {
  clearAuth()
  router.replace('/login')
}

let timer
onMounted(() => {
  refreshUnread()
  timer = setInterval(refreshUnread, 30000)
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.ky-topbar__user {
  font-size: 16px;
  color: var(--color-text-regular);
}
</style>
