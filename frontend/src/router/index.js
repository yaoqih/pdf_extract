import { createRouter, createWebHistory } from 'vue-router'
import MainWorkspace from '../views/MainWorkspace.vue'
import FieldConfiguration from '../views/FieldConfiguration.vue'

const routes = [
  {
    path: '/',
    name: 'MainWorkspace',
    component: MainWorkspace
  },
  {
    path: '/config',
    name: 'FieldConfiguration',
    component: FieldConfiguration
  },
  // Keep old /case/:id route for now if PageProcessingDetails relies on it directly
  // or redirect/remove if no longer needed by direct navigation.
  // For now, let's assume PageProcessingDetails is used as a child component
  // and doesn't need its own top-level route.
  // {
  //   path: '/case/:id',
  //   name: 'CaseDetail', // This name might conflict if CaseDetail.vue is removed
  //   component: () => import('../views/CaseDetail.vue'), // Example of lazy loading old component
  //   props: true
  // }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL), // Ensure correct base for Vite
  routes
})

export default router 