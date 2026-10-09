<template><div v-if="failure" class="api-error-banner"><el-alert :type="failure.code===1002?'warning':'error'" :closable="true" :title="failure.message" @close="failure=null"><span>此次加载或操作未成功，页面中的空列表不代表已经核实没有记录。</span><el-button style="margin-left:12px" size="small" @click="reload">重新加载页面</el-button></el-alert></div><router-view /><footer class="ky-disclaimer">健康建议不构成医疗诊断。如出现严重或持续不适，请及时联系医生或拨打急救电话。</footer></template>
<script setup>
import {ref,onMounted,onBeforeUnmount,watch} from 'vue'
import {useRoute} from 'vue-router'
const failure=ref(null),route=useRoute()
function onError(event){failure.value=event.detail}
function reload(){window.location.reload()}
onMounted(()=>window.addEventListener('ky:api-error',onError))
onBeforeUnmount(()=>window.removeEventListener('ky:api-error',onError))
watch(()=>route.fullPath,()=>failure.value=null)
</script>
<style scoped>.api-error-banner{padding:12px 24px;background:#fff}.ky-disclaimer{padding:18px 24px;color:#687885;text-align:center;font-size:14px;line-height:1.7}</style>
