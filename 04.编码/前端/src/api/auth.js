// 认证模块 api（mock）
// 【临时 mock】待丘宇乾替换为真实实现：request.post('/auth/login', ...)
import { db, respond, fail, delay } from './mock'

// 注册：D-01 规定仅 ELDER / FAMILY 可自助注册（CARE / ADMIN 由后台创建）
export async function register(payload) {
  await delay(400)
  const { phone, role, name } = payload
  if (!phone || !/^1\d{10}$/.test(phone)) throw fail(4001, '请输入正确的 11 位手机号')
  if (db.users[phone]) throw fail(4001, '该手机号已注册')
  if (!['ELDER', 'FAMILY'].includes(role)) throw fail(4002, '该角色不支持自助注册，请联系机构开通')
  const user = {
    user_id: 20000 + Math.floor(Math.random() * 1000),
    name: name || (role === 'ELDER' ? '新用户' : '家属'),
    role,
    phone,
    avatar: '',
  }
  db.users[phone] = user
  return respond({ token: `mock-token-${user.user_id}-${Date.now()}`, user })
}

export async function login(payload) {
  await delay(400)
  const { phone, password } = payload
  if (!phone || !password) throw fail(4001, '请输入手机号和密码')
  const user = db.users[phone]
  if (!user) throw fail(2001, '账号不存在，请先注册')
  // mock 阶段不校验密码；真实实现由后端校验并返回 JWT
  const token = `mock-token-${user.user_id}-${Date.now()}`
  db.tokens[token] = user
  return respond({ token, user })
}

export async function logout() {
  return respond(null)
}

export async function getMe() {
  await delay(120)
  const token = localStorage.getItem('kangyang_token')
  const user = token && db.tokens[token]
  if (!user) throw fail(1001, '未登录或会话已过期')
  return respond(user)
}
