import type { ApiCaseRevisionDetail, ApiCaseRevisionListItem } from '../types/api-test/case-version'
import { parseApiCaseRevisionPayload } from '../types/api-test/case-revision-payload'

export interface ApiCaseExecutionVersion {
  revisionId?: number
  releaseId: number | null
  label: string
  readOnly: boolean
}

export function toApiCaseCurrentExecutionVersion(): ApiCaseExecutionVersion {
  return {
    label: '当前配置',
    releaseId: null,
    readOnly: false,
  }
}

export function getApiCaseRevisionLabel(item: ApiCaseRevisionListItem): string {
  if (!item.release) return `修订 r${item.revision_no}`
  return `${item.release.version_label}${item.release.is_current ? '（当前已发布）' : ''}`
}

export function toApiCaseExecutionVersion(item: ApiCaseRevisionListItem): ApiCaseExecutionVersion {
  return {
    revisionId: item.id,
    releaseId: item.release?.id ?? null,
    label: getApiCaseRevisionLabel(item),
    readOnly: Boolean(item.release),
  }
}

export function getApiCaseRevisionStats(detail: ApiCaseRevisionDetail): {
  stepCount: number
  scenarioCount: number
} {
  const payload = parseApiCaseRevisionPayload(detail.payload)
  const steps = payload.api_case_detailed
  return {
    stepCount: steps.length,
    scenarioCount: steps.reduce((count, step) => {
      return count + step.api_case_detailed_parameter.length
    }, 0),
  }
}
