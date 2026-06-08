import { post } from '@/api/http'

export function postSystemAiTest() {
  return post({
    url: '/system/ai/test',
    data: () => {
      return {}
    },
  })
}
