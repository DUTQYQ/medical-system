<template>
  <div class="ky-page" style="max-width: 760px">
    <div class="ky-page-header">
      <div style="display: flex; align-items: center; gap: 12px">
        <el-button @click="$router.back()">← 返回</el-button>
        <h2 class="ky-page-title">{{ isEdit ? '编辑档案' : '新增档案' }}</h2>
      </div>
    </div>

    <div class="ky-card">
      <el-form :model="form" label-position="top">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12">
            <el-form-item label="姓名">
              <el-input v-model="form.name" placeholder="请输入姓名" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="性别">
              <el-radio-group v-model="form.gender">
                <el-radio-button label="F">女</el-radio-button>
                <el-radio-button label="M">男</el-radio-button>
              </el-radio-group>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="出生日期">
              <el-date-picker v-model="form.birthday" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="血型">
              <el-select v-model="form.blood_type" style="width: 100%">
                <el-option v-for="b in ['A', 'B', 'AB', 'O']" :key="b" :label="b + ' 型'" :value="b" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="身高（cm）">
              <el-input-number v-model="form.height" :min="100" :max="220" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="体重（kg）">
              <el-input-number v-model="form.weight" :min="30" :max="200" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="慢病标签">
              <el-select v-model="form.chronic_tags" multiple filterable allow-create default-first-option style="width: 100%" placeholder="选择或输入慢病标签">
                <el-option v-for="t in chronicOptions" :key="t" :label="t" :value="t" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="既往病史">
              <el-input v-model="form.medical_history" type="textarea" :rows="3" placeholder="如：2018 年脑梗，恢复良好" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="过敏史">
              <el-input v-model="form.allergy" placeholder="如：青霉素过敏，无则留空" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="主联系人">
              <el-input v-model="form.emergency_contact" placeholder="姓名" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="主联系人电话">
              <el-input v-model="form.emergency_phone" placeholder="手机号" maxlength="11" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="备用联系人">
              <el-input v-model="form.backup_contact" placeholder="姓名，可留空" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12">
            <el-form-item label="备用联系人电话">
              <el-input v-model="form.backup_phone" placeholder="手机号，可留空" maxlength="11" />
            </el-form-item>
          </el-col>
        </el-row>

        <div style="display: flex; gap: 12px; margin-top: 8px">
          <el-button type="primary" size="large" :loading="saving" @click="onSave">保存</el-button>
          <el-button size="large" @click="$router.back()">取消</el-button>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getUser } from '@/utils/auth'
import { getProfile, createProfile, updateProfile } from '@/api'

const route = useRoute()
const router = useRouter()
const user = getUser()
const editId = route.query.id ? Number(route.query.id) : null
const isEdit = computed(() => !!editId)
const saving = ref(false)

const chronicOptions = ['高血压', '2 型糖尿病', '冠心病', '骨质疏松', '慢阻肺', '失眠']

const form = reactive({
  name: '',
  gender: 'F',
  birthday: '',
  blood_type: 'A',
  height: 160,
  weight: 60,
  chronic_tags: [],
  medical_history: '',
  allergy: '',
  emergency_contact: '',
  emergency_phone: '',
  backup_contact: '',
  backup_phone: '',
})

onMounted(async () => {
  if (editId) {
    try {
      const p = await getProfile(editId)
      Object.keys(form).forEach((k) => {
        if (p[k] !== undefined && p[k] !== null) form[k] = p[k]
      })
    } catch (e) {
      ElMessage.error(e.message)
    }
  }
})

async function onSave() {
  if (!form.name.trim()) return ElMessage.warning('请填写姓名')
  if (!form.emergency_contact.trim() || !form.emergency_phone.trim()) return ElMessage.warning('请填写主联系人与电话')
  saving.value = true
  try {
    if (isEdit.value) {
      await updateProfile(editId, { ...form })
      ElMessage.success('档案已更新')
    } else {
      await createProfile({ ...form, user_id: user.user_id, age: calcAge(form.birthday) })
      ElMessage.success('档案已创建')
    }
    router.push('/elder/profile')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

function calcAge(birthday) {
  if (!birthday) return 70
  const b = new Date(birthday)
  return Math.floor((Date.now() - b.getTime()) / (365.25 * 24 * 3600 * 1000))
}
</script>
