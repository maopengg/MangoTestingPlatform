import type { CaseConfig, GraderBinding, QualityGate } from '../types'

export const configSteps = [
  { key: 'data', title: '评测数据' },
  { key: 'target', title: '被测目标' },
  { key: 'answering', title: '召回后生成回答' },
  { key: 'grading', title: '评分规则' },
  { key: 'policy', title: '通过条件与运行设置' },
] as const

export const caseColumns = [
  { title: 'ID', key: 'index', width: 80, align: 'center' },
  { title: '用例名称', key: 'name', dataIndex: 'name', width: 220, ellipsis: true, tooltip: true },
  {
    title: '场景描述',
    key: 'description',
    dataIndex: 'description',
    width: 260,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '数据集',
    key: 'dataset_name',
    dataIndex: 'dataset_name',
    width: 170,
    ellipsis: true,
    tooltip: true,
  },
  {
    title: '数据版本',
    key: 'dataset_version_no',
    dataIndex: 'dataset_version_no',
    width: 100,
    align: 'center',
  },
  { title: '目标类型', key: 'target_type', dataIndex: 'target_type', width: 115, align: 'center' },
  { title: '最近执行', key: 'latest', width: 140, align: 'center' },
  { title: '平均分', key: 'score', width: 90, align: 'center' },
  { title: '最近有效率', key: 'valid_rate', width: 110, align: 'center' },
  { title: '最近完成时间', key: 'finished_at', width: 190, ellipsis: true, tooltip: true },
  { title: '启用', key: 'status', width: 85, align: 'center' },
  { title: '项目/产品', key: 'project_product', width: 150, ellipsis: true, tooltip: true },
  { title: '模块', key: 'module', width: 180, ellipsis: true, tooltip: true },
  { title: '操作', key: 'actions', width: 160, align: 'center', fixed: 'right' },
]
export const CASE_SCROLL_X = 2160
export const gateMetrics = [
  { label: '有效率', value: 'valid_rate' },
  { label: '通过率', value: 'effect_pass_rate' },
  { label: '平均分', value: 'average_score' },
  { label: '无效条目数', value: 'invalid' },
  { label: '不通过条目数', value: 'failed' },
  { label: '硬门禁失败条目数', value: 'hard_gate_failed_count' },
]
export const gateOperators = [
  { label: '大于等于', value: 'gte' },
  { label: '大于', value: 'gt' },
  { label: '小于等于', value: 'lte' },
  { label: '小于', value: 'lt' },
  { label: '等于', value: 'eq' },
  { label: '必须为零', value: 'zero' },
]
export const gateSeverities = [
  { label: '判为不通过', value: 'critical' },
  { label: '标记警告', value: 'warning' },
]
export function qualityGateError(gates: QualityGate[]) {
  for (const [index, gate] of gates.entries()) {
    const prefix = `质量门禁第 ${index + 1} 条：`
    if (!gate || typeof gate.key !== 'string' || !gate.key.trim()) return prefix + '请选择统计指标'
    if (!gateOperators.some((item) => item.value === (gate.operator ?? 'gte')))
      return prefix + '请选择比较方式'
    if (!gateSeverities.some((item) => item.value === (gate.severity ?? 'critical')))
      return prefix + '请选择未达标时的处理方式'
    if (typeof gate.threshold !== 'number' || !Number.isFinite(gate.threshold))
      return prefix + '请填写有效的数值阈值'
    if (
      !gate.metric_key &&
      ['valid_rate', 'effect_pass_rate', 'pass_rate'].includes(gate.key) &&
      (gate.threshold < 0 || gate.threshold > 1)
    )
      return prefix + '比例阈值应在 0～1 之间'
  }
  return ''
}
export const pythonTargetTemplate =
  'def main(input, context):\n    data = ${{case_input}}\n    return {"answer": data}\n'
