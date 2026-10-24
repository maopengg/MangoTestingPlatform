import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../../../../src/views/timing/tasks/components/TaskGroupManager.vue', import.meta.url), 'utf8')
const functions = source.slice(source.indexOf('  async function openResendNotice('), source.indexOf('  function deleteGroup('))
const compiled = ts.transpileModule(functions, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText

function fixture({ executions = [{ id: 68, test_env: 0 }], send = async () => ({ msg: '发送成功' }) } = {}) {
  const state = {
    noticeLoadingIds: new Set(), noticeSending: { value: false }, noticeVisible: { value: false },
    noticeGroup: { value: null }, noticeExecutions: { value: [] }, noticeExecutionId: { value: null },
    getLatestTaskGroupExecutions: async () => ({ data: executions }),
    resendTaskGroupNotice: send, Message: { success() {}, warning() {} }, console: { log() {} },
  }
  return { state, ...new Function(...Object.keys(state), `${compiled}; return { openResendNotice, confirmResendNotice }`)(...Object.values(state)) }
}

test('任务组表格包含重发报告按钮，并确认环境、时间和原通知组', () => {
  assert.match(source, /label: '重发报告'/)
  assert.match(source, /onClick: \(\) => openResendNotice\(record\)/)
  assert.match(source, /label="最近执行"/)
  assert.match(source, /label="原通知组"/)
  assert.match(source, /@before-ok="confirmResendNotice"/)
})

test('选择明确批次重发，不触发任务；重复点击发送只请求一次', async () => {
  let resolve, calls = []
  const pending = new Promise((done) => { resolve = done })
  const { state, openResendNotice, confirmResendNotice } = fixture({
    executions: [{ id: 68, test_env: 0 }, { id: 69, test_env: 1 }],
    send: (...args) => { calls.push(args); return pending },
  })
  await openResendNotice({ id: 2, name: '示例任务组' })
  assert.equal(state.noticeVisible.value, true)
  assert.equal(state.noticeLoadingIds.size, 0)
  state.noticeExecutionId.value = 69
  const first = confirmResendNotice()
  assert.equal(state.noticeSending.value, true)
  assert.equal(await confirmResendNotice(), false)
  assert.deepEqual(calls, [[2, 69]])
  resolve({ msg: '成功' })
  assert.equal(await first, true)
  assert.equal(state.noticeSending.value, false)
})

test('没有执行批次不打开确认框，发送失败保留弹窗供重试并清理 loading', async () => {
  const empty = fixture({ executions: [] })
  await empty.openResendNotice({ id: 2 })
  assert.equal(empty.state.noticeVisible.value, false)
  assert.equal(empty.state.noticeLoadingIds.size, 0)
  const failed = fixture({ send: async () => { throw new Error('用例未完成') } })
  await failed.openResendNotice({ id: 2 })
  assert.equal(await failed.confirmResendNotice(), false)
  assert.equal(failed.state.noticeVisible.value, true)
  assert.equal(failed.state.noticeSending.value, false)
})
