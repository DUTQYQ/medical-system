// 认证相关的本地存储与角色跳转辅助
// 归属：梁霁鸣（公共工具 utils/）

const TOKEN_KEY = 'kangyang_token'
const USER_KEY = 'kangyang_user'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token)
}

export function getUser() {
  try {
    return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
  } catch {
    return null
  }
}

export function setUser(user) {
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

// 角色 → 登录后跳转首页（后端只返回 role，前端不自行判断角色含义，仅做跳转映射）
export const ROLE_HOME = {
  ELDER: '/elder',
  FAMILY: '/family',
  CARE: '/care',
  ADMIN: '/admin',
}

export function roleHome(role) {
  return ROLE_HOME[role] || '/login'
}
