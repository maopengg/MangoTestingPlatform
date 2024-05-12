import { deleted, get, post, put } from '@/api/http'
import * as url from './url'

export function getSystemEnumExp(): Promise<object[]> {
  return get({
    url: url.systemEnumExp,
    data: () => {
      return {}
    },
  })
    .then((res) => {
      return res.data
    })
    .catch(console.log)
}
