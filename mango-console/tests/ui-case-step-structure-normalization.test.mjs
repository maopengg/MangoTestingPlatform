import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { deferred, method } from './helpers/case-details-harness.mjs'

const base = 'src/views/uitest/case/details', assets = loadModule('src/components/business/ui-case-step-create.ts')
const structure = loadModule(`${base}/step-structure.ts`, { '@/components/business/ui-case-step-create': assets })
const long = '90071992547409930000'
function setup(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, writes = [], confirmations = [], messages = [], changes = []
  const state = vue.reactive({ caseId: 0, ids: [0, long, 2] })
  const route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] })
  const api = Object.fromEntries(Object.entries({ deleteUiCaseStepsDetailed: overrides.remove || (async () => ({ code: 200 })), getUiCaseStepsRefreshCacheData: overrides.sync || (async () => ({ code: 200 })), putUiCasePutCaseSort: overrides.sort || (async () => ({ code: 200 })) }).map(([name, fn]) => [name, (...args) => { writes.push([name, ...args]); return fn(...args) }]))
  const module = loadModule(`${base}/composables/useCaseStepStructure.ts`, {
    vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
    'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
    '@/api/uitest/case-steps-detailed': api, '@/components/business/ui-case-step-create': assets, '../step-structure': structure,
    '@arco-design/web-vue': { Message: { success: message => messages.push(message) }, Modal: { confirm(options) { const shell = { closed: false, options, close() { this.closed = true } }; confirmations.push(shell); return shell } } },
  })
  const scope = vue.effectScope(), h = scope.run(() => module.useCaseStepStructure({ caseId: () => state.caseId, stepIds: () => state.ids, committed: value => { if (overrides.commit) overrides.commit(value); changes.push(value) } }))
  return { ...h, state, route, user, permission, writes, confirmations, messages, changes, callbacks,
    mount() { callbacks.mount.forEach(fn => fn()) }, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); scope.stop(); globalThis.document = previous },
  }
}
test('finite structure IDs/order and sync summary preserve zero/long IDs, reject duplicates and use matching summary', () => {
  assert.deepEqual(structure.caseStepIds([0, long]), [0, long]); assert.throws(() => structure.caseStepIds([1, '1'])); assert.throws(() => structure.caseStepIds({})); assert.throws(() => structure.caseStepIds([false]))
  const ids = [0, long, 2]; assert.deepEqual(structure.moveCaseStep(ids, 0, 2), [long, 2, 0]); assert.deepEqual(ids, [0, long, 2]); assert.throws(() => structure.moveCaseStep(ids, 9, 0))
  assert.equal(structure.caseStepSyncMessage({ code: 200, data: { updated: [{ case_step_id: 9 }, { case_step_id: 0, added_count: 1, updated_count: 2, removed_count: 3, unchanged_count: 4, initialized_count: 5 }] } }, 0), '同步完成：新增 1，更新 2，删除 3，保留 9')
  assert.equal(structure.caseStepSyncMessage({ code: 200, data: { updated: [{ case_step_id: 0, added_count: 'bad' }] } }, 0), '同步完成'); assert.equal(structure.caseStepSyncMessage({ code: 200 }, 0), '同步完成'); assert.throws(() => structure.caseStepSyncMessage({ code: 403 }, 0))
})
test('delete confirmation fixes original IDs, makes no early write and blocks duplicate confirmations/submission', async t => {
  const pending = deferred(), h = setup({ remove: () => pending.promise }); t.after(h.close)
  assert.equal(h.remove(long), true); assert.equal(h.remove(0), false); assert.equal(h.sync(0), false); assert.deepEqual(h.writes, [])
  const shell = h.confirmations[0]; assert.equal(shell.options.okButtonProps.status, 'danger'); const saving = shell.options.onBeforeOk()
  assert.equal(await shell.options.onBeforeOk(), false); assert.equal(h.pending.value.kind, 'delete')
  h.state.ids = [long, 0, 2, 3]; assert.deepEqual(h.writes, [['deleteUiCaseStepsDetailed', long, 0]])
  pending.resolve({ code: 200 }); assert.equal(await saving, true); assert.equal(shell.closed, true); assert.equal(h.pending.value, null); assert.deepEqual(h.changes, [{ kind: 'delete', caseId: 0, recordId: long }])
})
test('cancel before confirming closes without write and allows another operation', async t => {
  const h = setup(); t.after(h.close); h.remove(0); const shell = h.confirmations[0]; shell.options.onCancel()
  assert.equal(await shell.options.onBeforeOk(), false); assert.deepEqual(h.writes, []); assert.equal(h.sync(0), true)
})
test('delete network/non-success failures keep confirmation open, restore loading and can retry', async t => {
  let mode = 'network'; const h = setup({ remove: async () => { if (mode === 'network') throw Error('network'); return { code: mode === 'response' ? 403 : 200 } } }); t.after(h.close)
  h.remove(0); const shell = h.confirmations[0]
  for (const value of ['network', 'response']) { mode = value; assert.equal(await shell.options.onBeforeOk(), false); assert.equal(shell.closed, false); assert.equal(h.pending.value, null); assert.match(h.error.value, /删除失败/); assert.deepEqual(h.changes, []) }
  mode = ''; assert.equal(await shell.options.onBeforeOk(), true); assert.equal(shell.closed, true); assert.equal(h.messages.length, 1)
})
test('sync retains original refresh protocol, reports matching counts and notifies parent only after success', async t => {
  let fail = true; const h = setup({ sync: async () => fail ? { code: 403 } : { code: 200, data: { updated: [{ case_step_id: long, added_count: 0, updated_count: 1, removed_count: 0, unchanged_count: 2, initialized_count: 1 }] } } }); t.after(h.close)
  h.sync(long); const shell = h.confirmations[0]; assert.equal(await shell.options.onBeforeOk(), false); assert.match(h.error.value, /同步失败/); assert.equal(shell.closed, false)
  fail = false; assert.equal(await shell.options.onBeforeOk(), true); assert.deepEqual(h.writes, [['getUiCaseStepsRefreshCacheData', long], ['getUiCaseStepsRefreshCacheData', long]])
  assert.deepEqual(h.changes, [{ kind: 'sync', caseId: 0, recordId: long }]); assert.match(h.messages[0], /保留 3/)
})
test('cancel during delete retains physical lock and commits original result without stale toast', async t => {
  const pending = deferred(), h = setup({ remove: () => pending.promise }); t.after(h.close); h.remove(0)
  const shell = h.confirmations[0], saving = shell.options.onBeforeOk(); shell.options.onCancel(); assert.equal(h.sync(long), false); assert.equal(await h.move(0, 2), false)
  pending.resolve({ code: 200 }); assert.equal(await saving, true); assert.equal(h.changes.length, 1); assert.deepEqual(h.messages, [])
})
test('malformed IDs, missing rows and rows removed before confirmation never issue a write', async t => {
  const h = setup(); t.after(h.close); assert.equal(h.remove('bad'), false); assert.equal(h.sync(9), false)
  h.remove(0); h.state.ids = [long, 2]; assert.equal(await h.confirmations[0].options.onBeforeOk(), false); assert.equal(h.confirmations[0].closed, true); assert.deepEqual(h.writes, [])
})
const identityChanges = [h => h.state.caseId = 2, h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/other', h => h.route.fullPath += '&other=1', h => { h.state.caseId = 2; h.state.caseId = 0 }]
test('all context changes invalidate confirmations before any write, including A-B-A', async () => {
  for (const change of identityChanges) { const h = setup(); try { h.remove(0); change(h); const shell = h.confirmations[0]; assert.equal(shell.closed, true); assert.equal(await shell.options.onBeforeOk(), false); assert.deepEqual(h.writes, []) } finally { h.close() } }
})
test('all context changes invalidate late delete/sync completion but retain lock until settlement', async () => {
  for (const kind of ['remove', 'sync']) for (const change of identityChanges) {
    const pending = deferred(), h = setup({ [kind]: () => pending.promise })
    try { h[kind](0); const saving = h.confirmations[0].options.onBeforeOk(); change(h); assert.notEqual(h.pending.value, null); assert.equal(h.remove(long), false); pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.equal(h.pending.value, null); assert.deepEqual(h.changes, []); assert.deepEqual(h.messages, []) } finally { h.close() }
  }
})
test('sort snapshots finite order, delays visible update until success and blocks concurrent structure operations', async t => {
  const pending = deferred(), h = setup({ sort: () => pending.promise }); t.after(h.close)
  const saving = h.move(0, 2); assert.deepEqual(h.state.ids, [0, long, 2]); assert.deepEqual(h.changes, []); assert.equal(h.pending.value.kind, 'sort'); assert.equal(h.sync(0), false); assert.equal(await h.move(2, 0), false)
  assert.deepEqual(h.writes, [['putUiCasePutCaseSort', [{ id: long, case_sort: 0 }, { id: 2, case_sort: 1 }, { id: 0, case_sort: 2 }]]])
  pending.resolve({ code: 200 }); assert.equal(await saving, true); assert.deepEqual(h.changes, [{ kind: 'sort', caseId: 0, order: [long, 2, 0] }])
})
test('sort failure retains order, releases lock and supports retry; invalid moves do not write', async t => {
  let fail = true; const h = setup({ sort: async () => { if (fail) throw Error('network'); return { code: 200 } } }); t.after(h.close)
  assert.equal(await h.move(9, 0), false); assert.equal(h.writes.length, 0); assert.equal(await h.move(0, 2), false); assert.match(h.error.value, /排序保存失败/); assert.deepEqual(h.changes, []); assert.deepEqual(h.state.ids, [0, long, 2]); assert.equal(h.pending.value, null)
  fail = false; assert.equal(await h.move(0, 2), true)
})
test('sort ignores completion for every changed identity/context and keeps original payload until settlement', async () => {
  for (const change of identityChanges) {
    const pending = deferred(), h = setup({ sort: () => pending.promise })
    try {
      const saving = h.move(0, 2); change(h); assert.notEqual(h.pending.value, null); assert.equal(await h.move(long, 2), false)
      pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.deepEqual(h.changes, []); assert.deepEqual(h.messages, []); assert.equal(h.pending.value, null)
      assert.deepEqual(h.writes[0], ['putUiCasePutCaseSort', [{ id: long, case_sort: 0 }, { id: 2, case_sort: 1 }, { id: 0, case_sort: 2 }]])
    } finally { h.close() }
  }
})
test('drag captures stable ID, follows current list after refresh, and invalidates across context changes', async t => {
  const h = setup(); t.after(h.close); assert.equal(h.beginDrag(0), true); assert.equal(h.draggingId.value, 0)
  h.state.ids = [2, 0, long]; assert.equal(await h.drop(long), true); assert.deepEqual(h.changes[0].order, [2, long, 0]); assert.equal(h.draggingId.value, null)
  h.beginDrag(0); h.user.roleId++; assert.equal(h.draggingId.value, null); assert.equal(await h.drop(long), false); assert.equal(h.writes.length, 1)
})
test('background/KeepAlive/unmount close confirmations and reject late sort even after resume', async () => {
  for (const leave of [h => { h.visibility('hidden'); h.visibility('visible') }, h => { h.callbacks.deactivate.forEach(fn => fn()); h.callbacks.activate.forEach(fn => fn()) }, h => h.callbacks.unmount.forEach(fn => fn())]) {
    const pending = deferred(), h = setup({ sort: () => pending.promise })
    try { h.mount(); h.remove(0); leave(h); assert.equal(h.confirmations[0].closed, true); assert.equal(await h.confirmations[0].options.onBeforeOk(), false) } finally { h.close() }
    const current = setup({ sort: () => pending.promise })
    try { current.mount(); const saving = current.move(0, 2); leave(current); assert.notEqual(current.pending.value, null); pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.deepEqual(current.changes, []); assert.deepEqual(current.messages, []) } finally { current.close() }
  }
})
test('accepted write with local update failure is not treated as failed mutation or retried blindly', async t => {
  const h = setup({ commit() { throw Error('render') } }); t.after(h.close); h.remove(0); const shell = h.confirmations[0]
  assert.equal(await shell.options.onBeforeOk(), true); assert.equal(shell.closed, true); assert.match(h.error.value, /操作已完成/); assert.equal(await shell.options.onBeforeOk(), false); assert.equal(h.writes.length, 1)
  assert.equal(await h.move(0, 2), true); assert.match(h.error.value, /排序已保存/)
})
test('parent commits scoped immutable delete/sort, retains newer rows/fields and invalidates old list requests', () => {
  const first = { id: 0, name: 'Keep fields' }, second = { id: long }, added = { id: 8 }, caseSteps = { value: [first, second, added] }, uiCaseId = { value: 0 }, stepTableLoading = { value: true }, stamp = { value: 0 }, refresh = []
  const apply = method('applyStepStructureChange', { caseSteps, uiCaseId, replaceCaseSteps: rows => caseSteps.value = rows, invalidateCaseSteps: () => stepTableLoading.value = false, caseCanvasRefreshStamp: stamp, doRefresh: value => refresh.push(value) }, path.resolve(base, 'index.vue'))
  apply({ kind: 'sort', caseId: 2, order: [long, 0] }); assert.equal(stepTableLoading.value, true)
  apply({ kind: 'sort', caseId: 0, order: [long, 0] }); assert.deepEqual(caseSteps.value, [second, first, added]); assert.equal(caseSteps.value[1], first); assert.equal(stepTableLoading.value, false); assert.deepEqual(refresh, [])
  apply({ kind: 'sync', caseId: 0, recordId: long }); assert.equal(stamp.value, 1); assert.deepEqual(refresh, [false])
  apply({ kind: 'delete', caseId: 0, recordId: 0 }); assert.deepEqual(caseSteps.value, [second, added])
})
test('delete and sort API retain exact URLs/parameter keys and zero/long IDs', () => {
  const calls = [], api = loadModule('src/api/uitest/case-steps-detailed.ts', { '@/api/http': { get() {}, post() {}, deleted: value => calls.push(value), put: value => calls.push(value) } })
  api.deleteUiCaseStepsDetailed(long, 0); api.putUiCasePutCaseSort([{ id: long, case_sort: 0 }])
  assert.equal(calls[0].url, '/ui/case/steps/detailed'); assert.deepEqual(calls[0].data(), { id: long, parent_id: 0 }); assert.equal(calls[1].url, '/ui/case/steps/detailed/sort'); assert.deepEqual(calls[1].data(), { case_sort_list: [{ id: long, case_sort: 0 }] })
})
test('parent SFC compiles with structure loading/errors and stable-ID drag bindings', () => {
  const filename = path.resolve(base, 'index.vue'), source = readFileSync(filename, 'utf8'), { descriptor, errors } = parse(source); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'ui-structure' }), template = compileTemplate({ source: descriptor.template.content, filename, id: 'ui-structure', compilerOptions: { bindingMetadata: script.bindings } }); assert.deepEqual(template.errors, [])
  assert.match(source, /@drop.prevent="dropCaseStep\(record.id\)"/); assert.match(source, /stepStructurePending\?\.kind === 'sort'/); assert.match(source, /mango-ui-step-structure-error/); assert.doesNotMatch(source, /function oeFreshSteps|function onDelete\(|const handleChange|caseStepDragIndex/)
})
