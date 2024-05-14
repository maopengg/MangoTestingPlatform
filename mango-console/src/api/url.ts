import { baseURL } from './axios.config'

export const baseAddress = baseURL

// 项目原始接口
export const updateUserInfo = '/updateUser'
export const addDepartment = '/addDepartment'
export const getCardList = '/getCardList'
export const getCommentList = '/getCommentList'

// 修改原始接口后的
export const login = '/login'
export const register = '/register'
export const getMenuListByRoleId = '/menu'
export const getAllMenuByRoleId = '/role'
export const test = '/config/test'

export const userFilesAllList = '/user/files/all/list'
export const userFilesUpload = '/user/files/upload'
export const userFilesDownload = '/user/files/download'
export const userFilesDelete = '/user/files/delete'

declare module '@vue/runtime-core' {
  interface ComponentCustomProperties {
    $urlPath: Record<string, string>
  }
}
