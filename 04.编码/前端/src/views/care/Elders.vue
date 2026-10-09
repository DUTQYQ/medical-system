<template>
  <div class="ky-page" v-loading="loading">
    <div class="ky-page-header"><h2 class="ky-page-title">负责老人工作台</h2><el-button @click="load">刷新</el-button></div>
    <div class="ky-card">
      <el-space wrap>
        <el-select v-model="status" clearable placeholder="全部健康状态" style="width:180px" @change="load"><el-option label="异常优先" value="ABNORMAL" /><el-option label="需关注" value="WATCH" /><el-option label="正常" value="NORMAL" /></el-select>
        <el-date-picker v-model="measuredRange" type="datetimerange" start-placeholder="测量开始时间" end-placeholder="测量结束时间" value-format="YYYY-MM-DDTHH:mm:ss" clearable @change="load" />
      </el-space>
      <p class="ky-sub">按指标实际测量时间筛选负责的老人；结果优先展示异常老人。</p>
      <el-table :data="rows" style="margin-top:16px"><el-table-column prop="elder_name" label="姓名" /><el-table-column prop="age" label="年龄" /><el-table-column prop="address" label="住址" /><el-table-column prop="latest_bp" label="最近血压" /><el-table-column prop="latest_sugar" label="最近血糖" /><el-table-column label="状态"><template #default="{row}"><el-tag :type="row.status==='ABNORMAL'?'danger':row.status==='WATCH'?'warning':row.status==='NORMAL'?'success':'info'">{{ states[row.status] || row.status || '暂无记录' }}</el-tag></template></el-table-column><el-table-column prop="pending_warnings" label="待处理预警" /><el-table-column label="操作"><template #default="{row}"><el-button link type="primary" @click="$router.push('/care/elder/'+row.profile_id)">查看与照护</el-button></template></el-table-column></el-table>
      <el-alert v-if="error" type="error" :closable="false" :title="error" />
    </div>
  </div>
</template>
<script setup>
import { ref,onMounted } from 'vue'
import { listCareElders } from '@/api'
const rows=ref([]),status=ref(''),measuredRange=ref(null),error=ref(''),loading=ref(false),states={ABNORMAL:'异常',WATCH:'需关注',NORMAL:'正常',UNKNOWN:'暂无记录'}
async function load(){loading.value=true;error.value='';try{rows.value=await listCareElders({status:status.value||undefined,start_at:measuredRange.value?.[0],end_at:measuredRange.value?.[1]})}catch(e){error.value=e.message}finally{loading.value=false}}
onMounted(load)
</script>
