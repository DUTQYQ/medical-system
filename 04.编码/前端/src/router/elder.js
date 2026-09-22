// 老人端路由（梁霁鸣）
// 顶部导航 6 项：首页 / 健康档案 / 指标录入 / AI 健康咨询 / 通知中心 / 我的
// 其中「健康档案」「指标录入」「我的」为分组，组内子页面通过页内链接进入。

export default [
  {
    path: '/elder',
    component: () => import('../components/elder/ElderLayout.vue'),
    redirect: '/elder/home',
    children: [
      { path: 'home', name: 'ElderHome', component: () => import('../views/elder/Home.vue') },
      // 健康档案
      { path: 'profile', name: 'ElderProfile', component: () => import('../views/elder/HealthProfile.vue') },
      { path: 'profile/edit', name: 'ElderProfileEdit', component: () => import('../views/elder/ProfileEdit.vue') },
      // 指标录入
      { path: 'input', name: 'ElderInput', component: () => import('../views/elder/IndicatorInput.vue') },
      { path: 'history', name: 'ElderHistory', component: () => import('../views/elder/IndicatorHistory.vue') },
      { path: 'trend', name: 'ElderTrend', component: () => import('../views/elder/TrendChart.vue') },
      // AI 健康咨询（共用组件）
      { path: 'ai', name: 'ElderAI', meta: { scope: 'elder' }, component: () => import('../components/common/AIConsult.vue') },
      { path: 'consult-history', name: 'ElderConsultHistory', component: () => import('../views/elder/ConsultHistory.vue') },
      // 通知中心 + 预警详情（共用组件）
      { path: 'notifications', name: 'ElderNotifications', component: () => import('../views/elder/NotificationCenter.vue') },
      { path: 'alert/:id', name: 'ElderAlertDetail', meta: { scope: 'elder' }, component: () => import('../components/common/AlertDetail.vue') },
      // 我的（选配 + 个人中心）
      { path: 'mine', name: 'ElderMine', component: () => import('../components/common/ProfileCenter.vue') },
      { path: 'bind', name: 'ElderBind', component: () => import('../views/elder/BindConfirm.vue') },
      { path: 'checkin', name: 'ElderCheckin', component: () => import('../views/elder/HealthCheckin.vue') },
      { path: 'medication', name: 'ElderMedication', component: () => import('../views/elder/Medication.vue') },
    ],
  },
]
