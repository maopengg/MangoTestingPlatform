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
          title: '数据看板',
          affix: true
        }
      },
      {
        path: 'work-place',
        name: 'WorkPlace',
        component: (): any => import('@/views/index/work-place.vue'),
        meta: {
          title: '任务进展'
        }
      }
    ]
  }
]
