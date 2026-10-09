export default [{
  path: '/care', meta: { role: 'CARE', scope: 'care' }, component: () => import('../components/common/StaffLayout.vue'), redirect: '/care/elders',
  children: [
    { path: 'profile/edit', component: () => import('../views/elder/ProfileEdit.vue') },
    { path: 'elders', component: () => import('../views/care/Elders.vue') },
    { path: 'elder/:id', component: () => import('../views/care/ElderDetail.vue') },
    { path: 'alerts', component: () => import('../components/common/AlertList.vue') },
    { path: 'alert/:id', component: () => import('../components/common/AlertDetail.vue') },
    { path: 'handles', component: () => import('../views/care/Handles.vue') },
    { path: 'input', component: () => import('../components/common/HealthInput.vue') },
    { path: 'mine', component: () => import('../components/common/ProfileCenter.vue') },
  ],
}]
