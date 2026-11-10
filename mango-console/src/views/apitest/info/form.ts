import { getOptionId } from '@/utils/business-format'
import { cloneLosslessJson } from '@/utils/lossless-json'
import type {
  ApiInfoDraft,
  ApiInfoMetadataRecord,
  McpBinding,
  NavigationDefaults,
  GrpcMethod,
} from './types'

export function normalizeProtocolType(value?: string | null) {
  return String(value || 'http').toLowerCase()
}
export function createApiInfoDraft(
  record?: ApiInfoMetadataRecord,
  defaults: NavigationDefaults = {},
  protocol = 'http'
): ApiInfoDraft {
  return {
    project_product: record ? getOptionId(record.project_product) : defaults.projectProduct ?? null,
    module: record
      ? getOptionId(record.module)
      : defaults.module === '__all__'
      ? null
      : defaults.module ?? null,
    name: record?.name ?? '',
    url: record?.url ?? '',
    protocol_type: record?.protocol_type || protocol,
    method: record?.method ?? null,
    body_type: record?.body_type || 'none',
    curl_command: '',
    tool_name: record?.mcp_binding?.tool_name || '',
  }
}
export function apiInfoPayload(draft: ApiInfoDraft, importing: boolean, binding: McpBinding = {}) {
  const base = {
    project_product: getOptionId(draft.project_product),
    module: getOptionId(draft.module),
    name: draft.name,
  }
  if (importing) return { ...base, curl_command: draft.curl_command }
  const protocol = normalizeProtocolType(draft.protocol_type)
  return {
    ...base,
    url: draft.url.trim(),
    protocol_type: protocol,
    method: draft.method,
    body_type: draft.body_type,
    ...(protocol === 'mcp'
      ? {
          mcp_binding: {
            ...cloneLosslessJson(binding),
            tool_name: draft.tool_name.trim(),
            tool_type: binding.tool_type ?? 'tool',
            tool_enabled: binding.tool_enabled ?? true,
            transport_type: binding.transport_type ?? 0,
          },
        }
      : {}),
  }
}
export function grpcStreamingLabel(item: GrpcMethod) {
  if (item.client_streaming && item.server_streaming) return '双向流'
  if (item.client_streaming) return '客户端流'
  if (item.server_streaming) return '服务端流'
  return ''
}
