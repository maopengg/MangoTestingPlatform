import type { ParameterSchema } from '../types'

export const fieldLabels: Record<string, string> = {
  objective: '测评目标', scope: '覆盖范围', exclusions: '不覆盖的能力', score_interpretation: '分数含义', assessment: '测评说明', answering: '回答生成配置', retrieval: '实际召回记忆', classification: '判定类别', answer_quote: '答案引用', reference_quote: '参考证据引用', answer_model: '回答模型快照',
  question: '问题', query: '查询内容', answer: '答案', expected_answer: '期望答案', input_data: '输入', expected_output: '期望输出', actual_output: '实际输出',
  context: '上下文', metadata: '元数据', content: '记忆内容', evidence: '来源证据', excerpt: '原文', occurredAt: '发生时间', relation: '证据关系', timeBasis: '时间依据',
  first_content: '首条记忆', first_excerpt: '首条原文', top_items: '检索结果', top_excerpts: '召回原文', scope_state: '范围状态', candidate_gap: '候选不足', truncated_by_budget: '预算截断',
  item_id: '条目 ID', dataset_item_id: '条目 ID', item_ids: '条目选择', tags: '标签', priority: '优先级', weight: '权重', enabled: '启用', description: '说明', name: '名称', version: '版本',
  source_ref: '来源引用', source: '来源', resource_id: '资源 ID', source_resource_id: '源资源 ID', source_excerpt: '来源原文', source_excerpts: '来源原文列表', source_evidence: '原文材料', occurred_at: '发生时间', answer_terms: '答案关键词', scene: '场景',
  schema_version: '结构版本', input_schema: '输入字段', expected_schema: '期望字段', context_schema: '上下文字段', metadata_schema: '元数据字段',
  expected_path: '期望字段路径', actual_path: '输出字段路径', normalize: '文本规范化', absolute_tolerance: '绝对容差', relative_tolerance: '相对容差',
  schema: '输出结构', rubric: '评分标准', max_tokens: '最大输出 Token', confidence_threshold: '置信度阈值', k: '检索 K 值',
  target: '被测目标', type: '类型', ref_id: '对象 ID', version_ref: '固定版本', kind: '版本类型', parameters: '参数', static_output: '静态输出',
  mapping: '字段映射', input: '输入', output: '输出', mode: '模式', fields: '字段', collections: '集合映射', source_path: '来源路径', target_path: '目标路径',
  runtime_context: '运行时上下文', fixture: '数据准备', data_selection: '数据选择', execution: '执行策略', grading: '评分规则',
  max_concurrency: '并发数', item_timeout_seconds: '单条超时（秒）', repeat_count: '重复次数', retry_count: '重试次数', stop_on_critical_failure: '硬门禁失败后停止',
  aggregation: '通过条件', policy_version: '判定口径版本', min_valid_rate: '最低有效率', min_effect_pass_rate: '最低通过率', quality_gates: '质量门禁',
  default_graders: '默认评分项', required_graders: '强制评分项', graders: '评分项', grading_config: '条目评分配置', grader_key: '评分器', grader_version: '评分器版本', metric_key: '指标', threshold: '通过阈值', hard_gate: '硬门禁',
  score: '得分', passed: '是否通过', reason: '评分理由', details: '详情', attempts: '执行尝试', references: '引用', timing: '耗时', implementation_hash: '实现摘要',
  memoryRef: '记忆引用', memoryKind: '记忆类型', scopeLabel: '范围', validity: '有效期', evidenceTruncated: '证据截断',
  identity: '执行身份', oracle: '真值来源', identity_key: '身份引用', tenant_key: '租户引用', contract_ids: '订单 ID 集合', required_facts: '必需事实', forbidden_claims: '禁止断言', behavior: '回答行为',
  target_visible: '目标可见上下文', annotation: '标注信息', material: '参考材料', selectors: '字段选择', template: '模板', path: '来源路径', value_path: '取值路径', where: '筛选条件', cardinality: '结果数量', key: '编码',
  operator: '比较方式', severity: '严重程度', group_by: '分组', matched: '命中项', missing: '缺失项', extra: '多余项', expected: '期望值', actual: '实际值',
  properties: '字段定义', required: '必填字段', additionalProperties: '允许额外字段', items: '列表条目', enum: '可选值', minimum: '最小值', maximum: '最大值', default: '默认值',
  dataset: '数据集', case: '测试用例', environment: '执行环境', test_env: '环境 ID', version_id: '版本 ID', version_no: '版本号', content_hash: '内容摘要', config_hash: '配置摘要',
}
export const fieldTitle = (key: string) => fieldLabels[key] || key
export function formatVersion(value: unknown): string {
  if (value == null || value === '' || value === '—' || value === '-' || Number(value) === 0) return '—'
  return `V${String(value).replace(/^v/i, '')}`
}
export function formatEvaluationDate(value: unknown): string {
  if (value == null || value === '') return '—'
  const text = String(value)
  const match = text.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/)
  return match ? `${match[1]} ${match[2]}` : text
}
export const valueType = (value: unknown) => value === null ? 'null' : Array.isArray(value) ? 'array' : typeof value
export function dataSummary(value: unknown): string {
  if (value == null) return '未设置'
  if (Array.isArray(value)) return value.length ? value.map(dataSummary).join('；') : '空列表'
  if (typeof value === 'object') return Object.entries(value).map(([key, item]) => `${fieldTitle(key)}：${dataSummary(item)}`).join('；') || '空对象'
  if (typeof value === 'boolean') return value ? '是' : '否'
  return String(value)
}
export const schemaColumns = [{ title: '字段名称', slotName: 'field', width: 240, ellipsis: true, tooltip: true }, { title: '类型', dataIndex: 'type', width: 100, align: 'center' }, { title: '必填', slotName: 'required', width: 70, align: 'center' }, { title: '说明与约束', dataIndex: 'description', width: 320, ellipsis: true, tooltip: true }]
export interface SchemaRow {
  key: string
  label: string
  path: string
  type: string
  required: boolean
  description: string
}
export function schemaRows(schema: ParameterSchema | null | undefined, prefix = ''): SchemaRow[] {
  if (!schema || typeof schema !== 'object') return []
  return Object.entries(schema.properties || {}).flatMap(([key, spec]) => {
    const path = prefix ? `${prefix}.${key}` : key
    const hints = [spec.description, spec.enum && `可选：${spec.enum.join('、')}`, spec.minimum != null && `最小 ${spec.minimum}`, spec.maximum != null && `最大 ${spec.maximum}`, spec.default !== undefined && `默认：${dataSummary(spec.default)}`].filter(Boolean)
    return [{ key: path, label: fieldTitle(key), path, type: spec.type || (spec.anyOf ? '多种类型' : '任意'), required: (schema.required || []).includes(key), description: hints.join('；') || '—' }, ...schemaRows(spec, path), ...schemaRows(spec.items, `${path}[]`)]
  })
}
