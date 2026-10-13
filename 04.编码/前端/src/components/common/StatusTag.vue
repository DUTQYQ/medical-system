<template>
  <el-tag :type="conf.type" effect="light" size="small">{{ conf.text }}</el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  // kind: level(预警等级) | status(处理状态) | summary(AI摘要状态) | read(已读) | bind(绑定状态)
  kind: { type: String, default: 'status' },
  value: { type: [String, Number, Boolean], default: '' },
})

const MAPS = {
  level: {
    0: { text: '正常', type: 'success' },
    1: { text: 'Ⅰ级', type: 'warning' },
    2: { text: 'Ⅱ级', type: 'danger' },
    3: { text: 'Ⅲ级', type: 'danger' },
  },
  status: {
    PENDING: { text: '待处理', type: 'danger' },
    PROCESSING: { text: '处理中', type: 'warning' },
    RESOLVED: { text: '已处理', type: 'success' },
    IGNORED: { text: '已忽略', type: 'info' },
  },
  summary: {
    SUCCESS: { text: 'AI 摘要已生成', type: 'success' },
    PENDING: { text: 'AI 摘要生成中', type: 'info' },
    FAILED: { text: 'AI 摘要生成失败', type: 'danger' },
    SKIPPED: { text: '本条未生成摘要', type: 'info' },
  },
  read: {
    READ: { text: '已读', type: 'info' },
    UNREAD: { text: '未读', type: 'danger' },
    true: { text: '已读', type: 'info' },
    false: { text: '未读', type: 'danger' },
  },
  bind: {
    PENDING: { text: '待确认', type: 'warning' },
    APPROVED: { text: '已生效', type: 'success' },
    REJECTED: { text: '已拒绝', type: 'info' },
    REVOKED: { text: '已解绑', type: 'info' },
  },
  abnormal: {
    1: { text: '异常', type: 'danger' },
    0: { text: '正常', type: 'success' },
    true: { text: '异常', type: 'danger' },
    false: { text: '正常', type: 'success' },
  },
  judgement: {
    '健康': { text: '健康', type: 'success' },
    '需关注（波动）': { text: '需关注（波动）', type: 'warning' },
    '轻度异常': { text: '轻度异常', type: 'warning' },
    '较高异常': { text: '较高异常', type: 'danger' },
    '高风险异常': { text: '高风险异常', type: 'danger' },
    '未记录': { text: '未记录', type: 'info' },
  },
  suitability: {
    '适合': { text: '适合', type: 'success' },
    '需谨慎': { text: '需谨慎', type: 'warning' },
    '不建议': { text: '不建议', type: 'danger' },
  },
  fluctuation: {
    true: { text: '需关注', type: 'warning' },
    false: { text: '平稳', type: 'success' },
  },
}

const conf = computed(() => {
  const map = MAPS[props.kind] || MAPS.status
  return map[props.value] || { text: String(props.value ?? '—'), type: 'info' }
})
</script>
