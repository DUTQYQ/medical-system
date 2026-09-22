<template>
  <div class="ky-page" style="max-width: 760px">
    <div class="ky-page-header">
      <h2 class="ky-page-title">健康打卡</h2>
      <span class="ky-sub">今日完成 {{ doneCount }}/{{ items.length }} 项</span>
    </div>

    <div class="ky-card">
      <el-progress :percentage="progress" :stroke-width="18" :text-inside="true" />
    </div>

    <div class="ky-card">
      <div class="checkin-list">
        <div
          v-for="it in items"
          :key="it.key"
          class="checkin-item"
          :class="{ 'checkin-item--done': it.done }"
          @click="it.done = !it.done"
        >
          <div class="checkin-item__icon">{{ it.icon }}</div>
          <div class="checkin-item__name">{{ it.name }}</div>
          <div class="checkin-item__state">{{ it.done ? '✅ 已完成' : '○ 待完成' }}</div>
        </div>
      </div>
      <div class="ky-sub" style="margin-top: 16px">点击卡片即可标记完成。坚持每日打卡，养成良好健康习惯（演示数据，刷新后重置）。</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const items = ref([
  { key: 'bp', name: '测量血压', icon: '🩺', done: false },
  { key: 'sugar', name: '测量血糖', icon: '🩸', done: false },
  { key: 'med', name: '按时服药', icon: '💊', done: false },
  { key: 'sport', name: '适量运动 30 分钟', icon: '🚶', done: false },
  { key: 'sleep', name: '规律作息', icon: '😴', done: false },
])

const doneCount = computed(() => items.value.filter((i) => i.done).length)
const progress = computed(() => Math.round((doneCount.value / items.value.length) * 100))
</script>

<style scoped>
.checkin-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.checkin-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 18px 20px;
  border: 2px solid var(--color-border-light);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
}
.checkin-item--done {
  border-color: var(--color-success);
  background: #f0f9eb;
}
.checkin-item__icon {
  font-size: 28px;
}
.checkin-item__name {
  flex: 1;
  font-size: 18px;
  font-weight: 600;
}
.checkin-item__state {
  color: var(--color-text-secondary);
}
.checkin-item--done .checkin-item__state {
  color: var(--color-success);
  font-weight: 600;
}
</style>
