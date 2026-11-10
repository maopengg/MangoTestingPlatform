import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/report/details')
const statusOptions = [{ key: 3, title: '进行中' }, { key: 0, title: '失败' }, { key: 1, title: '通过' }]
function table(name, cases = []) {
  return harness(name, 'flatRows,statusText,statusColor,spanMethod,retry', {
    base, filename: path.join(base, name + '.vue'),
    props: { cases, canRetry: true, retryingIds: [], statusOptions, statusColors: { 0: 'red', 1: 'green' } },
  })
}
for (const name of ['ApiCaseTable', 'UiCaseTable', 'PytestCaseTable']) {
  test(`${name} 保留 ID0/长字符串与数量0，行合并不修改原始执行证据`, t => {
    const input = [{ id: 0, case_id: '9223372036854775807', case_sum: 0, children: [
      { id: 'example-uuid', name: 'first', status: 0, children: { evidence: ['original'] } },
      { id: 0, name: 'second', status: 1 },
    ] }]
    const before = JSON.stringify(input), h = table(name, input); t.after(h.close)
    const rows = h.flatRows.value
    assert.equal(rows[0].__detailId, '0'); assert.equal(rows[0].__caseSourceId, '0')
    assert.equal(rows[0].__caseId, '9223372036854775807'); assert.equal(rows[0].__caseCount, 0)
    assert.equal(rows[0].id, 'example-uuid'); assert.equal(rows[1].id, 0)
    assert.equal(rows[0].__caseRowSpan, 2); assert.equal(rows[1].__caseRowSpan, 0)
    assert.deepEqual(h.spanMethod({ record: rows[0], columnIndex: 0 }), { rowspan: 2, colspan: 1 })
    assert.deepEqual(h.spanMethod({ record: rows[1], columnIndex: 0 }), { rowspan: 0, colspan: 0 })
    for (const row of rows) assert.equal(row.children, undefined)
    assert.deepEqual(rows[0].__sourceRecord.children[0].children, { evidence: ['original'] })
    assert.equal(JSON.stringify(input), before)
  })

  test(`${name} 状态按枚举 key 查找，null/false/空值保持未知；枚举和数据更新立即生效`, t => {
    const h = table(name, [{ id: 1, children: [{ name: 'Example', status: null }] }]); t.after(h.close)
    assert.equal(h.statusText(0), '失败'); assert.equal(h.statusText('1'), '通过')
    for (const value of [null, undefined, false, '', '  ', NaN]) {
      assert.equal(h.statusText(value), '未知'); assert.equal(h.statusColor(value), 'gray')
    }
    assert.equal(h.statusText(4), '警告'); assert.equal(h.statusColor(0), 'red')
    h.props.statusOptions = [{ key: 0, title: 'Failed' }]; assert.equal(h.statusText(0), 'Failed')
    h.props.cases = [{ id: 0, name: 'new', status: 0 }]
    assert.equal(h.flatRows.value[0].name, 'new'); assert.equal(h.flatRows.value[0].status, 0)
  })

  test(`${name} 警告只补未写入部分，负数/异常计数不扩展；重复/缺失行 ID 的 key 不冲突`, t => {
    const h = table(name, [
      { id: 0, warning: 2, children: [{ id: 0, status: 4 }, { id: 0, status: 1 }] },
      { id: 0, warning: -5, children: [{ status: 0 }] },
      { warning: 'invalid', name: 'no id' },
    ]); t.after(h.close)
    const rows = h.flatRows.value
    assert.equal(rows.length, 5); assert.equal(rows.filter(r => r.__isWarningRow).length, 1)
    assert.equal(rows[2].status, 4); assert.equal(rows[2].error_message, '该用例前置步骤失败，未被执行')
    assert.equal(new Set(rows.map(r => r.__rowKey)).size, rows.length)
  })

  test(`${name} 重试只发合法首行 ID，逐 ID loading 与业务限制都阻止重复操作`, t => {
    const h = table(name, [{ id: 0, children: [{ name: 'first' }, { name: 'second' }] }]); t.after(h.close)
    const [first, second] = h.flatRows.value
    h.props.retryingIds = ['0']; h.retry(first); assert.deepEqual(h.events, [])
    h.props.retryingIds = []; h.retry(second); assert.deepEqual(h.events, [])
    h.props.canRetry = false; h.retry(first); assert.deepEqual(h.events, [])
    h.props.canRetry = true; h.retry(first); assert.deepEqual(h.events, [['retry', '0']])
    h.props.cases = [{ name: 'missing id' }]; h.retry(h.flatRows.value[0]); assert.equal(h.events.length, 1)
  })
}

test('API 快照参数0命中正确场景；进度/重试0、响应耗时0和基础设施标记都保留', t => {
  const h = table('ApiCaseTable', [{ id: 1, result_mode: 'snapshot', snapshot_current_step: { parameter_id: 0 },
    snapshot_progress: { done: 0, total: 0 }, snapshot_retry: { current: 0, max: 0 },
    execution_control: { phase: 'infrastructure_blocked' }, failure_reason: 'environment',
    children: [{ parameter_id: '0', status: 0, response: { time: 0 } }, { parameter_id: 1, status: 1 }],
  }]); t.after(h.close)
  const [active, other] = h.flatRows.value
  assert.equal(active.__isSnapshotRow, true); assert.equal(active.status, 3)
  assert.equal(other.__isSnapshotRow, false); assert.equal(other.status, 1)
  assert.match(active.error_message, /重试 0\/0/); assert.match(active.error_message, /进度 0\/0/)
  assert.equal(active.response_time, 0); assert.equal(active.__infrastructurePhase, 'infrastructure_blocked')
  assert.equal(active.__detailRecord.__caseSourceId, '1')
})

