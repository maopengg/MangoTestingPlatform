import { mapTwoLevelRouter } from '@/store/help'
import { App } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import { constantRoutes, defaultPathRoute } from './routes/constants'

const Layout = () => import('@/layouts/Layout.vue')

export const extraRoutes = [
  {
    path: '/evaluation', name: 'evaluationCaseDetails', component: Layout, meta: { title: '效果测试' },
    children: [{ path: 'case/details', component: () => import('@/views/evaluation/case/details/index.vue'),
      meta: { title: 'Case 详情', permissionKey: 'evaluation.case', breadcrumb: [{ title: '测试用例', path: '/evaluation/case/index' }] } },
      { path: 'dataset/details', component: () => import('@/views/evaluation/dataset/details/index.vue'),
        meta: { title: '版本与数据条目', permissionKey: 'evaluation.dataset', breadcrumb: [{ title: '评测数据集', path: '/evaluation/dataset/index' }] } },
    ],
  },
  {
    path: '/perf',
    name: 'perfTest',
    component: Layout,
    meta: { title: '性能测试' },
    children: [
      {
        path: 'scenario/index',
        component: () => import('@/views/perf/scenario/index.vue'),
        meta: { title: '性能场景', permissionKey: 'perf.scenario' },
      },
      {
        path: 'scenario/details',
        component: () => import('@/views/perf/scenario/details/index.vue'),
        meta: { title: '场景配置', permissionKey: 'perf.scenario', breadcrumb: [{ title: '性能场景', path: '/perf/scenario/index' }] },
      },
      {
        path: 'run/index',
        component: () => import('@/views/perf/run/index.vue'),
        meta: { title: '运行历史', permissionKey: 'perf.run' },
      },
      {
        path: 'run/details',
        component: () => import('@/views/perf/run/details/index.vue'),
        meta: { title: '运行结果', permissionKey: 'perf.run', breadcrumb: [{ title: '运行历史', path: '/perf/run/index' }] },
      },
      {
        path: 'capacity/index',
        component: () => import('@/views/perf/capacity/index.vue'),
        meta: { title: '执行器容量', permissionKey: 'perf.capacity' },
      },
    ],
  },
  {
    path: '/functional-test',
    name: 'manualTest',
    component: Layout,
    meta: {
      title: '研发协同',
    },
    children: [
      {
        path: 'iteration/index',
        component: () => import('@/views/functional-test/iteration/index.vue'),
        meta: {
          title: '迭代管理',
          permissionKey: 'functional.iteration',
        },
      },
      {
        path: 'iteration/details',
        component: () => import('@/views/functional-test/iteration/details/index.vue'),
        meta: {
          title: '迭代详情',
          permissionKey: 'functional.iteration',
          breadcrumb: [{ title: '迭代管理', path: '/functional-test/iteration/index' }],
        },
      },
      {
        path: 'suite/index',
        component: () => import('@/views/functional-test/suite/index.vue'),
        meta: {
          title: '需求管理',
          permissionKey: 'functional.suite',
        },
      },
      {
        path: 'design/index',
        component: () => import('@/views/functional-test/design/index.vue'),
        meta: {
          title: '开发设计',
          permissionKey: 'functional.design',
        },
      },
      {
        path: 'case/index',
        component: () => import('@/views/functional-test/case-library/index.vue'),
        meta: {
          title: '测试用例',
          permissionKey: 'functional.case',
        },
      },
      {
        path: 'plan/index',
        component: () => import('@/views/functional-test/plan/index.vue'),
        meta: {
          title: '测试计划',
          permissionKey: 'functional.plan',
        },
      },
      {
        path: 'defect/index',
        component: () => import('@/views/functional-test/defect/index.vue'),
        meta: {
          title: '缺陷库',
          permissionKey: 'functional.defect',
        },
      },
      {
        path: 'plan/details',
        component: () => import('@/views/functional-test/plan/details.vue'),
        meta: {
          title: '测试计划详情',
          permissionKey: 'functional.plan',
          breadcrumb: [{ title: '测试计划', path: '/functional-test/plan/index' }],
        },
      },
      {
        path: 'suite/details',
        component: () => import('@/views/functional-test/suite/details/index.vue'),
        meta: {
          title: '用例生成工作台',
          permissionKey: 'functional.suite',
          breadcrumb: [{ title: '需求管理', path: '/functional-test/suite/index' }],
        },
      },
      {
        path: 'requirement/details',
        component: () => import('@/views/functional-test/requirement/details/index.vue'),
        meta: {
          title: '需求详情',
          permissionKey: 'functional.suite',
          breadcrumb: [{ title: '需求管理', path: '/functional-test/suite/index' }],
        },
      },
      {
        path: 'case/details',
        component: () => import('@/views/functional-test/case/details/index.vue'),
        meta: {
          title: '功能用例详情',
          permissionKey: 'functional.case',
          breadcrumb: [{ title: '测试用例', path: '/functional-test/case/index' }],
        },
      },
    ],
  },
  {
    path: '/uitest',
    name: 'uiTest',
    component: Layout,
    meta: {
      title: 'UI自动化',
    },
    children: [
      {
        path: 'auth-config/index',
        component: () => import('@/views/uitest/auth-config/index.vue'),
        meta: {
          title: 'UI授权管理',
          permissionKey: 'ui.auth_config',
        },
      },
      {
        path: 'page/steps/details',
        component: () => import('@/views/uitest/page-steps/details/index.vue'),
        meta: {
          title: '页面步骤工作台',
          permissionKey: 'ui.page_steps',
          breadcrumb: [{ title: '页面步骤', path: '/uitest/page-steps/index' }],
        },
      },
      {
        path: 'page/elements',
        component: () => import('@/views/uitest/page/elements/index.vue'),
        meta: {
          title: '页面元素配置',
          permissionKey: 'ui.page',
          breadcrumb: [{ title: '页面元素', path: '/uitest/page/index' }],
        },
      },
      {
        path: 'case/details',
        component: () => import('@/views/uitest/case/details/index.vue'),
        meta: {
          title: '界面用例配置',
          permissionKey: 'ui.case',
          breadcrumb: [{ title: '测试用例', path: '/uitest/case/index' }],
        },
      },
      {
        path: 'live-workbench',
        component: () => import('@/views/uitest/live-workbench/index.vue'),
        meta: {
          title: 'UI实时工作台',
          permissionKey: 'ui.page',
          hidden: true,
          noShowTabbar: true,
        },
      },
    ],
  },
  {
    path: '/apitest',
    name: 'apiTest',
    component: Layout,
    meta: {
      title: 'API自动化',
    },
    children: [
      {
        path: 'module-coverage/index',
        component: () => import('@/views/apitest/module-coverage/index.vue'),
        meta: {
          title: '模块覆盖',
          permissionKey: 'api.module_coverage',
        },
      },
      {
        path: 'info/details',
        component: () => import('@/views/apitest/info/details/index.vue'),
        meta: {
          title: '服务调用工作台',
          permissionKey: 'api.info',
          breadcrumb: [{ title: '服务调用', path: '/apitest/info/index' }],
        },
      },
      {
        path: 'mock/details',
        component: () => import('@/views/apitest/mock/details/index.vue'),
        meta: {
          title: 'Mock 接口配置',
          permissionKey: 'api.mock',
          breadcrumb: [{ title: 'Mock服务', path: '/apitest/mock/index' }],
        },
      },
      {
        path: 'case/details',
        component: () => import('@/views/apitest/case/details/index.vue'),
        meta: {
          title: '接口用例配置',
          permissionKey: 'api.case',
          breadcrumb: [{ title: '测试用例', path: '/apitest/case/index' }],
        },
      },
    ],
  },
  {
    path: '/pytest',
    name: 'pytest',
    component: Layout,
    meta: {
      title: 'Pytest自动化',
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
          permissionKey: 'data_factory.template',
          breadcrumb: [{ title: '场景模板', path: '/data-factory/template/index' }],
        },
      },
    ],
  },
  {
    path: '/report',
    name: 'report',
    component: Layout,
    meta: {
      title: '质量报告',
    },
    children: [
      {
        path: 'system/details',
        name: 'ReportDetails',
        component: () => import('@/views/report/details/index.vue'),
        meta: {
          title: '测试报告详情',
          hideFooter: true,
          permissionKey: 'report',
          breadcrumb: [{ title: '执行报告', path: '/report/index' }],
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
          permissionKey: 'timing.tasks',
          breadcrumb: [{ title: '定时任务', path: '/timing/tasks/index' }],
        },
      },
      {
        path: 'fire-record/index',
        component: () => import('@/views/system/fire-record/index.vue'),
        meta: {
          title: '触发记录',
          permissionKey: 'timing.fire_record',
          breadcrumb: [{ title: '任务调度', path: '/timing/tasks/index' }],
        },
      },
      {
        path: 'system-jobs/index',
        redirect: '/system/system-jobs/index',
        meta: {
          hidden: true,
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
          permissionKey: 'config.product',
          breadcrumb: [{ title: '产品配置', path: '/config/product/index' }],
        },
      },
      {
        path: 'product/datasource',
        component: () => import('@/views/config/product/datasource/index.vue'),
        meta: {
          title: '产品逻辑数据库',
          permissionKey: 'config.product',
          breadcrumb: [{ title: '产品配置', path: '/config/product/index' }],
        },
      },
      {
        path: 'project/notice',
        component: () => import('@/views/config/project/notice/index.vue'),
        meta: {
          title: '通知组配置',
          permissionKey: 'config.project',
          breadcrumb: [{ title: '项目配置', path: '/config/project/index' }],
        },
      },
      {
        path: 'data-source/index',
        component: () => import('@/views/config/data-source/index.vue'),
        meta: {
          title: '数据库配置',
          permissionKey: 'config.datasource',
          reuseOnQueryChange: true,
        },
      },
    ],
  },
  {
    path: '/system',
    name: 'system',
    component: Layout,
    meta: {
      title: '系统运维',
    },
    children: [
      {
        path: 'runtime-center/index',
        component: () => import('@/views/system/runtime-center/index.vue'),
        meta: {
          title: '运行中心',
          permissionKey: 'system.runtime_center',
        },
      },
      {
        path: 'system-jobs/index',
        component: () => import('@/views/timing/system-jobs/index.vue'),
        meta: {
          title: '系统定时任务',
          permissionKey: 'timing.system_jobs',
          breadcrumb: [{ title: '系统运维', path: '/system/runtime-center/index' }],
        },
      },
      {
        path: 'user/index',
        redirect: '/organization-permission/user/index',
        meta: {
          hidden: true,
        },
      },
      {
        path: 'role/index',
        redirect: '/organization-permission/role/index',
        meta: {
          hidden: true,
        },
      },
      {
        path: 'department/index',
        redirect: '/organization-permission/department/index',
        meta: {
          hidden: true,
        },
      },
      {
        path: 'fire-record/index',
        redirect: '/timing/fire-record/index',
        meta: {
          hidden: true,
        },
      },
      {
        path: 'error-record/index',
        component: () => import('@/views/system/error-record/index.vue'),
        meta: {
          title: '系统异常记录',
          permissionKey: 'system.error_record',
          breadcrumb: [{ title: '系统运维', path: '/system/runtime-center/index' }],
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
