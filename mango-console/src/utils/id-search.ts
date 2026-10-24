import { Message } from '@arco-design/web-vue'
import { customRef, type Ref } from 'vue'

const FULL_WIDTH_DIGIT_OFFSET = 0xfee0
const POSITIVE_INTEGER_PATTERN = /^[1-9]\d*$/
const ID_LIST_PATTERN = /^[1-9]\d*(?:,[1-9]\d*)*,?$/

export function normalizeIdSearchValue(value: unknown, multiple = true): string | null {
  const normalized = String(value ?? '')
    .trim()
    .replace(/[０-９]/g, (digit) =>
      String.fromCharCode(digit.charCodeAt(0) - FULL_WIDTH_DIGIT_OFFSET)
    )
    .replace(/[，、]/g, ',')
    .replace(/\s*,\s*/g, ',')
  if (!normalized) return ''
  return (multiple ? ID_LIST_PATTERN : POSITIVE_INTEGER_PATTERN).test(normalized) ? normalized : null
}

export function normalizeIdSearchParams(params: Record<string, unknown>) {
  const normalized = normalizeIdSearchValue(params.id)
  if (!normalized || !normalized.includes(',') || params.id__in != null) return params
  const result = { ...params }
  result.id__in = [...new Set(normalized.split(',').filter(Boolean))].join(',')
  delete result.id
  return result
}

export function createIdSearchValue(initialValue = '', multiple = true): Ref<string> {
  let currentValue = normalizeIdSearchValue(initialValue, multiple) ?? ''

  return customRef<string>((track, trigger) => ({
    get() {
      track()
      return currentValue
    },
    set(value) {
      const normalized = normalizeIdSearchValue(value, multiple)
      if (normalized === null) {
        Message.warning({
          id: 'mango-id-search-input-warning',
          content: multiple ? 'ID 请输入正整数，多个 ID 用逗号或顿号分隔' : 'ID 只能输入正整数',
        })
        trigger()
        return
      }
      currentValue = normalized
      trigger()
    },
  }))
}
