import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = new URL('../../../src/views/report/index.vue', import.meta.url).pathname
const source = readFileSync(filename, 'utf8')
const handler = source.slice(source.indexOf('  async function onRetryFailed('), source.indexOf('  function buildProjectProductValue('))
const compiled = ts.transpileModule(handler, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText

test('重试弹窗展示报告统计和两种重试按钮，不保留独立菜单入口', () => {
  assert.doesNotMatch(source, /label: '重试失败 Case'/)
  for (const label of ['用例总数', '失败用例', '通过用例', '告警用例', '全量重试', '重试失败及受阻']) assert.ok(source.includes(label))
  const { descriptor, errors } = parse(source, { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'report-retry-failed' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'report-retry-failed', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})

test('确认后仅调用失败重试接口，重复提交受保护且结束清理 loading', async () => {
  let resolve, calls = 0, refreshed = 0, closed = 0
  const retryState = { failedId: null, loading: false, record: { id: 10 } }
  const pending = new Promise((done) => { resolve = done })
  const onRetryFailed = new Function('retryState', 'retryModalRef', 'retryFailedReportCases', 'Message', 'doRefresh',
    `const available = () => true, isReportRunning = () => false,
      reportResultCount = (row, key) => row[key] || 0, actionVersion = 1,
      identityKey = () => 'user', retryGeneration = 1, actionCurrent = () => true,
      reportEnvelope = value => value, reportObject = value => value || {},
      reportNumber = value => typeof value === 'number' ? value : null, reportText = value => value || '',
      onCancelRetryModal = () => { retryState.record = null };
      ${compiled}; return onRetryFailed`)(retryState,
    { value: { close: () => { closed++ } } },
    (id, confirmed) => { assert.equal(id, 10); assert.equal(confirmed, true); calls++; return pending },
    { success() {}, info() {}, error() {} }, () => { refreshed++ })
  assert.equal(await onRetryFailed({ id: 10, fail: 0, automation_types: [1] }), false)
  const first = onRetryFailed({ id: 10, fail: 0, blocked: 2, automation_types: [1] })
  assert.equal(retryState.failedId, 10)
  assert.equal(await onRetryFailed({ id: 10, fail: 2, automation_types: [1] }), false)
  resolve({ data: { retry_count: 2 } })
  assert.equal(await first, true)
  assert.equal(calls, 1)
  assert.equal(refreshed, 1)
  assert.equal(retryState.failedId, null)
  assert.equal(retryState.record, null)
  assert.equal(closed, 1)
})
