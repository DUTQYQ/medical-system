<template>
  <div class="ky-page">
    <div class="ky-page-header">
      <h2 class="ky-page-title">咨询历史</h2>
      <el-button type="primary" @click="$router.push('/elder/ai')">＋ 发起新咨询</el-button>
    </div>

    <div class="ky-card">
      <el-table :data="sessions" style="width: 100%" v-loading="loading">
        <el-table-column prop="title" label="会话标题" min-width="200" />
        <el-table-column label="创建时间" min-width="180">
          <template #default="{ row }">{{ fmtDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="openSession(row)">查看</el-button>
            <el-button link type="danger" @click="removeSession(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!sessions.length && !loading" class="ky-empty">暂无历史咨询会话</div>
    </div>

    <el-dialog v-model="dialogVisible" :title="currentSession?.title" width="640px">
      <div class="dialog-chat">
        <div v-for="m in dialogMessages" :key="m.message_id" class="ai-msg">
          <div class="ky-bubble" :class="m.role === 'user' ? 'ky-bubble--user' : 'ky-bubble--ai'">{{ m.content }}</div>
        </div>
        <div v-if="!dialogMessages.length" class="ky-empty">暂无消息</div>
      </div>
      <template #footer>
        <el-button @click="dialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="$router.push('/elder/ai')">继续咨询</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUser } from '@/utils/auth'
import { fmtDate } from '@/api/mock'
import { listSessions, listMessages, deleteSession } from '@/api'

const user = getUser()
const sessions = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const currentSession = ref(null)
const dialogMessages = ref([])

async function load() {
  loading.value = true
  try {
    sessions.value = await listSessions({ user_id: user.user_id })
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

async function openSession(s) {
  currentSession.value = s
  try {
    dialogMessages.value = await listMessages(s.session_id)
    dialogVisible.value = true
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function removeSession(s) {
  await ElMessageBox.confirm(`确定删除会话「${s.title}」吗？`, '提示', { type: 'warning' })
  try {
    await deleteSession(s.session_id)
    ElMessage.success('已删除')
    load()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.dialog-chat {
  max-height: 420px;
  overflow-y: auto;
}
.ai-msg {
  margin-bottom: 12px;
  display: flex;
}
</style>
