<template><div class="ky-page" v-loading="loading"><div class="ky-page-header"><h2 class="ky-page-title">预警中心</h2><el-button @click="load">刷新</el-button></div><div class="ky-card"><el-select v-model="status" clearable placeholder="全部处理状态" @change="page=1;load()"><el-option v-for="(label,value) in statuses" :key="value" :label="label" :value="value" /></el-select><el-table :data="rows" style="margin-top:16px" @row-click="open"><el-table-column prop="elder_name" label="老人" /><el-table-column prop="title" label="预警" /><el-table-column prop="value_text" label="异常值" /><el-table-column label="风险"><template #default="{row}"><StatusTag kind="level" :value="row.level" /></template></el-table-column><el-table-column label="处理"><template #default="{row}"><StatusTag :value="row.status" /></template></el-table-column><el-table-column label="阅读"><template #default="{row}"><StatusTag kind="read" :value="row.my_read_status" /></template></el-table-column><el-table-column prop="created_at" label="触发时间" min-width="160" /></el-table><el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="prev,pager,next,total" @current-change="load" /><el-alert v-if="error" type="error" :title="error" :closable="false" /></div></div></template>
<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { listAlerts } from '@/api'
import StatusTag from './StatusTag.vue'
const route=useRoute(), router=useRouter(), rows=ref([]), status=ref(''), page=ref(1), total=ref(0), loading=ref(false), error=ref('')
const statuses={ PENDING:'待处理', PROCESSING:'处理中', RESOLVED:'已处理', IGNORED:'已忽略' }
async function load(){ loading.value=true; error.value=''; try{const d=await listAlerts({status:status.value||undefined,page:page.value,page_size:20});rows.value=d.list;total.value=d.total}catch(e){error.value=e.message}finally{loading.value=false}}
function open(row){router.push('/'+route.meta.scope+'/alert/'+row.warning_id)}
onMounted(load)
</script>
