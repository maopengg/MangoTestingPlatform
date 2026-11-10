import type { EntityRecord, StatusLog } from './types'
export function enumTitle(
  options: Array<{ key: string | number; title: string }> = [],
  value: unknown
) {
  return options.find((item) => Number(item.key) === Number(value))?.title || String(value ?? '-')
}
export function statusSourceColor(value: unknown) {
  const colors: Record<number, string> = {
    0: 'gray',
    1: 'arcoblue',
    2: 'purple',
    3: 'orange',
    4: 'cyan',
    5: 'blue',
  }
  return colors[Number(value)] || 'gray'
}
export const formatStatusTime = (value?: string) =>
  value ? value.replace('T', ' ').replace(/\.\d+(?=\+|Z|$)/, '') : '-'
export const formatStatusReference = (record: StatusLog) =>
  !record.source_record_type
    ? '-'
    : record.source_record_id
    ? `${record.source_record_type} #${record.source_record_id}`
    : record.source_record_type
export function statusTooltip(
  record: EntityRecord,
  options: Array<{ key: string | number; title: string }>
) {
  const source =
    options.find((item) => Number(item.key) === Number(record.status_change_source))?.title ||
    '历史来源未知'
  return `来源：${source}；原因：${
    record.status_change_reason || '未记录原因'
  }；时间：${formatStatusTime(record.status_changed_at)}`
}
