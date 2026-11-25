import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { reactive } from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

function setup(t, values = {}) {
  const requests = [], errors = []
  const user = reactive({ userId: 1, roleId: 1, token: 'example-token' })
  const state = harness('CaseVersionResultPopover',
    'visible,loading,failed,items,onVisibleChange,loadResults,resultLabel,environmentLabel', {
      base: path.resolve('src/views/apitest/case'),
      props: { caseId: 10, ...values },
      api: { getApiCaseVersionResults: (id, env) => {
        const task = deferred(); requests.push({id, env, task}); return task.promise
      } },
      modules: {
        '@/store/modules/user': {default: () => user},
        '@/store/modules/get-enum': {useEnum: () => ({task_status: {
          0:{title:'失败'},1:{title:'通过'},3:{title:'进行中'}}, report_execution_phase:{},
          environment_type:[{key:0,title:'测试环境'},{key:1,title:'开发环境'},{key:2,title:'生产环境'}]})},
        '@/utils/load-error': {reportLoadError: (...args) => errors.push(args)},
      },
    })
  t.after(state.close)
  return {...state, requests, errors, user}
}

test('no eager requests; hovering fetches once without an environment filter', async t => {
  const state = setup(t)
  assert.equal(state.requests.length, 0)
  state.onVisibleChange(true)
  state.onVisibleChange(true)
  assert.equal(state.requests.length, 1)
  assert.equal(state.loading.value, true)
  assert.deepEqual([state.requests[0].id, state.requests[0].env], [10, undefined])
  state.requests[0].task.resolve({data:[{publication_status:'unpublished', label:'未发布（编辑态）', status:null}]})
  await flush()
  assert.equal(state.loading.value, false)
  assert.equal(state.items.value.length, 1)
  assert.equal(state.resultLabel(state.items.value[0]), '待测试')
  assert.equal(state.resultLabel({status:1}), '通过')
  state.onVisibleChange(false)
  state.onVisibleChange(true)
  assert.equal(state.requests.length, 2)
})

test('identity and asset changes invalidate results and in-flight responses', async t => {
  const state = setup(t)
  for (const change of [() => {state.props.caseId=20},
                        () => {state.user.token='example-new-token'}]) {
    state.onVisibleChange(true)
    const request = state.requests.at(-1)
    change(); await flush()
    request.task.resolve({data:[{status:0}]}); await flush()
    assert.equal(state.visible.value, false)
    assert.equal(state.items.value.length, 0)
    assert.equal(state.loading.value, false)
  }
})

test('closing before failure is silent and visible failures permit retry', async t => {
  const state = setup(t)
  state.onVisibleChange(true)
  state.onVisibleChange(false)
  state.requests[0].task.reject(new Error('example')); await flush()
  assert.equal(state.errors.length, 0)
  state.onVisibleChange(true)
  state.requests[1].task.reject(new Error('example')); await flush()
  assert.equal(state.failed.value, true)
  assert.equal(state.errors.length, 1)
  void state.loadResults()
  state.requests[2].task.resolve({data:[{status:1}]}); await flush()
  assert.equal(state.failed.value, false)
  assert.equal(state.items.value[0].status, 1)
  assert.equal(state.requests.length, 3)
})

test('result timestamps are formatted to seconds without changing the reported wall time', t => {
  const state = setup(t)
  const {formatCaseResultTime} = state.load('result-presentation.ts')
  assert.equal(formatCaseResultTime('2026-11-18T09:55:50.529131'), '2026-11-18 09:55:50')
  assert.equal(formatCaseResultTime('2026-11-18T09:55:50+08:00'), '2026-11-18 09:55:50')
  assert.equal(formatCaseResultTime(null), '')
})

test('each row uses its recorded environment, including zero, never the selected execution environment', t => {
  const state = setup(t)
  assert.equal(state.environmentLabel({status:1,test_env:0}), '测试环境')
  assert.equal(state.environmentLabel({status:0,test_env:1}), '开发环境')
  assert.equal(state.environmentLabel({status:1,test_env:2}), '生产环境')
  assert.equal(state.environmentLabel({status:null,test_env:null}), '—')
  assert.equal(state.environmentLabel({status:1,test_env:null}), '环境未记录')
  assert.equal(state.environmentLabel({status:1,test_env:99}), '环境 #99')
})

test('hover preserves separate rows for the same publication state in different environments', async t => {
  const state = setup(t)
  state.onVisibleChange(true)
  const rows = [
    {publication_status:'unpublished', label:'未发布（编辑态）', test_env:0, status:1},
    {publication_status:'unpublished', label:'未发布（编辑态）', test_env:1, status:0},
    {publication_status:'prepublished', label:'预发布 r1', test_env:null, status:null},
  ]
  state.requests[0].task.resolve({data:rows}); await flush()
  assert.deepEqual(state.items.value, rows)
  assert.deepEqual(state.items.value.map(state.environmentLabel), ['测试环境','开发环境','—'])
})
