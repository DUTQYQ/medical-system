// 公共 / 认证页路由（梁霁鸣）：登录、注册、忘记密码
// 这三个页面无角色导航壳，独立居中布局。

export default [
  { path: '/login', name: 'Login', component: () => import('../views/auth/Login.vue') },
  { path: '/register', name: 'Register', component: () => import('../views/auth/Register.vue') },
  { path: '/forgot', name: 'ForgotPassword', component: () => import('../views/auth/ForgotPassword.vue') },
]
