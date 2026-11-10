import { getOptionId } from '@/utils/business-format'
import { cloneLosslessJson } from '@/utils/lossless-json'
import type { MockConfigPayload, MockRule } from '@/api/apitest/mock'
import type { MockDraft, MockRecord } from './types'
import { emptyResponse } from './config'

export function createMockDraft(record?: MockRecord): MockDraft {
  return cloneLosslessJson({
    id: record?.id,
    project_product: record ? getOptionId(record.project_product) : null,
    name: record?.name ?? '',
    mock_key: record?.mock_key ?? '',
    description: record?.description ?? '',
    method: record?.method ?? 0,
    path: record?.path ?? '/',
    enabled: record?.enabled ?? true,
    record_call_log: record?.record_call_log ?? false,
    update_time: record?.update_time,
    config: {
      methods: record?.config?.methods ?? [record?.method ?? 0],
      assertions: record?.config?.assertions ?? [],
      rules: record?.config?.rules ?? [],
      default_response: record?.config?.default_response ?? emptyResponse(),
      request_decryption: {
        type: 'none' as const,
        encrypt_key: '',
        verification_token: '',
        configuration_error: '',
        ...record?.config?.request_decryption,
      },
    },
  })
}
export function mockPayload(form: MockDraft): MockConfigPayload {
  const { configuration_error, ...decryption } = form.config.request_decryption
  return cloneLosslessJson({
    ...(form.id == null ? {} : { id: form.id }),
    // 后端使用更新时间做并发修改校验，不能作为普通审计字段剔除。
    ...(form.update_time ? { update_time: form.update_time } : {}),
    project_product: getOptionId(form.project_product) ?? '',
    name: form.name,
    mock_key: form.mock_key,
    description: form.description,
    method: form.config.methods[0] ?? 0,
    path: form.path,
    enabled: form.enabled,
    record_call_log: form.record_call_log,
    config: {
      methods: form.config.methods,
      assertions: form.config.assertions,
      rules: form.config.rules,
      default_response: form.config.default_response,
      request_decryption: decryption,
    },
  })
}
export function editorKey(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`
}
export function createMockRule(index: number): MockRule {
  return {
    key: editorKey('rule'),
    name: `响应规则 ${index + 1}`,
    enabled: true,
    matchers: [],
    response: emptyResponse(),
  }
}
export function mockRequestPath(form: Pick<MockDraft, 'mock_key' | 'path'>) {
  return form.mock_key ? `/${form.mock_key}${form.path && form.path !== '/' ? form.path : ''}` : ''
}
export function setMockRequestPath(form: MockDraft, value: string) {
  const normalized = value.trim().replace(/^\/+/, ''),
    separator = normalized.indexOf('/')
  form.mock_key = separator === -1 ? normalized : normalized.slice(0, separator)
  form.path = separator === -1 ? '/' : `/${normalized.slice(separator + 1)}`
}
