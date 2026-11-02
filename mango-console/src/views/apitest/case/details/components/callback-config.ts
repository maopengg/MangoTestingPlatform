export function callbackRulesForStep(rules: any[], stepId: number | string | undefined) {
  if (!stepId) return []
  return rules.filter((rule) => rule.trigger_step_key === `step-${stepId}`)
}

export function callbackConfigurationBlock(
  step: any,
  scenarioCount: number,
  scenarioRetry?: number
) {
  if (!step?.id) return '请先选择并保存触发接口步骤。'
  if (step.execution_config?.is_recovery)
    return '最终恢复步骤不支持触发回调验证，请选择正常执行步骤。'
  if (!scenarioCount) return '请先为当前步骤保存一个触发场景。'
  if (scenarioCount !== 1)
    return '当前步骤包含多个场景，暂不支持逐场景回调验证；请将触发接口拆成单场景步骤。'
  if (Number(scenarioRetry || 1) > 1) return '请先在场景编辑中关闭失败重试，避免重复触发事件。'
  return ''
}

export function callbackRuleName(trigger: string, rules: any[]) {
  const base = `${trigger || '接口'}回调断言`
  const existing = new Set(rules.map((rule) => rule.name))
  let index = 1
  let name = Array.from(base).slice(0, 128).join('')
  while (existing.has(name)) {
    const suffix = `（${++index}）`
    name =
      Array.from(base)
        .slice(0, 128 - suffix.length)
        .join('') + suffix
  }
  return name
}

export function hasCustomCallbackSettings(rule: any) {
  return (
    (rule.observation_seconds ?? 0) !== 0 ||
    (rule.events?.mode ?? 'at_least') !== 'at_least' ||
    (rule.events?.count ?? 1) !== 1 ||
    (rule.delivery_policy ?? 'all_observed_pass') !== 'all_observed_pass' ||
    (rule.response_mode ?? 'observe') !== 'observe' ||
    (rule.min_deliveries ?? 1) !== 1 ||
    (rule.max_deliveries ?? 100) !== 100 ||
    (rule.min_retry_interval_ms ?? 0) !== 0 ||
    rule.max_retry_interval_ms != null
  )
}

export function callbackRequiredConfigError(rule: any) {
  if (!rule.mock_config_id) return '请选择 Mock 接口'
  if (!rule.correlation?.source) return '请选择关联来源'
  if (!rule.correlation?.field?.trim()) return '请填写关联字段'
  if (!rule.correlation?.expected?.cache_key?.trim())
    return '请填写匹配缓存键，例如 callback_run_id'
  if (!rule.event_id_source) return '请选择事件ID来源'
  if (!rule.event_id_field?.trim()) return '请填写事件ID字段'
  return ''
}

export function callbackCheckSummary(check: any) {
  if (check.type === 'json_compact') return 'JSON 不含格式化空白'
  if (check.type === 'lark_signature') return '按原始正文验证 X-Lark-Signature'
  if (check.type === 'lark_compact_signature_simulation')
    return '压紧后验签，仅诊断，不影响通过状态'
  if (check.assertions?.length) {
    return check.assertions
      .map((assertion: any) => {
        const method = assertion.value?.label || assertion.method || '待选择断言方法'
        const parameters = (assertion.value?.parameter || [])
          .filter((parameter: any) => parameter.f !== 'actual')
          .map(
            (parameter: any) =>
              `${parameter.n || parameter.f}：${
                typeof parameter.v === 'string' ? parameter.v : JSON.stringify(parameter.v)
              }`
          )
        const group = assertion.group_name
          ? `${assertion.group_name}（${assertion.group_logic === 'OR' ? '或' : '且'}）· `
          : ''
        return `${group}${method}${parameters.length ? ' · ' + parameters.join('，') : ''}`
      })
      .join('；')
  }
  if (check.general_editor) return '待配置断言'
  if (check.operator === 'exists') return '字段存在'
  return `${check.operator === 'contains' ? '包含' : '等于'} · ${
    check.expected_text ?? JSON.stringify(check.expected)
  }`
}

export const checkColumns = [
  { title: '序号', slotName: 'index', width: 50, align: 'center' },
  { title: '检查类型', slotName: 'type', width: 210, align: 'center' },
  { title: '检查来源', slotName: 'source', width: 150, align: 'center' },
  { title: '回调字段', slotName: 'field', width: 200 },
  { title: '断言要求', slotName: 'summary', ellipsis: true, tooltip: true },
  { title: '操作', slotName: 'actions', width: 160, fixed: 'right', align: 'center' },
] as any[]

export const ruleColumns = [
  { title: '名称', slotName: 'name', ellipsis: true, tooltip: true },
  { title: '超时(秒)', dataIndex: 'timeout_seconds', width: 90, align: 'center' },
  { title: '操作', slotName: 'actions', width: 120, fixed: 'right', align: 'center' },
] as any[]
export const resultColumns = [
  { title: '名称', dataIndex: 'name', ellipsis: true, tooltip: true },
  { title: '状态', slotName: 'status', width: 90, align: 'center' },
  { title: '事件数', dataIndex: 'events', width: 75, align: 'center' },
  { title: '投递数', dataIndex: 'deliveries', width: 75, align: 'center' },
  { title: '等待(ms)', dataIndex: 'wait_ms', width: 100, align: 'center' },
  { title: '原因', dataIndex: 'error_message', ellipsis: true, tooltip: true },
  { title: '操作', slotName: 'actions', width: 120, fixed: 'right', align: 'center' },
] as any[]
export const deliveryColumns = [
  { title: 'Trace', dataIndex: 'trace_id', ellipsis: true, tooltip: true },
  { title: '事件ID', dataIndex: 'event_id', ellipsis: true, tooltip: true },
  { title: '接收时间(UTC)', dataIndex: 'received_at', width: 220, ellipsis: true, tooltip: true },
  { title: '检查', slotName: 'passed', width: 80, align: 'center' },
  { title: 'HTTP', dataIndex: 'response_status', width: 70, align: 'center' },
  { title: '操作', slotName: 'actions', width: 120, fixed: 'right', align: 'center' },
] as any[]
