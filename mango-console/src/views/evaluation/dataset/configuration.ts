import { cloneLosslessJson } from '@/utils/lossless-json'
import type { DatasetConfiguration, DatasetSchemaSnapshot } from './types'
import type { ParameterSchema } from '../types'

export function createDatasetConfiguration(snapshot?: DatasetSchemaSnapshot): DatasetConfiguration {
  return cloneLosslessJson({
    ...snapshot,
    input_variables: snapshot?.input_variables ?? [{ name: 'case_input', path: '$' }],
    workflow: snapshot?.workflow ?? {
      preparation: 'none',
      sequence: 'independent',
      steps: [],
      bindings: [],
    },
  })
}

export function datasetInputFields(config: DatasetConfiguration, sample: unknown) {
  const fields = new Map<string, string>([['$', '完整输入']])
  function collect(
    schema: ParameterSchema | undefined,
    value: unknown,
    path: string,
    label: string,
    depth: number
  ) {
    if (depth > 5) return
    const record =
      value && typeof value === 'object' && !Array.isArray(value)
        ? (value as Record<string, unknown>)
        : {}
    const keys = new Set([...Object.keys(schema?.properties || {}), ...Object.keys(record)])
    for (const key of keys) {
      const child = schema?.properties?.[key]
      const next =
        path + (/^[A-Za-z_][A-Za-z0-9_]*$/.test(key) ? '.' + key : '[' + JSON.stringify(key) + ']')
      const title = label + (child?.title || key)
      fields.set(next, title)
      collect(child, record[key], next, title + ' / ', depth + 1)
    }
  }
  collect(config.input_schema, sample, '$', '', 0)
  for (const variable of config.input_variables) {
    if (!fields.has(variable.path))
      fields.set(variable.path, variable.path.replace(/^\$\.?/, '') || '完整输入')
  }
  return [...fields].map(([value, label]) => ({ value, label }))
}
