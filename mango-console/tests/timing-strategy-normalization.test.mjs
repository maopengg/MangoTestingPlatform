import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/timing/strategy')
const row = (values = {}) => ({ id: 0, name: 'Example strategy', cron: '*/5 * * * *', create_time: '2026-11-09 10:00:00',
  update_time: '2026-11-09 11:00:00', update_user: { id: 0, name: 'Example', username: 'example@example.com' }, ...values })
const ok = (data = [], totalSize = 1) => ({ code: 200, msg: 'ok', data, totalSize })
function actual(filename, dependencies) {
  const exports = {}, source = ts.transpileModule(readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  new Function('exports', 'require', source)(exports, name => { if (name in dependencies) return dependencies[name]; { if (['@/utils/load-error', '@/utils/api-response'].includes(name)) return loadFeedbackModule(name); throw Error('Unexpected dependency ' + name) } })
  return exports
}
function setup(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, calls = [], messages = [], confirms = []
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['timing.strategy:read'] })
  const route = vue.reactive({ path: '/timing/strategy/index', fullPath: '/timing/strategy/index' })
  const api = Object.fromEntries(['getSystemTime', 'getUserName', 'postSystemTime', 'putSystemTime', 'deleteSystemTime'].map(name => [name, (...args) => {
    calls.push([name, ...args]); return overrides[name]?.(...args) ?? Promise.resolve(name === 'getSystemTime' ? ok([row()]) : name === 'getUserName' ? ok([{ key: 0, title: 'Example' }]) : ok())
  }]))
  const h = harness('index', 'rows,listLoading,listError,conditionItems,pagination,updaterOptions,updaterLoading,updaterError,modalDialogRef,form,editorId,editorVisible,saving,saveError,deletingId,writeBusy,actionTitle,buildQuery,doRefresh,onSearch,onResetSearch,loadUpdaters,onAdd,onUpdate,closeEditor,onDataForm,onDelete', { base, api,
    modules: { vue: { ...vue, onMounted: f => callbacks.mount.push(f), onActivated: f => callbacks.activate.push(f), onDeactivated: f => callbacks.deactivate.push(f), onBeforeUnmount: f => callbacks.unmount.push(f) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@/hooks/table': actual('src/hooks/table.ts', { vue }), '@/hooks/use-latest-request': actual('src/hooks/use-latest-request.ts', {}),
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'warning', 'error'].map(name => [name, value => messages.push([name, value])])),
        Modal: { confirm(options) { const handle = { options, closed: false, close() { this.closed = true } }; confirms.push(handle); return handle } } } } })
  const shell = { visible: false, loading: false, closed: 0, show() { this.visible = true; return Promise.resolve(true) }, close() { this.visible = false; this.closed++; this.loading = false; return Promise.resolve(false) }, setConfirmLoading(value) { this.loading = value } }
  h.modalDialogRef.value = shell
  return { ...h, shell, user, permission, route, callbacks, calls, messages, confirms,
    mount() { callbacks.mount.forEach(f => f()); callbacks.activate.forEach(f => f()) },
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(f => f()); h.close(); globalThis.document = previous } }
}

