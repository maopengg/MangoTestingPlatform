import { deleted, get, post, put } from '@/api/http'

export function getFunctionalIterations(data: Record<string, unknown>) {
  return get({ url: '/functional-test/iteration', data: () => data })
}

export function getFunctionalIterationDetail(id: number | string) {
  return get({ url: '/functional-test/iteration/detail', data: () => ({ id }) })
}

export function getFunctionalIterationGantt(data: Record<string, unknown>) {
  return get({ url: '/functional-test/iteration/gantt', data: () => data })
}

export function getFunctionalIterationBoard(iterationId: number | string) {
  return get({ url: '/functional-test/iteration/board', data: () => ({ iteration_id: iterationId }) })
}

export function getFunctionalIterationCases(data: Record<string, unknown>) {
  return get({ url: '/functional-test/iteration/cases', data: () => data })
}

export function postFunctionalIteration(data: Record<string, unknown>) {
  return post({ url: '/functional-test/iteration', data: () => data })
}

export function putFunctionalIteration(data: Record<string, unknown>) {
  return put({ url: '/functional-test/iteration', data: () => data })
}

export function deleteFunctionalIteration(id: number) {
  return deleted({ url: '/functional-test/iteration', data: () => ({ id }) })
}

export function getManualSuite(data: Record<string, unknown>) {
  return get({ url: '/functional-test/suite', data: () => data })
}

export function putFunctionalRequirement(data: Record<string, unknown>) {
  return put({ url: '/functional-test/requirement', data: () => data })
}

export function postManualSuite(data: Record<string, unknown>) {
  return post({ url: '/functional-test/suite', data: () => data })
}

export function putManualSuite(data: Record<string, unknown>) {
  return put({ url: '/functional-test/suite', data: () => data })
}

export function deleteManualSuite(id: number) {
  return deleted({ url: '/functional-test/suite', data: () => ({ id }) })
}

export function confirmManualSuiteSubmit(id: number | string) {
  return post({ url: '/functional-test/suite/confirm-submit', data: () => ({ id }) })
}

export function transitionManualSuiteStatus(data: Record<string, unknown>) {
  return post({ url: '/functional-test/suite/status', data: () => data })
}

export function unlinkManualSuiteCases(data: Record<string, unknown>) {
  return deleted({ url: '/functional-test/suite/cases', data: () => data })
}

export function getFunctionalRequirementTasks(requirementVersion: number) {
  return get({ url: '/functional-test/requirement-task', data: () => ({ requirement_version: requirementVersion }) })
}

export function postFunctionalRequirementTask(data: Record<string, unknown>) {
  return post({ url: '/functional-test/requirement-task', data: () => data })
}

export function putFunctionalRequirementTask(data: Record<string, unknown>) {
  return put({ url: '/functional-test/requirement-task', data: () => data })
}

export function deleteFunctionalRequirementTask(id: number) {
  return deleted({ url: '/functional-test/requirement-task', data: () => ({ id }) })
}

export function getFunctionalRequirementCases(requirementVersion: number) {
  return get({ url: '/functional-test/requirement-case', data: () => ({ requirement_version: requirementVersion }) })
}

export function bindFunctionalRequirementCases(requirementVersion: number, caseIds: number[]) {
  return post({
    url: '/functional-test/requirement-case/bind',
    data: () => ({ requirement_version: requirementVersion, case_ids: caseIds }),
  })
}

export function unbindFunctionalRequirementCases(requirementVersion: number, caseIds: number[]) {
  return deleted({
    url: '/functional-test/requirement-case/unbind',
    data: () => ({ requirement_version: requirementVersion, case_ids: caseIds }),
  })
}

export function getManualCase(data: Record<string, unknown>) {
  return get({ url: '/functional-test/case', data: () => data })
}

export function getManualCaseExport(data: Record<string, unknown>) {
  return get({ url: '/functional-test/case/export', data: () => data })
}

export function getManualCaseModules(data: Record<string, unknown>) {
  return get({ url: '/functional-test/case/modules', data: () => data })
}

export function getManualSuiteModuleCounts(projectProduct: number | string) {
  return get({
    url: '/functional-test/suite/module-counts',
    data: () => ({ project_product: projectProduct }),
  })
}

export function getManualCaseModuleCounts(projectProduct: number | string) {
  return get({
    url: '/functional-test/case/module-counts',
    data: () => ({ project_product: projectProduct }),
  })
}

export function getManualSuiteContextCandidates(suiteId: number | string) {
  return get({
    url: '/functional-test/suite/context-candidates',
    data: () => ({ suite_id: suiteId }),
  })
}

export function postManualCase(data: Record<string, unknown>) {
  return post({ url: '/functional-test/case', data: () => data })
}

export function postManualCaseBatch(data: Record<string, unknown>) {
  return post({ url: '/functional-test/case/batch-create', data: () => data, silentError: true })
}

export function putManualCase(data: Record<string, unknown>) {
  return put({ url: '/functional-test/case', data: () => data })
}

export function putManualCaseBatch(data: Record<string, unknown>) {
  return put({ url: '/functional-test/case/batch-update', data: () => data, silentError: true })
}

export function deleteManualCase(data: number | Array<number | string> | Record<string, unknown>) {
  return deleted({
    url: '/functional-test/case',
    data: () => {
      if (typeof data === 'number' || Array.isArray(data)) {
        return { id: data }
      }
      if (Array.isArray(data.ids)) {
        return { ...data, id: data.ids }
      }
      return data
    },
  })
}

