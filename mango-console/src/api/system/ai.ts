import { post } from '@/api/http'

export function postSystemAiTest(capability: 'text' | 'vision' = 'text') {
  return post({
    url: '/system/ai/test',
    data: () => ({ capability }),
  })
}
