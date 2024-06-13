import { deleted, get, post, put, Response } from '@/api/http'
import * as url from './url'

export function getUserModuleName(projectProductId: number | string | null): Promise<Response> {
  return get({
    url: url.userModuleName,
    data: () => {
      return {
        project_product_id: projectProductId,
      }
    },
  })
}
export function getUserProductAllModuleName(projectId: number | string | null): Promise<Response> {
  return get({
    url: url.userProductAllModuleName,
    data: () => {
      return {
        project_id: projectId,
      }
    },
  })
}

export function getUserTestObjName() {
  return get({
    url: url.userTestObjName,
    data: () => {
      return {}
    },
  })
}

export function getUserProjectProductName(): Promise<Response> {
  return get({
    url: url.userProjectProductName,
    data: () => {
      return {}
    },
  })
}

export function getUserProjectEnvironment(userId: number): Promise<Response> {
  return get({
    url: url.userProjectEnvironment,
    data: () => {
      return {
        id: userId,
      }
    },
  })
}

export function getUserProjectAll(): Promise<Response> {
  return get({
    url: url.userProjectAll,
    data: () => {
      return {}
    },
  })
}

export function getUserNickname() {
  return get({
    url: url.userNickname,
    data: () => {
      return {}
    },
  })
}

export function getUserProduct(data: object) {
  return get({
    url: url.userProduct,
    data: () => {
      return data
    },
  })
}
export function postUserProduct(data: object) {
  return post({
    url: url.userProduct,
    data: () => {
      return data
    },
  })
}

export function putUserProduct(data: object) {
  return put({
    url: url.userProduct,
    data: () => {
      return data
    },
  })
}

export function deleteUserProduct(id: number | string[] | number[]) {
  return deleted({
    url: url.userProduct,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getUserProductName(projectId: number | null = null) {
  return get({
    url: url.userProductName,
    data: () => {
      return {
        project_id: projectId,
      }
    },
  })
}

export function getUserModule(data: object) {
  return get({
    url: url.userModule,
    data: () => {
      return data
    },
  })
}

export function postUserModule(data: object) {
  return post({
    url: url.userModule,
    data: () => {
      return data
    },
  })
}

export function putUserModule(data: object) {
  return put({
    url: url.userModule,
    data: () => {
      return data
    },
  })
}

export function deleteUserModule(id: number | string[] | number[]) {
  return deleted({
    url: url.userModule,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getUserDepartmentList(data: object) {
  return get({
    url: url.userDepartmentList,
    data: () => {
      return data
    },
  })
}

export function postUserDepartmentList(data: object) {
  return post({
    url: url.userDepartmentList,
    data: () => {
      return data
    },
  })
}

export function putUserDepartmentList(data: object) {
  return put({
    url: url.userDepartmentList,
    data: () => {
      return data
    },
  })
}

export function deleteUserDepartmentList(id: number | string[] | number[]) {
  return deleted({
    url: url.userDepartmentList,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getUserInfo(data: object) {
  return get({
    url: url.userInfo,
    data: () => {
      return data
    },
  })
}

export function postUserInfo(data: object) {
  return post({
    url: url.userInfo,
    data: () => {
      return data
    },
  })
}

export function putUserInfo(data: object) {
  return put({
    url: url.userInfo,
    data: () => {
      return data
    },
  })
}

export function deleteUserInfo(id: number | string[] | number[]) {
  return deleted({
    url: url.userInfo,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function postUserPassword(data: object) {
  return put({
    url: url.userPassword,
    data: () => {
      return data
    },
  })
}

export function getUserAllRole() {
  return get({
    url: url.userAllRole,
    data: () => {
      return {}
    },
  })
}

export function getUserRoleList(data: object) {
  return get({
    url: url.userRoleList,
    data: () => {
      return data
    },
  })
}

export function postUserRoleList(data: object) {
  return post({
    url: url.userRoleList,
    data: () => {
      return data
    },
  })
}

export function putUserRoleList(data: object) {
  return put({
    url: url.userRoleList,
    data: () => {
      return data
    },
  })
}

export function deleteUserRoleList(id: number | string[] | number[]) {
  return deleted({
    url: url.userRoleList,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function getUserLogs(data: object) {
  return get({
    url: url.userUserLogs,
    data: () => {
      return data
    },
  })
}

export function postUserLogs(data: object) {
  return post({
    url: url.userUserLogs,
    data: () => {
      return data
    },
  })
}

export function putUserLogs(data: object) {
  return put({
    url: url.userUserLogs,
    data: () => {
      return data
    },
  })
}

export function deleteUserLogs(id: number | string[] | number[]) {
  return deleted({
    url: url.userUserLogs,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function putUserPutProject(userId: number, key: any) {
  return put({
    url: url.userPutProject,
    data: () => {
      return { id: userId, selected_project: key }
    },
  })
}

export function putUserEnvironment(userId: number, key: any) {
  return put({
    url: url.userEnvironment,
    data: () => {
      return { id: userId, selected_environment: key }
    },
  })
}

export function getUserTestObject(data: object) {
  return get({
    url: url.userTestObject,
    data: () => {
      return data
    },
  })
}

export function postUserTestObject(data: object) {
  return post({
    url: url.userTestObject,
    data: () => {
      return data
    },
  })
}

export function putUserTestObject(data: object) {
  return put({
    url: url.userTestObject,
    data: () => {
      return data
    },
  })
}

export function deleteUserTestObject(id: number | string[] | number[]) {
  return deleted({
    url: url.userTestObject,
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function putUserTestObjectPutStatus(data: object) {
  return put({
    url: url.userTestObjectPutStatus,
    data: () => {
      return data
    },
  })
}

export function getUserTestObjectName(projectProductId: number | null) {
  return get({
    url: url.userTestObjectName,
    data: () => {
      return {
        project_product_id: projectProductId,
      }
    },
  })
}
export function getUserFile(type = 0) {
  return get({
    url: url.userFile,
    data: () => {
      return {
        type: type,
      }
    },
  })
}

export function postUserFile(data: object) {
  return post({
    url: url.userFile,
    data: () => {
      return data
    },
  })
}

export function putUserFile(data: object) {
  return put({
    url: url.userFile,
    data: () => {
      return data
    },
  })
}

export function deleteUserFile(id: number | string[] | number[]) {
  return deleted({
    url: url.userFile,
    data: () => {
      return {
        id: id,
      }
    },
  })
}
