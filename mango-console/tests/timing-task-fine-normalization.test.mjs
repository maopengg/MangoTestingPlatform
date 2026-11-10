import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/timing/tasks')
function actual(file, dependencies = {}) {
  const exports = {}, source = ts.transpileModule(readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  new Function('exports', 'require', source)(exports, name => { if (name in dependencies) return dependencies[name]; { if (['@/utils/load-error', '@/utils/api-response'].includes(name)) return loadFeedbackModule(name); throw Error('Unexpected dependency ' + name) } })
  return exports
}
const fine = actual(path.join(base, 'fine-tuning.ts'))
const row = (overrides = {}) => ({ id: 0, name: 'Example task', task_group_name: 'Example group', case_types: [1], case_people: { id: 0, name: 'Example owner' }, api_concurrency_limit: 2, report_retention_policy: 'all', ...overrides })
function setup(api = async () => ({ code: 200 })) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, writes = [], messages = []
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['timing.tasks:change'] })
  const route = vue.reactive({ path: '/timing/tasks/index', fullPath: '/timing/tasks/index' })
  const h = harness('TaskFineTuningModal', 'dialog,task,form,saving,saveError,supportsApi,availableUsers,open,save,closeEditor:close', { base,
    props: { userOptions: [{ key: 1, title: 'Another owner' }], retentionOptions: [{ key: 'all', title: '全部保留' }], platformLimit: 8 },
    api: { putSystemTasks: payload => { writes.push(payload); return api(payload) } },
    modules: { vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@arco-design/web-vue': { Message: Object.fromEntries(['error','success'].map(name => [name, value => messages.push([name,value])])) },
    } })
  const shell = { visible: false, loading: false, closed: 0, show() { this.visible = true; return Promise.resolve(true) }, close() { this.visible = false; this.loading = false; this.closed++; return Promise.resolve(false) }, setConfirmLoading(value) { this.loading = value } }
  h.dialog.value = shell
  return { ...h, shell, writes, messages, user, permission, route, callbacks,
    mount() { callbacks.mount.forEach(fn => fn()); callbacks.activate.forEach(fn => fn()) },
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); h.close(); globalThis.document = previous },
  }
}

