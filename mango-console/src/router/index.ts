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
      isSingle: true,
    },
    children: [
      {
        path: 'home',
        name: 'Details',
        component: () => import('@/views/index/main.vue'),
        meta: {
          title: '首页',
        },
      },
    ],
  },
  {
    path: '/uitest',
    name: 'uiTest',
    component: Layout,
    meta: {
      title: 'Ui自动化',
    },
    children: [
      {
        path: 'page/steps/details',
        component: () => import('@/views/uitest/page-steps/details/index.vue'),
        meta: {
          title: '页面步骤详情',
        },
      },
      {
        path: 'page/elements',
        component: () => import('@/views/uitest/page/elements/index.vue'),
        meta: {
          title: '页面元素详情页',
        },
      },
      {
        path: 'case/details',
        component: () => import('@/views/uitest/case/details/index.vue'),
        meta: {
          title: '测试用例详情',
        },
      },
      {
        path: 'report/details',
        component: () => import('@/views/uitest/report/details/index.vue'),
        meta: {
          title: '界面测试报告详情',
        },
      },
    ],
  },
  {
    path: '/apitest',
    name: 'apiTest',
    component: Layout,
    meta: {
      title: 'Api自动化',
    },
    children: [
      {
        path: 'info/details',
        component: () => import('@/views/apitest/info/details/index.vue'),
        meta: {
          title: '接口详情',
        },
      },
      {
        path: 'case/details',
        component: () => import('@/views/apitest/case/details/index.vue'),
        meta: {
          title: '用例详情',
        },
      },
      {
        path: 'report/details',
        component: () => import('@/views/apitest/report/details/index.vue'),
        meta: {
          title: '接口测试报告详情',
        },
      },
    ],
  },
  {
    path: '/timing',
    name: 'task',
    component: Layout,
    meta: {
      title: '定时任务',
    },
    children: [
      {
        path: 'case',
        component: () => import('@/views/timing/scheduled-tasks/case/index.vue'),
        meta: {
          title: '添加用例',
        },
      },
    ],
  },
  {
    path: '/config',
    name: '测试配置',
    component: Layout,
    meta: {
      title: '测试配置',
    },
    children: [
      {
        path: 'product/module',
        component: () => import('@/views/config/product/module/index.vue'),
        meta: {
          title: '测试项目',
        },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHashHistory(),
  routes: mapTwoLevelRouter([...constantRoutes, ...extraRoutes, defaultPathRoute]),
})

export default router

export function setupRouter(app: App) {
  app.use(router)
}
