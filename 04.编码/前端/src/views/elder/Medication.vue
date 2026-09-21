<template>
  <div class="ky-page" style="max-width: 860px">
    <div class="ky-page-header">
      <h2 class="ky-page-title">用药信息</h2>
      <el-button type="primary" @click="openAdd">＋ 添加药品</el-button>
    </div>

    <div class="ky-card">
      <el-table :data="meds" style="width: 100%">
        <el-table-column prop="name" label="药品名称" min-width="140" />
        <el-table-column prop="dose" label="剂量" width="120" />
        <el-table-column prop="frequency" label="频次" width="140" />
        <el-table-column prop="time" label="服药时间" width="160" />
        <el-table-column prop="note" label="备注" min-width="120" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button link type="danger" @click="removeMed(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div v-if="!meds.length" class="ky-empty">暂无用药记录，点击右上角添加</div>
    </div>

    <div class="ky-card">
      <div class="ky-card__title">用药提醒</div>
      <ul class="med-tips">
        <li>请严格遵医嘱服药，勿自行增减剂量或停药；</li>
        <li>注意药物过敏史（参见健康档案「过敏史」）；</li>
        <li>如出现不适，请及时咨询医生或药师。</li>
      </ul>
    </div>

    <el-dialog v-model="dialogVisible" title="添加药品" width="520px">
      <el-form :model="form" label-position="top">
        <el-form-item label="药品名称"><el-input v-model="form.name" placeholder="如：苯磺酸氨氯地平片" /></el-form-item>
        <el-form-item label="剂量"><el-input v-model="form.dose" placeholder="如：5mg" /></el-form-item>
        <el-form-item label="频次">
          <el-select v-model="form.frequency" style="width: 100%">
            <el-option v-for="f in ['每日一次', '每日两次', '每日三次', '睡前一次', '按需服用']" :key="f" :label="f" :value="f" />
          </el-select>
        </el-form-item>
        <el-form-item label="服药时间"><el-input v-model="form.time" placeholder="如：早 8:00" /></el-form-item>
        <el-form-item label="备注"><el-input v-model="form.note" placeholder="可选" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveMed">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'

// 选配页面（用药信息），演示数据保存在当前会话内存中
const meds = ref([
  { id: 1, name: '苯磺酸氨氯地平片', dose: '5mg', frequency: '每日一次', time: '早 8:00', note: '降压' },
  { id: 2, name: '盐酸二甲双胍片', dose: '0.5g', frequency: '每日两次', time: '早晚餐后', note: '降糖' },
])
const dialogVisible = ref(false)
const form = reactive({ name: '', dose: '', frequency: '每日一次', time: '', note: '' })

function openAdd() {
  Object.keys(form).forEach((k) => (form[k] = k === 'frequency' ? '每日一次' : ''))
  dialogVisible.value = true
}

function saveMed() {
  if (!form.name.trim()) return ElMessage.warning('请填写药品名称')
  meds.value.push({ id: Date.now(), ...form })
  dialogVisible.value = false
  ElMessage.success('已添加')
}

function removeMed(row) {
  meds.value = meds.value.filter((m) => m.id !== row.id)
}
</script>

<style scoped>
.med-tips {
  margin: 0;
  padding-left: 20px;
  line-height: 2;
  color: var(--color-text-regular);
}
</style>
