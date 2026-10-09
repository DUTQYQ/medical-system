export default [{
  path: '/admin', meta: { role: 'ADMIN', scope: 'admin' }, component: () => import('../components/common/StaffLayout.vue'), redirect: '/admin/statistics',
  children: [
    { path: 'profiles', component: () => import('../views/admin/Profiles.vue') },
    { path: 'profile/edit', component: () => import('../views/elder/ProfileEdit.vue') },
    { path: 'statistics', component: () => import('../views/admin/Statistics.vue') },
    { path: 'users', component: () => import('../views/admin/Users.vue') },
    { path: 'thresholds', component: () => import('../views/admin/Thresholds.vue') },
    { path: 'indicators', component: () => import('../views/admin/Indicators.vue') },
    { path: 'knowledge', component: () => import('../views/admin/Knowledge.vue') },
    { path: 'bindings', component: () => import('../views/elder/BindConfirm.vue') },
    { path: 'alerts', component: () => import('../components/common/AlertList.vue') },
    { path: 'alert/:id', component: () => import('../components/common/AlertDetail.vue') },
    { path: 'mine', component: () => import('../components/common/ProfileCenter.vue') },
  ],
}]
