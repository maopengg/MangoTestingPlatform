export type ApiInfoSnapshotRecord = Record<string, any>

export interface ApiInfoRevisionRuntimeSnapshot extends ApiInfoSnapshotRecord {}

export interface ApiInfoRevisionPayload {
  api_info: ApiInfoSnapshotRecord
  runtime: ApiInfoRevisionRuntimeSnapshot
}

function isRecord(value: unknown): value is Record<string, any> {
  return Object.prototype.toString.call(value) === '[object Object]'
}

export function parseApiInfoRevisionPayload(value: unknown): ApiInfoRevisionPayload {
  const source = isRecord(value) ? value : {}
  return {
    api_info: isRecord(source.api_info) ? source.api_info : {},
    runtime: isRecord(source.runtime) ? source.runtime : {},
  }
}
