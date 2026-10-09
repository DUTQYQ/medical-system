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
}

const conf = computed(() => {
  const map = MAPS[props.kind] || MAPS.status
  return map[props.value] || { text: String(props.value ?? '—'), type: 'info' }
})
</script>
