<template>
<div class="ky-layout"><header class="ky-topbar"><div class="ky-topbar__left"><span class="ky-logo">智能康养系统</span><span class="ky-role-tag">{{ admin ? '管理员端' : '护工端' }}</span></div><div class="ky-topbar__right"><span>{{ user?.name }}</span><el-button link type="primary" @click="signOut">退出登录</el-button></div></header>
<nav class="ky-nav"><ul class="ky-nav__list"><li v-for="n in navs" :key="n.path" class="ky-nav__item" tabindex="0" role="button" :class="{ 'ky-nav__item--active': route.path.startsWith(n.path) }" @click="router.push(n.path)" @keydown.enter="router.push(n.path)" @keydown.space.prevent="router.push(n.path)">{{ n.label }}<span v-if="n.alert && unread > 0" class="ky-dot" /></li></ul></nav>
<main class="ky-main"><el-alert v-if="pollError" type="warning" :closable="false" title="站内通知连接暂时中断，将自动重试" /><router-view :key="route.fullPath" /></main></div>
</template>
<script setup>
import { computed, ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getUser, clearAuth } from '@/utils/auth'
import { getUnreadCount, logout } from '@/api'
const user = getUser(), route = useRoute(), router = useRouter(), admin = user?.role === 'ADMIN'
const unread = ref(0), pollError = ref(false), base = admin ? '/admin' : '/care'
const navs = computed(() => (admin ? [['统计','statistics'],['用户管理','users'],['健康档案','profiles'],['预警阈值','thresholds'],['指标配置','indicators'],['知识库','knowledge'],['绑定审核','bindings'],['预警中心','alerts'],['我的','mine']] : [['负责老人','elders'],['预警中心','alerts'],['处理记录','handles'],['我的','mine']]).map(([label,path]) => ({ label, path: base + '/' + path, alert: path === 'alerts' })))
let timer
async function poll() { if (!getUser()?.privacy_consent?.accepted) return; try { unread.value = (await getUnreadCount()).count; pollError.value = false } catch { pollError.value = true } }
async function signOut() { try { await logout() } catch {} finally { clearAuth(); router.replace('/login') } }
onMounted(() => { poll(); timer = setInterval(poll, 30000) })
onBeforeUnmount(() => clearInterval(timer))
</script>