test('strategy DTO preserves zero/long IDs, nullable updater and copies whitelist without audit extras', t => {
  const h = setup(); t.after(h.close); const m = h.load('strategy-records.ts'), original = row({ extra: 'omit' }), copied = m.copyStrategyRecord(original)
  assert.equal(copied.id, 0); assert.equal(copied.update_user.id, 0); assert.equal('extra' in copied, false)
  copied.update_user.name = 'Changed'; assert.equal(original.update_user.name, 'Example')
  const nullable = m.copyStrategyRecord(row({ id: '90071992547409931234', update_user: null, create_time: null })); assert.equal(nullable.id, '90071992547409931234'); assert.equal(nullable.update_user, null); assert.equal(nullable.create_time, '')
})
test('invalid lists and option responses remain errors instead of successful empty data', t => {
  const h = setup(); t.after(h.close); const m = h.load('strategy-records.ts')
  for (const value of [{ code: 403, data: [] }, ok({}), ok([row()], '1'), ok([row(), row()], 2), ok([row({ id: Number.MAX_SAFE_INTEGER + 1 })]), ok([row({ cron: {} })]), ok([row()], -1)]) assert.throws(() => m.parseStrategies(value))
  assert.deepEqual(m.parseStrategies(ok([], 0)), { rows: [], total: 0 })
  assert.throws(() => m.parseStrategyUsers(ok([{ key: 0, title: 'A' }, { key: '0', title: 'B' }]))); assert.throws(() => m.parseStrategyUsers({ code: 403, data: [] }))
  assert.deepEqual(m.parseStrategyUsers(ok([{ key: 0, title: 'Example', extra: 1 }])), [{ key: 0, title: 'Example' }])
})
test('draft mapping and save payload preserve original cron/text and fixed trigger contract, excluding audit fields', t => {
  const h = setup(); t.after(h.close); const m = h.load('strategy-records.ts'), record = m.copyStrategyRecord(row()), draft = m.createStrategyDraft(record)
  draft.name = ' Changed '; assert.equal(record.name, 'Example strategy')
  assert.deepEqual(m.strategyPayload(draft, null), { name: ' Changed ', cron: '*/5 * * * *', trigger_type: 'cron' })
  assert.equal(m.strategyPayload(draft, 0).id, 0); assert.equal('create_time' in m.strategyPayload(draft, 0), false)
  assert.equal(m.validateStrategyDraft(m.createStrategyDraft()), '请输入定时器的介绍'); assert.match(m.validateStrategyDraft({ name: 'Example', cron: '' }), /cron/)
  assert.equal(m.validateStrategyDraft({ name: 'Example', cron: 'server-validated-expression' }), '')
})
test('search factories are independent and updater collections/ID separators use existing public contracts', t => {
  const h = setup(); t.after(h.close); const a = h.load('config.ts').createConditionItems(), b = h.load('config.ts').createConditionItems()
  a.find(item => item.key === 'id').value = '5574、5577'; assert.equal(a[0].value, '5574,5577'); assert.equal(b[0].value, '')
  const updater = a.find(item => item.key === 'update_user'); assert.equal(updater.multiple, true); assert.equal(updater.searchOperator, 'in')
  updater.value.push(0); assert.deepEqual(b.find(item => item.key === 'update_user').value, []); updater.reset(); assert.deepEqual(updater.value, [])
})
test('query whitelist omits empty/unrelated values and preserves zero, long ID and multi-user protocol', t => {
  const h = setup(); t.after(h.close); h.conditionItems.find(item => item.key === 'id').value = '90071992547409931234,5574'; h.conditionItems.find(item => item.key === 'update_user').value = [0, 2]
  assert.deepEqual(h.buildQuery(), { id__in: '90071992547409931234,5574', update_user__in: '0,2' })
  const m = h.load('strategy-records.ts'); assert.deepEqual(m.strategyQuery({ id: 0, name: '', update_user__in: null, unrelated: 1 }), { id: 0 }); assert.throws(() => m.strategyQuery({ name: {} }))
})
test('list and updater reads start independently and duplicate calls coalesce', async t => {
  const list = deferred(), users = deferred(), h = setup({ getSystemTime: () => list.promise, getUserName: () => users.promise }); t.after(h.close)
  h.mount(); const first = h.doRefresh(), options = h.loadUpdaters(); assert.equal(h.doRefresh(), first); assert.equal(h.loadUpdaters(), options); await flush()
  assert.deepEqual(h.calls.map(([name]) => name), ['getSystemTime', 'getUserName'])
  list.resolve(ok([row()])); await first; assert.equal(h.listLoading.value, false); assert.equal(h.updaterLoading.value, true)
  users.resolve(ok([{ key: 0, title: 'Example' }])); await options; assert.equal(h.updaterLoading.value, false)
})
test('list failure retains same-context data and retries without stuck loading; options fail independently', async t => {
  let count = 0, userCount = 0; const h = setup({ getSystemTime: async () => ++count === 2 ? { code: 403 } : ok([row()]), getUserName: async () => { if (++userCount === 1) throw Error('offline'); return ok([{ key: 0, title: 'Example' }]) } }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.rows.value.length, 1); assert.match(h.updaterError.value, /重试/); assert.equal(h.updaterLoading.value, false)
  await h.doRefresh(); assert.match(h.listError.value, /重试/); assert.equal(h.rows.value.length, 1); assert.equal(h.listLoading.value, false)
  await h.doRefresh(); await h.loadUpdaters(); assert.equal(h.listError.value, ''); assert.equal(h.updaterError.value, '')
})
test('search resets first page and late old list cannot overwrite new filters', async t => {
  const a = deferred(), b = deferred(); let n = 0; const h = setup({ getSystemTime: () => ++n === 1 ? a.promise : b.promise }); t.after(h.close)
  h.mount(); await flush(); h.pagination.page = 3; h.conditionItems.find(item => item.key === 'name').value = 'New'; const task = h.onSearch(); await flush()
  assert.equal(h.calls.filter(([name]) => name === 'getSystemTime').at(-1)[1].page, 1)
  b.resolve(ok([row({ id: 2 })])); await task; a.resolve(ok([row({ id: 1 })])); await flush(); assert.equal(h.rows.value[0].id, 2)
})
test('reset clears ID/text/collections and shrinking totals refetch final page', async t => {
  const h = setup({ getSystemTime: async () => ok([], 0) }); t.after(h.close); h.mount(); await flush(); h.pagination.page = 4; await h.doRefresh()
  assert.equal(h.pagination.page, 1); assert.equal(h.pagination.pageCount, 0)
  h.conditionItems.find(item => item.key === 'update_user').value = [0]; h.conditionItems[0].value = '5574'; await h.onResetSearch()
  assert.deepEqual(h.calls.filter(([name]) => name === 'getSystemTime').at(-1)[1], { page: 1, pageSize: 20 }); assert.deepEqual(h.conditionItems.find(item => item.key === 'update_user').value, [])
})
test('add/edit/cancel reopen use independent drafts and synchronous ID-zero edit mode', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush(); const input = row()
  h.onUpdate(input); assert.equal(h.editorId.value, 0); assert.equal(h.actionTitle.value, '编辑'); assert.equal(h.form.cron, input.cron)
  h.form.name = 'Changed'; assert.equal(input.name, 'Example strategy'); h.closeEditor(); h.onAdd()
  assert.equal(h.editorId.value, null); assert.equal(h.actionTitle.value, '新增'); assert.deepEqual({ ...h.form }, { name: '', cron: '' }); assert.equal(h.editorVisible.value, true)
  h.onUpdate(row({ id: 2, name: 'Next' })); assert.equal(h.form.name, 'Next'); assert.equal(h.editorId.value, 2)
})
test('required input validation releases modal loading without sending requests', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush(); h.onAdd(); h.shell.loading = true; await h.onDataForm()
  assert.equal(h.shell.loading, false); assert.equal(h.calls.some(([name]) => name === 'postSystemTime'), false)
  h.form.name = 'Example'; await h.onDataForm(); assert.equal(h.calls.some(([name]) => name === 'postSystemTime'), false)
})
test('create saves fixed payload once, blocks duplicate/new record and closes only after success', async t => {
  const write = deferred(), h = setup({ postSystemTime: () => write.promise }); t.after(h.close); h.mount(); await flush(); h.onAdd()
  Object.assign(h.form, { name: 'Example', cron: '*/5 * * * *' }); const task = h.onDataForm(); h.form.name = 'Later'; await h.onDataForm(); h.onUpdate(row({ id: 2 }))
  assert.equal(h.calls.filter(([name]) => name === 'postSystemTime').length, 1); assert.equal(h.calls.find(([name]) => name === 'postSystemTime')[1].name, 'Example')
  assert.equal(h.saving.value, true); assert.equal(h.editorId.value, null); assert.equal(h.editorVisible.value, true); assert.equal(h.shell.loading, true)
  write.resolve(ok()); await task; assert.equal(h.saving.value, false); assert.equal(h.editorVisible.value, false)
})
test('update uses fixed ID and whitelist; failure preserves draft and retry succeeds', async t => {
  let count = 0; const h = setup({ putSystemTime: async () => ++count === 1 ? { code: 400 } : ok() }); t.after(h.close); h.mount(); await flush()
  const input = row({ id: '90071992547409931234' }); h.onUpdate(input); input.id = 2; h.form.name = 'Updated'; await h.onDataForm()
  assert.equal(h.editorVisible.value, true); assert.equal(h.form.name, 'Updated'); assert.match(h.saveError.value, /重试/); assert.equal(h.shell.loading, false)
  const payload = h.calls.find(([name]) => name === 'putSystemTime')[1]; assert.equal(payload.id, '90071992547409931234'); assert.equal('update_user' in payload, false)
  await h.onDataForm(); assert.equal(h.editorVisible.value, false); assert.equal(count, 2)
})
test('cancel during write preserves physical lock and late save does not reopen/close or notify next window', async t => {
  const write = deferred(), h = setup({ putSystemTime: () => write.promise }); t.after(h.close); h.mount(); await flush(); h.onUpdate(row())
  const task = h.onDataForm(); h.closeEditor(); const closed = h.shell.closed; h.onUpdate(row({ id: 2 })); assert.equal(h.editorVisible.value, false); assert.equal(h.saving.value, true)
  write.resolve(ok()); await task; assert.equal(h.shell.closed, closed); assert.equal(h.messages.some(([name]) => name === 'success'), false); assert.equal(h.saving.value, false)
  h.onUpdate(row({ id: 2 })); assert.equal(h.editorId.value, 2)
})
test('delete confirmation retains on server rejection, retries fixed target and explicitly closes after success', async t => {
  let n = 0; const h = setup({ deleteSystemTime: async () => ++n === 1 ? { code: 400 } : ok() }); t.after(h.close); h.mount(); await flush()
  const input = row({ id: '90071992547409931234' }); h.onDelete(input); input.id = 4; const confirmation = h.confirms.at(-1)
  assert.equal(await confirmation.options.onBeforeOk(), false); assert.equal(confirmation.closed, false); assert.equal(h.deletingId.value, null)
  assert.equal(await confirmation.options.onBeforeOk(), true); assert.equal(confirmation.closed, true); assert.equal(h.calls.filter(([name]) => name === 'deleteSystemTime').at(-1)[1], '90071992547409931234')
})
test('delete physical lock persists during identity change and late success does not notify new identity', async t => {
  const write = deferred(), h = setup({ deleteSystemTime: () => write.promise }); t.after(h.close); h.mount(); await flush(); h.onDelete(row())
  const confirmation = h.confirms.at(-1), task = confirmation.options.onBeforeOk(); assert.equal(await confirmation.options.onBeforeOk(), false)
  h.user.userId = 2; await flush(); assert.equal(confirmation.closed, true); assert.equal(h.deletingId.value, 0)
  write.resolve(ok()); assert.equal(await task, false); assert.equal(h.deletingId.value, null); assert.equal(h.messages.some(([name]) => name === 'success'), false)
})
test('cancelled confirmation and context-invalid old callback never send deletion', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush(); h.onDelete(row()); const cancelled = h.confirms.at(-1); cancelled.options.onCancel()
  assert.equal(await cancelled.options.onBeforeOk(), false); h.onDelete(row()); const stale = h.confirms.at(-1); h.visibility('hidden')
  assert.equal(await stale.options.onBeforeOk(), false); assert.equal(h.calls.some(([name]) => name === 'deleteSystemTime'), false)
})
test('successful save remains successful when following list refresh fails', async t => {
  let reads = 0; const h = setup({ getSystemTime: async () => { if (++reads > 1) throw Error('offline'); return ok([row()]) } }); t.after(h.close)
  h.mount(); await flush(); h.onUpdate(row()); await h.onDataForm(); assert.equal(h.editorVisible.value, false); assert.equal(h.saveError.value, '')
  assert.match(h.listError.value, /重试/); assert.equal(h.messages.some(([name]) => name === 'success'), true)
  await flush(); assert.equal(reads, 2); assert.match(h.listError.value, /重试/)
})
test('all identity dimensions clear old filters/results/editor and late reads cannot repopulate them', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush()
  for (const change of [() => h.user.userId++, () => h.user.roleId++, () => { h.user.token = 'next-session' }, () => h.user.selected_environment++, () => h.permission.permissionKeys.push('timing.strategy:change')]) {
    h.onUpdate(row()); h.conditionItems.find(item => item.key === 'update_user').value = [0]; change()
    assert.deepEqual(h.rows.value, []); assert.deepEqual(h.updaterOptions.value, []); assert.equal(h.editorVisible.value, false); assert.equal(h.form.name, '')
    assert.deepEqual(h.conditionItems.find(item => item.key === 'update_user').value, []); await flush(); assert.equal(h.rows.value.length, 1)
  }
})
test('late list/updater results cannot replace a new identity', async t => {
  const list = deferred(), users = deferred(); let n = 0, u = 0
  const h = setup({ getSystemTime: () => ++n === 1 ? list.promise : Promise.resolve(ok([row({ id: 2 })])), getUserName: () => ++u === 1 ? users.promise : Promise.resolve(ok([{ key: 2, title: 'New' }])) }); t.after(h.close)
  h.mount(); await flush(); h.user.token = 'other'; await flush(); list.resolve(ok([row({ id: 1 })])); users.resolve(ok([{ key: 1, title: 'Old' }])); await flush()
  assert.equal(h.rows.value[0].id, 2); assert.equal(h.updaterOptions.value[0].key, 2)
})
test('background save completion is silent and foreground waits for physical write before reloading', async t => {
  const write = deferred(), h = setup({ putSystemTime: () => write.promise }); t.after(h.close); h.mount(); await flush(); h.onUpdate(row()); const task = h.onDataForm()
  h.visibility('hidden'); h.visibility('visible'); const count = h.calls.filter(([name]) => name === 'getSystemTime').length; assert.equal(h.editorVisible.value, false)
  write.resolve(ok()); await task; await flush(); assert.equal(h.messages.some(([name]) => name === 'success'), false)
  assert.ok(h.calls.filter(([name]) => name === 'getSystemTime').length > count); assert.equal(h.calls.filter(([name]) => name === 'putSystemTime').length, 1)
})
test('KeepAlive pause/return resumes reads and route leave/unmount invalidate all pending work', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush(); const before = h.calls.length
  h.callbacks.deactivate.forEach(f => f()); await h.doRefresh(); await h.loadUpdaters(); assert.equal(h.calls.length, before)
  h.callbacks.activate.forEach(f => f()); await flush(); assert.equal(h.calls.length, before + 2)
  h.route.path = '/index/home'; h.route.fullPath = '/index/home'; const after = h.calls.length; await h.doRefresh(); h.onAdd(); assert.equal(h.editorVisible.value, false)
  h.callbacks.unmount.forEach(f => f()); h.visibility('visible'); await flush(); assert.equal(h.calls.length, after)
})
test('actual SFC script/template/style compile', async () => {
  const filename = path.join(base, 'index.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
  assert.deepEqual(errors, []); const script = compileScript(descriptor, { id: filename })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ source: style.content, filename, id: filename, scoped: true })).errors, [])
})
