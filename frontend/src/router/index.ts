import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/store/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'login', component: () => import('@/pages/Login.vue') },
    {
      path: '/board', name: 'board', component: () => import('@/pages/Leaderboard.vue'),
      meta: { requiresAuth: true },
    },
    {
      path: '/leave', name: 'leave', component: () => import('@/pages/Leave.vue'),
      meta: { requiresAuth: true },
    },
    { path: '/public/:slug', name: 'public-board', component: () => import('@/pages/PublicBoard.vue') },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login' }
  }
  return true
})

export default router
