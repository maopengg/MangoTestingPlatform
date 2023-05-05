import { mapTwoLevelRouter } from '@/store/help'
import { App } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import { constantRoutes, defaultPathRoute } from './routes/constants'

const Layout = () => import('@/layouts/Layout.vue')

export const extraRoutes = [
  {
    path: '/uitest',
    name: 'uiTest',
    component: Layout,
    meta: {
      title: 'Ui自动化'
    },
    children: [
      {
        path: 'details',
        component: () => import('@/views/uitest/ui-case-debug-details.vue'),
        meta: {
          title: '用例详情'
        }
      },
      {
        path: 'pageel',
        component: () => import('@/views/uitest/page_elements.vue'),
        meta: {
          title: '页面元素详情页'
        }
      }
    ]
  },
  {
    path: '/apitest',
    name: 'apiTest',
    component: Layout,
    meta: {
      title: 'Api自动化'
    },
    children: [
      {
        path: 'group',
        component: () => import('@/views/apitest/api-case-group.vue'),
        meta: {
          title: '用例组'
        }
      },
      {
        path: 'details',
        component: () => import('@/views/apitest/api-case-debug-details.vue'),
        meta: {
          title: '接口用例详情'
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes: mapTwoLevelRouter([...constantRoutes, ...extraRoutes, defaultPathRoute])
})

export default router

export function setupRouter(app: App) {
  app.use(router)
}
