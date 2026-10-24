import { deleted, get, post, put } from '@/api/http'
import type { UiPageStepsPayload } from '@/types/ui-test/case'
import type { FlowData } from '@/types/components'

export function getUiSteps(data: Record<string, unknown>) {
  return get({
    url: '/ui/page/steps',
    data: () => {
      return data
    },
  })
}

export function getUiPageStepReferencedCases(pageStepId: number | string) {
  return get({
    url: '/ui/page/steps/cases',
    data: () => ({
      page_step_id: pageStepId,
    }),
  })
}

export function deleteUiSteps(id: number | string[] | number[]) {
  return deleted({
    url: '/ui/page/steps',
    data: () => {
      return {
        id: id,
      }
    },
  })
}

export function postUiSteps(data: UiPageStepsPayload) {
  return post({
    url: '/ui/page/steps',
    data: () => {
      return data
    },
  })
}

export function postUiPageStepRecordingCommit(data: {
  page_id: number | string
  name: string
  nodes: Record<string, unknown>[]
}) {
  return post({
    url: '/ui/page/steps/recording/commit',
    data: () => data,
  })
}

export function putUiSteps(data: UiPageStepsPayload) {
  return put({
    url: '/ui/page/steps',
    data: () => {
      return data
    },
  })
}

export function getUiStepsTest(
  id: any,
  testObj: number,
  workspaceId?: string,
  control: {
    close_after_execution?: boolean
    before_wait_seconds?: number
    after_wait_seconds?: number
    close_live_after_execution?: boolean
  } = {},
  pageStepDetailId?: number | string,
  silentError = false
) {
  const normalizedPageStepDetailId = Number(pageStepDetailId)
  return get({
    url: '/ui/page/steps/test',
    data: () => {
      return {
        page_step_id: id,
        te: testObj,
        workspace_id: workspaceId || undefined,
        page_step_detail_id:
          Number.isInteger(normalizedPageStepDetailId) && normalizedPageStepDetailId > 0
            ? normalizedPageStepDetailId
            : undefined,
        ...control,
      }
    },
    silentError,
  })
}

export function postUiPageStepOpenBrowser(data: {
  page_step_id: number | string
  test_env: number
}) {
  return post({
    url: '/ui/page/steps/browser/open',
    data: () => data,
  })
}

export function getUiStepsPageStepsName(pageId: number) {
  return get({
    url: '/ui/page/steps/name',
    data: () => {
      return {
        page_id: pageId,
      }
    },
  })
}

export function getUiPageStepAssetProducts() {
  return get({
    url: '/ui/page/steps/asset/products',
    data: () => {
      return {}
    },
  })
}

export function getUiPageStepAssetModules(projectProductId: number | string) {
  return get({
    url: '/ui/page/steps/asset/modules',
    data: () => {
      return {
        project_product_id: projectProductId,
      }
    },
  })
}

export function getUiPageStepAssetSteps(
  projectProductId: number | string,
  moduleId: number | string
) {
  return get({
    url: '/ui/page/steps/asset/steps',
    data: () => ({
      project_product_id: projectProductId,
      module_id: moduleId,
    }),
  })
}

export function getUiPageStepsCopy(pageId: number) {
  return post({
    url: '/ui/page/steps/copy',
    data: () => {
      return {
        page_id: pageId,
      }
    },
  })
}

export function getUiPageStepHealRecords(pageStepId: number | string, page = 1, pageSize = 20) {
  return get({
    url: '/ui/page/steps/healing/records',
    data: () => ({ page_step_id: pageStepId, page, page_size: pageSize }),
  })
}

export function getUiPageStepHealRecord(recordId: number | string) {
  return get({
    url: '/ui/page/steps/healing/record',
    data: () => ({ record_id: recordId }),
  })
}

export function postUiPageStepHealApply(recordId: number | string, reviewedFlowData?: FlowData) {
  return post({
    url: '/ui/page/steps/healing/apply',
    data: () => ({ record_id: recordId, reviewed_flow_data: reviewedFlowData }),
  })
}

export function postUiPageStepHealReject(recordId: number | string) {
  return post({
    url: '/ui/page/steps/healing/reject',
    data: () => ({ record_id: recordId }),
  })
}

export function getUiPageStepVersions(pageStepId: number | string) {
  return get({
    url: '/ui/page/steps/healing/versions',
    data: () => ({ page_step_id: pageStepId }),
  })
}

export function postUiPageStepRollback(pageStepId: number | string, version: number) {
  return post({
    url: '/ui/page/steps/healing/rollback',
    data: () => ({ page_step_id: pageStepId, version }),
  })
}
