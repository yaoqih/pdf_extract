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

router.afterEach((to, from) => {
  // 当从任何页面导航到主工作台时，发送一个事件
  if (to.name === 'MainWorkspace') {
    // 使用 document dispatchEvent 来创建一个简单的全局事件总线
    // 确保在 MainWorkspace 组件的 onMounted 中监听此事件
    document.dispatchEvent(new CustomEvent('refresh-workspace'));
  }
});

export default router 