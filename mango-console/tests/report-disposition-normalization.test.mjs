import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/report/details')
const response = data => ({ code: 200, data })
function setup(api = () => response(null), sharedWrites) {
  const route = vue.reactive({ fullPath: '/report/details?id=1' })
  const user = vue.reactive({ userId: 1, roleId: 1, token: '', selected_environment: 0 })
  const life = { mount: [], activate: [], deactivate: [], unmount: [] }, calls = [], messages = []
  const originalDocument = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' })
  globalThis.document = doc
  const writesModule = './composables/useReportDispositionWrite'
  const h = harness('ReportDisposition', 'visible,saving,form,snapshot,record,eligible,errorText,open,save,dialogClose:close,reasonOptions,writes', {
    base, filename: path.join(base, 'ReportDisposition.vue'),
    props: { record: { id: 0, status: 0, case_sum: 0, failure_reason: 'environment', failure_description: 'old', is_excluded: false }, editable: true },
    modules: {
      vue: { ...vue, onMounted: fn => life.mount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn), onBeforeUnmount: fn => life.unmount.push(fn) },
      'vue-router': { useRoute: () => route },
      '@/store/modules/user': { useUserStoreContext: () => user },
      '@/store/modules/get-enum': { useEnum: () => ({ report_failure_reason: [{ key: 'environment', title: '环境' }] }) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'warning', 'error'].map(name => [name, text => messages.push([name, text])])) },
      ...(sharedWrites ? { [writesModule]: { useReportDispositionWrite: () => sharedWrites } } : {}),
    },
    api: { updateReportDisposition(id, payload) { calls.push({ id, payload }); return api(id, payload) } },
  })
  life.mount.forEach(fn => fn()); life.activate.forEach(fn => fn())
  return { ...h, user, route, life, doc, calls, messages, data: h.load('report-disposition.ts'),
    close() { life.unmount.forEach(fn => fn()); h.close(); globalThis.document = originalDocument } }
}

test('打开保留 ID0/数量0，固定白名单草稿；取消重开不保留未保存修改', t => {
  const h = setup(); t.after(h.close)
  h.open(); assert.equal(h.visible.value, true); assert.equal(h.snapshot.value.id, '0'); assert.equal(h.snapshot.value.case_sum, 0)
  h.form.failure_description = 'unsaved'; h.form.unexpected = 'discard'
  assert.equal(h.props.record.failure_description, 'old')
  h.visible.value = false
  assert.equal(h.snapshot.value, null); assert.equal(h.form.failure_description, '')
  h.open(); assert.equal(h.form.failure_description, 'old')
  assert.deepEqual(h.data.dispositionPayload(h.form), { is_excluded: false, failure_reason: 'environment', failure_description: 'old' })
})

test('原因可单独保存；排除必须补齐原因和说明；成功仅提交三个字段', async t => {
  const h = setup(); t.after(h.close)
  h.open(); h.form.is_excluded = true; h.form.failure_reason = ''; h.form.failure_description = ''
  assert.equal(await h.save(), false); assert.equal(h.calls.length, 0)
  h.form.is_excluded = false; h.form.failure_reason = 'environment'; h.form.failure_description = '  diagnosis  '
  h.form.audit = 'discard'
  assert.equal(await h.save(), true)
  assert.deepEqual(h.calls, [{ id: '0', payload: { is_excluded: false, failure_reason: 'environment', failure_description: 'diagnosis' } }])
  assert.equal(h.visible.value, false); assert.deepEqual(h.events, [['saved']])
})

test('失败码与网络失败保留草稿和错误，显式重试成功才关闭', async t => {
  let count = 0
  const h = setup(() => ++count === 1 ? { code: 403 } : count === 2 ? Promise.reject(new Error('failed')) : response(null)); t.after(h.close)
  h.open(); h.form.failure_description = 'draft'
  assert.equal(await h.save(), false); assert.ok(h.errorText.value)
  assert.equal(h.visible.value, true); assert.equal(h.form.failure_description, 'draft'); assert.equal(h.saving.value, false)
  assert.equal(await h.save(), false); assert.equal(h.events.length, 0)
  assert.equal(await h.save(), true); assert.equal(h.messages.filter(m => m[0] === 'success').length, 1)
})

