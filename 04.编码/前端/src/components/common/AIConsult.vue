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

    <div class="ai-layout">
      <!-- 左侧会话列表 -->
      <aside class="ai-sessions ky-card">
        <el-button type="primary" style="width: 100%" @click="newSession">＋ 新建咨询</el-button>
        <div class="ai-sessions__list">
          <div
            v-for="s in sessions"
            :key="s.session_id"
            class="ai-session-item"
            :class="{ 'ai-session-item--active': s.session_id === currentSessionId }"
            @click="openSession(s)"
          >
            <div class="ai-session-item__title">{{ s.title }}</div>
            <div class="ai-session-item__time">{{ fmtDate(s.created_at) }}</div>
            <el-button link type="danger" size="small" @click.stop="removeSession(s)">删除</el-button>
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
                <el-tag v-for="q in presets" :key="q" class="ai-preset" @click="sendPreset(q)">{{ q }}</el-tag>
              </div>
            </div>

            <div v-for="m in messages" :key="m.message_id" class="ai-msg">
              <div class="ai-msg__bubble" :class="m.role === 'user' ? 'ky-bubble--user' : 'ky-bubble--ai'">
                <div v-if="m.role === 'assistant'" class="ai-msg__meta">
                  <el-tag size="small" :type="safetyType(m.safety_level)">{{ safetyText(m.safety_level) }}</el-tag>
                  <el-tag size="small" type="info" v-if="m.intent">{{ intentText(m.intent) }}</el-tag>
                </div>
                <div style="white-space: pre-wrap">{{ m.content }}</div>
                <div v-if="m.sources && m.sources.length" class="ai-msg__sources">
                  参考来源：{{ m.sources.join('、') }}
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
import { ElMessage } from 'element-plus'
import { getUser } from '@/utils/auth'
import { fmtDate } from '@/api/mock'
import { listProfiles, listSessions, createSession, listMessages, sendMessage, deleteSession } from '@/api'
import DisclaimerFooter from './DisclaimerFooter.vue'

const route = useRoute()
const scope = route.meta.scope || 'elder'
const user = getUser()

const profiles = ref([])
const selectedProfileId = ref(null)
const sessions = ref([])
const currentSessionId = ref(null)
const messages = ref([])
const input = ref('')
const loading = ref(false)
const chatBody = ref(null)

const presets = ['我血压有点高要注意什么？', '血糖高了怎么吃？', '最近睡眠不好怎么办？']

const SAFETY = { SAFE: { text: '健康建议', type: 'success' }, NEED_CONFIRM: { text: '需谨慎', type: 'warning' }, ESCALATE: { text: '紧急', type: 'danger' } }
const INTENT = { HEALTH_CONSULT: '健康咨询', MEDICATION_CONSULT: '用药咨询', EMERGENCY: '紧急求助' }

function safetyType(v) {
  return (SAFETY[v] || { type: 'info' }).type
}
function safetyText(v) {
  return (SAFETY[v] || { text: v || '建议' }).text
}
function intentText(v) {
  return INTENT[v] || v || ''
}

async function loadProfiles() {
  try {
    profiles.value = await listProfiles(user.user_id, scope === 'family' ? 'FAMILY' : 'ELDER')
    if (profiles.value.length) selectedProfileId.value = profiles.value[0].profile_id
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function loadSessions() {
  try {
    sessions.value = await listSessions({ user_id: user.user_id })
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function openSession(s) {
  currentSessionId.value = s.session_id
  try {
    messages.value = await listMessages(s.session_id)
    await scrollBottom()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function newSession() {
  if (!selectedProfileId.value) return
  try {
    const s = await createSession({ user_id: user.user_id, profile_id: selectedProfileId.value, title: '新的健康咨询' })
    sessions.value.unshift(s)
    currentSessionId.value = s.session_id
    messages.value = []
    input.value = ''
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function removeSession(s) {
  try {
    await deleteSession(s.session_id)
    sessions.value = sessions.value.filter((x) => x.session_id !== s.session_id)
    if (currentSessionId.value === s.session_id) {
      currentSessionId.value = null
      messages.value = []
    }
  } catch (e) {
    ElMessage.error(e.message)
  }
}

function onSwitchProfile() {
  currentSessionId.value = null
  messages.value = []
}

async function send() {
  const content = input.value.trim()
  if (!content || !selectedProfileId.value) return
  if (!currentSessionId.value) await newSession()
  if (!currentSessionId.value) return

  input.value = ''
  messages.value.push({ message_id: 'tmp-u', session_id: currentSessionId.value, role: 'user', content })
  loading.value = true
  await scrollBottom()
  try {
    const aiMsg = await sendMessage({
      session_id: currentSessionId.value,
      profile_id: selectedProfileId.value,
      content,
    })
    messages.value.push(aiMsg)
    if (!sessions.value.some((s) => s.session_id === currentSessionId.value)) {
      sessions.value = await listSessions({ user_id: user.user_id })
    }
  } catch (e) {
    messages.value.push({ message_id: 'tmp-e', session_id: currentSessionId.value, role: 'assistant', content: e.message, safety_level: null })
    ElMessage.error(e.message)
  } finally {
    loading.value = false
    await scrollBottom()
  }
}

function sendPreset(q) {
  input.value = q
  send()
}

async function scrollBottom() {
  await nextTick()
  if (chatBody.value) chatBody.value.scrollTop = chatBody.value.scrollHeight
}

onMounted(async () => {
  await loadProfiles()
  await loadSessions()
})
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
