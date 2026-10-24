import type {
  ApiCaseBatchExecutionPlan,
  ApiCaseBatchExecutionItem,
  ApiCaseBatchRunRequestItem,
  ApiCasePublicationMeta,
  ApiCasePublicationStatus,
  ApiCaseTaskBindingPlan,
  ApiCaseTaskCandidate,
  ApiCaseVersionListRow,
} from '../types/api-test/case-version'

export function buildScheduledTaskCaseItems(
  rows: ApiCaseTaskCandidate[],
  selectedReleaseIds: Record<string, number | null | undefined>
): ApiCaseTaskBindingPlan {
  return rows.reduce<ApiCaseTaskBindingPlan>(
    (plan, row) => {
      const releaseId = selectedReleaseIds[String(row.key)] ?? row.published_release_id
      const release = row.release_options.find(
        (item) => item.release_id === releaseId && item.status === 'published'
      )
      if (!release) {
        plan.blocked.push({
          case_id: Number(row.key),
          case_name: row.title,
          reason: row.published_release_id ? '所选版本不可执行' : '请先发布用例',
        })
        return plan
      }
      plan.items.push({
        case_id: Number(row.key),
        case_release_id: release.release_id,
      })
      return plan
    },
    { items: [], blocked: [] }
  )
}

export function toApiCaseBatchRunItems(
  items: ApiCaseBatchExecutionItem[]
): ApiCaseBatchRunRequestItem[] {
  return items.map(({ case_id, case_release_id }) => ({ case_id, case_release_id }))
}

export function getApiCasePublicationMeta(
  status: ApiCasePublicationStatus,
  versionLabel: string | null,
  hasUnpublishedChanges: boolean,
  prepublishedRevisionNo?: number | null
): ApiCasePublicationMeta {
  void hasUnpublishedChanges
  if (status === 'prepublished') {
    const prepublishedLabel = prepublishedRevisionNo
      ? `预发布 r${prepublishedRevisionNo}`
      : '预发布'
    return {
      label: prepublishedLabel,
      color: 'orange',
    }
  }
  if (status === 'published') {
    return {
      label: versionLabel ? `已发布 ${versionLabel}` : '已发布',
      color: 'green',
    }
  }
  return { label: '未发布', color: 'gray' }
}

export function buildPublishedBatchItems(rows: ApiCaseVersionListRow[]): ApiCaseBatchExecutionPlan {
  return rows.reduce<ApiCaseBatchExecutionPlan>(
    (plan, row) => {
      if (
        row.published_release_id === null ||
        row.published_revision_id === null ||
        !row.published_version_label
      ) {
        plan.blocked.push({
          case_id: row.id,
          case_name: row.name,
          reason: '请先发布用例',
        })
        return plan
      }
      plan.executable.push({
        case_id: row.id,
        case_release_id: row.published_release_id,
        case_revision_id: row.published_revision_id,
        version_label: row.published_version_label,
      })
      return plan
    },
    { executable: [], blocked: [] }
  )
}
