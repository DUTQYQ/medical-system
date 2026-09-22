<template>
  <div class="ky-page" style="max-width: 860px">
    <div class="ky-page-header">
      <h2 class="ky-page-title">绑定确认</h2>
    </div>

    <!-- 待确认 -->
    <div class="ky-card">
      <div class="ky-card__title" style="display: flex; align-items: center; gap: 8px">
        待确认
        <el-badge v-if="pending.length" :value="pending.length" type="danger" />
      </div>
      <div v-if="pending.length" class="bind-list">
        <div v-for="b in pending" :key="b.bind_id" class="bind-item">
          <div class="bind-item__main">
            <div class="bind-item__relation">{{ b.relation }}</div>
            <div class="bind-item__note">申请时间：{{ fmtDate(b.created_at) }}<template v-if="b.note"> · 备注：{{ b.note }}</template></div>
          </div>
          <div class="bind-item__actions">
            <el-button type="primary" @click="approve(b)">同意</el-button>
            <el-button @click="reject(b)">拒绝</el-button>
          </div>
        </div>
      </div>
      <div v-else class="ky-empty">暂无待确认的绑定申请</div>
    </div>

    <!-- 已授权 -->
    <div class="ky-card">
      <div class="ky-card__title">已授权家属</div>
      <div v-if="approved.length">
        <el-table :data="approved" style="width: 100%">
          <el-table-column prop="relation" label="关系" width="140" />
          <el-table-column prop="note" label="备注" />
          <el-table-column label="生效时间" min-width="180">
            <template #default="{ row }">{{ row.confirmed_at ? fmtDate(row.confirmed_at) : '—' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120">
            <template #default="{ row }">
              <el-button link type="danger" @click="onUnbind(row)">解除授权</el-button>
            </template>
          </el-table-column>
        </el-table>
      </div>
      <div v-else class="ky-empty">暂无已授权的家属</div>
    </div>

    <!-- 已拒绝 -->
    <div class="ky-card">
      <div class="ky-card__title">已拒绝</div>
      <div v-if="rejected.length">
        <el-table :data="rejected" style="width: 100%">
          <el-table-column prop="relation" label="关系" width="140" />
          <el-table-column prop="reject_reason" label="拒绝原因">
            <template #default="{ row }">{{ row.reject_reason || '—' }}</template>
          </el-table-column>
        </el-table>
      </div>
      <div v-else class="ky-empty">暂无已拒绝的申请</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUser } from '@/utils/auth'
import { fmtDate } from '@/api/mock'
import { listBindRequests, confirmBind, unbind } from '@/api'

const user = getUser()
const pending = ref([])
const approved = ref([])
const rejected = ref([])

async function load() {
  try {
    const res = await listBindRequests(user.user_id)
    pending.value = res.pending
    approved.value = res.approved
    rejected.value = res.rejected
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function approve(b) {
  await ElMessageBox.confirm(`确认同意该家属绑定为您的「${b.relation}」吗？授权后对方可查看您的健康数据。`, '确认授权', {
    type: 'info',
    confirmButtonText: '同意授权',
  })
  try {
    await confirmBind({ bind_id: b.bind_id, decision: 'APPROVE' })
    ElMessage.success('已授权')
    load()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function reject(b) {
  const { value } = await ElMessageBox.prompt('请输入拒绝原因（可选）', '拒绝申请', {
    confirmButtonText: '确认拒绝',
    cancelButtonText: '取消',
    inputValue: '',
  })
  try {
    await confirmBind({ bind_id: b.bind_id, decision: 'REJECT', reason: value || '' })
    ElMessage.success('已拒绝')
    load()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e.message)
  }
}

async function onUnbind(b) {
  await ElMessageBox.confirm(`确定解除与「${b.relation}」的授权吗？解除后对方将无法查看您的健康数据。`, '解除授权', { type: 'warning' })
  try {
    await unbind(b.bind_id)
    ElMessage.success('已解除授权')
    load()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.bind-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.bind-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px;
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  flex-wrap: wrap;
}
.bind-item__relation {
  font-size: 18px;
  font-weight: 600;
}
.bind-item__note {
  color: var(--color-text-secondary);
  font-size: 14px;
  margin-top: 4px;
}
.bind-item__actions {
  display: flex;
  gap: 8px;
}
</style>
