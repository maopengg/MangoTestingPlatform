import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import router from '..'
import { connectWebSocket } from '@/utils/socket'

const whiteRoutes: string[] = ['/login', '/404', '/403', '/500', '/report/details']
const reportDetailsSystemRoute = '/report/system/details'
const reportDetailsShareRoute = '/report/details'
const reportListRoute = '/report/index'
const reportDetailsAccessKey = 'reportDetailsSystemAccessId'

function usePermissionGuard() {
  router.beforeEach(async (to, from) => {
    if (to.path === reportDetailsSystemRoute) {
      const reportId = String(to.query.id || '')
      const accessId = window.sessionStorage.getItem(reportDetailsAccessKey)

      if (!reportId || (accessId !== reportId && from.path !== reportListRoute)) {
        return {
          path: reportDetailsShareRoute,
          query: to.query,
          replace: true,
        }
      }
    }

    if (whiteRoutes.includes(to.path)) {
      return true
    }
    const userStore = useUserStore()
    if (userStore.isTokenExpire()) {
      return {
        path: '/login',
        query: { redirect: to.fullPath },
      }
    }

    // 用户已登录，确保 WebSocket 已连接（处理页面刷新的情况）
    if (userStore.userName && userStore.password) {
      connectWebSocket(userStore.userName, userStore.password)
    }

    const permissionStore = usePermissionStore()
    const isEmptyRoute = permissionStore.isEmptyPermissionRoute()
    if (isEmptyRoute) {
      await permissionStore.initPermissionRoute()
      return { ...to, replace: true }
    }
    return true
  })

  router.afterEach((to, _from, failure) => {
    if (!failure && to.path === reportDetailsSystemRoute) {
      window.sessionStorage.removeItem(reportDetailsAccessKey)
    }
  })
}

export default usePermissionGuard
