import type { NavigationCreateSelection } from '@/utils/navigation-create-defaults'

export type ScenarioLoadType = 'concurrency' | 'arrival_rate' | 'iteration_rate'
export type ScenarioProductSelection = string | number | (string | number)[] | null
export interface ScenarioCreateDraft {
  name: string
  project_product: ScenarioProductSelection
  module: string | number | null
  engine: 'k6'
  load_type: ScenarioLoadType
  default_executor_count: number | undefined
  description: string
}

export function selectionId(value: unknown): number | null {
  const leaf = Array.isArray(value) ? value[value.length - 1] : value
  if (typeof leaf !== 'number' && (typeof leaf !== 'string' || !/^\d+$/.test(leaf))) return null
  const id = Number(leaf)
  return Number.isSafeInteger(id) && id > 0 ? id : null
}

export function createScenarioDraft(selection?: NavigationCreateSelection): ScenarioCreateDraft {
  return { name: '', project_product: selectionId(selection?.projectProduct), module: selectionId(selection?.module),
    engine: 'k6', load_type: 'concurrency', default_executor_count: 1, description: '' }
}

export function scenarioCreatePayload(draft: ScenarioCreateDraft): Record<string, unknown> {
  const product = selectionId(draft.project_product), module = selectionId(draft.module)
  if (!draft.name.trim() || draft.name.length > 128) throw new Error('请输入不超过 128 字的场景名称')
  if (!product || !module) throw new Error('请选择项目产品和产品模块')
  if (draft.engine !== 'k6' || !['concurrency', 'arrival_rate', 'iteration_rate'].includes(draft.load_type)) throw new Error('请选择有效的引擎和负载模型')
  if (typeof draft.default_executor_count !== 'number' || !Number.isInteger(draft.default_executor_count) || draft.default_executor_count < 1 || draft.default_executor_count > 100) throw new Error('请输入 1-100 的执行器数量')
  if (draft.description.length > 1000) throw new Error('说明不能超过 1000 字')
  const rate = draft.load_type !== 'concurrency'
  return { name: draft.name, project_product: product, module, engine: draft.engine, load_type: draft.load_type,
    default_executor_count: draft.default_executor_count, description: draft.description,
    execution_mode: 'sequential', node_failure_policy: 'strict', user_wait_min_ms: 0, user_wait_max_ms: 0,
    status: 1, tags: [], target_users: rate ? null : 10, target_rate: rate ? 10 : null,
    rate_time_unit: rate ? 'second' : null, preallocated_vus: rate ? 10 : null, max_vus: rate ? 100 : null }
}

export function createdScenarioId(value: unknown): number {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new Error('创建场景未成功')
  const response = value as Record<string, unknown>
  if (response.code !== 200 || !response.data || typeof response.data !== 'object' || Array.isArray(response.data)) throw new Error('创建场景未成功')
  const data = response.data as Record<string, unknown>
  if (typeof data.id !== 'number' || !Number.isSafeInteger(data.id) || data.id < 1) throw new Error('创建场景响应格式不正确')
  return data.id
}
