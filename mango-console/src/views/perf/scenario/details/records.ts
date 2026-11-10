import { formatModulePath } from '@/utils/business-format'
import { readLoadConfiguration } from './load-configuration'
import { isRecommendedPerformanceGoal, performanceGoalFromApi } from './performance-goal'
import type { ScenarioConfigurationRecord, SourceCaseRelease, SourceCaseStep } from './types'

function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('场景响应格式不正确')
  return value as Record<string, unknown>
}
function data(value: unknown): unknown {
  const response = object(value)
  if (response.code !== 200) throw new Error('场景请求未成功')
  return response.data
}
function text(value: unknown): string {
  if (typeof value !== 'string') throw new Error('场景文本格式不正确')
  return value
}
function integer(value: unknown, min = 0): number {
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < min) throw new Error('场景数值格式不正确')
  return value
}
function boolean(value: unknown): boolean {
  if (typeof value !== 'boolean') throw new Error('来源用例状态格式不正确')
  return value
}
const optionalInteger = (value: unknown) => value === null || value === undefined ? undefined : integer(value)

export function readSourceCase(value: unknown): SourceCaseRelease {
  const row = object(value)
  if (!Array.isArray(row.steps) || !Array.isArray(row.incompatible_reasons)) throw new Error('来源用例列表格式不正确')
  const steps: SourceCaseStep[] = row.steps.map(item => {
    const step = object(item)
    return {
      key: text(step.key), name: text(step.name),
      api_info_id: step.api_info_id === null || step.api_info_id === undefined ? null : integer(step.api_info_id, 1),
      extractor_count: integer(step.extractor_count), check_count: integer(step.check_count),
    }
  })
  return {
    release_id: integer(row.release_id, 1), case_id: integer(row.case_id, 1),
    name: text(row.name), title: text(row.title), disabled: boolean(row.disabled), compatible: boolean(row.compatible),
    incompatible_reasons: row.incompatible_reasons.map(text),
    version_label: text(row.version_label), revision_no: integer(row.revision_no, 1),
    module_full_path: formatModulePath({ full_path: text(row.module_full_path) }), steps,
  }
}

export function readSourceCaseOptions(value: unknown): SourceCaseRelease[] {
  const rows = data(value)
  if (!Array.isArray(rows)) throw new Error('来源用例列表格式不正确')
  const result = rows.map(readSourceCase)
  if (new Set(result.map(item => item.release_id)).size !== result.length) throw new Error('来源用例版本重复')
  return result
}

export function readScenarioConfiguration(value: unknown, expectedId: string): ScenarioConfigurationRecord {
  const row = object(data(value)), id = integer(row.id, 1)
  if (id !== Number(expectedId)) throw new Error('场景响应与当前页面不一致')
  if (row.engine !== 'k6' || (row.node_failure_policy !== 'strict' && row.node_failure_policy !== 'continue') ||
    (row.load_type !== 'concurrency' && row.load_type !== 'arrival_rate' && row.load_type !== 'iteration_rate'))
    throw new Error('场景配置枚举格式不正确')
  const source = row.source_case === null || row.source_case === undefined ? null : readSourceCase(row.source_case)
  const releaseId = row.source_case_release_id === null || row.source_case_release_id === undefined
    ? source?.release_id : integer(row.source_case_release_id, 1)
  if (source && releaseId !== source.release_id) throw new Error('场景来源版本不一致')
  const goal = performanceGoalFromApi(row.performance_goal)
  const goalConfig = row.performance_goal === null || row.performance_goal === undefined ? null : object(row.performance_goal)
  if (goalConfig?.template_key !== undefined && goalConfig.template_key !== 'recommended' && goalConfig.template_key !== 'custom')
    throw new Error('性能目标模板格式不正确')
  return {
    id,
    form: {
      name: text(row.name), engine: row.engine, project_product: integer(row.project_product, 1),
      version: integer(row.version, 1), source_case_release_id: releaseId,
      default_executor_count: integer(row.default_executor_count, 1), node_failure_policy: row.node_failure_policy,
      min_ready_nodes: optionalInteger(row.min_ready_nodes), load_type: row.load_type,
    },
    load: readLoadConfiguration(row.load_config, row.load_type), source, goal,
    goalTemplate: goalConfig?.template_key === 'custom' || !isRecommendedPerformanceGoal(goal) ? 'custom' : 'recommended',
  }
}

export function readSavedScenarioVersion(value: unknown, expectedId: string, previousVersion: number | null): number {
  const row = object(data(value)), version = integer(row.version, 1)
  if (integer(row.id, 1) !== Number(expectedId) || previousVersion === null || version <= previousVersion)
    throw new Error('场景保存版本不正确')
  return version
}

export function readScenarioValidation(value: unknown): { step_count: number; duration_seconds: number } {
  const row = object(data(value))
  if (row.valid !== true) throw new Error('场景校验未通过')
  return { step_count: integer(row.step_count), duration_seconds: integer(row.duration_seconds, 1) }
}