export function getManualCaseDetail(id: number) {
  return get({ url: '/functional-test/case/detail', data: () => ({ id }) })
}

export function getManualCaseVersions(id: number) {
  return get({ url: '/functional-test/case/versions', data: () => ({ id }) })
}

export function getFunctionalContextResource(data: Record<string, unknown>) {
  return get({ url: '/functional-test/context-resource', data: () => data })
}

export function postFunctionalContextResource(data: Record<string, unknown>) {
  return post({ url: '/functional-test/context-resource', data: () => data })
}

export function putFunctionalContextResource(data: Record<string, unknown>) {
  return put({ url: '/functional-test/context-resource', data: () => data })
}

export function deleteFunctionalContextResource(id: number) {
  return deleted({ url: '/functional-test/context-resource', data: () => ({ id }) })
}

export function postManualAutomationBind(data: Record<string, unknown>) {
  return post({ url: '/functional-test/case/automation/bind', data: () => data })
}

export function getFunctionalCaseCategoryOptions(data: Record<string, unknown>) {
  return get({ url: '/functional-test/case/category-options', data: () => data })
}

export function getFunctionalRequirements(data: Record<string, unknown>) {
  return get({ url: '/functional-test/plan/requirement-options', data: () => data })
}

export function getFunctionalPlans(data: Record<string, unknown>) {
  return get({ url: '/functional-test/plan', data: () => data })
}

export function postFunctionalPlan(data: Record<string, unknown>) {
  return post({ url: '/functional-test/plan', data: () => data })
}

export function putFunctionalPlan(data: Record<string, unknown>) {
  return put({ url: '/functional-test/plan', data: () => data })
}

export function deleteFunctionalPlan(id: number) {
  return deleted({ url: '/functional-test/plan', data: () => ({ id }) })
}

export function getFunctionalPlanDetail(id: number | string) {
  return get({ url: '/functional-test/plan/detail', data: () => ({ id }) })
}

export function getRelatedFunctionalPlans(data: Record<string, unknown>) {
  return get({ url: '/functional-test/plan/related', data: () => data })
}

export function getFunctionalPlanCases(planId: number | string) {
  return get({ url: '/functional-test/plan/cases', data: () => ({ plan_id: planId }) })
}

export function addFunctionalPlanCases(data: Record<string, unknown>) {
  return post({ url: '/functional-test/plan/case/add', data: () => data })
}

export function removeFunctionalPlanCases(data: Record<string, unknown>) {
  return deleted({ url: '/functional-test/plan/case/remove', data: () => data })
}

export function putFunctionalPlanCase(data: Record<string, unknown>) {
  return put({ url: '/functional-test/plan/case', data: () => data })
}

export function copyFunctionalPlanCases(data: Record<string, unknown>) {
  return post({ url: '/functional-test/plan/case/copy', data: () => data })
}

export function startFunctionalPlan(planId: number | string, updateRequirementStatus = false) {
  return post({
    url: '/functional-test/plan/start',
    data: () => ({ plan_id: planId, update_requirement_status: updateRequirementStatus }),
  })
}

export function finishFunctionalPlan(planId: number | string) {
  return post({ url: '/functional-test/plan/finish', data: () => ({ plan_id: planId }) })
}

export function batchFunctionalPlanResult(data: Record<string, unknown>) {
  return post({ url: '/functional-test/plan/case/batch-result', data: () => data })
}

export function getFunctionalGridView(gridKey: string) {
  return get({ url: '/functional-test/case/grid-view', data: () => ({ grid_key: gridKey }) })
}

export function saveFunctionalGridView(data: Record<string, unknown>) {
  return post({ url: '/functional-test/case/grid-view', data: () => data })
}

export function getFunctionalDefects(data: Record<string, unknown>) {
  return get({ url: '/functional-test/defect', data: () => data })
}

export function getFunctionalDefectDetail(id: number | string) {
  return get({ url: '/functional-test/defect/detail', data: () => ({ id }) })
}

export function postFunctionalDefect(data: Record<string, unknown>) {
  return post({ url: '/functional-test/defect', data: () => data })
}

export function putFunctionalDefect(data: Record<string, unknown>) {
  return put({ url: '/functional-test/defect', data: () => data })
}

export function deleteFunctionalDefect(id: number) {
  return deleted({ url: '/functional-test/defect', data: () => ({ id }) })
}

export function transitionFunctionalDefect(data: Record<string, unknown>) {
  return post({ url: '/functional-test/defect/status', data: () => data })
}

export function getFunctionalDefectStats(data: Record<string, unknown>) {
  return get({ url: '/functional-test/defect/stats', data: () => data })
}

export function getRelatedFunctionalDefects(data: Record<string, unknown>) {
  return get({ url: '/functional-test/defect/related', data: () => data })
}

export function getFunctionalDefectOptions(data: Record<string, unknown>) {
  return get({ url: '/functional-test/defect/options', data: () => data })
}

export function bindFunctionalDefectCases(data: Record<string, unknown>) {
  return post({ url: '/functional-test/defect/case/bind', data: () => data })
}

export function unbindFunctionalDefectCases(data: Record<string, unknown>) {
  return deleted({ url: '/functional-test/defect/case/unbind', data: () => data })
}

export function createFunctionalDefectRetestPlan(data: Record<string, unknown>) {
  return post({ url: '/functional-test/defect/retest-plan', data: () => data })
}
