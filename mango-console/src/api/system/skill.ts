import { get } from '@/api/http'
import request from '@/api/axios.config'

export function getSystemSkillList() {
  return get({
    url: 'system/skill/list',
    data: () => ({}),
  })
}

export function getSystemSkillDetail(key: string) {
  return get({
    url: 'system/skill/detail',
    data: () => ({ key }),
  })
}

export function downloadSystemSkill(key: string) {
  return request.get('system/skill/download', {
    params: { key },
    responseType: 'blob',
  })
}
