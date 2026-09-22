// 系统配置模块 api（mock）
// 【临时 mock】待丘宇乾替换为真实实现
// 关键：阈值不硬编码到页面，统一从此处读取（R-04）
import { indicators, thresholds, respond } from './mock'

export async function getIndicators() {
  return respond(indicators)
}

export async function getThresholds() {
  return respond(thresholds)
}
