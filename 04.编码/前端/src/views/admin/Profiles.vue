<template><div class="ky-page" v-loading="loading"><div class="ky-page-header"><h2 class="ky-page-title">健康档案管理</h2><el-button type="primary" @click="$router.push('/admin/profile/edit')">创建老人档案</el-button></div><div class="ky-card"><el-table :data="rows"><el-table-column prop="name" label="姓名" /><el-table-column prop="user_id" label="所属账号" /><el-table-column prop="birthday" label="出生日期" /><el-table-column prop="emergency_contact" label="紧急联系人" /><el-table-column prop="emergency_phone" label="联系电话" /><el-table-column label="操作"><template #default="{row}"><el-button link type="primary" @click="$router.push('/admin/profile/edit?id='+row.profile_id)">编辑</el-button><el-button link type="danger" @click="remove(row)">删除</el-button></template></el-table-column></el-table><el-alert v-if="error" :title="error" type="error" :closable="false" /></div></div></template>
<script setup>
import {ref,onMounted} from 'vue'
import {ElMessage,ElMessageBox} from 'element-plus'
import {listProfiles,deleteProfile} from '@/api'
const rows=ref([]),loading=ref(false),error=ref('')
async function load(){loading.value=true;error.value='';try{rows.value=await listProfiles()}catch(e){error.value=e.message}finally{loading.value=false}}
async function remove(row){try{await ElMessageBox.confirm('确认删除档案 '+row.name+'？历史处理记录保留。','删除档案',{type:'warning'});await deleteProfile(row.profile_id);await load();ElMessage.success('档案已删除')}catch(e){if(!['cancel','close'].includes(e))ElMessage.error(e.message)}}
onMounted(load)
</script>
