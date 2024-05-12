import { get } from '@/api/http'
import * as url from './url'

export function getUserProjectModuleGetAll(projectId: number | string | null): Promise<object[]> {
  return get({
    url: url.userModuleGetAll,
    data: () => {
      return {
        project_id: projectId,
      }
    },
  })
    .then((res) => {
      return res.data
    })
    .catch(console.log)
}
