// 新结果只从 steps[].ass 读取；旧归档保留只读兼容，不再双写检查明细。
export function callbackResultsFromAssertions(assertions: any[], legacyRuns: any[] = []) {
  const callbackAssertions = (assertions || []).filter((item) => item.callback)
  if (!callbackAssertions.length) return legacyRuns
  const runs = callbackAssertions
    .filter((item) => item.callback.run_status)
    .map((item) => ({
      id: item.callback.run_id,
      name: item.group_name,
      rule_key: item.callback.rule_key,
      status: item.callback.run_status,
      error_message: item.status === 1 ? '' : item.ass_msg,
      events: item.callback.events,
      deliveries: item.callback.deliveries,
      delivery_results: [] as any[],
    }))
  for (const item of callbackAssertions) {
    const context = item.callback
    if (!context.check_key) continue
    const run = runs.find((value) => value.id === context.run_id)
    if (!run) continue
    let delivery = run.delivery_results.find((value) => value.id === context.delivery_id)
    if (!delivery) {
      delivery = {
        id: context.delivery_id,
        event_id: context.event_id,
        received_at: context.received_at,
        checks: [],
      }
      run.delivery_results.push(delivery)
    }
    delivery.checks.push({
      key: context.check_key,
      type: context.check_type,
      source: context.source,
      field: context.field,
      passed: context.passed,
      diagnostic: context.diagnostic,
      message: item.ass_msg,
      assertions: context.assertions,
    })
  }
  return runs
}

export function callbackResultsForScenario(
  result: any,
  stepId: unknown,
  scenarioId: unknown,
  rules: any[]
) {
  const steps = Array.isArray(result?.steps) ? result.steps : []
  const executed = steps.some(
    (step: any) =>
      String(step.id) === String(stepId) &&
      (String(step.parameter_id) === String(scenarioId) ||
        step.parameters?.some((parameter: any) => String(parameter.id) === String(scenarioId)))
  )
  if (!stepId || !scenarioId || !executed) return []
  const key = `step-${stepId}`
  const ruleKeys = new Set(
    rules.filter((rule) => rule.trigger_step_key === key).map((rule) => rule.key)
  )
  return (Array.isArray(result.callback_results) ? result.callback_results : []).filter(
    (run: any) => (run.trigger_step_key ? run.trigger_step_key === key : ruleKeys.has(run.rule_key))
  )
}

export function callbackAssertionCount(runs: any[]) {
  return runs.reduce(
    (total, run) =>
      total +
      Math.max(
        1,
        (run.delivery_results || []).reduce(
          (count: number, delivery: any) => count + (delivery.checks || []).length,
          0
        )
      ),
    0
  )
}

export function callbackCheckRows(run: any) {
  return (run.delivery_results || []).flatMap((delivery: any) =>
    (delivery.checks || []).map((check: any, index: number) => {
      const definition = (run.check_definitions || []).find((item: any) => item.key === check.key)
      return {
        ...check,
        ...(!check.type && definition?.type && { type: definition.type }),
        ...(!check.source && definition?.source && { source: definition.source }),
        ...(!check.field && definition?.field && { field: definition.field }),
        rowKey: `${delivery.id}-${index}`,
        deliveryId: delivery.id,
        eventId: delivery.event_id,
        receivedAt: delivery.received_at,
      }
    })
  )
}

export function callbackCheckPresentation(check: any, enums: any) {
  const type = enums.api_callback_check_type?.find((item: any) => item.key === check.type)?.title
  const source = enums.api_callback_source?.find((item: any) => item.key === check.source)?.title
  const methods = [
    ...new Set(
      (check.assertions || [])
        .filter((item: any) => item.source_type !== 'assertion_group')
        .map((item: any) => item.method)
        .filter(Boolean)
    ),
  ]
  const requirements: Record<string, string> = {
    json_compact: 'JSON 不含格式化换行和多余空格',
    lark_signature: '按收到的原始正文验证 X-Lark-Signature',
    lark_compact_signature_simulation: '模拟压紧正文后验签，仅诊断',
  }
  return {
    title: type || (check.type ? '回调检查' : '历史检查项'),
    target: check.field || source || '检查对象未归档',
    source: check.field ? source : '',
    requirement: requirements[check.type] || methods.join('；') || '断言要求未归档',
    missingDefinition: !check.type,
  }
}

export function callbackNeedsDefinitions(run: any) {
  return callbackCheckRows(run).some((check: any) => !check.type)
}

export const callbackCheckResultColumns = [
  { title: '检查项', slotName: 'check', width: 210 },
  { title: '检查对象', slotName: 'target', width: 220 },
  { title: '断言要求', slotName: 'requirement', width: 260 },
  { title: '结果', slotName: 'status', width: 80, align: 'center' },
  { title: '结果说明', slotName: 'message', width: 220 },
] as any[]
