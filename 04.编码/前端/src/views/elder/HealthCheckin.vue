<template><div class="ky-page" style="max-width:760px"><div class="ky-page-header"><h2 class="ky-page-title">【选配】本机健康打卡</h2></div><div class="ky-card"><el-alert type="info" :closable="false" title="本机备忘，仅保存在当前浏览器，未同步服务器。勾选不会代替真实指标录入。" /><p>日期：{{ today }}</p><el-checkbox-group v-model="done" @change="save"><div v-for="item in items" :key="item" style="padding:16px"><el-checkbox :label="item">{{ item }}</el-checkbox></div></el-checkbox-group></div></div></template>
<script setup>
import {ref} from 'vue'
import {getUser} from '@/utils/auth'
import {todayOnly} from '@/utils/format'
import {ElMessage} from 'element-plus'
const today=todayOnly(),key='ky-checkin-'+getUser()?.user_id+'-'+today,items=['测量血压','测量血糖','按医嘱服药','适量活动','规律作息']
let stored=[];try{stored=JSON.parse(localStorage.getItem(key)||'[]')}catch{}
const done=ref(stored)
function save(){try{localStorage.setItem(key,JSON.stringify(done.value))}catch{ElMessage.error('本机存储不可用，打卡未保存')}}
</script>
