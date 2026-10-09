<template><div class="ky-page" v-loading="loading"><div class="ky-page-header"><h2 class="ky-page-title">预警阈值配置</h2><el-button @click="load">刷新</el-button></div><el-alert type="info" :closable="false" title="保存后由后台配置即时生效，新录入记录按新阈值检测，历史预警仍保留原结果。" style="margin-bottom:16px" /><div class="ky-card"><el-table :data="rows"><el-table-column prop="indicator_name" label="指标" /><el-table-column prop="unit" label="单位" /><el-table-column prop="level0_range" label="正常范围" /><el-table-column prop="level1_range" label="Ⅰ级" /><el-table-column prop="level2_range" label="Ⅱ级" /><el-table-column prop="level3_range" label="Ⅲ级" /><el-table-column label="操作"><template #default="{row}"><el-button link type="primary" @click="edit(row)">修改</el-button></template></el-table-column></el-table><el-alert v-if="error" type="error" :closable="false" :title="error" /></div><el-dialog v-model="dialog" title="编辑预警阈值" width="min(560px,95vw)"><el-form label-position="top"><el-form-item v-for="level in [0,1,2,3]" :key="level" :label="level===0?'正常范围':'风险'+level+'级范围'"><el-input v-model="form['level'+level+'_range']" placeholder="支持 min~max、>=value、<value，多个范围用英文逗号分隔" /></el-form-item><el-form-item label="启用阈值检测"><el-switch v-model="form.enabled" /></el-form-item></el-form><template #footer><el-button @click="dialog=false">取消</el-button><el-button type="primary" :loading="saving" @click="save">保存到后台</el-button></template></el-dialog></div></template>
<script setup>
import {ref,onMounted} from 'vue'
import {ElMessage} from 'element-plus'
import {listAdminThresholds,saveThreshold} from '@/api'
import {asList} from '@/utils/format'
const rows=ref([]),form=ref({}),dialog=ref(false),loading=ref(false),saving=ref(false),error=ref('')
async function load(){loading.value=true;error.value='';try{rows.value=asList(await listAdminThresholds())}catch(e){error.value=e.message}finally{loading.value=false}}
function edit(row){form.value={...row};dialog.value=true}
async function save(){saving.value=true;try{const p=Object.fromEntries(['level0_range','level1_range','level2_range','level3_range','enabled'].map(k=>[k,form.value[k]]));await saveThreshold(form.value.config_id,p);dialog.value=false;await load();ElMessage.success('阈值已保存，新录入即时生效')}catch(e){ElMessage.error(e.message)}finally{saving.value=false}}
onMounted(load)
</script>
