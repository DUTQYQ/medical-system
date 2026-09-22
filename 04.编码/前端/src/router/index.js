// 路由总入口（梁霁鸣）
// 职责：只负责 import 各人的路由文件并拼装 + 全局登录守卫，不写任何具体路由。
// 各角色路由分别维护在 auth.js / elder.js / family.js，care/admin 由对应负责人后续补充。

import { createRouter, createWebHistory } from 'vue-router'
import authRoutes from './auth'
import elderRoutes from './elder'
import familyRoutes from './family'
import { getToken, getUser, roleHome } from '../utils/auth'

const routes = [
  ...authRoutes,
  ...elderRoutes,
  ...familyRoutes,
  { path: '/', redirect: '/login' },
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 全局守卫：未登录跳登录；已登录访问登录页则按角色跳首页
const PUBLIC_PATHS = ['/login', '/register', '/forgot']

router.beforeEach((to) => {
  const hasToken = !!getToken()
  if (!hasToken && !PUBLIC_PATHS.includes(to.path)) {
    return '/login'
  }
  if (hasToken && to.path === '/login') {
    const user = getUser()
    return roleHome(user ? user.role : null)
  }
  return true
})

export default router
