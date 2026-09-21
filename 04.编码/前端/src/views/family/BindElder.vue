<template>
  <div class="ky-page" style="max-width: 860px">
    <div class="ky-page-header">
      <h2 class="ky-page-title">绑定老人</h2>
    </div>

    <div class="ky-card">
      <div class="ky-card__title">发起绑定申请</div>
      <el-alert
        type="info"
        :closable="false"
        style="margin-bottom: 20px"
        title="绑定流程：提交申请 → 老人确认 → 生效"
        description="生效后您才能查看老人的健康档案、指标趋势与预警信息（设计决策 D-02 三段式绑定）。"
      />
      <el-form :model="form" label-position="top">
        <el-form-item label="老人手机号（其在档案中登记的主/备联系号码）">
          <el-input v-model="form.phone" placeholder="请输入老人手机号" maxlength="11" />
        </el-form-item>
        <el-form-item label="您与老人的关系">
          <el-select v-model="form.relation" style="width: 100%">
            <el-option v-for="r in relations" :key="r" :label="r" :value="r" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注（可选）">
          <el-input v-model="form.note" placeholder="如：日常照护、代买药" maxlength="50" />
        </el-form-item>
        <el-button type="primary" size="large" :loading="submitting" @click="onSubmit">提交申请</el-button>
      </el-form>
    </div>

    <div class="ky-card">
      <div class="ky-card__title">我的绑定</div>
      <el-table :data="binds" style="width: 100%">
        <el-table-column prop="elder_name" label="老人" width="120" />
        <el-table-column prop="relation" label="关系" width="100" />
        <el-table-column prop="note" label="备注" />
        <el-table-column label="状态" width="110">
          <template #default="{ row }">
            <StatusTag kind="bind" :value="row.status" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button v-if="row.status === 'APPROVED'" link type="danger" @click="onUnbind(row)">解绑</el-button>
            <el-button v-else-if="row.status === 'PENDING'" link type="info" disabled>等待确认</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!binds.length" class="ky-empty">暂无绑定记录</div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUser } from '@/utils/auth'
import { submitBind, listMyBinds, unbind } from '@/api'
import StatusTag from '@/components/common/StatusTag.vue'

const user = getUser()
const relations = ['儿子', '女儿', '女婿', '儿媳', '孙子', '孙女', '配偶', '其他亲属']
const form = reactive({ phone: '', relation: '儿子', note: '' })
const binds = ref([])
const submitting = ref(false)

async function load() {
  try {
    binds.value = await listMyBinds(user.user_id)
  } catch (e) {
    ElMessage.error(e.message)
  }
}

async function onSubmit() {
  if (!/^1\d{10}$/.test(form.phone)) return ElMessage.warning('请输入正确的老人手机号')
  submitting.value = true
  try {
    await submitBind({ family_user_id: user.user_id, elder_phone: form.phone, relation: form.relation, note: form.note })
    ElMessage.success('申请已提交，等待老人确认')
    form.phone = ''
    form.note = ''
    load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    submitting.value = false
  }
}

async function onUnbind(row) {
  await ElMessageBox.confirm(`确定解除与「${row.elder_name}」的绑定吗？解除后将无法查看其健康数据。`, '解绑确认', { type: 'warning' })
  try {
    await unbind(row.bind_id)
    ElMessage.success('已解绑')
    load()
  } catch (e) {
    ElMessage.error(e.message)
  }
}

onMounted(load)
</script>
