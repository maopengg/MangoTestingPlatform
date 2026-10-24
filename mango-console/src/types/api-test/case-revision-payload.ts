export type ApiCaseSnapshotRecord = Record<string, any>

export interface ApiCaseDetailedParameterSnapshot extends ApiCaseSnapshotRecord {
  resolved_headers?: Record<string, any> | null
  missing_header_ids: any[]
  gray_configs: ApiCaseSnapshotRecord[]
}

export interface ApiCaseDetailedSnapshot extends ApiCaseSnapshotRecord {
  logical_id: string
  api_info_id: number
  api_info_revision_id: number
  api_info_snapshot?: {
    id: number
    name: string
    project_product_id: number
    module_id: number
    revision_id: number
    revision_no: number
    snapshot_schema_version: number
    checksum: string
    payload: ApiCaseSnapshotRecord
  } | null
  api_case_detailed_parameter: ApiCaseDetailedParameterSnapshot[]
}

export interface ApiCaseRevisionRuntimeSnapshot {
  resolved_front_headers: Record<string, any>
  missing_front_header_ids: any[]
  gray_configs: ApiCaseSnapshotRecord[]
  dependency_freeze_level: string | null
  unsupported_dependency_types: string[]
}

export interface ApiCaseRevisionDependenciesSnapshot {
  data_factory_configs: ApiCaseSnapshotRecord[]
  api_revision_dependencies: ApiCaseSnapshotRecord[]
}

export interface ApiCaseRevisionPayload {
  api_case: ApiCaseSnapshotRecord
  api_case_detailed: ApiCaseDetailedSnapshot[]
  runtime: ApiCaseRevisionRuntimeSnapshot
  dependencies: ApiCaseRevisionDependenciesSnapshot
}

function isRecord(value: unknown): value is Record<string, any> {
  return Object.prototype.toString.call(value) === '[object Object]'
}

function toRecord(value: unknown): ApiCaseSnapshotRecord {
  return isRecord(value) ? value : {}
}

function toArray<T>(value: unknown): T[] {
  return Array.isArray(value) ? (value as T[]) : []
}

export function parseApiCaseRevisionPayload(value: unknown): ApiCaseRevisionPayload {
  const source = toRecord(value)
  const runtime = toRecord(source.runtime)
  const dependencies = toRecord(source.dependencies)
  return {
    api_case: toRecord(source.api_case),
    api_case_detailed: toArray<ApiCaseDetailedSnapshot>(source.api_case_detailed).map((step) => ({
      ...step,
      api_case_detailed_parameter: toArray<ApiCaseDetailedParameterSnapshot>(
        step.api_case_detailed_parameter
      ).map((parameter) => ({
        ...parameter,
        missing_header_ids: toArray(parameter.missing_header_ids),
        gray_configs: toArray(parameter.gray_configs),
      })),
    })),
    runtime: {
      resolved_front_headers: toRecord(runtime.resolved_front_headers),
      missing_front_header_ids: toArray(runtime.missing_front_header_ids),
      gray_configs: toArray(runtime.gray_configs),
      dependency_freeze_level:
        typeof runtime.dependency_freeze_level === 'string'
          ? runtime.dependency_freeze_level
          : null,
      unsupported_dependency_types: toArray<string>(runtime.unsupported_dependency_types),
    },
    dependencies: {
      data_factory_configs: toArray<ApiCaseSnapshotRecord>(dependencies.data_factory_configs),
      api_revision_dependencies: toArray<ApiCaseSnapshotRecord>(
        dependencies.api_revision_dependencies
      ),
    },
  }
}
