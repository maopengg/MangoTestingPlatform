import type { Component } from 'vue'
import usePermissionStore from '@/store/modules/permission'

export function useHomeMenuIcon() {
  const permissionStore = usePermissionStore()

  function resolveMenuIcon(rootPath: string, fallback: string | Component) {
    const normalizedPath = rootPath.replace(/\/$/, '')
    const route = permissionStore.getPermissionSideBar.find((item) => {
      const routePath = String(item.path || '').replace(/\/$/, '')
      return routePath === normalizedPath
    })

    return (route?.meta?.icon as string | undefined) || fallback
  }

  return { resolveMenuIcon }
}