test('UI 子结果的耗时0、空视频、空缓存与 false 不被父元数据覆盖', t => {
  const h = table('UiCaseTable', [{ id: 0, test_time: 20, video_path: 'parent', cache_data: { stale: true }, children: [
    { name: 'step', test_time: 0, video_path: '', cache_data: false, data_factory_cache_data: {} },
  ] }]); t.after(h.close)
  const detail = h.flatRows.value[0].__detailRecord
  assert.equal(detail.test_time, 0); assert.equal(detail.video_path, ''); assert.equal(detail.cache_data, false)
  assert.deepEqual(detail.data_factory_cache_data, {}); assert.equal(detail.children[0].test_time, 0)
})

test('Pytest 原始异常优先，时间戳0可展示，坏时间不再显示 NaN', t => {
  const h = table('PytestCaseTable', [{ id: 1, children: [{ statusDetails: { message: 'original failure' }, error_message: 'fallback', start: 0 }] }]); t.after(h.close)
  assert.equal(h.flatRows.value[0].error_message, 'original failure')
  const data = h.load('report-rows.ts')
  assert.match(data.formatReportDateTime(0), /^\d{4}-\d{2}-\d{2} /)
  assert.equal(data.formatReportDateTime('invalid date'), '-')
  assert.equal(data.formatReportDuration(0), '0.00 秒')
})

function evaluation(cases = []) {
  return harness('EvaluationCaseTable', 'rows,statusText,statusColor', {
    base, filename: path.join(base, 'EvaluationCaseTable.vue'), props: { cases, statusOptions, statusColors: { 0: 'red' } },
  })
}
test('评测结果保留0/空指标、版本、发布目标及多个评分器变体，计算不修改源数据', t => {
  const input = [{ id: 0, status: 0, case_sum: 0, case_name: 'Example', children: {
    execution_no: 'run-example', dataset: { id: 0, version_no: 0 }, target: { type: 'api', ref_id: '9223372036854775807', version_ref: { kind: 'api_info_release', id: 0 } },
    grader_names: { grader_a: '评分器A' }, summary: { valid: 0, invalid: 0, average_score: 0, valid_rate: 0, effect_pass_rate: null,
      memory_qa: { rates: { correct: 0, hallucination: 0.2, omission: null } },
      metrics: { metric: { variants: [
        { grader_key: 'grader_a', grader_version: 0, passed: 0, total: 0, average_score: 0, pass_rate: 0 },
        { grader_key: 'grader_a', grader_version: 1, passed: 1, total: 2, average_score: 50, pass_rate: 0.5 },
      ] } }, ai_summary: { status: 'completed', overview: 'Summary', findings: ['A', 'A'], recommendations: ['B'] },
    },
  } }]
  const before = JSON.stringify(input), h = evaluation(input); t.after(h.close)
  const row = h.rows.value[0]
  assert.equal(row.valid, 0); assert.equal(row.total, 0); assert.equal(row.averageScore, 0)
  assert.equal(row.datasetId, '0'); assert.equal(row.datasetVersion, '0')
  assert.equal(row.targetText, '接口 #9223372036854775807 · 发布 #0')
  assert.equal(row.validRate, '0.0%'); assert.equal(row.effectPassRate, '—')
  assert.deepEqual(row.memory, { correct: '0.0%', hallucination: '20.0%', omission: '—' })
  assert.equal(row.metrics.length, 2); assert.equal(row.metrics[0].version, 'V0')
  assert.equal(row.metrics[0].average_score, 0); assert.equal(row.metrics[0].counts, '0 / 0')
  assert.equal(row.metrics[0].grader_key, '评分器A'); assert.equal(row.metrics[1].pass_rate_text, '50.0%')
  assert.equal(h.statusText(0), '失败'); assert.equal(h.statusColor(0), 'red')
  assert.equal(JSON.stringify(input), before)
})

test('评测残缺/清理/坏结构均可展示缺省值，指标和 AI 列表只接收正确结构', t => {
  const h = evaluation([null, 1, { id: 1, children: null }, { id: 1, children: { target: { type: 'script' },
    summary: { memory_qa: {}, valid_rate: Infinity, ai_summary: { status: 'failed', error_message: 'summary failed', findings: 'not list' },
      metrics: { bad: false, empty: { variants: [] }, one: { grader_key: 'one', grader_version: 1, variants: 'not list' } },
    },
  } }]); t.after(h.close)
  assert.equal(h.rows.value.length, 2)
  assert.equal(h.rows.value[0].metrics.length, 0); assert.equal(h.rows.value[0].averageScore, null)
  assert.equal(h.rows.value[1].validRate, '—'); assert.equal(h.rows.value[1].targetText, 'Python 脚本')
  assert.equal(h.rows.value[1].metrics.length, 1); assert.equal(h.rows.value[1].aiSummary.error_message, 'summary failed')
  assert.deepEqual(h.rows.value[1].aiSummary.findings, [])
  assert.notEqual(h.rows.value[0].key, h.rows.value[1].key)
  h.props.cases = []; assert.deepEqual(h.rows.value, [])
})

test('四个结果组件脚本、模板和 scoped LESS/CSS 均可编译', async () => {
  for (const name of ['ApiCaseTable', 'UiCaseTable', 'PytestCaseTable', 'EvaluationCaseTable']) {
    const filename = path.join(base, name + '.vue'), source = readFileSync(filename, 'utf8')
    const { descriptor, errors } = parse(source, { filename }); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: name })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: name, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) {
      const compiled = await compileStyleAsync({ source: style.content, filename, id: 'data-v-' + name, scoped: style.scoped, preprocessLang: style.lang, preprocessOptions: { paths: [base] } })
      assert.deepEqual(compiled.errors, [])
    }
  }
})
