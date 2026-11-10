import { RouteRecordRaw } from 'vue-router'
import { defineStore } from 'pinia'
import router from '@/router'
import { getMenuListByRoleId } from '@/api/url'
import { post } from '@/api/http'
import { findRootPathRoute, generatorRoutes, mapTwoLevelRouter } from '../help'
import { constantRoutes } from '@/router/routes/constants'
import { hasPermissionKeys, PermissionRequirement } from '@/utils/permission'

let removePermissionRoutes: Array<() => void> = []

const usePermissionStore = defineStore('permission-route', {
  state: () => {
    return {
      permissionRoutes: [] as RouteRecordRaw[],
      homePath: '/index/home',
      permissionKeys: [] as string[],
      isSuperAdmin: false,
    }
  },
  getters: {
    getPermissionSideBar(state) {
      return state.permissionRoutes.filter((it) => {
        return it.meta && !it.meta.hidden
      })
    },
    getPermissionSplitTabs(state) {
      return state.permissionRoutes.filter((it) => {
        return it.meta && !it.meta.hidden && it.children && it.children.length > 0
      })
    },
    getTopLevelTabs(state) {
      return state.permissionRoutes
        .filter((it) => {
          return it.meta && !it.meta.hidden && it.children && it.children.length > 0
        })
        .map((it) => {
          const obj = { ...it, items: it.children }
          delete obj.children
          return obj
        })
    },
    hasPermission(state) {
      return (permissionKey?: PermissionRequirement) =>
        hasPermissionKeys(state.permissionKeys, state.isSuperAdmin, permissionKey,
                          router.currentRoute.value.path === '/report/details')
    },
  },
  actions: {
    async getRoutes(isCurrent: () => boolean = () => true) {
      try {
        const res = await post({
          url: getMenuListByRoleId,
          data: {},
        })
        if (!isCurrent()) return []
        const routeData = Array.isArray(res.data) ? res.data : res.data?.menus || []
        this.permissionKeys = Array.isArray(res.data?.permissions) ? res.data.permissions : []
        this.isSuperAdmin = !!res.data?.is_super_admin
        return generatorRoutes(routeData)
      } catch (error) {
        console.error(
          '路由加载失败了，请清空一下Cookie和localStorage，重新登录；如果已经采用真实接口的，请确保菜单接口地址真实可用并且返回的数据格式和mock中的一样'
        )
        throw error
      }
    },
    clearPermissionRoute() {
      removePermissionRoutes.forEach((removeRoute) => removeRoute())
      removePermissionRoutes = []
      this.permissionRoutes = []
      this.homePath = '/index/home'
      this.permissionKeys = []
      this.isSuperAdmin = false
    },
    async initPermissionRoute(force = false, isCurrent: () => boolean = () => true) {
      // 加载路由
      const accessRoutes = await this.getRoutes(isCurrent)
      if (!isCurrent()) return
      const mapRoutes = mapTwoLevelRouter(accessRoutes)
      if (force) {
        removePermissionRoutes.forEach((removeRoute) => removeRoute())
        removePermissionRoutes = []
      }
      // 首页路径必须在路由展平后计算，避免得到 `home` 这类相对路径。
      const homePath = findRootPathRoute(mapRoutes)
      this.homePath = homePath
      mapRoutes.forEach((it: any) => {
        removePermissionRoutes.push(router.addRoute(it))
      })
      // 配置 `/` 路由的默认跳转地址
      removePermissionRoutes.push(router.addRoute({
        path: '/',
        redirect: homePath,
        meta: {
          hidden: true,
        },
      }))
      // 这个路由一定要放在最后
      removePermissionRoutes.push(router.addRoute({
        path: '/:pathMatch(.*)*',
        redirect: '/404',
        meta: {
          hidden: true,
        },
      }))
      this.permissionRoutes = [...constantRoutes, ...accessRoutes]
    },
    isEmptyPermissionRoute() {
      return !this.permissionRoutes || this.permissionRoutes.length === 0
    },
    reset() {
      this.clearPermissionRoute()
      this.$reset()
    },
  },
})

export default usePermissionStore
