import { LAYOUT } from '@/store/keys'

export const asyncRoutes = [
  {
    path: '/index',
    component: LAYOUT,
    name: 'Index',
    meta: {
      title: '首页',
      iconPrefix: 'iconfont',
      icon: 'icon-dashboard',
      isSingle: true,
    },
    children: [
      {
        path: 'home',
        name: 'Home',
        component: (): any => import('@/views/index/main.vue'),
        meta: {
          title: '首页',
          affix: true,
        },
      },
    ],
  },
  {
    path: '/aicase',
    component: LAYOUT,
    name: 'AiCase',
    meta: {
      title: 'AI写用例',
      icon: 'IconRobot',
    },
    children: [
      {
        path: 'generate/index',
        name: 'AiCaseGenerate',
        component: (): any => import('@/views/aicase/generate/index.vue'),
        meta: { title: 'AI生成用例' },
      },
      {
        path: 'requirement/index',
        name: 'AiCaseRequirement',
        component: (): any => import('@/views/aicase/requirement/index.vue'),
        meta: { title: '需求管理' },
      },
      {
        path: 'requirement/detail',
        name: 'AiCaseRequirementDetail',
        component: (): any => import('@/views/aicase/requirement/detail.vue'),
        meta: { title: '需求详情', hidden: true },
      },
    ],
  },
]
