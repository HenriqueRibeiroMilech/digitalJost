import { createRouter, createWebHistory } from 'vue-router'

export default createRouter({
  history: createWebHistory('/app/'),
  routes: [
    { path: '/', redirect: '/eventos' },
    {
      path: '/eventos',
      name: 'events',
      component: () => import('@/features/events/pages/EventsPage.vue'),
    },
    {
      path: '/demandas/solicitacoes',
      name: 'demand-requests',
      component: () => import('@/features/demands/pages/RequestsPage.vue'),
    },
    {
      path: '/:pathMatch(.*)*',
      component: () => import('@/app/pages/NotFoundPage.vue'),
    },
  ],
})
