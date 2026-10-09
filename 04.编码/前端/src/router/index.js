import { createRouter, createWebHistory } from 'vue-router'
import authRoutes from './auth'
import elderRoutes from './elder'
import familyRoutes from './family'
import careRoutes from './care'
import adminRoutes from './admin'
import systemRoutes from './system'
import { getToken, getUser, setUser, clearAuth, roleHome } from '../utils/auth'
import { getMe } from '../api/auth'
const router = createRouter({ history: createWebHistory(), routes: [...authRoutes, ...elderRoutes, ...familyRoutes, ...careRoutes, ...adminRoutes, ...systemRoutes] })
router.beforeEach(async to => {
  const publicPage = ['/login', '/register', '/forgot'].includes(to.path)
  if (!getToken()) return publicPage ? true : { path: '/login', query: { redirect: to.fullPath } }
  try {
    const user = await getMe()
    setUser(user)
    if (publicPage) return roleHome(user.role)
    if (user.privacy_consent?.accepted !== true && to.path !== roleHome(user.role) + '/mine') return roleHome(user.role) + '/mine'
    if (to.meta.role && to.meta.role !== user.role) return { path: '/forbidden' }
    return true
  } catch (e) {
    if ([1001, 1003].includes(e.code)) { clearAuth(); return publicPage ? true : '/login' }
    // 服务短暂断开时仍允许展示已有登录用户的错误状态；所有数据访问仍需服务器鉴权。
    if (!getUser()) { clearAuth(); return publicPage ? true : '/login' }
    if (to.meta.role && to.meta.role !== getUser().role) return '/forbidden'
    return true
  }
})
export default router
