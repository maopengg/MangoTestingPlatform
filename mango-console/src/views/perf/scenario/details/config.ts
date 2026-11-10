import type { LoadConfiguration, LoadProfile, LoadType, PerformanceGoal, ScenarioExecutionDraft, ScenarioForm } from './types'

export const performanceGoalTemplateOptions = [
  { label: '系统推荐模板', value: 'recommended' },
  { label: '自定义目标', value: 'custom' },
]

export function createDefaultPerformanceGoal(): PerformanceGoal {
  return {
    p95_ms: 500,
    error_rate_percent: 1,
    load_achievement_rate_percent: 95,
  }
}

export const assignmentModeTitles: Record<string, string> = {
  unique: '唯一分片',
  cyclic: '分片内循环',
  shared: '每节点共享',
}

export const rateTimeUnitOptions = [
  { label: 'Case 启动/秒', value: 'second' },
  { label: 'Case 启动/分钟', value: 'minute' },
]

export const loadProfileHints: Record<LoadProfile, string> = {
  constant_concurrency: '固定人数持续运行指定时间；每个虚拟用户重复执行完整 Case。',
  fixed_iterations: '所有执行器合计完成指定次数的完整 Case；到截止时间仍未完成则本次运行不达标。',
  staircase: '从首阶开始，每隔指定秒数增加并发，最后可保持峰值。',
  linear_ramp: '从起始并发平滑升至目标并发，可在峰值保持一段时间。',
  spike: '先运行基线，再快速升至峰值，保持后恢复至基线。',
  soak: '固定并发长期运行，用于观察稳定性；最长 24 小时。',
  constant_arrival_rate: '按固定速率启动完整 Case；单个 Case 可以包含多个 HTTP 请求。',
  constant_iteration_rate: '按固定速率启动完整 Case；与到达率执行语义相同，保留独立模型供分类。',
}

export function createDefaultLoadConfiguration(loadType: LoadType = 'concurrency'): LoadConfiguration {
  const rate = loadType !== 'concurrency'
  return {
    name: '基础负载',
    profile: !rate ? 'constant_concurrency' : loadType === 'arrival_rate' ? 'constant_arrival_rate' : 'constant_iteration_rate',
    duration_seconds: 60, target_users: rate ? null : 10, target_rate: rate ? 10 : null,
    rate_time_unit: rate ? 'second' : null, preallocated_vus: rate ? 10 : null,
    max_vus: rate ? 100 : null, ramp_type: 'linear', spawn_rate: null,
    user_wait_min_ms: 0, user_wait_max_ms: 0, total_iterations: 10000,
    start_users: 1, step_users: 10, step_interval_seconds: 30, ramp_seconds: 30,
    hold_seconds: 30, baseline_seconds: 30, recovery_seconds: 30,
  }
}

export function createScenarioExecutionDraft(): ScenarioExecutionDraft {
  return {
    test_env: undefined, selected_executor_fingerprints: [], remark: '',
    production_load_confirmed: false, capture_request: false, capture_response: false,
  }
}

export const failurePolicyOptions = [
  { label: '严格：全部节点就绪', value: 'strict' },
  { label: '满足最小节点后继续', value: 'continue' },
]

export function createScenarioForm(): ScenarioForm {
  return {
    name: '', engine: 'k6', project_product: null, version: null,
    source_case_release_id: undefined, default_executor_count: 1,
    node_failure_policy: 'strict', min_ready_nodes: undefined, load_type: 'concurrency',
  }
}
