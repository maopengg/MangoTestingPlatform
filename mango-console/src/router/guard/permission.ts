import useUserStore from '@/store/modules/user'
import usePermissionStore from '@/store/modules/permission'
import { useEnum } from '@/store/modules/get-enum'
import router from '..'
import { connectWebSocket } from '@/utils/socket'

const whiteRoutes: string[] = [
  '/login',
  '/cli-auth',
  '/404',
  '/403',
  '/500',
  '/report/details',
]

function usePermissionGuard() {
  router.beforeEach(async (to) => {
    if (whiteRoutes.includes(to.path)) {
      return true
    }
    const userStore = useUserStore()
    if (userStore.isTokenExpire()) {
      if (to.path === '/report/system/details') {
        return {
          path: '/report/details',
          query: to.query,
          replace: true,
        }
      }
      return {
        path: '/login',
        query: { redirect: to.fullPath },
      }
    }

    await useEnum().getEnum()

    // 用户已登录，确保 WebSocket 已连接（处理页面刷新或会话标记丢失的情况）
    if (userStore.userName && userStore.password) {
      connectWebSocket(userStore.userName, userStore.password)
    }

    const permissionStore = usePermissionStore()
    const isEmptyRoute = permissionStore.isEmptyPermissionRoute()
    if (isEmptyRoute) {
      await permissionStore.initPermissionRoute()
      return { ...to, replace: true }
    }
    const permissionKey = to.meta?.permissionKey as string | undefined
    if (permissionKey && !permissionStore.hasPermission(permissionKey)) {
      return {
        path: '/403',
        replace: true,
      }
    }
    return true
  })
}

export default usePermissionGuard
