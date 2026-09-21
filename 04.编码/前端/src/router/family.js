// 家属端路由（梁霁鸣）
// 顶部导航 5 项：首页 / 绑定老人 / 健康概况 / 通知中心 / 我的
// AI 咨询与预警详情与老人端共用同一组件，仅入口与数据权限不同（meta.scope）。

export default [
  {
    path: '/family',
    component: () => import('../components/family/FamilyLayout.vue'),
    redirect: '/family/home',
    children: [
      { path: 'home', name: 'FamilyHome', component: () => import('../views/family/Home.vue') },
      { path: 'bind', name: 'FamilyBind', component: () => import('../views/family/BindElder.vue') },
      { path: 'elder/:id', name: 'FamilyElderOverview', component: () => import('../views/family/ElderOverview.vue') },
      { path: 'report', name: 'FamilyReport', component: () => import('../views/family/HealthReport.vue') },
      { path: 'notifications', name: 'FamilyNotifications', component: () => import('../views/family/NotificationCenter.vue') },
      { path: 'ai', name: 'FamilyAI', meta: { scope: 'family' }, component: () => import('../components/common/AIConsult.vue') },
      { path: 'alert/:id', name: 'FamilyAlertDetail', meta: { scope: 'family' }, component: () => import('../components/common/AlertDetail.vue') },
      { path: 'mine', name: 'FamilyMine', component: () => import('../components/common/ProfileCenter.vue') },
    ],
  },
]
