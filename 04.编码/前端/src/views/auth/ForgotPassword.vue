<template>
  <div class="ky-auth-wrap">
    <div class="ky-auth-box">
      <div class="ky-auth-box__title">找回密码</div>
      <div class="ky-auth-box__sub">通过手机号重置登录密码</div>

      <el-form :model="form" label-position="top" @submit.prevent>
        <el-form-item label="手机号">
          <el-input v-model="form.phone" placeholder="请输入注册手机号" maxlength="11" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="form.password" type="password" show-password placeholder="6-20 位新密码" />
        </el-form-item>
        <el-form-item label="确认新密码">
          <el-input v-model="form.confirm" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="onSubmit">提交</el-button>
      </el-form>

      <div style="text-align: center; margin-top: 16px">
        <el-link type="primary" @click="$router.push('/login')">返回登录</el-link>
      </div>

      <el-alert type="info" :closable="false" style="margin-top: 20px" title="提示" description="本功能为原型演示，mock 阶段不真正发送验证码、不修改后端密码。" />
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'

const router = useRouter()
const form = reactive({ phone: '', password: '', confirm: '' })
const loading = ref(false)

async function onSubmit() {
  if (!/^1\d{10}$/.test(form.phone)) return ElMessage.warning('请输入正确的 11 位手机号')
  if (form.password.length < 6) return ElMessage.warning('新密码至少 6 位')
  if (form.password !== form.confirm) return ElMessage.warning('两次输入的密码不一致')
  loading.value = true
  // mock：直接提示成功并返回登录
  setTimeout(() => {
    loading.value = false
    ElMessage.success('密码已重置，请使用新密码登录')
    router.push('/login')
  }, 600)
}
</script>
