import { deleted, get, post, put } from '@/api/http'

export function getUserDepartment(data: object) {
  return get({
    url: '/user/department',
    data: () => data,
  })
}

export function postUserDepartment(data: object) {
  return post({
    url: '/user/department',
    data: () => data,
  })
}

export function putUserDepartment(data: object) {
  return put({
    url: '/user/department',
    data: () => data,
  })
}

export function deleteUserDepartment(id: number | string[] | number[]) {
  return deleted({
    url: '/user/department',
    data: () => ({ id }),
  })
}

export function getUserDepartmentProductScope(departmentId: number) {
  return get({
    url: '/user/department/product-scope',
    data: () => ({
      department_id: departmentId,
    }),
  })
}

export function putUserDepartmentProductScope(data: object) {
  return put({
    url: '/user/department/product-scope',
    data: () => data,
  })
}
