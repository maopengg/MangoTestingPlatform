import { deleted, get, post } from '@/api/http'

export function getApiInfoRevisionList(apiInfoId: number | string) {
  return get({ url: '/api/info/revision', data: () => ({ api_info_id: apiInfoId }) })
}

export function getApiInfoRevisionDetail(revisionId: number) {
  return get({
    url: '/api/info/revision/detail',
    losslessJson: true,
    data: () => ({ id: revisionId }),
  })
}

export function createApiInfoRevision(apiInfoId: number | string, summary?: string) {
  return post({
    url: '/api/info/revision',
    data: () => ({ api_info_id: Number(apiInfoId), summary }),
  })
}

export function publishApiInfoRevision(
  apiInfoId: number | string,
  revisionId: number,
  releaseNote?: string
) {
  return post({
    url: '/api/info/release',
    data: () => ({
      api_info_id: Number(apiInfoId),
      revision_id: revisionId,
      release_note: releaseNote,
    }),
  })
}

export function checkoutApiInfoRevision(
  apiInfoId: number | string,
  revisionId: number,
  summary?: string
) {
  return post({
    url: '/api/info/revision/checkout',
    data: () => ({ api_info_id: Number(apiInfoId), revision_id: revisionId, summary }),
  })
}

export function deleteApiInfoRevision(apiInfoId: number | string, revisionId: number) {
  return deleted({
    url: '/api/info/revision',
    data: () => ({ api_info_id: Number(apiInfoId), revision_id: revisionId }),
  })
}
