<template>
  <div class="ky-page ai-page">
    <div class="ky-page-header">
      <h2 class="ky-page-title">AI 健康咨询</h2>
      <div style="display: flex; align-items: center; gap: 12px">
        <span class="ky-sub">咨询对象：</span>
        <el-select v-model="selectedProfileId" style="width: 180px" @change="onSwitchProfile">
          <el-option v-for="p in profiles" :key="p.profile_id" :label="p.name" :value="p.profile_id" />
        </el-select>
      </div>
    </div>

    <el-alert v-if="error" type="error" :closable="false" :title="error" style="margin-bottom:16px" /><el-alert v-if="retrievalInfo?.semantic_embedding === false" type="info" :closable="false" title="当前知识检索使用离线词形向量，尚未启用语义 Embedding；来源匹配能力有此限制。" style="margin-bottom:16px" /><el-alert v-if="modelStatus==='BYPASSED_FOR_SAFETY'" type="warning" :closable="false" title="紧急求助提示由安全规则生成，已触发预警；请立即寻求人工医疗帮助。" style="margin-bottom:16px" /><div class="ai-layout">
      <!-- 左侧会话列表 -->
      <aside class="ai-sessions ky-card">
        <el-button type="primary" style="width: 100%" @click="newSession">＋ 新建咨询</el-button>
        <div class="ai-sessions__list">
          <div
            v-for="s in sessions"
            :key="s.session_id"
            class="ai-session-item" tabindex="0" role="button"
            :class="{ 'ai-session-item--active': s.session_id === currentSessionId }"
            @click="openSession(s)" @keydown.enter="openSession(s)"
          >
            <div class="ai-session-item__title">{{ s.title }}</div>
            <div class="ai-session-item__time">{{ fmtDate(s.created_at) }}</div>
            <el-button v-if="s.can_delete !== false" link type="danger" size="small" @click.stop="removeSession(s)">删除</el-button>
          </div>
          <div v-if="!sessions.length" class="ky-empty">暂无历史会话</div>
        </div>
      </aside>

      <!-- 右侧聊天窗 -->
      <section class="ai-chat ky-card">
        <div v-if="!profiles.length" class="ky-empty">
          {{ scope === 'family' ? '尚未绑定老人，请先前往「绑定老人」完成绑定后再咨询' : '暂无可咨询的健康档案' }}
        </div>

        <template v-else>
          <div ref="chatBody" class="ai-chat__body">
            <div v-if="!messages.length" class="ai-chat__hint">
              <p>您好，我是您的 AI 健康助手。您可以问我血压、血糖、睡眠、运动、用药等问题。</p>
              <div class="ai-presets">
                <el-tag v-for="q in presets" :key="q" class="ai-preset" tabindex="0" role="button" @click="sendPreset(q)" @keydown.enter="sendPreset(q)">{{ q }}</el-tag>
              </div>
            </div>

            <div v-for="m in messages" :key="m.message_id" class="ai-msg">
              <div class="ai-msg__bubble" :class="m.role === 'user' ? 'ky-bubble--user' : 'ky-bubble--ai'">
                <div v-if="m.role === 'assistant'" class="ai-msg__meta">
                  <el-tag size="small" :type="safetyType(m.safety_level)">{{ safetyText(m.safety_level) }}</el-tag>
                  <el-tag size="small" type="info" v-if="m.intent">{{ intentText(m.intent) }}</el-tag><el-tag v-if="m.agent" size="small">Agent: {{ m.agent }}</el-tag>
                </div>
                <div style="white-space: pre-wrap">{{ m.content }}</div>
                <div v-if="m.sources && m.sources.length" class="ai-msg__sources">
                  参考来源：{{ m.sources.map(x => typeof x === 'string' ? x : x.title || x.source || '知识条目').join('、') }}
                </div>
              </div>
            </div>

            <div v-if="loading" class="ai-msg">
              <div class="ky-bubble ky-bubble--ai">正在思考…</div>
            </div>
          </div>

          <div class="ai-chat__input">
            <el-input
              v-model="input"
              type="textarea"
              :rows="2"
              maxlength="500"
              show-word-limit
              placeholder="请输入您想咨询的健康问题…"
              @keydown.enter.exact.prevent="send"
            />
            <el-button type="primary" :disabled="!input.trim() || loading" @click="send">发送</el-button>
          </div>
        </template>
      </section>
    </div>

    <DisclaimerFooter />
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { fmtDate } from '@/utils/format'
import { listProfiles, listSessions, listMessages, sendMessage, deleteSession } from '@/api'
import DisclaimerFooter from './DisclaimerFooter.vue'
const route=useRoute(),scope=route.meta.scope||'elder'
const profiles=ref([]),selectedProfileId=ref(null),sessions=ref([]),currentSessionId=ref(null),messages=ref([]),input=ref(''),loading=ref(false),chatBody=ref(null),error=ref('')
const retrievalInfo=ref(null), modelStatus=ref('')
const presets=['我血压有点高要注意什么？','血糖高了怎么吃？','最近睡眠不好怎么办？']
const SAFETY={L1:{text:'L1 日常健康建议',type:'success'},L2:{text:'L2 数据建议',type:'info'},L3:{text:'L3 异常关注',type:'warning'},L4:{text:'L4 紧急求助',type:'danger'}}
const INTENT={NORMAL:'日常咨询',DATA:'健康数据',ABNORMAL:'异常关注',EMERGENCY:'紧急求助'}
function safetyType(v){return SAFETY[v]?.type||'info'}
function safetyText(v){return SAFETY[v]?.text||v||'健康建议'}
function intentText(v){return INTENT[v]||v}
async function loadSessions(){if(!selectedProfileId.value)return;try{sessions.value=await listSessions({profile_id:selectedProfileId.value})}catch(e){error.value=e.message}}
async function openSession(s){currentSessionId.value=s.session_id;selectedProfileId.value=s.profile_id;try{messages.value=await listMessages(s.session_id);await scrollBottom()}catch(e){error.value=e.message}}
function newSession(){currentSessionId.value=null;messages.value=[];input.value='';error.value=''}
async function removeSession(s){try{await ElMessageBox.confirm('确认删除会话 '+s.title+'？','删除会话',{type:'warning'});await deleteSession(s.session_id);sessions.value=sessions.value.filter(x=>x.session_id!==s.session_id);if(currentSessionId.value===s.session_id)newSession()}catch(e){if(!['cancel','close'].includes(e))ElMessage.error(e.message)}}
function onSwitchProfile(){newSession();loadSessions()}
async function send(){
 const content=input.value.trim();if(!content||!selectedProfileId.value||loading.value)return
 loading.value=true;error.value='';input.value=''
 const tmp={message_id:'pending-'+Date.now(),role:'user',content};messages.value.push(tmp);await scrollBottom()
 try{const reply=await sendMessage({session_id:currentSessionId.value,profile_id:selectedProfileId.value,content});currentSessionId.value=reply.session_id;messages.value=await listMessages(reply.session_id);retrievalInfo.value=reply.retrieval||null;modelStatus.value=reply.model_status||'';await loadSessions()}
 catch(e){error.value=e.message;input.value=content;messages.value=messages.value.filter(m=>m!==tmp);await loadSessions()}
 finally{loading.value=false;await scrollBottom()}
}
function sendPreset(q){input.value=q;send()}
async function scrollBottom(){await nextTick();if(chatBody.value)chatBody.value.scrollTop=chatBody.value.scrollHeight}
onMounted(async()=>{try{profiles.value=await listProfiles();selectedProfileId.value=profiles.value.find(p=>p.profile_id===Number(route.query.profile_id))?.profile_id||profiles.value[0]?.profile_id;await loadSessions()}catch(e){error.value=e.message}})
</script>


