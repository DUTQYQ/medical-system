export default [
  { path: '/', redirect: '/login' },
  { path: '/forbidden', component: () => import('../views/auth/Forbidden.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/login' },
]
