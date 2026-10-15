<template><div class="threshold-evidence"><template v-if="assessment"><p><strong>检测时使用的健康阈值</strong> · 风险 {{ assessment.risk_level }} 级 · {{ fmtDate(assessment.assessed_at) }}</p><div v-for="(rule,key) in assessment.thresholds || {}" :key="key"><el-tag :type="rule.source==='PERSONAL'?'success':'info'">{{ rule.source==='PERSONAL'?'个体设置':'院内默认' }}</el-tag> {{ rule.indicator_name || key }}，正常范围 {{ rule.level0_range }} {{ rule.unit }}，版本 {{ rule.version_id ?? '默认' }}</div><p class="ky-sub">此处展示录入时保存的检测依据，后续修改配置不会改变这条历史结果。</p></template><p v-else class="ky-sub">本条记录不含指标阈值快照，仅展示已保存的检测结果。</p></div></template>
<script setup>
import {fmtDate} from '@/utils/format'
defineProps({assessment:{type:Object,default:null}})
</script>
<style scoped>.threshold-evidence{line-height:1.9;margin-top:12px}.threshold-evidence .el-tag{margin-right:6px}</style>
