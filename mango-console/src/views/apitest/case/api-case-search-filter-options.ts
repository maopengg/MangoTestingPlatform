import { resolveSearchFilterOptions } from '../search-filter-options'

const enumKeys: Record<string, string> = {
  status: 'task_status',
  level: 'case_level',
  scenario_layer: 'api_case_scenario_layer',
  scenario_type: 'api_case_scenario_type',
  scenario_tags: 'api_case_scenario_tag',
  execution_configuration: 'api_case_configuration_filter',
}

export function resolveApiCaseSearchOptions(
  item: any,
  userList: any[],
  enumStore: Record<string, any>
) {
  const options = resolveSearchFilterOptions(item, userList, enumStore, enumKeys, [
    'case_people',
    'update_user',
  ])
  if (item.key === 'status') return options.map((option: any) =>
    String(option.key) === '2' ? { ...option, title: '待测试' } : option)
  if (item.key !== 'execution_configuration') return options
  const selected = new Set(Array.isArray(item.value) ? item.value.map(String) : [])
  return options.map((option: any) => {
    const key = String(option.key)
    const opposite = key.startsWith('has_') ? key.replace(/^has_/, 'no_') : key.replace(/^no_/, 'has_')
    return { ...option, disabled: selected.has(opposite) }
  })
}
