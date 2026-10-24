import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = new URL('../../../src/views/report/index.vue', import.meta.url).pathname
const source = readFileSync(filename, 'utf8')
const handler = source.slice(source.indexOf('  async function onRetryFailed('), source.indexOf('  async function onRetry('))
const compiled = ts.transpileModule(handler, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText

test('重试弹窗展示报告统计和两种重试按钮，不保留独立菜单入口', () => {
  assert.doesNotMatch(source, /label: '重试失败 Case'/)
  for (const label of ['用例总数', '失败用例', '通过用例', '告警用例', '全量重试', '只重试失败']) assert.ok(source.includes(label))
  const { descriptor, errors } = parse(source, { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'report-retry-failed' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'report-retry-failed', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})

test('确认后仅调用失败重试接口，重复提交受保护且结束清理 loading', async () => {
  let resolve, calls = 0, refreshed = 0, closed = 0
  const data = { failedRetryLoadingId: null, retryLoading: false, retryRecord: { id: 10 } }
  const pending = new Promise((done) => { resolve = done })
  const onRetryFailed = new Function('data', 'isReportRunning', 'reportResultCount', 'retryModalRef', 'retryFailedReportCases', 'Message', 'doRefresh',
    `${compiled}; return onRetryFailed`)(data, () => false, (record) => record.fail || 0,
    { value: { close: () => { closed++ } } },
    (id) => { assert.equal(id, 10); calls++; return pending }, { success() {}, info() {}, error() {} }, () => { refreshed++ })
  assert.equal(await onRetryFailed({ id: 10, fail: 0 }), false)
  const first = onRetryFailed({ id: 10, fail: 2 })
  assert.equal(data.failedRetryLoadingId, 10)
  assert.equal(await onRetryFailed({ id: 10, fail: 2 }), false)
  resolve({ data: { retry_count: 2 } })
  assert.equal(await first, true)
  assert.equal(calls, 1)
  assert.equal(refreshed, 1)
  assert.equal(data.failedRetryLoadingId, null)
  assert.equal(data.retryRecord, null)
  assert.equal(closed, 1)
})
