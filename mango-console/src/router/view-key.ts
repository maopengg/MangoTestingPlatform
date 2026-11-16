import type { RouteLocationNormalizedLoaded } from 'vue-router'

// 菜单动态生成的路由不会继承静态 meta；连接 ID 只切换工作台右侧内容。
const queryReusablePaths = new Set(['/config/data-source/index'])

export function getRouteViewKey(
  route: Pick<RouteLocationNormalizedLoaded, 'path' | 'fullPath' | 'meta'>
): string {
  return route.meta.reuseOnQueryChange === true || queryReusablePaths.has(route.path)
    ? route.path
    : route.fullPath
}
