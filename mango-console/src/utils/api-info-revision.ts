import { parseApiInfoRevisionPayload } from '@/types/api-test/info-revision-payload'

export function getApiInfoRevisionLabel(item: {
  revision_no: number
  release: { version_label: string; is_current: boolean } | null
}) {
  if (!item.release) return `修订 r${item.revision_no}`
  return `${item.release.version_label}${item.release.is_current ? '（当前已发布）' : ''}`
}

export function getApiInfoPublicationMeta(
  status: 'unpublished' | 'published' | 'draft_changed',
  versionLabel: string | null,
  hasUnpublishedChanges: boolean
) {
  void hasUnpublishedChanges
  if (status === 'published' || status === 'draft_changed') {
    return { label: versionLabel ? `已发布 ${versionLabel}` : '已发布', color: 'green' }
  }
  return { label: '未发布', color: 'gray' }
}

export function getApiInfoRequestSnapshot(payload: Record<string, unknown>) {
  const source = Object.prototype.hasOwnProperty.call(payload, 'api_info')
    ? parseApiInfoRevisionPayload(payload).api_info
    : payload
  const fields = ['method', 'url', 'headers', 'params', 'body_type', 'body_config', 'ass_schema']
  return Object.fromEntries(
    fields
      .filter((field) => Object.prototype.hasOwnProperty.call(source, field))
      .map((field) => [field, source[field]])
  )
}
