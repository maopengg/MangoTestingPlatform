import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { setupGroupList } from '../../../helpers/timing-task-group-list-harness.mjs'

const filename = new URL('../../../../src/views/timing/tasks/components/TaskGroupManager.vue', import.meta.url).pathname
const source = readFileSync(filename, 'utf8')

test('任务组触发按钮统一展示并使用独立行 loading，组件编译正常', () => {
  assert.doesNotMatch(source, /permission: 'timing.tasks:change'|v-permission|hasPermission\(/)
  assert.match(source, /label: '重发报告'/)
  assert.match(source, /label: '触发',\s*loading: triggeringIds.has\(record.id\),\s*disabled: busy\(record.id\),\s*onClick: \(\) => triggerGroup\(record\)/)
  const { descriptor, errors } = parse(source, { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'task-group-trigger' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'task-group-trigger', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})

test('重复点击只请求一次，生成失败提示数量，结束后清理 loading', async t => {
  let resolve
  const pending = new Promise((done) => { resolve = done })
  const h = setupGroupList({ triggerScheduledTaskGroup: () => pending }); t.after(h.close); await h.mount()
  h.triggerGroup({ id: 7, name: '回归测试' }); assert.equal(h.writes.length, 0)
  h.triggerGroup({ id: 7, name: '回归测试' }); assert.equal(h.confirmations.length, 1)
  const modal = h.confirmations[0], first = modal.config.onBeforeOk()
  assert.equal(h.triggeringIds.has(7), true)
  assert.equal(await modal.config.onBeforeOk(), false)
  assert.deepEqual(h.writes, [['triggerScheduledTaskGroup',7]])
  resolve({ code: 200, data: { generated_count: 2, failed_count: 1 } })
  await first
  assert.equal(modal.closed, true)
  assert.equal(h.triggeringIds.size, 0)
  assert.match(h.messages[0][1], /生成 2 个执行报告，1 个子任务生成失败/)
})

test('触发接口异常后可再次点击', async t => {
  const h = setupGroupList({ triggerScheduledTaskGroup: async () => { throw Error('request failed') } }); t.after(h.close); await h.mount()
  h.triggerGroup({ id:7,name:'回归测试' }); h.confirmations[0].config.onCancel()
  assert.equal(h.writes.length,0); assert.equal(h.confirmations[0].closed,true)
  h.triggerGroup({ id:7,name:'回归测试' }); const modal=h.confirmations[1]
  assert.equal(await modal.config.onBeforeOk(),false); assert.equal(await modal.config.onBeforeOk(),false)
  assert.equal(h.writes.length,2); assert.equal(h.triggeringIds.size,0); modal.config.onCancel(); assert.equal(modal.closed,true)
})