interface LegacyOutput {
  selectors?: Record<string, string>
  collections?: Record<
    string,
    { path: string; value_path?: string; cardinality?: string; where?: Record<string, unknown> }
  >
  template?: Record<string, unknown>
}
interface LegacyCaseInput
  extends Omit<CaseConfig, 'mapping' | 'grading' | 'answering' | 'data_selection'> {
  runtime_context?: unknown
  assessment?: unknown
  data_selection: CaseConfig['data_selection'] & { input_variable?: string }
  mapping: { output: CaseConfig['mapping']['output'] | LegacyOutput }
  grading: Omit<CaseConfig['grading'], 'aggregation'> & {
    aggregation: CaseConfig['grading']['aggregation'] & {
      pass_score?: unknown
      warning_score?: unknown
      invalid_policy?: unknown
    }
  }
  answering?: (NonNullable<CaseConfig['answering']> & { memories_path?: string }) | null
}
export function normalizeCaseInput(value: LegacyCaseInput): CaseConfig {
  const { runtime_context, assessment, ...config } = value
  const output = config.mapping?.output || { paths: [] }
  const legacy = 'paths' in output ? {} : output
  const aliases = [...Object.keys(legacy.selectors || {}), ...Object.keys(legacy.collections || {})]
  if (
    Object.keys(legacy.template || {}).length ||
    Object.values(legacy.collections || {}).some(
      (item) => Object.keys(item.where || {}).length || (item.cardinality || 'many') !== 'many'
    )
  )
    throw new Error('请重新填写响应提取 JSONPath')
  const paths = [
    ...Object.values(legacy.selectors || {}),
    ...Object.values(legacy.collections || {}).map((item) =>
      !item.value_path || item.value_path === '$'
        ? item.path
        : `${item.path}[*].${item.value_path.replace(/^\$\./, '')}`
    ),
  ]
  const normalizedOutput =
    'paths' in output
      ? output
      : {
          paths: paths.map((path) =>
            (path.startsWith('$') ? path : `$.${path}`).replace(/\.(\d+)(?=\.|$)/g, '[$1]')
          ),
        }
  const grading = config.grading && { ...config.grading }
  if (grading) {
    const { pass_score, warning_score, invalid_policy, ...aggregation } = grading.aggregation || {}
    grading.aggregation = Object.assign(
      { policy_version: 2, min_valid_rate: 0.95, min_effect_pass_rate: 0.8 },
      aggregation
    )
  }
  if (grading && aliases.length)
    for (const group of ['default_graders', 'required_graders'] as const) {
      grading[group] = (grading[group] || []).map((binding) => {
        const parameters = { ...binding.parameters }
        const parts =
          typeof parameters.actual_path === 'string'
            ? parameters.actual_path.replace(/^\$\./, '').split('.')
            : []
        if (aliases.includes(parts[0]))
          parameters.actual_path = [
            ...(aliases.length === 1 ? [] : [String(aliases.indexOf(parts[0]))]),
            ...parts.slice(1),
          ].join('.')
        return { ...binding, parameters }
      })
    }
  const answering = config.answering && { ...config.answering }
  if (answering) delete answering.memories_path
  const { input_variable, ...selection } = config.data_selection || {}
  return {
    ...config,
    data_selection: selection,
    ...(grading ? { grading } : {}),
    ...(answering ? { answering } : {}),
    mapping: { output: normalizedOutput },
  }
}
export const defaultGrader = (): GraderBinding => ({
  grader_key: 'exact_match',
  grader_version: 1,
  metric_key: 'accuracy',
  threshold: 100,
  weight: 1,
  hard_gate: false,
  enabled: true,
  parameters: {},
})
export const defaultCaseConfig = (): CaseConfig => ({
  ai: {
    judge_profile_id: null as string | null,
    summary_profile_id: null as string | null,
    answer_profile_id: null as string | null,
  },
  schema_version: 1,
  data_selection: { exclude: false, item_ids: [] as number[] },
  target: { type: 'api_info', ref_id: null, version_ref: null, parameters: {} },
  mapping: { output: { paths: [] as string[] } },
  grading: {
    default_graders: [defaultGrader()],
    required_graders: [] as ReturnType<typeof defaultGrader>[],
    aggregation: { policy_version: 2, min_valid_rate: 0.95, min_effect_pass_rate: 0.8 },
    quality_gates: [],
  },
  execution: {
    max_concurrency: 1,
    item_timeout_seconds: 600,
    retry_count: 0,
    repeat_count: 1,
    stop_on_critical_failure: false,
  },
})
export const isTerminal = (status?: string) =>
  Boolean(status && ['completed', 'failed', 'stopped'].includes(status))
