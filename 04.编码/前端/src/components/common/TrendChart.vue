<template>
  <div>
    <div ref="chartRef" class="trend-chart" :style="{ height: height + 'px' }" />
  </div>
</template>

<script setup>
// ECharts 趋势图（老人端/家属端共用）
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  dates: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  abnormalIndexes: { type: Array, default: () => [] },
  unit: { type: String, default: '' },
  height: { type: Number, default: 360 },
})

const emit = defineEmits(['point-click'])

const chartRef = ref(null)
let chart = null

function render() {
  if (!chartRef.value) return
  if (!chart) chart = echarts.init(chartRef.value)

  const markPointData = props.abnormalIndexes.map((i) => ({
    coord: [props.dates[i], props.series[0] ? props.series[0].values[i] : 0],
    value: '异常',
  }))

  const option = {
    tooltip: { trigger: 'axis' },
    legend: { data: props.series.map((s) => s.name), top: 0 },
    grid: { left: 55, right: 24, top: 44, bottom: 40 },
    xAxis: { type: 'category', data: props.dates, boundaryGap: false },
    yAxis: { type: 'value', name: props.unit },
    series: props.series.map((s, idx) => ({
      name: s.name,
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 7,
      data: s.values,
      markPoint:
        idx === 0 && markPointData.length
          ? {
              data: markPointData,
              itemStyle: { color: '#f56c6c' },
              label: { color: '#fff', fontSize: 10 },
            }
          : undefined,
    })),
  }
  chart.setOption(option, true)
  chart.off('click')
  chart.on('click', (p) => {
    if (p.componentType === 'markPoint' && p.data && p.data.coord) {
      emit('point-click', { date: p.data.coord[0] })
    }
  })
}

function resize() {
  chart && chart.resize()
}

onMounted(() => {
  render()
  window.addEventListener('resize', resize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart && chart.dispose()
})

watch(() => [props.dates, props.series, props.abnormalIndexes], render, { deep: true })
</script>

<style scoped>
.trend-chart {
  width: 100%;
}
</style>
