import type { RouteLocationNormalizedLoaded } from 'vue-router'

export function getRouteViewKey(
  route: Pick<RouteLocationNormalizedLoaded, 'path' | 'fullPath' | 'meta'>
): string {
  return route.meta.reuseOnQueryChange === true ? route.path : route.fullPath
}
