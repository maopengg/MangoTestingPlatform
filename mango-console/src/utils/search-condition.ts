import type { FormItem } from '@/types/components'

const DEFAULT_SINGLE_SELECT_SEARCH_KEYS = new Set([
  'project_product',
  'module',
  'page_id',
  'tasks_id',
  'scheduled_task',
  'report_source',
  'project',
  'scenario_tags',
  'test_envs',
  'is_latest',
])

/**
 * 将普通枚举搜索条件统一升级为多选；有上下级依赖或专用查询协议的字段保持单选。
 */
export function enableMultiSelectSearch(
  formItems: FormItem[],
  extraSingleSelectKeys: string[] = []
): FormItem[] {
  const singleSelectKeys = new Set([...DEFAULT_SINGLE_SELECT_SEARCH_KEYS, ...extraSingleSelectKeys])
  formItems.forEach((item) => {
    if (
      !['select', 'cascader'].includes(item.type || '') ||
      item.multiple ||
      singleSelectKeys.has(String(item.key))
    ) {
      return
    }
    item.value = []
    item.multiple = true
    item.searchOperator = 'in'
    item.reset = function () {
      this.value = []
    }
  })
  return formItems
}

/** 手写搜索区仅转换声明过的集合字段，不改分页、文本或编辑表单数据。 */
export function normalizeMultiSelectSearchParams(params: Record<string, unknown>, keys: string[]) {
  const result = { ...params }
  for (const key of keys) {
    const value = result[key]
    if (!Array.isArray(value)) continue
    const values = [...new Set(value.filter(item => item !== '' && item != null))]
    delete result[key]
    if (values.length) result[`${key}__in`] = values.join(',')
  }
  return result
}
