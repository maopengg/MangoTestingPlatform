import { mapTwoLevelRouter } from '@/store/help'
import { App } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import { constantRoutes, defaultPathRoute } from './routes/constants'

const Layout = () => import('@/layouts/Layout.vue')

export const extraRoutes = [
  {
    path: '/index',
    name: 'home',
    component: Layout,
    redirect: { path: 'report-details' },
    meta: {
      title: '首页',
      isSingle: true
    },
    children: [
      {
        path: 'home',
        name: 'Details',
        component: () => import('@/views/index/main.vue'),
        meta: {
          title: '首页'
        }
      }
    ]
  },
  {
    path: '/uitest',
    name: 'uiTest',
    component: Layout,
    meta: {
      title: 'Ui自动化'
    },
    children: [
      {
        path: 'page-steps-details',
        component: () => import('@/views/uitest/page-steps-details.vue'),
        meta: {
          title: '页面步骤详情'
        }
      },
      {
        path: 'pageel',
        component: () => import('@/views/uitest/page-elements.vue'),
        meta: {
          title: '页面元素详情页'
        }
      },
      {
        path: 'ui-case-details',
        component: () => import('@/views/uitest/case-details.vue'),
        meta: {
          title: '测试用例详情'
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
        component: () => import('@/views/apitest/case.vue'),
        meta: {
          title: '用例组'
        }
      },
      {
        path: 'details',
        component: () => import('@/views/apitest/case-details.vue'),
        meta: {
          title: '接口用例详情'
        }
      }
    ]
  },
  {
    path: '/timing',
    name: 'task',
    component: Layout,
    meta: {
      title: '定时任务'
    },
    children: [
      {
        path: 'runcase',
        component: () => import('@/views/timing/runcase.vue'),
        meta: {
          title: '添加用例'
        }
      }
    ]
  },
  {
    path: '/index',
    name: '测试报告',
    component: Layout,
    meta: {
      title: '测试报告'
    },
    children: [
      {
        path: 'report-details',
        component: () => import('@/views/index/report-details.vue'),
        meta: {
          title: '测试报告'
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
