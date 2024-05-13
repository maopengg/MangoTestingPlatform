import { get, Response } from '@/api/http'
import * as url from './url'
import { userProjectProductName } from './url'

export function getUserProjectModuleGetAll(
  projectProductId: number | string | null
): Promise<Response> {
  return get({
    url: url.userModuleGetAll,
    data: () => {
      return {
        project_product_id: projectProductId,
      }
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
