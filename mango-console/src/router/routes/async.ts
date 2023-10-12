import { LAYOUT } from '@/store/keys'

export const asyncRoutes = [
  {
    path: '/index',
    component: LAYOUT,
    name: 'Index',
    meta: {
      title: '首页',
      iconPrefix: 'iconfont',
      icon: 'icon-dashboard'
    },
    children: [
      {
        path: 'home',
        name: 'Home',
        component: (): any => import('@/views/index/main.vue'),
        meta: {
          title: '项目数据',
          affix: true
        }
      },
      {
        path: 'test_report',
        name: 'TestReport',
        component: (): any => import('@/views/index/test_report.vue'),
        meta: {
          title: '测试报告'
        }
      }
    ]
  }
]
