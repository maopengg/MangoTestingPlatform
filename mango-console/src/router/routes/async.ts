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
      isSingle: true
    },
    children: [
      {
        path: 'home',
        name: 'Home',
        component: (): any => import('@/views/index/main.vue'),
        meta: {
          title: '首页',
          affix: true
        }
      }
    ]
  }
]
