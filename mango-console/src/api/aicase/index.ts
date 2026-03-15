import { deleted, get, post, put } from '@/api/http'

// ===== 需求管理 =====
export function getAiRequirement(data: object) {
  return get({ url: '/ai/requirement', data: () => data })
}
export function postAiRequirement(data: object) {
  return post({ url: '/ai/requirement', data: () => data })
}
export function putAiRequirement(data: object) {
  return put({ url: '/ai/requirement', data: () => data })
}
export function deleteAiRequirement(id: number | string[] | number[]) {
  return deleted({ url: '/ai/requirement', data: () => ({ id }) })
}
export function getAiRequirementName(projectProductId?: number) {
  return get({ url: '/ai/requirement/name', data: () => ({ project_product: projectProductId }) })
}
export function postAiRequirementAnalyze(requirementId: number) {
  return post({ url: '/ai/requirement/analyze', data: () => ({ requirement_id: requirementId }) })
}
export function postAiRequirementGeneratePoints(requirementId: number) {
  return post({ url: '/ai/requirement/generate/points', data: () => ({ requirement_id: requirementId }) })
}
export function postAiRequirementGenerateCases(requirementId: number) {
  return post({ url: '/ai/requirement/generate/cases', data: () => ({ requirement_id: requirementId }) })
}

// ===== 需求拆分 =====
export function getAiRequirementSplit(data: object) {
  return get({ url: '/ai/requirement/split', data: () => data })
}
export function putAiRequirementSplit(data: object) {
  return put({ url: '/ai/requirement/split', data: () => data })
}
export function deleteAiRequirementSplit(id: number | string[] | number[]) {
  return deleted({ url: '/ai/requirement/split', data: () => ({ id }) })
}
export function getAiSplitByRequirement(requirementId: number) {
  return get({ url: '/ai/requirement/split/by/requirement', data: () => ({ requirement_id: requirementId }) })
}
export function postAiSplitBatchConfirm(requirementId: number, items: any[]) {
  return post({ url: '/ai/requirement/split/batch/confirm', data: () => ({ requirement_id: requirementId, items }) })
}

// ===== 测试点 =====
export function getAiTestPoint(data: object) {
  return get({ url: '/ai/test/point', data: () => data })
}
export function putAiTestPoint(data: object) {
  return put({ url: '/ai/test/point', data: () => data })
}
export function deleteAiTestPoint(id: number | string[] | number[]) {
  return deleted({ url: '/ai/test/point', data: () => ({ id }) })
}
export function getAiTestPointByRequirement(requirementId: number) {
  return get({ url: '/ai/test/point/by/requirement', data: () => ({ requirement_id: requirementId }) })
}
export function getAiTestPointBySplit(splitId: number) {
  return get({ url: '/ai/test/point/by/split', data: () => ({ requirement_split_id: splitId }) })
}
export function postAiTestPointBatchConfirm(requirementId: number, items: any[]) {
  return post({ url: '/ai/test/point/batch/confirm', data: () => ({ requirement_id: requirementId, items }) })
}

// ===== 测试用例 =====
export function getAiTestCase(data: object) {
  return get({ url: '/ai/test/case', data: () => data })
}
export function putAiTestCase(data: object) {
  return put({ url: '/ai/test/case', data: () => data })
}
export function deleteAiTestCase(id: number | string[] | number[]) {
  return deleted({ url: '/ai/test/case', data: () => ({ id }) })
}
export function getAiTestCaseByRequirement(requirementId: number) {
  return get({ url: '/ai/test/case/by/requirement', data: () => ({ requirement_id: requirementId }) })
}
export function getAiTestCaseByTestPoint(testPointId: number) {
  return get({ url: '/ai/test/case/by/test/point', data: () => ({ test_point_id: testPointId }) })
}
export function getAiTestCaseExportExcel(requirementId: number) {
  return get({ url: '/ai/test/case/export/excel', data: () => ({ requirement_id: requirementId }) })
}
