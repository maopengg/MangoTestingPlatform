/**
 * 这里的 defaultRoutes 是为了在一开始对接项目的时候，后端人员还没有准备好菜单接口，导致前端开发者不能进入主页面。
 * 所以这里返回默认的菜单数据，同时也向大家说明菜单数据的数据结构。后端的菜单接口一定要按这个格式去返回json数据，否则会解析菜单失败
 */
export const defaultRoutes = [
  {
    menuUrl: '/index',
    menuName: 'Dashborad',
    routeName: 'dashborad',
    icon: 'icon-dashboard',
    parentPath: '',
    children: [
      {
        parentPath: '/index',
        menuUrl: '/index/home',
        menuName: '主控台',
        routeName: 'home',
      },
      {
        parentPath: '/index',
        menuUrl: '/index/work-place',
        menuName: '工作台',
        routeName: 'workPlace',
      },
    ],
  },
  {
    menuUrl: '/config',
    menuName: '系统管理',
    icon: 'icon-settings',
    parentPath: '',
    routeName: 'system',
    children: [
      {
        parentPath: '/config',
        menuUrl: '/config/department',
        menuName: '部门管理',
        routeName: 'department',
        localFilePath: '/config/local-path/department',
      },
      {
        parentPath: '/config',
        menuUrl: '/config/user',
        menuName: '用户管理',
        routeName: 'user',
        isRootPath: true,
      },
      {
        parentPath: '/config',
        menuUrl: '/config/role',
        menuName: '角色管理',
      },
      {
        parentPath: '/config',
        menuUrl: '/config/menu',
        menuName: '菜单管理',
      },
    ],
  },
]
