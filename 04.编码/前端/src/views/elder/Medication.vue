<template><div class="ky-page" style="max-width:860px"><div class="ky-page-header"><h2 class="ky-page-title">【选配】本机用药备忘</h2><el-button type="primary" @click="dialog=true">添加备忘</el-button></div><div class="ky-card"><el-alert type="info" :closable="false" title="记录仅保存在当前浏览器，未同步服务器。请按实际医嘱记录，不提供自动开药或改剂量建议。" /><el-table :data="meds" style="margin-top:16px"><el-table-column prop="name" label="药品" /><el-table-column prop="dose" label="医嘱剂量" /><el-table-column prop="frequency" label="频次" /><el-table-column prop="time" label="时间" /><el-table-column prop="note" label="备注" /><el-table-column label="操作"><template #default="{row}"><el-button link type="danger" @click="remove(row)">删除</el-button></template></el-table-column></el-table></div><el-dialog v-model="dialog" title="添加本机备忘" width="min(520px,95vw)"><el-form label-position="top"><el-form-item v-for="(label,key) in fields" :key="key" :label="label"><el-input v-model="form[key]" /></el-form-item></el-form><template #footer><el-button @click="dialog=false">取消</el-button><el-button type="primary" @click="save">保存到本机</el-button></template></el-dialog></div></template>
<script setup>
import {ref,reactive} from 'vue'
import {ElMessage,ElMessageBox} from 'element-plus'
import {getUser} from '@/utils/auth'
const key='ky-medications-'+getUser()?.user_id,fields={name:'药品名称',dose:'医嘱剂量',frequency:'频次',time:'时间',note:'备注'},form=reactive({name:'',dose:'',frequency:'',time:'',note:''}),dialog=ref(false)
let stored=[];try{stored=JSON.parse(localStorage.getItem(key)||'[]')}catch{}
const meds=ref(stored)
function persist(next){try{localStorage.setItem(key,JSON.stringify(next));meds.value=next;return true}catch{ElMessage.error('本机存储不可用，修改未保存');return false}}
function save(){if(!form.name.trim())return ElMessage.warning('请填写药品名称');if(persist([...meds.value,{id:Date.now(),...form}])){dialog.value=false;Object.keys(form).forEach(k=>form[k]='');ElMessage.success('备忘已保存到本机')}}
async function remove(row){try{await ElMessageBox.confirm('删除此本机备忘？','确认删除',{type:'warning'});persist(meds.value.filter(m=>m.id!==row.id))}catch{}}
</script>