test('task search and editor factories create independent values, options and ID normalization', () => {
  const config = actual(path.join(base, 'config.ts'), {
    vue, '@arco-design/web-vue': { Message: { error() {} } },
    '@/utils/search-condition': actual('src/utils/search-condition.ts'), '@/utils/id-search': actual('src/utils/id-search.ts', { vue, '@arco-design/web-vue': { Message: { warning() {} } } }),
    '@/utils/update-user': actual('src/utils/update-user.ts', { vue }), '@/hooks/table': actual('src/hooks/table.ts', { vue }),
  })
  const editor = actual(path.join(base, 'task-editor-records.ts'))
  const first = config.createConditionItems(), second = config.createConditionItems(), a = editor.createTaskEditorDraft(), b = editor.createTaskEditorDraft()
  first.find(item => item.key === 'id').value = '5574、5577'; assert.equal(first[0].value, '5574,5577'); assert.equal(second[0].value, '')
  for (const key of ['task_group','status','is_notice']) {
    const field = first.find(item => item.key === key); assert.equal(field.multiple, true); assert.equal(field.searchOperator, 'in')
    field.value.push(0); assert.deepEqual(second.find(item => item.key === key).value, []); field.reset(); assert.deepEqual(field.value, [])
  }
  first.find(item => item.key === 'status').optionItems[0].title = 'Changed'; assert.equal(second.find(item => item.key === 'status').optionItems[0].title, '已开启')
  for (const field of first) { field.value = field.multiple ? [0] : '1'; field.reset(); assert.deepEqual(field.value, field.multiple ? [] : '') }
  a.case_types.push(1); assert.deepEqual(b.case_types, [])
  assert.equal(config.tableColumns.find(column => column.key === 'actions').width, 160)
})
test('fine tuning DTOs copy only independent fields and finite summary, preserving zero and long IDs', () => {
  const source = row({ id: '90071992547409931234', extra: 'omit' }), summary = fine.readFineTuningTask(source), draft = fine.readFineTuning(source)
  assert.equal(summary.id, '90071992547409931234'); assert.equal(draft.case_people, 0); assert.equal('extra' in summary, false)
  summary.case_types.push(2); assert.deepEqual(source.case_types, [1]); assert.equal('name' in draft, false)
  assert.deepEqual(fine.fineTuningPatch(draft, { ...draft, case_people: 1 }), { case_people: 1 })
  assert.equal(fine.validateFineTuning(draft, 8), '')
  for (const value of [null, [], { case_people: {} }, { api_concurrency_limit: '2' }]) assert.throws(() => fine.readFineTuning(value))
  assert.throws(() => fine.assertFineTuningSaved({ code: 403 })); assert.throws(() => fine.readFineTuningTask(row({ id: Number.MAX_SAFE_INTEGER + 1 })))
})
test('open, cancel and reopen isolate draft from original task and preserve an unavailable selected owner label', t => {
  const h = setup(); t.after(h.close); const source = row()
  h.open(source); h.form.api_concurrency_limit = 5; source.name = 'Changed source'
  assert.equal(h.task.value.name, 'Example task'); assert.equal(source.api_concurrency_limit, 2); assert.deepEqual(h.availableUsers.value[0], { key: 0, title: 'Example owner' })
  assert.equal(h.props.userOptions.length, 1); h.closeEditor(); assert.equal(h.task.value, null); assert.equal(h.form.case_people, null)
  h.open(row({ id: 2, api_concurrency_limit: null, case_people: { id: 1, name: 'Another owner' } })); assert.equal(h.form.api_concurrency_limit, null); assert.equal(h.form.case_people, 1)
})
test('save submits only a fixed ID and independent changed fields, ignoring extra data', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close)
  h.open(row()); h.form.case_people = 1; const saving = h.save()
  assert.deepEqual(h.writes, [{ id: 0, case_people: 1 }]); assert.equal(h.saving.value, true)
  await h.save(); assert.equal(h.writes.length, 1); h.form.case_people = 2; assert.equal(h.writes[0].case_people, 1)
  pending.resolve({ code: 200 }); await saving; assert.equal(h.shell.visible, false); assert.equal(h.saving.value, false); assert.deepEqual(h.events, [['saved']])
})
test('selected owner uses the exact form value type without mutating shared options', t => {
  const h = setup(); t.after(h.close); h.open(row({ case_people: { id: '1', name: 'Another owner' } }))
  assert.equal(h.availableUsers.value[0].key, '1'); assert.equal(h.props.userOptions[0].key, 1)
})
test('invalid owner or changed concurrency returns local validation and releases dialog loading', async t => {
  const h = setup(); t.after(h.close); h.open(row()); h.shell.loading = true; h.form.case_people = null
  await h.save(); assert.match(h.saveError.value, /负责人/); assert.equal(h.shell.loading, false); assert.equal(h.writes.length, 0)
  h.form.case_people = 0; h.form.api_concurrency_limit = 9; await h.save(); assert.match(h.saveError.value, /1 到 8/); assert.equal(h.writes.length, 0)
  h.form.api_concurrency_limit = 1.5; await h.save(); assert.equal(h.writes.length, 0)
})
test('unchanged hidden non-API concurrency is omitted when editing the owner', async t => {
  const h = setup(); t.after(h.close); h.open(row({ case_types: [0], api_concurrency_limit: 99 })); h.form.case_people = 1
  assert.equal(h.supportsApi.value, false); await h.save(); assert.deepEqual(h.writes, [{ id: 0, case_people: 1 }])
})
test('no-op save closes without issuing a request', async t => {
  const h = setup(); t.after(h.close); h.open(row()); await h.save(); assert.equal(h.writes.length, 0); assert.equal(h.shell.visible, false); assert.equal(h.events.length, 0)
})
test('network and business-response failure keep the editor and draft available for retry', async t => {
  let mode = 'network'; const h = setup(async () => { if (mode === 'network') throw Error('network'); return { code: mode === 'business' ? 403 : 200 } }); t.after(h.close)
  h.open(row()); h.form.case_people = 1
  for (const value of ['network', 'business']) { mode = value; await h.save(); assert.equal(h.shell.visible, true); assert.equal(h.form.case_people, 1); assert.equal(h.saving.value, false); assert.match(h.saveError.value, /失败/) }
  mode = 'success'; await h.save(); assert.equal(h.shell.visible, false); assert.deepEqual(h.events, [['saved']])
})
test('cancel during save keeps physical lock, emits refresh only for the same identity and does not reopen a window', async t => {
  const pending = deferred(), h = setup(() => pending.promise); t.after(h.close)
  h.open(row()); h.form.case_people = 1; const saving = h.save(); h.closeEditor(); h.open(row({ id: 2 }))
  assert.equal(h.task.value, null); assert.equal(h.saving.value, true); pending.resolve({ code: 200 }); await saving
  assert.equal(h.shell.visible, false); assert.equal(h.messages.filter(([name]) => name === 'success').length, 0); assert.deepEqual(h.events, [['saved']])
  h.open(row({ id: 2 })); assert.equal(h.task.value.id, 2)
})
test('all identity changes close drafts and suppress a prior save response', async () => {
  for (const change of [h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new-session', h => h.user.selected_environment++,
    h => h.permission.permissionKeys = [], h => h.route.fullPath = '/timing/tasks/index?example=1']) {
    const pending = deferred(), h = setup(() => pending.promise)
    try {
      h.open(row()); h.form.case_people = 1; const saving = h.save(); change(h)
      assert.equal(h.shell.visible, false); assert.equal(h.saving.value, true); pending.resolve({ code: 200 }); await saving
      assert.equal(h.saving.value, false); assert.equal(h.events.length, 0); assert.equal(h.messages.filter(([name]) => name === 'success').length, 0)
    } finally { h.close() }
  }
})
test('background, KeepAlive and unmount close the editor without replaying a save', async t => {
  const h = setup(); t.after(h.close); h.mount(); h.open(row()); h.visibility('hidden'); assert.equal(h.shell.visible, false)
  h.open(row()); assert.equal(h.shell.visible, false); h.visibility('visible'); h.open(row()); assert.equal(h.shell.visible, true)
  h.callbacks.deactivate.forEach(fn => fn()); assert.equal(h.shell.visible, false); h.callbacks.activate.forEach(fn => fn()); assert.equal(h.writes.length, 0)
  const pending = deferred(), other = setup(() => pending.promise)
  other.open(row()); other.form.case_people = 1; const request = other.save(); other.close(); pending.resolve({ code: 200 }); await request
  assert.equal(other.events.length, 0); assert.equal(other.saving.value, false)
})
test('malformed task data is rejected without opening an editor', t => {
  const h = setup(); t.after(h.close); h.open({ id: {}, case_people: 1 }); assert.equal(h.task.value, null); assert.equal(h.shell.visible, false)
  assert.equal(h.messages[0][0], 'error')
})
test('main page, fine-tuning and readonly recent-result scripts, templates and styles compile', async () => {
  for (const relative of ['index.vue', 'components/TaskFineTuningModal.vue', 'components/TaskRecentResults.vue']) {
    const filename = path.join(base, relative), { descriptor, errors } = parse(readFileSync(filename, 'utf8')); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: relative }), template = compileTemplate({ source: descriptor.template.content, filename, id: relative, compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ source: style.content, filename, id: relative, scoped: true })).errors, [])
  }
})
