import type { DatasetConfiguration, DatasetItemSource, DatasetWorkflow } from './types'
export const defaultDatasetInputs = () => [{ name: 'case_input', path: '$' }]
export const cloneDatasetConfig = <T>(value: T): T => JSON.parse(JSON.stringify(value))
export const defaultDatasetWorkflow = (): DatasetWorkflow => ({
  preparation: 'none',
  sequence: 'independent',
  steps: [],
  bindings: [],
})
export const inputVariableColumns = [
  { title: '变量名称', slotName: 'name', width: 180 },
  { title: '输入字段', slotName: 'path', width: 260 },
  { title: '引用方式', slotName: 'reference', width: 200 },
  { title: '操作', slotName: 'actions', width: 160, align: 'center', fixed: 'right' },
]
export function datasetConfigurationError(config: Pick<DatasetConfiguration, 'input_variables'>) {
  const variables = config.input_variables || []
  if (
    !variables.length ||
    variables.some((v) => !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(v.name) || !v.path?.startsWith('$'))
  )
    return '请填写有效的变量名称并选择输入字段'
  const names = variables.map((v) => v.name)
  if (
    new Set(names).size !== names.length ||
    names.some((name: string) => ['steps', 'session', 'execution', 'turn'].includes(name))
  )
    return '输入变量名称重复或使用了保留名称'
  return ''
}

export function itemDataSourceError(source: DatasetItemSource | undefined | null) {
  if (!source?.kind || source.kind === 'manual') return ''
  if (!source.binding?.project_product_id || !source.binding?.ref_id)
    return '请选择当前条目的数据来源资源'
  if (source.kind === 'api_info') {
    const variables = source.variables || []
    if (
      !variables.length ||
      variables.some(
        (variable) =>
          !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(variable.name) ||
          !variable.path?.startsWith('$') ||
          variable.path !== variable.path.trim()
      )
    )
      return '请填写有效的响应变量名称和 JSONPath'
    const names = variables.map((variable) => variable.name)
    if (
      new Set(names).size !== names.length ||
      names.some((name: string) => ['steps', 'session', 'execution', 'turn'].includes(name))
    )
      return '响应变量不能重复或使用保留名称'
  }
  if (source.kind === 'sql' && !source.query?.trim()) return '请填写当前条目的 SQL 查询'
  if (source.kind === 'sql' && source.key?.trim()) {
    const keys = source.key
      .split(',')
      .map((key: string) => key.trim())
      .filter(Boolean)
    if (!keys.length || keys.some((key: string) => !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(key)))
      return '变量 Key 需为字母或下划线开头的名称，多个名称用英文逗号分隔'
    if (
      new Set(keys).size !== keys.length ||
      keys.some((key: string) => ['steps', 'session', 'execution', 'turn'].includes(key))
    )
      return '变量 Key 不能重复或使用 steps、session、execution、turn 保留名称'
  }
  return ''
}
