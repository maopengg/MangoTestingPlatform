import { cloneLosslessJson } from '@/utils/lossless-json'
import type { DataFactoryOutputConfig } from '@/types/data-factory'

export type FactoryConfigId = number | string
interface Reference { id: FactoryConfigId | null; name: string }
export interface FactoryConfigTemplate {
  id: FactoryConfigId; name: string
  project_product: Reference | null; module: Reference | null
  entity: (Reference & { table_name: string; datasource_alias: Reference | null }) | null
  cleanup_strategy: number | null; output_config: DataFactoryOutputConfig
}
export interface FactoryConfigRecord {
  id: FactoryConfigId; source_type: number | null; source_id: FactoryConfigId | null
  name: string; template: FactoryConfigTemplate | null; sort: number; status: number; stage: number
  cleanup_strategy: number | null; field_overrides: unknown
}
export interface FactoryConfigWrite {
  id: FactoryConfigId | null; template: FactoryConfigId; name: string; sort: number
  field_overrides: unknown; cleanup_strategy: number | null; status: number; stage: number
}
export interface FactoryConfigSummary { count: number | null; loading: boolean; error: string }
export function factoryConfigObject(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw Error('Invalid factory configuration')
  return value as Record<string, unknown>
}
export function factoryConfigId(value: unknown): FactoryConfigId | null {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? value
    : typeof value === 'string' && value.trim() ? value : null
}
function requiredId(value: unknown): FactoryConfigId { const id = factoryConfigId(value); if (id === null) throw Error('Missing factory configuration ID'); return id }
function text(value: unknown): string { if (value == null) return ''; if (typeof value !== 'string') throw Error('Invalid factory text'); return value }
function integer(value: unknown, fallback: number): number { if (value == null) return fallback; if (typeof value !== 'number' || !Number.isSafeInteger(value)) throw Error('Invalid factory number'); return value }
function cleanupStrategy(value: unknown): number | null { return value == null || value === '' ? null : integer(value, 0) }
function reference(value: unknown): Reference | null {
  if (value == null) return null
  if (typeof value !== 'object') return { id: requiredId(value), name: '' }
  const row = factoryConfigObject(value)
  return { id: factoryConfigId(row.id), name: text(row.name) }
}
export function readFactoryConfigTemplate(value: unknown): FactoryConfigTemplate | null {
  if (value == null) return null
  if (typeof value !== 'object') return { id: requiredId(value), name: '', project_product: null, module: null, entity: null, cleanup_strategy: null, output_config: [] }
  const row = factoryConfigObject(value), entity = reference(row.entity), entityRow = row.entity && typeof row.entity === 'object' ? factoryConfigObject(row.entity) : {}
  if (row.output_config != null && !Array.isArray(row.output_config)) throw Error('Invalid factory outputs')
  return {
    id: requiredId(row.id), name: text(row.name), project_product: reference(row.project_product), module: reference(row.module),
    entity: entity ? { ...entity, table_name: text(entityRow.table_name), datasource_alias: reference(entityRow.datasource_alias) } : null,
    cleanup_strategy: row.cleanup_strategy == null ? null : integer(row.cleanup_strategy, 0),
    output_config: (Array.isArray(row.output_config) ? row.output_config : []).map(value => { const item = factoryConfigObject(value); return { field: text(item.field), key: text(item.key) } }),
  }
}
export function readFactoryConfigRows(values: unknown, owner?: { sourceId: FactoryConfigId; sourceType: number }): FactoryConfigRecord[] {
  if (!Array.isArray(values)) throw Error('Invalid factory configuration list')
  const rows = values.map((value): FactoryConfigRecord => {
    const row = factoryConfigObject(value), sourceId = factoryConfigId(row.source_id ?? row.case), sourceType = row.source_type == null ? null : integer(row.source_type, 0)
    if (owner && (sourceId === null || sourceType === null || String(sourceId) !== String(owner.sourceId) || sourceType !== owner.sourceType)) throw Error('Unexpected factory configuration owner')
    const status = integer(row.status, 1)
    if (status !== 0 && status !== 1) throw Error('Invalid factory configuration status')
    return { id: requiredId(row.id), source_id: sourceId ?? owner?.sourceId ?? null, source_type: sourceType ?? owner?.sourceType ?? null, name: text(row.name), template: readFactoryConfigTemplate(row.template), sort: integer(row.sort, 0), status, stage: integer(row.stage, 1), cleanup_strategy: row.cleanup_strategy == null ? null : integer(row.cleanup_strategy, 0), field_overrides: cloneLosslessJson(row.field_overrides ?? {}) }
  })
  if (new Set(rows.map(row => String(row.id))).size !== rows.length) throw Error('Duplicate factory configurations')
  return rows
}
export function factoryConfigResponse(response: unknown): unknown { const row = factoryConfigObject(response); if (row.code !== 200) throw Error('Factory request failed'); return row.data }
export function factoryConfigWrite(value: FactoryConfigWrite): FactoryConfigWrite {
  const status = integer(value.status, 1)
  if (status !== 0 && status !== 1) throw Error('Invalid factory configuration status')
  return { id: value.id == null ? null : requiredId(value.id), template: requiredId(value.template), name: text(value.name), sort: integer(value.sort, 0), field_overrides: cloneLosslessJson(value.field_overrides), cleanup_strategy: cleanupStrategy(value.cleanup_strategy), status, stage: integer(value.stage, 1) }
}
