import type {
  ExecutionRecord,
  ExecutionDetail,
  SourceInfo,
  ExecutionItem,
  JsonValue,
} from './types'
const CLEANABLE_STATUSES = new Set([0, 2, 4]),
  ACTIVE_EXECUTION_STATUSES = new Set([2, 3])
export const canCleanup = (record: ExecutionRecord) =>
  CLEANABLE_STATUSES.has(Number(record.cleanup_status)) &&
  !ACTIVE_EXECUTION_STATUSES.has(Number(record.status))
export const enumTitle = (
  options: Array<{ key: string | number; title: string }> = [],
  value: unknown
) => options.find((item) => String(item.key) === String(value))?.title || String(value ?? '-')
export function stringifyCellValue(value: JsonValue | undefined) {
  if (typeof value === 'string') return value
  if (value == null) return '-'
  return JSON.stringify(value)
}
export function formatSourceId(source?: SourceInfo | null) {
  if (!source) return '-'
  return (
    [
      source.source_id ? `来源 ${source.source_id}` : '',
      source.template_id ? `模板 ${source.template_id}` : '',
    ]
      .filter(Boolean)
      .join(' / ') || '-'
  )
}
export function formatSourceMeta(source?: SourceInfo | null) {
  if (!source) return '-'
  return (
    [
      source.executor_name ? `执行人 ${source.executor_name}` : '',
      !source.executor_name && source.case_owner_name ? `责任人 ${source.case_owner_name}` : '',
      source.case_id ? `用例ID ${source.case_id}` : '',
      source.scenario_id ? `场景ID ${source.scenario_id}` : '',
      source.template_id ? `模板ID ${source.template_id}` : '',
    ]
      .filter(Boolean)
      .join(' / ') || formatSourceId(source)
  )
}
export function formatUserName(name?: string, username?: string) {
  return name && username ? `${name}（${username}）` : name || username || '-'
}
export function formatApiInfo(source?: SourceInfo | null) {
  return source?.api_info_url
    ? `${source.api_info_method_name ? `${source.api_info_method_name} ` : ''}${
        source.api_info_url
      }`
    : '-'
}
export function formatStorageSnapshot(snapshot: ExecutionItem['storage_snapshot']) {
  if (!snapshot) return '-'
  return (
    [
      snapshot.database_name || (snapshot.database_id ? `数据库 ${snapshot.database_id}` : ''),
      snapshot.table_name || '',
      snapshot.primary_key ? `主键 ${snapshot.primary_key}` : '',
    ]
      .filter(Boolean)
      .join(' / ') || '-'
  )
}
export const sqlExecutionStatusColor = (status: string) =>
  status === 'success'
    ? 'green'
    : status === 'running'
    ? 'blue'
    : status === 'rolled_back'
    ? 'orange'
    : 'red'
export const sqlExecutionStatusName = (status: string) =>
  ({ running: '执行中', success: '成功', fail: '失败', timeout: '超时', rolled_back: '已回滚' }[
    status
  ] ||
  status ||
  '-')
export function formatStage(
  stage: string,
  options: Array<{ key: string | number; title: string }> = []
) {
  return (
    {
      create: '创建',
      post_insert_update: '插入后回写',
      cleanup: '清理',
      residual_check: '残留校验',
    }[stage] ||
    enumTitle(options, stage) ||
    '-'
  )
}
export function cleanupResources(detail: ExecutionDetail | null) {
  return (detail?.items || []).flatMap((item) => {
    const state = item.cleanup_resources || {}
    return (state.snapshots || []).map((snapshot, index) => {
      const result = (state.results || []).find((result) =>
        result.snapshot_index != null
          ? result.snapshot_index === index
          : result.index === snapshot.index && result.document_id === snapshot.document_id
      )
      return {
        key: `${item.id}:${index}`,
        item_id: item.id,
        snapshot_index: index,
        tenant_lineage: snapshot.rule?.tenant_lineage,
        alias: item.alias,
        mode: snapshot.rule?.mode === 'delete_and_verify' ? '精确删除并验证' : '仅验证，不删除',
        document_id_field:
          snapshot.rule?.document_id_field || item.storage_snapshot?.primary_key || '-',
        index: snapshot.index,
        document_id: snapshot.document_id,
        sql_status: state.sql_cleaned ? '已清理' : '未清理',
        status: !result
          ? item.cleanup_status === 2
            ? '未确认清理'
            : '待检查'
          : result.success
          ? '已确认消失'
          : '失败',
        checked_at: result?.checked_at || '-',
        error:
          result?.error || item.cleanup_error || (!result ? '尚未完成ES验证，不代表零残留' : '-'),
      }
    })
  })
}
