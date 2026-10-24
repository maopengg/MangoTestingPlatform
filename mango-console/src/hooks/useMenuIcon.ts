import usePermissionStore from '@/store/modules/permission'
import type { RouteRecordRaw } from 'vue-router'

export function useMenuIcon() {
  const permissionStore = usePermissionStore()

  function findIcon(routes: RouteRecordRaw[], path: string, parentPath = ''): string | undefined {
    for (const route of routes) {
      const fullPath = (
        route.path.startsWith('/') ? route.path : `${parentPath}/${route.path}`
      ).replace(/\/$/, '')
      if (fullPath === path && typeof route.meta?.icon === 'string' && route.meta.icon) {
        return route.meta.icon
      }
      const childIcon = findIcon(route.children || [], path, fullPath)
      if (childIcon) return childIcon
    }
  }

  function resolveMenuIcon(paths: string[], fallback: string) {
    for (const path of paths) {
      const icon = findIcon(permissionStore.getPermissionSideBar, path.replace(/\/$/, ''))
      if (icon) return icon
    }
    return fallback
  }

  return { resolveMenuIcon }
}
