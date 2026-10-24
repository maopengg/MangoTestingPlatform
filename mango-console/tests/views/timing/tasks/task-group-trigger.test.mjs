import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = new URL('../../../../src/views/timing/tasks/components/TaskGroupManager.vue', import.meta.url).pathname
const source = readFileSync(filename, 'utf8')
const functionSource = source.slice(source.indexOf('  function triggerGroup('), source.indexOf('  async function openResendNotice('))
const compiled = ts.transpileModule(functionSource, {
  compilerOptions: { module: ts.ModuleKind.ESNext },
}).outputText

test('任务组触发按钮无权限限制，使用独立行 loading，组件编译正常', () => {
  assert.match(source, /label: '触发',\s*loading: triggeringIds.has\(record.id\),\s*onClick: \(\) => triggerGroup\(record\)/)
  const { descriptor, errors } = parse(source, { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'task-group-trigger' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'task-group-trigger', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})

test('重复点击只请求一次，生成失败提示数量，结束后清理 loading', async () => {
  const ids = new Set()
  const messages = []
  let resolve, calls = 0
  let modal, dialogs = 0
  const confirming = new Set()
  const pending = new Promise((done) => { resolve = done })
  const trigger = new Function('triggeringIds', 'triggerConfirmingIds', 'Modal', 'triggerScheduledTaskGroup', 'Message', `${compiled}; return triggerGroup`)(
    ids,
    confirming,
    { confirm: (config) => { modal = config; dialogs++ } },
    () => { calls++; return pending },
    { success: (text) => messages.push(text), warning: (text) => messages.push(text) },
  )
  trigger({ id: 7, name: '回归测试' })
  assert.equal(calls, 0)
  trigger({ id: 7 })
  assert.equal(dialogs, 1)
  const first = modal.onBeforeOk()
  assert.equal(ids.has(7), true)
  assert.equal(await modal.onBeforeOk(), false)
  assert.equal(calls, 1)
  resolve({ data: { generated_count: 2, failed_count: 1 } })
  await first
  modal.onOk()
  assert.equal(confirming.size, 0)
  assert.equal(ids.size, 0)
  assert.match(messages[0], /生成 2 个执行报告，1 个子任务生成失败/)
})

test('触发接口异常后可再次点击', async () => {
  const ids = new Set()
  const confirming = new Set()
  let modal, calls = 0
  const trigger = new Function('triggeringIds', 'triggerConfirmingIds', 'Modal', 'triggerScheduledTaskGroup', 'Message', 'console', `${compiled}; return triggerGroup`)(
    ids, confirming, { confirm: (config) => { modal = config } },
    async () => { calls++; throw new Error('request failed') }, {}, { log() {} },
  )
  trigger({ id: 7 })
  modal.onCancel()
  assert.equal(calls, 0)
  assert.equal(confirming.size, 0)
  trigger({ id: 7 })
  assert.equal(await modal.onBeforeOk(), false)
  assert.equal(await modal.onBeforeOk(), false)
  assert.equal(calls, 2)
  assert.equal(ids.size, 0)
  modal.onCancel()
  assert.equal(confirming.size, 0)
})
