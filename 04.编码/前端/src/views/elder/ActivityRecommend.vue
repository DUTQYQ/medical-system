<template>
  <div class="ky-page">
    <div class="ky-page-header">
      <h2 class="ky-page-title">活动推荐</h2>
      <div style="display: flex; gap: 12px">
        <el-select v-if="profiles.length > 1" v-model="profileId" style="width: 160px">
          <el-option v-for="p in profiles" :key="p.profile_id" :label="p.name" :value="p.profile_id" />
        </el-select>
        <el-button @click="load">刷新</el-button>
      </div>
    </div>

    <el-alert type="info" :closable="false" title="结合已记录档案、季节和近期有效指标筛选活动建议；资料不足会提示确认。建议库不代表已发布活动、剩余名额或已完成报名。" style="margin-bottom: 16px" />

    <el-alert v-if="error" type="error" :closable="false" :title="error" style="margin-bottom:16px" />
    <div v-loading="loading">
      <div v-for="a in list" :key="a.activity_id" class="ky-card activity-card" :class="'is-' + suitClass(a.suitability)">
        <div class="activity-card__head">
          <span class="activity-card__name">{{ a.name }}</span>
          <el-tag v-if="a.category" size="small" effect="plain">{{ a.category }}</el-tag>
          <el-tag v-if="a.intensity" size="small" :type="intensityType(a.intensity)" effect="light">{{ intensityText(a.intensity) }}</el-tag>
          <StatusTag kind="suitability" :value="a.suitability" />
        </div>
        <div class="activity-card__desc">{{ a.description }}</div>
        <div class="activity-card__grid">
          <div class="activity-cell">
            <div class="activity-cell__label">活动说明与用途</div>
            <div>{{ a.benefits || '—' }}</div>
          </div>
          <div class="activity-cell">
            <div class="activity-cell__label">建议时长</div>
            <div>{{ a.duration_hint || '—' }}</div>
          </div>
          <div class="activity-cell">
            <div class="activity-cell__label">推荐理由</div>
            <div>
              <el-tag v-for="r in a.reasons" :key="r" size="small" type="info" effect="plain" style="margin: 0 6px 4px 0">{{ r }}</el-tag>
              <span v-if="!a.reasons?.length">—</span>
            </div>
          </div>
          <div class="activity-cell">
            <div class="activity-cell__label">注意事项</div>
            <div>{{ a.contraindications || '需与工作人员核实注意事项' }}</div>
          </div>
        </div>
        <el-button type="primary" :disabled="!a.can_request" @click="requestActivity(a)">申请工作人员协助</el-button>
      </div>
      <div v-if="!loading && !list.length" class="ky-empty">暂无活动推荐</div>
      <p class="ky-sub">活动筛选由已配置规则生成，参与安排须工作人员确认。健康建议不构成医疗诊断。</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listProfiles, getRecommendations } from '@/api'
import StatusTag from '@/components/common/StatusTag.vue'

const INTENSITY = { LOW: { text: '低强度', type: 'success' }, MODERATE: { text: '中强度', type: 'warning' }, HIGH: { text: '高强度', type: 'danger' } }

const profiles = ref([])
const profileId = ref(null)
const list = ref([])
const loading = ref(false), error=ref('')
const route=useRoute(),router=useRouter()
let requestVersion=0
watch(profileId,load,{flush:'sync'})
onBeforeUnmount(()=>{requestVersion++})

function intensityText(v) { return INTENSITY[v]?.text || v }
function intensityType(v) { return INTENSITY[v]?.type || 'info' }
function suitClass(v) { return ({ '可了解': 'ok', '需谨慎': 'warn', '需确认': 'warn', '暂缓参与': 'avoid', '不建议': 'avoid' })[v] || '' }

function requestActivity(activity){
  if(activity.profile_id!==profileId.value||!activity.can_request)return ElMessage.warning('档案已切换或当前建议需要先核验，请刷新后确认')
  router.push({path:'/elder/services',query:{profile_id:activity.profile_id,category:activity.service_category,title:'希望了解或参加'+activity.name,description:'请工作人员核验活动适宜性、陪同要求及实际安排。'}})
}
async function load() {
  const id=profileId.value,ticket=++requestVersion
  list.value=[];error.value=''
  if(!id){loading.value=false;return;}
  loading.value=true
  try {
    const response=await getRecommendations(id)
    if(ticket===requestVersion&&id===profileId.value)list.value=response
  } catch(e) {if(ticket===requestVersion&&id===profileId.value)error.value=e.message}
  finally {if(ticket===requestVersion)loading.value=false}
}
async function initialize(){
  loading.value=true
  try{profiles.value=await listProfiles();const requested=Number(route.query.profile_id);profileId.value=profiles.value.find(p=>p.profile_id===requested)?.profile_id || profiles.value[0]?.profile_id || null;if(!profileId.value)loading.value=false}
  catch(e){error.value=e.message;loading.value=false}
}
onMounted(initialize)
</script>

<style scoped>
.activity-card {
  margin-bottom: 14px;
  border-left: 4px solid var(--color-primary);
}
.activity-card.is-warn { border-left-color: var(--color-warning); }
.activity-card.is-avoid { border-left-color: var(--color-danger); opacity: 0.85; }
.activity-card__head {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 10px;
}
.activity-card__name {
  font-size: 20px;
  font-weight: 700;
}
.activity-card__desc {
  color: var(--color-text-regular);
  line-height: 1.8;
  margin-bottom: 12px;
}
.activity-card__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}
.activity-cell__label {
  font-size: 13px;
  color: var(--color-text-secondary);
  margin-bottom: 4px;
}
</style>
