import axios from 'axios'
import { getToken, clearAuth } from './auth'
const request = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '/api', timeout: 60000 })
request.interceptors.request.use(config => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})
function fail(body, status) {
  const error = new Error(body?.message || (status === 403 ? '无权限访问' : '请求失败，请稍后重试'))
  error.code = body?.code || (status === 401 ? 1001 : status === 403 ? 1002 : 5001)
  if ([1001, 1003].includes(error.code)) {
    clearAuth()
    if (window.location.pathname !== '/login') window.location.assign(`/login?expired=${error.code}`)
  }
  window.dispatchEvent(new CustomEvent('ky:api-error', { detail: { message: error.message, code: error.code } }))
  return error
}
request.interceptors.response.use(response => {
  const body = response.data
  if (body?.code !== 0) return Promise.reject(fail(body, response.status))
  return body.data
}, error => {
  if (error.response) return Promise.reject(fail(error.response.data, error.response.status))
  const failure = new Error(error.code === 'ECONNABORTED' ? '请求超时，请重试；已提交的记录请先刷新确认' : '无法连接服务器，请确认后端服务已启动')
  window.dispatchEvent(new CustomEvent('ky:api-error', { detail: { message: failure.message, code: 5001 } }))
  return Promise.reject(failure)
})
export default request
