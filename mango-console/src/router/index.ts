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
      title: '界面自动化',
    },
    children: [
      {
        path: 'page/steps/details',
        component: () => import('@/views/uitest/page-steps/details/index.vue'),
        meta: {
          title: '页面步骤工作台',
          breadcrumb: [{ title: '页面步骤', path: '/uitest/page/steps' }],
        },
      },
      {
        path: 'page/elements',
        component: () => import('@/views/uitest/page/elements/index.vue'),
        meta: {
          title: '页面元素配置',
          breadcrumb: [{ title: '页面元素', path: '/uitest/page' }],
        },
      },
      {
        path: 'case/details',
        component: () => import('@/views/uitest/case/details/index.vue'),
        meta: {
          title: '界面用例配置',
          breadcrumb: [{ title: '测试用例', path: '/uitest/case' }],
        },
      },
    ],
  },
  {
    path: '/apitest',
    name: 'apiTest',
    component: Layout,
    meta: {
      title: '接口自动化',
    },
    children: [
      {
        path: 'info/details',
        component: () => import('@/views/apitest/info/details/index.vue'),
        meta: {
          title: '接口配置工作台',
          breadcrumb: [{ title: '接口管理', path: '/apitest/info' }],
        },
      },
      {
        path: 'case/details',
        component: () => import('@/views/apitest/case/details/index.vue'),
        meta: {
          title: '接口用例配置',
          breadcrumb: [{ title: '测试用例', path: '/apitest/case' }],
        },
      },
    ],
  },
  {
    path: '/pytest',
    name: 'pytest',
    component: Layout,
    meta: {
      title: 'Pytest',
    },
    children: [],
  },
  {
    path: '/data-factory',
    name: 'dataFactory',
    component: Layout,
    meta: {
      title: '数据工厂',
    },
    children: [
      {
        path: 'template/preview',
        component: () => import('@/views/data-factory/template/preview/index.vue'),
        meta: {
          title: '场景模板配置',
          breadcrumb: [{ title: '场景模板', path: '/data-factory/template' }],
        },
      },
    ],
  },
  {
    path: '/report',
    name: 'report',
    component: Layout,
    meta: {
      title: '测试报告',
    },
    children: [
      {
        path: 'system/details',
        name: 'ReportDetails',
        component: () => import('@/views/report/details/index.vue'),
        meta: {
          title: '测试报告详情',
          breadcrumb: [{ title: '测试报告', path: '/report/index' }],
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
        component: () => import('@/views/timing/tasks/case/index.vue'),
        meta: {
          title: '添加用例',
          breadcrumb: [{ title: '定时任务', path: '/timing/tasks' }],
        },
      },
      {
        path: 'fire-record/index',
        component: () => import('@/views/timing/fire-record/index.vue'),
        meta: {
          title: '触发记录',
          breadcrumb: [{ title: '定时任务', path: '/timing/tasks/index' }],
        },
      },
      {
        path: 'system-jobs/index',
        component: () => import('@/views/timing/system-jobs/index.vue'),
        meta: {
          title: '系统任务',
          breadcrumb: [{ title: '定时任务', path: '/timing/tasks/index' }],
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
          title: '产品模块配置',
          breadcrumb: [{ title: '项目产品', path: '/config/product' }],
        },
      },
      {
        path: 'product/datasource',
        component: () => import('@/views/config/product/datasource/index.vue'),
        meta: {
          title: '产品逻辑数据源',
          breadcrumb: [{ title: '项目产品', path: '/config/product' }],
        },
      },
      {
        path: 'project/notice',
        component: () => import('@/views/config/project/notice/index.vue'),
        meta: {
          title: '通知组配置',
          breadcrumb: [{ title: '项目配置', path: '/config/project' }],
        },
      },
      {
        path: 'test/object/database',
        component: () => import('@/views/config/test-object/database/index.vue'),
        meta: {
          title: '数据源配置',
          breadcrumb: [{ title: '测试对象', path: '/config/test/object' }],
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
