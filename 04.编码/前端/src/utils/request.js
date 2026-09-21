// Axios 统一封装（对接真实后端时使用）
// 归属：梁霁鸣（公共工具 utils/）
//
// 约定：后端统一响应 { code, message, data }。
//   - code === 0        成功
//   - code === 1001     未登录 / Token 失效 → 跳登录页
//   - code === 1002     无权限 → 提示并返回上一页
//   - 其余非 0          业务错误，展示 message
//
// 说明：本阶段后端尚未实现，页面数据走 src/api/ 的 mock 实现（见 src/api/mock.js），
//      并未真正发起 axios 请求。此文件与 src/api/*.js 一起，供后端完成后无缝切换：
//      只需把 api/*.js 内 mock 调用替换为 request.get/post 即可，页面代码不用改。

import axios from 'axios'
import { ElMessage } from 'element-plus'
import { getToken, clearAuth } from './auth'

const request = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => {
    const body = response.data
    if (body && typeof body.code === 'number') {
      if (body.code === 1001) {
        clearAuth()
        ElMessage.error('会话已过期，请重新登录')
        window.location.href = '/login'
        return Promise.reject(new Error(body.message || '会话已过期'))
      }
      if (body.code === 1002) {
        ElMessage.error(body.message || '无权限访问')
        return Promise.reject(new Error(body.message || '无权限访问'))
      }
      if (body.code !== 0) {
        ElMessage.error(body.message || '请求失败')
        return Promise.reject(new Error(body.message || '请求失败'))
      }
    }
    return body
  },
  (error) => {
    ElMessage.error('网络异常，请稍后重试')
    return Promise.reject(error)
  }
)

export default request