test('保存固定目标和参数，进行中不重复；同 ID 轮询更新不覆盖草稿', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close)
  h.open(); h.form.failure_description = 'submitted'
  const write = h.save(); assert.equal(h.saving.value, true)
  h.props.record = { ...h.props.record, failure_description: 'new server value' }
  h.form.failure_description = 'later edit'
  assert.equal(await h.save(), false)
  assert.equal(h.calls.length, 1); assert.equal(h.calls[0].payload.failure_description, 'submitted')
  pending.resolve(response(null)); assert.equal(await write, true); assert.equal(h.saving.value, false)
})

for (const field of ['record', 'editable', 'userId', 'roleId', 'token', 'selected_environment', 'route']) {
  test(`${field} A-B-A 关闭旧草稿，旧保存不提示、不刷新，物理锁不提前释放`, async t => {
    const pending = deferred(), h = setup(() => pending.promise); t.after(h.close)
    h.open(); const write = h.save()
    if (field === 'record') { h.props.record = { id: 1, status: 0 }; h.props.record = { id: 0, status: 0 } }
    else if (field === 'editable') { h.props.editable = false; h.props.editable = true }
    else if (field === 'route') { h.route.fullPath = '/report/details?id=2'; h.route.fullPath = '/report/details?id=1' }
    else { const previous = h.user[field]; h.user[field] = field === 'token' ? 'fixture-b' : 2; h.user[field] = previous }
    assert.equal(h.visible.value, false); assert.equal(h.snapshot.value, null); assert.equal(h.saving.value, true)
    h.open(); assert.equal(h.visible.value, false)
    pending.resolve(response(null)); assert.equal(await write, false)
    assert.equal(h.saving.value, false); assert.equal(h.events.length, 0); assert.equal(h.messages.length, 0)
    h.open(); assert.equal(h.visible.value, true)
  })
}

test('后台、KeepAlive 和卸载关闭草稿；恢复不会自动打开，迟到保存不发事件', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close)
  h.open(); const write = h.save()
  h.doc.visibilityState = 'hidden'; h.doc.dispatchEvent(new Event('visibilitychange'))
  h.doc.visibilityState = 'visible'; h.doc.dispatchEvent(new Event('visibilitychange'))
  assert.equal(h.visible.value, false)
  pending.resolve(response(null)); await write
  assert.equal(h.events.length, 0)
  h.open(); h.life.deactivate.forEach(fn => fn()); assert.equal(h.visible.value, false)
  h.open(); assert.equal(h.visible.value, false)
  h.life.activate.forEach(fn => fn()); assert.equal(h.visible.value, false)
  h.open(); assert.equal(h.visible.value, true)
  h.life.unmount.forEach(fn => fn()); h.open(); assert.equal(h.visible.value, false)
})

test('行组件卸载重建也不能并发写入同一明细，真实请求结束后才释放共享锁', async t => {
  const pending = deferred(), first = setup(() => pending.promise)
  first.open(); const write = first.save()
  first.life.unmount.forEach(fn => fn())
  const second = setup(() => response(null), first.writes); t.after(() => { second.close(); first.close() })
  assert.equal(second.saving.value, true); second.open(); assert.equal(second.visible.value, false)
  pending.resolve(response(null)); await write; await flush()
  assert.equal(second.saving.value, false); second.open()
  assert.equal(await second.save(), true); assert.equal(first.events.length, 0)
})

test('状态组件正确显示未知/基础设施待核查，枚举按 key 匹配', t => {
  const h = harness('ReportDispositionStatus', 'record,description', {
    base, filename: path.join(base, 'ReportDispositionStatus.vue'), props: { record: null },
    modules: { '@/store/modules/get-enum': { useEnum: () => ({ report_failure_reason: [{ key: 'environment', title: '环境' }] }) } },
  }); t.after(h.close)
  assert.equal(h.record.value, null)
  h.props.record = { id: 0, failure_reason: 'environment', failure_description: 'diagnosis', execution_control: { phase: 'infrastructure_blocked', requires_review: false } }
  assert.equal(h.record.value.execution_control.requires_review, false)
  assert.equal(h.description.value, '原因：环境；说明：diagnosis')
})
