import { deleted, get, post } from '@/api/http'
import type { CreateApiCaseRevisionPayload } from '@/types/api-test/case-version'

export function getApiCaseRevisionList(caseId: number | string) {
  return get({
    url: '/api/case/revision',
    data: () => ({ case_id: caseId }),
  })
}

export function getApiCaseRevisionDetail(revisionId: number) {
  return get({
    url: '/api/case/revision/detail',
    losslessJson: true,
    data: () => ({ id: revisionId }),
  })
}

export function createApiCaseRevision(data: CreateApiCaseRevisionPayload) {
  return post({
    url: '/api/case/revision',
    data: () => data,
  })
}

export function submitApiCasePrepublication(caseId: number, revisionId: number) {
  return post({
    url: '/api/case/prepublication',
    data: () => ({ case_id: caseId, revision_id: revisionId }),
  })
}

export function approveApiCasePrepublication(caseId: number) {
  return post({
    url: '/api/case/prepublication/approve',
    data: () => ({ case_id: caseId }),
  })
}

export function revertApiCasePrepublication(caseId: number) {
  return deleted({
    url: '/api/case/prepublication',
    data: () => ({ case_id: caseId }),
  })
}

export function unpublishApiCaseRelease(caseId: number, releaseId: number) {
  return post({
    url: '/api/case/release/unpublish',
    data: () => ({ case_id: caseId, release_id: releaseId }),
  })
}

export function getApiCaseRevisionCheckoutImpact(caseId: number, revisionId: number) {
  return get({
    url: '/api/case/revision/checkout/impact',
    data: () => ({ case_id: caseId, revision_id: revisionId }),
  })
}

export function checkoutApiCaseRevision(
  caseId: number,
  revisionId: number,
  restoreMissingDependencies: boolean
) {
  return post({
    url: '/api/case/revision/checkout',
    data: () => ({
      case_id: caseId,
      revision_id: revisionId,
      restore_missing_dependencies: restoreMissingDependencies,
    }),
  })
}

export function deleteApiCaseRevision(caseId: number | string, revisionId: number) {
  return deleted({
    url: '/api/case/revision',
    data: () => ({ case_id: Number(caseId), revision_id: revisionId }),
  })
}
