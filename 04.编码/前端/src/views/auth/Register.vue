<template>
  <div class="ky-auth-wrap">
    <div class="ky-auth-box">
      <div class="ky-auth-box__title">注册账号</div>
      <div class="ky-auth-box__sub">仅支持老人、家属自助注册</div>

      <el-form :model="form" label-position="top" @submit.prevent>
        <el-form-item label="身份">
          <el-radio-group v-model="form.role">
            <el-radio-button label="ELDER">我是老人</el-radio-button>
            <el-radio-button label="FAMILY">我是家属</el-radio-button>
          </el-radio-group>
          <div class="ky-sub" style="margin-top: 6px">照护人员 / 管理员账号由机构后台统一开通</div>
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="form.name" placeholder="请输入姓名" maxlength="20" />
        </el-form-item>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="请输入 11 位手机号" maxlength="11" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="6-20 位密码" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="form.confirm" type="password" show-password placeholder="再次输入密码" />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="onRegister">注 册</el-button>
      </el-form>

      <div style="text-align: center; margin-top: 16px">
        <el-link type="primary" @click="$router.push('/login')">已有账号？去登录</el-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { register } from '@/api'

const router = useRouter()
const form = reactive({ role: 'ELDER', name: '', phone: '', password: '', confirm: '' })
const loading = ref(false)

async function onRegister() {
  if (!form.name.trim()) return ElMessage.warning('请输入姓名')
  if (!/^1\d{10}$/.test(form.phone)) return ElMessage.warning('请输入正确的 11 位手机号')
  if (form.password.length < 6) return ElMessage.warning('密码至少 6 位')
  if (form.password !== form.confirm) return ElMessage.warning('两次输入的密码不一致')
  loading.value = true
  try {
    await register({ role: form.role, name: form.name, phone: form.phone, password: form.password })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}
</script>