<style scoped>
.ai-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 16px;
}
.ai-sessions__list {
  margin-top: 16px;
  max-height: 560px;
  overflow-y: auto;
}
.ai-session-item {
  padding: 12px;
  border: 1px solid var(--color-border-light);
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
}
.ai-session-item--active {
  border-color: var(--color-primary);
  background: var(--color-primary-light);
}
.ai-session-item__title {
  font-weight: 600;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ai-session-item__time {
  font-size: 13px;
  color: var(--color-text-secondary);
}
.ai-chat {
  display: flex;
  flex-direction: column;
  min-height: 560px;
}
.ai-chat__body {
  flex: 1;
  overflow-y: auto;
  padding: 8px 4px;
  max-height: 480px;
}
.ai-chat__hint {
  text-align: center;
  color: var(--color-text-secondary);
  padding: 40px 0;
}
.ai-presets {
  margin-top: 16px;
  display: flex;
  gap: 8px;
  justify-content: center;
  flex-wrap: wrap;
}
.ai-preset {
  cursor: pointer;
}
.ai-msg {
  margin-bottom: 16px;
  display: flex;
}
.ai-msg__bubble {
  max-width: 72%;
  padding: 12px 16px;
  border-radius: 12px;
  line-height: 1.7;
}
.ai-msg__meta {
  display: flex;
  gap: 6px;
  margin-bottom: 6px;
}
.ai-msg__sources {
  margin-top: 8px;
  font-size: 13px;
  color: var(--color-text-secondary);
}
.ai-chat__input {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  padding-top: 12px;
  border-top: 1px solid var(--color-border-light);
}
@media (max-width: 820px) {
  .ai-layout {
    grid-template-columns: 1fr;
  }
}
</style>
