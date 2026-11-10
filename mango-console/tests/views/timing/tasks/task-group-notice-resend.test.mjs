import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { setupGroupList } from '../../../helpers/timing-task-group-list-harness.mjs'

const source = readFileSync(new URL('../../../../src/views/timing/tasks/components/TaskGroupManager.vue', import.meta.url), 'utf8')

test('任务组表格包含重发报告按钮，并确认环境、时间和原通知组', () => {
  assert.match(source, /label: '重发报告'/)
  assert.match(source, /onClick: \(\) => openResendNotice\(record\)/)
  assert.match(source, /label="最近执行"/)
  assert.match(source, /label="原通知组"/)
  assert.match(source, /@before-ok="confirmResendNotice"/)
})

test('选择明确批次重发，不触发任务；重复点击发送只请求一次', async t => {
  let resolve, calls = []
  const pending = new Promise((done) => { resolve = done })
  const h = setupGroupList({ getLatestTaskGroupExecutions: async () => ({code:200,data:[{id:68,test_env:0},{id:69,test_env:1}]}), resendTaskGroupNotice: (...args) => { calls.push(args);return pending } }); t.after(h.close);await h.mount()
  await h.openResendNotice({ id:2,name:'示例任务组' })
  assert.equal(h.noticeVisible.value,true);assert.equal(h.noticeLoadingIds.size,0)
  h.noticeExecutionId.value=69
  const first=h.confirmResendNotice()
  assert.equal(h.noticeSending.value,true);assert.equal(await h.confirmResendNotice(),false)
  assert.deepEqual(calls, [[2, 69]])
  resolve({ code:200,msg:'成功' })
  assert.equal(await first, true)
  assert.equal(h.noticeSending.value,false);assert.equal(h.writes.every(call=>call[0]==='resendTaskGroupNotice'),true)
})

test('没有执行批次不打开确认框，发送失败保留弹窗供重试并清理 loading', async () => {
  const empty=setupGroupList({getLatestTaskGroupExecutions:async()=>({code:200,data:[]})})
  try {await empty.mount();await empty.openResendNotice({id:2,name:'示例任务组'});assert.equal(empty.noticeVisible.value,false);assert.equal(empty.noticeLoadingIds.size,0)}finally{empty.close()}
  const failed=setupGroupList({resendTaskGroupNotice:async()=>{throw Error('用例未完成')}})
  try {await failed.mount();await failed.openResendNotice({id:2,name:'示例任务组'});assert.equal(await failed.confirmResendNotice(),false);assert.equal(failed.noticeVisible.value,true);assert.equal(failed.noticeSending.value,false)}finally{failed.close()}
})
