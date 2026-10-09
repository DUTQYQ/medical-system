<template>
  <div class="ky-auth-wrap">
    <div class="ky-auth-box">
      <div class="ky-auth-box__title">智能康养系统</div>
      <div class="ky-auth-box__sub">基于 AI 智能体的老人健康管理平台</div>

      <el-form :model="form" label-position="top" @submit.prevent>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="请输入 11 位手机号" maxlength="11" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="请输入密码" @keyup.enter="onLogin" />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="onLogin">登 录</el-button>
      </el-form>

      <div style="display: flex; justify-content: space-between; margin-top: 16px">
        <el-link type="primary" @click="$router.push('/register')">注册账号</el-link>
        <el-link type="info" @click="$router.push('/forgot')">忘记密码？</el-link>
      </div>

      <el-alert v-if="route.query.expired" type="warning" :closable="false" style="margin-top:24px" :title="route.query.expired === '1003' ? '账号已禁用，请联系管理员' : '会话已过期，请重新登录'" />
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api'
import { setToken, setUser, roleHome } from '@/utils/auth'

const router = useRouter()
const route = useRoute()
const form = reactive({ phone: '', password: '' })
const loading = ref(false)

async function onLogin() {
  if (!/^1\d{10}$/.test(form.phone)) {
    ElMessage.warning('请输入正确的 11 位手机号')
    return
  }
  if (!form.password) {
    ElMessage.warning('请输入密码')
    return
  }
  loading.value = true
  try {
    const data = await login({ phone: form.phone, password: form.password })
    setToken(data.token)
    setUser(data.user)
    ElMessage.success(`欢迎回来，${data.user.name}`)
    router.replace(roleHome(data.user.role))
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}
</script>
