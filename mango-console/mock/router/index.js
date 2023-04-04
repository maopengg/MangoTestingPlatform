import { getMenuList } from '@/api/url'
import Mock from 'mockjs'

export const adminRoutes = [
  {
    menuUrl: '/index',
    menuName: '首页',
    icon: 'icon-mind-mapping',
    isSingle: true,
    children: [
      {
        parentPath: '/index',
        menuUrl: '/index/home',
        menuName: '数据看板'
      }
    ]
  },
  // {
  //   menuUrl: '/index',
  //   menuName: 'Dashborad',
  //   routeName: '首页',
  //   icon: 'icon-dashboard',
  //   parentPath: '',
  //   children: [
  //     {
  //       parentPath: '/index',
  //       menuUrl: '/index/home',
  //       menuName: '数据看板',
  //       routeName: 'home',
  //     },
  //     {
  //       parentPath: '/index',
  //       menuUrl: '/index/work-place',
  //       menuName: '个人中心',
  //       routeName: 'workPlace',
  //       isRootPath: true,
  //     },
  //   ],
  // },
  {
    menuUrl: '/list',
    menuName: 'Api自动化',
    icon: 'IconSend',
    parentPath: '',
    children: [
      {
        parentPath: '/list',
        menuUrl: '/list/table-with-search',
        menuName: '本期接口'
      },
      {
        parentPath: '/list',
        menuUrl: '/list/table-custom',
        menuName: '用例调试'
      },
      {
        parentPath: '/list',
        menuUrl: '/list/list',
        menuName: '自动化用例'
      },
      {
        parentPath: '/list',
        menuUrl: '/list/card-list',
        menuName: '公共变量'
      },
      {
        parentPath: '/list',
        menuUrl: '/list/card-list',
        menuName: '测试报告'
      }
    ]
  },
  {
    menuUrl: '/next',
    menuName: 'Ui自动化',
    icon: 'IconFindReplace',
    parentPath: '',
    children: [
      {
        parentPath: '/next',
        menuUrl: '/next/menu2',
        menuName: '页面对象',
        children: [
          {
            parentPath: '/next/menu2',
            menuUrl: '/next/menu2/menu-2-1',
            menuName: 'web页面对象'
          },
          {
            parentPath: '/next/menu2',
            menuUrl: '/next/menu2/menu-2-1',
            menuName: 'mini页面对象'
          },
          {
            parentPath: '/next/menu2',
            menuUrl: '/next/menu2/menu-2-1',
            menuName: 'app页面对象'
          }
        ]
      },
      {
        parentPath: '/next',
        menuUrl: '/next/',
        menuName: '用例调试',
        cacheable: true
      },
      {
        parentPath: '/next',
        menuUrl: '/next/',
        menuName: '自动化用例',
        cacheable: true
      },
      {
        parentPath: '/next',
        menuUrl: '/next/',
        menuName: '公共变量',
        cacheable: true
      },
      {
        parentPath: '/next',
        menuUrl: '/next/',
        menuName: '测试报告'
      }
    ]
  },
  {
    menuUrl: '/route-params',
    menuName: '性能测试',
    icon: 'IconMinus',
    parentPath: '',
    children: [
      {
        parentPath: '/route-params',
        menuUrl: '/route-params/query',
        menuName: '接口准备'
      },
      {
        parentPath: '/route-params',
        menuUrl: '/route-params/params',
        menuName: '数据汇总'
      }
    ]
  },

  {
    menuUrl: '/map',
    menuName: '定时任务',
    icon: 'IconSchedule',
    children: [
      {
        parentPath: '/map',
        menuUrl: '/map/gaode',
        menuName: '调度中心'
      },
      {
        parentPath: '/map',
        menuUrl: '/map/baidu',
        menuName: '定时方案'
      }
    ]
  },

  {
    menuUrl: '/result',
    menuName: '系统配置',
    icon: 'icon-settings',
    parentPath: '',
    children: [
      {
        parentPath: '/result',
        menuUrl: '/result/success',
        menuName: '项目环境配置'
      },
      {
        parentPath: '/result',
        menuUrl: '/result/fail',
        menuName: '通知方式配置'
      },
      {
        parentPath: '/result',
        menuUrl: '/result',
        menuName: '数据库配置'
      },
      {
        parentPath: '/result',
        menuUrl: '/result',
        menuName: 'UI自动化配置'
      }
    ]
  },

  {
    menuUrl: '/testconfig',
    menuName: '项目管理',
    icon: 'IconAlignLeft',
    parentPath: '',
    routeName: 'system',
    children: [
      {
        parentPath: '/testconfig',
        menuUrl: '/testconfig/department',
        menuName: '部门管理',
        badge: 'new',
        routeName: 'department',
        localFilePath: '/testconfig/local-path/department'
      },
      {
        parentPath: '/testconfig',
        menuUrl: '/testconfig/user',
        menuName: '用户管理',
        badge: 'dot',
        routeName: 'user'
      },
      {
        parentPath: '/testconfig',
        menuUrl: '/testconfig/role',
        menuName: '角色管理',
        badge: '12'
      },
      {
        parentPath: '/testconfig',
        menuUrl: '/testconfig/menu',
        menuName: '菜单管理'
      }
    ]
  },
  {
    menuUrl: '/form',
    menuName: '帮助',
    badge: 'dot',
    icon: 'IconCompass',
    parentPath: '',
    children: [
      {
        parentPath: '/form',
        menuUrl: '/form',
        menuName: '公共变量'
      },
      {
        parentPath: '/form',
        menuUrl: '/form',
        menuName: '断言策略'
      },
      {
        parentPath: '/form',
        menuUrl: '/form',
        menuName: '使用手册'
      },
      {
        parentPath: '/form',
        menuUrl: '/form',
        menuName: '致谢'
      }
    ]
  },
  {
    menuUrl: '/other',
    menuName: '功能/组件',
    icon: 'icon-apps',
    parentPath: '',
    children: [
      {
        parentPath: '/other',
        menuUrl: '/other/chart',
        menuName: '图表',
        children: [
          {
            parentPath: '/other/chart',
            menuUrl: '/other/chart/icons',
            menuName: '图标'
          },
          {
            parentPath: '/other/chart',
            menuUrl: '/other/chart/echarts',
            menuName: 'echarts'
          },
          {
            parentPath: '/other/chart',
            menuUrl: '/other/chart/icon-select',
            menuName: '图标选择器'
          }
        ]
      },
      {
        parentPath: '/other',
        menuUrl: '/other/print',
        menuName: '打印'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/badge',
        menuName: '消息提示'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/clipboard',
        menuName: '剪贴板'
      },
      {
        parentPath: '/other',
        menuUrl: 'http://qingqingxuan.gitee.io/work-p-site',
        menuName: '外链'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/qrcode',
        menuName: '二维码'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/css-animation',
        menuName: 'CSS动画'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/flow',
        menuName: '流程图'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/player',
        menuName: '视频播放器'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/password-strong-page',
        menuName: '密码强度'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/cropper',
        menuName: '图片裁剪'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/iframe',
        menuName: '内嵌iframe'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/big-preview',
        menuName: '大图预览'
      }
    ]
  },

  {
    menuUrl: '/editor',
    menuName: '编辑器',
    badge: '12',
    icon: 'icon-edit',
    parentPath: '',
    children: [
      {
        parentPath: '/editor',
        menuUrl: '/editor/rich-text',
        menuName: '富文本'
      },
      {
        parentPath: '/editor',
        menuUrl: '/editor/markdown',
        menuName: 'markdown'
      }
    ]
  },
  {
    menuUrl: '/excel',
    menuName: 'Excel',
    icon: 'icon-nav',
    parentPath: '',
    children: [
      {
        parentPath: '/excel',
        menuUrl: '/excel/export-excel',
        menuName: '导出Excel'
      },
      {
        parentPath: '/excel',
        menuUrl: '/excel/export-rows-excel',
        menuName: '导出选中行'
      }
    ]
  },
  {
    menuUrl: '/draggable',
    menuName: '拖拽',
    icon: 'icon-drag-arrow',
    parentPath: '',
    children: [
      // {
      //   parentPath: '/draggable',
      //   menuUrl: '/draggable/dialog-draggable',
      //   menuName: '拖拽对话框',
      // },
      {
        parentPath: '/draggable',
        menuUrl: '/draggable/card-draggable',
        menuName: '卡片拖拽',
        cacheable: true
      },
      {
        parentPath: '/index',
        menuUrl: '/index/work-place',
        menuName: '个人中心',
        routeName: 'workPlace',
        isRootPath: true
      }
    ]
  }
]
export const editorRoutes = [
  {
    menuUrl: '/other',
    menuName: '功能/组件',
    iconPrefix: 'iconfont',
    icon: 'appstore',
    parentPath: '',
    children: [
      {
        parentPath: '/other',
        menuUrl: '/other/chart',
        menuName: '图表',
        children: [
          {
            parentPath: '/other/chart',
            menuUrl: '/other/chart/icon',
            menuName: '图标',
            children: [
              {
                parentPath: '/other/chart/icon',
                menuUrl: '/other/chart/icon/icon-font',
                menuName: 'IconFont'
              },
              {
                parentPath: '/other/chart/icon',
                menuUrl: '/other/chart/icon/xicons',
                menuName: 'xicons'
              }
            ]
          },
          {
            parentPath: '/other/chart',
            menuUrl: '/other/chart/echarts',
            menuName: 'echarts'
          },
          {
            parentPath: '/other/chart',
            menuUrl: '/other/chart/icon-selector',
            menuName: '图标选择器'
          }
        ]
      },
      {
        parentPath: '/other',
        menuUrl: '/other/print',
        menuName: '打印'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/badge',
        menuName: '消息提示'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/clipboard',
        menuName: '剪贴板'
      },
      {
        parentPath: '/other',
        menuUrl: 'http://qingqingxuan.gitee.io/work-p-site',
        menuName: '外链'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/qrcode',
        menuName: '二维码'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/css-animation',
        menuName: 'CSS动画'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/flow',
        menuName: '流程图'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/player',
        menuName: '视频播放器'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/password-strong',
        menuName: '密码强度'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/cropper',
        menuName: '图片裁剪'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/iframe',
        menuName: '内嵌iframe'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/big-preview',
        menuName: '大图预览'
      },
      {
        parentPath: '/other',
        menuUrl: '/other/city-selector',
        menuName: '省市区选择器'
      }
    ]
  },
  {
    menuUrl: '/next',
    menuName: '多级菜单',
    iconPrefix: 'iconfont',
    icon: 'Partition',
    parentPath: '',
    children: [
      {
        parentPath: '/next',
        menuUrl: '/next/menu1',
        menuName: 'menu-1',
        cacheable: true
      },
      {
        parentPath: '/next',
        menuUrl: '/next/menu2',
        menuName: 'menu-2',
        children: [
          {
            parentPath: '/next/menu2',
            menuUrl: '/next/menu2/menu-2-1',
            menuName: 'menu-2-1',
            children: [
              {
                parentPath: '/next/menu2/menu-2-1',
                menuUrl: '/next/menu2/menu-2-1/menu-2-1-1',
                menuName: 'menu-2-1-1',
                cacheable: true
              },
              {
                parentPath: '/next/menu2/menu-2-1',
                menuUrl: '/next/menu2/menu-2-1/menu-2-1-2',
                menuName: 'menu-2-1-2'
              }
            ]
          },
          {
            parentPath: '/next/menu2',
            menuUrl: '/next/menu2/menu-2-2',
            menuName: 'menu-2-2',
            cacheable: true
          }
        ]
      }
    ]
  },
  {
    menuUrl: '/map',
    menuName: '地图',
    iconPrefix: 'iconfont',
    icon: 'location',
    children: [
      {
        parentPath: '/map',
        menuUrl: '/map/gaode',
        menuName: '高德地图'
      },
      {
        parentPath: '/map',
        menuUrl: '/map/baidu',
        menuName: '百度地图'
      }
    ]
  },
  {
    menuUrl: '/project',
    menuName: '项目信息',
    iconPrefix: 'iconfont',
    icon: 'detail',
    children: [
      {
        parentPath: '/project',
        menuUrl: '/project/infomation',
        menuName: '项目依赖'
      }
    ]
  }
]

Mock.mock(RegExp(getMenuList), 'post', function () {
  return Mock.mock({ code: 200, data: adminRoutes, msg: '获取菜单列表成功' })
})
