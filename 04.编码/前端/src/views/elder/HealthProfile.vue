<template>
  <div class="ky-page">
    <div class="ky-page-header">
      <h2 class="ky-page-title">健康档案</h2>
      <div style="display: flex; gap: 12px">
        <el-select v-if="profiles.length > 1" v-model="profileId" style="width: 160px" @change="load">
          <el-option v-for="p in profiles" :key="p.profile_id" :label="p.name" :value="p.profile_id" />
        </el-select>
        <el-button @click="$router.push('/elder/profile/edit')">＋ 新增档案</el-button>
        <el-button type="primary" @click="$router.push(`/elder/profile/edit?id=${profileId}`)">编辑档案</el-button>
      </div>
    </div>

    <template v-if="profile">
      <div class="ky-card">
        <div class="ky-card__title">基本信息</div>
        <el-descriptions :column="3" border>
          <el-descriptions-item label="姓名">{{ profile.name }}</el-descriptions-item>
          <el-descriptions-item label="性别">{{ profile.gender === 'M' ? '男' : '女' }}</el-descriptions-item>
          <el-descriptions-item label="年龄">{{ profile.age }} 岁</el-descriptions-item>
          <el-descriptions-item label="出生日期">{{ profile.birthday }}</el-descriptions-item>
          <el-descriptions-item label="身高 / 体重">{{ profile.height }} cm / {{ profile.weight }} kg</el-descriptions-item>
          <el-descriptions-item label="血型">{{ profile.blood_type }} 型</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="ky-card">
        <div class="ky-card__title">慢病标签</div>
        <div v-if="profile.chronic_tags?.length" style="display: flex; gap: 8px; flex-wrap: wrap">
          <el-tag v-for="t in profile.chronic_tags" :key="t" type="warning" effect="light">{{ t }}</el-tag>
        </div>
        <div v-else class="ky-empty">暂无慢病标签</div>
      </div>

      <div class="ky-card">
        <div class="ky-card__title">既往病史与过敏史</div>
        <div class="info-row"><span class="info-label">既往病史：</span>{{ profile.medical_history || '无' }}</div>
        <div class="info-row"><span class="info-label">过敏史：</span>{{ profile.allergy || '无' }}</div>
      </div>

      <div class="ky-card">
        <div class="ky-card__title">紧急联系人</div>
        <el-descriptions :column="2" border>
          <el-descriptions-item label="主联系人">{{ profile.emergency_contact || '—' }}（{{ profile.emergency_phone || '—' }}）</el-descriptions-item>
          <el-descriptions-item label="备用联系人">{{ profile.backup_contact || '—' }}（{{ profile.backup_phone || '—' }}）</el-descriptions-item>
          <el-descriptions-item label="照护人员" :span="2">{{ profile.care_worker || '—' }}（{{ profile.care_phone || '—' }}）</el-descriptions-item>
        </el-descriptions>
      </div>

      <div class="ky-card">
        <div class="ky-card__title">已授权家属</div>
        <div v-if="families.length">
          <el-table :data="families" style="width: 100%">
            <el-table-column prop="relation" label="关系" width="120" />
            <el-table-column prop="note" label="备注" />
            <el-table-column label="状态" width="120">
              <template #default="{ row }">
                <StatusTag kind="bind" :value="row.status" />
              </template>
            </el-table-column>
          </el-table>
        </div>
        <div v-else class="ky-empty">暂无已授权的家属，家属可发起绑定申请，您前往「我的-绑定确认」处理</div>
      </div>
    </template>
    <div v-else class="ky-empty">暂无健康档案，点击右上角「新增档案」创建</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getUser } from '@/utils/auth'
import { listProfiles, listBindRequests } from '@/api'
import StatusTag from '@/components/common/StatusTag.vue'

const user = getUser()
const profiles = ref([])
const profileId = ref(null)
const profile = ref(null)
const families = ref([])

async function load() {
  try {
    profiles.value = await listProfiles(user.user_id, 'ELDER')
    if (profiles.value.length && !profileId.value) profileId.value = profiles.value[0].profile_id
    profile.value = profiles.value.find((p) => p.profile_id === profileId.value) || null
    if (profile.value) {
      const req = await listBindRequests(user.user_id)
      families.value = req.approved
    }
  } catch (e) {
    ElMessage.error(e.message)
  }
}

onMounted(load)
</script>

<style scoped>
.info-row {
  font-size: var(--fs-body);
  line-height: 2;
  color: var(--color-text-regular);
}
.info-label {
  color: var(--color-text-secondary);
  font-weight: 600;
}
</style>
