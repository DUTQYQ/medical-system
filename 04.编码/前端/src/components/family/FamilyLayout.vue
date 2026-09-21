<template>
  <div class="ky-layout">
    <header class="ky-topbar">
      <div class="ky-topbar__left">
        <span class="ky-logo">智能康养系统</span>
        <span class="ky-role-tag">家属端</span>
      </div>
      <div class="ky-topbar__right">
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
          @click="$router.push(navTarget(item))"
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
import { getUnreadCount, listElders } from '@/api'

const route = useRoute()
const router = useRouter()
const user = getUser()
const unread = ref(0)
const firstElderId = ref(null)

const navs = [
  { label: '首页', path: '/family/home', target: '/family/home', prefixes: ['/family/home'] },
  { label: '绑定老人', path: '/family/bind', target: '/family/bind', prefixes: ['/family/bind'] },
  { label: '健康概况', path: '/family/elder', target: '/family/elder', prefixes: ['/family/elder', '/family/report', '/family/ai'] },
  { label: '通知中心', path: '/family/notifications', target: '/family/notifications', prefixes: ['/family/notifications', '/family/alert'], badge: true },
  { label: '我的', path: '/family/mine', target: '/family/mine', prefixes: ['/family/mine'] },
]

function navTarget(item) {
  if (item.path === '/family/elder') {
    return firstElderId.value ? `/family/elder/${firstElderId.value}` : '/family/bind'
  }
  return item.target
}

function isActive(item) {
  return item.prefixes.some((p) => route.path.startsWith(p))
}

async function refreshUnread() {
  if (!user) return
  try {
    const d = await getUnreadCount(user.user_id)
    unread.value = d.count
  } catch {
    /* 忽略 */
  }
}

async function loadFirstElder() {
  if (!user) return
  try {
    const elders = await listElders(user.user_id)
    if (elders.length) firstElderId.value = elders[0].profile_id
  } catch {
    /* 忽略 */
  }
}

function onLogout() {
  clearAuth()
  router.replace('/login')
}

let timer
onMounted(() => {
  refreshUnread()
  loadFirstElder()
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
