<template><div class="ky-auth-wrap"><div class="ky-auth-box"><h2>无权限访问</h2><p>当前账号不能使用此角色页面。健康数据权限由服务器校验。</p><el-button type="primary" @click="$router.replace(roleHome(getUser()?.role))">返回我的首页</el-button></div></div></template>
<script setup>import { roleHome, getUser } from '@/utils/auth'</script>
