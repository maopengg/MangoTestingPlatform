import { baseURL } from './axios.config'

export const baseAddress = baseURL

// 修改原始接口后的
export const login = '/login'
export const register = '/register'
export const getMenuListByRoleId = '/menu'

declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $urlPath: Record<string, string>
  }
}
