import { getOptionId } from '@/utils/business-format'
import type { HeaderDraft, HeaderEntityId, HeaderRecord } from './types'

export function createHeaderDraft(
  record?: HeaderRecord,
  product: HeaderEntityId | null = null
): HeaderDraft {
  return {
    project_product: record ? record.project_product?.id ?? null : product,
    key: record?.key ?? '',
    value: record?.value ?? '',
  }
}

export function headerPayload(draft: HeaderDraft) {
  return {
    project_product: getOptionId(draft.project_product),
    key: draft.key,
    value: draft.value,
  }
}
