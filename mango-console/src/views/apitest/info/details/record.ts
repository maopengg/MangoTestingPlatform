import { cloneLosslessJson } from '@/utils/lossless-json'
import type { ApiInfoId, ApiInfoRecord } from './types'

export function normalizeApiInfoRecord(
  record:
    | (Partial<ApiInfoRecord> & {
        posterior_response?: ApiInfoRecord['posterior_json_path']
        posterior_response_text?: ApiInfoRecord['posterior_re']
      })
    | null,
  id: ApiInfoId
): ApiInfoRecord {
  return cloneLosslessJson({
    id,
    name: '',
    method: null,
    url: '',
    project_product: null,
    headers: null,
    params: null,
    protocol_type: 'http',
    body_type: 'none',
    body_config: null,
    sse_config: null,
    posterior_func: '',
    ...record,
    posterior_json_path: record?.posterior_json_path ?? record?.posterior_response ?? [],
    posterior_re: record?.posterior_re ?? record?.posterior_response_text ?? [],
  })
}
