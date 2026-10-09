<template><div class="ky-page" v-loading="loading"><div class="ky-page-header"><h2 class="ky-page-title">我的预警处理记录</h2><el-button @click="load">刷新</el-button></div><div class="ky-card"><el-table :data="rows"><el-table-column prop="elder_name" label="老人" /><el-table-column prop="action" label="处理方式" /><el-table-column prop="result" label="结论" min-width="260" /><el-table-column prop="created_at" label="处理时间" min-width="160" /><el-table-column label="预警"><template #default="{row}"><el-button link type="primary" @click="$router.push('/care/alert/'+row.warning_id)">查看预警</el-button></template></el-table-column></el-table><el-pagination v-model:current-page="page" :page-size="20" :total="total" layout="prev,pager,next,total" @current-change="load" /><el-alert v-if="error" type="error" :closable="false" :title="error" /></div></div></template>
<script setup>
import {ref,onMounted} from 'vue'
import {listCareHandles} from '@/api'
import {asList} from '@/utils/format'
const rows=ref([]),page=ref(1),total=ref(0),loading=ref(false),error=ref('')
async function load(){loading.value=true;error.value='';try{const d=await listCareHandles({page:page.value,page_size:20});rows.value=asList(d);total.value=d.total??rows.value.length}catch(e){error.value=e.message}finally{loading.value=false}}
onMounted(load)
</script>
