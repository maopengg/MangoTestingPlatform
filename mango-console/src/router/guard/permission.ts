import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import router from '..'
import { connectWebSocket } from '@/utils/socket'

const whiteRoutes: string[] = ['/login', '/404', '/403', '/500']

function usePermissionGuard() {
  router.beforeEach(async (to) => {
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
}

export default usePermissionGuard
