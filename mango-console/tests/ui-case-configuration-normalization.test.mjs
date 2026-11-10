import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync, mkdtempSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import ts from 'typescript'
import * as vue from 'vue'
import * as jsonc from 'jsonc-parser'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { deferred, flush, method } from './helpers/case-details-harness.mjs'

const base = 'src/views/uitest/case/details', assets = loadModule('src/components/business/ui-case-step-create.ts')
const lossless = loadModule('src/utils/lossless-json.ts', { 'jsonc-parser': jsonc })
const configuration = loadModule(`${base}/case-configuration.ts`, { '@/components/business/ui-case-step-create': assets, '@/utils/lossless-json': lossless })
const long = '90071992547409930000'
const row = (values = {}) => ({ id: 0, name: 'Example case', project_product: { id: 0, name: 'Example product' }, front_custom: [{ key: 'example', value: null, test_envs: [0] }], front_sql: [{ sql: { index: 'example', query: { match_all: {} } }, key_list: ['data'], datasource_alias: long, test_envs: [] }], posterior_sql: [], front_public: [0], front_auth_config: [], update_user: { id: 9 }, ...values })
const response = (values = {}) => ({ code: 200, data: [row(values)] })
function setup(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = [], writes = [], messages = []
  const state = vue.reactive({ caseId: 0 }), route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] })
  const module = loadModule(`${base}/composables/useUiCaseConfiguration.ts`, {
    vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
    'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
    '@/components/business/ui-case-step-create': assets, '@/utils/lossless-json': lossless, '../case-configuration': configuration,
    '@/api/uitest/case': { getUiCase: (...args) => { reads.push(args); return overrides.read ? overrides.read(...args) : Promise.resolve(response({ id: args[0].id })) }, putUiCase: (...args) => { writes.push(args); return overrides.write ? overrides.write(...args) : Promise.resolve({ code: 200 }) } },
    '@arco-design/web-vue': { Message: { success: message => messages.push(message) } },
  })
  const scope = vue.effectScope(), h = scope.run(() => module.useUiCaseConfiguration(() => state.caseId))
  return { ...h, state, route, user, permission, callbacks, reads, writes, messages,
    mount() { callbacks.mount.forEach(fn => fn()) }, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); scope.stop(); globalThis.document = previous },
  }
}
test('configuration DTOs whitelist fields, clone SQL/JSON, preserve null/zero/long IDs and reject wrong records', () => {
  const source = response(), result = configuration.readUiCaseConfigurationRecord(source, 0)
  assert.equal(result.front_custom[0].value, null); assert.equal(result.front_sql[0].datasource_alias, long); assert.equal(result.project_product.id, 0); assert.equal(result.update_user, undefined)
  result.front_sql[0].sql.query.changed = true; assert.equal(source.data[0].front_sql[0].sql.query.changed, undefined)
  assert.deepEqual(Object.keys(configuration.uiCaseConfigurationPayload(result, result, 'globals')), ['id', 'front_public', 'front_auth_config'])
  assert.deepEqual(Object.keys(configuration.uiCaseConfigurationPayload(result, result, 'all')), ['id', 'name', 'front_custom', 'front_sql', 'posterior_sql', 'front_public', 'front_auth_config'])
  assert.throws(() => configuration.readUiCaseConfigurationRecord(response({ id: 2 }), 0)); assert.throws(() => configuration.readUiCaseConfigurationRecord({ code: 200, data: [] }, 0)); assert.throws(() => configuration.readUiCaseConfiguration(row({ front_sql: [{ sql: 3 }] })))
})
test('context IDs retain explicit zero and long strings, block malformed explicit values and read only bootstrap ID', () => {
  assert.equal(configuration.firstUiCaseContextId('', 0, 9), 0); assert.equal(configuration.firstUiCaseContextId([long]), long); assert.equal(configuration.firstUiCaseContextId('bad', 9), null)
  assert.equal(configuration.bootstrapUiCaseContextId({ id: 0, token: 'example' }), 0); assert.equal(configuration.bootstrapUiCaseContextId(null), null)
})
test('load provides independent record/draft/baseline and deduplicates concurrent reads', async t => {
  const pending = deferred(), h = setup({ read: () => pending.promise }); t.after(h.close)
  const first = h.load(), second = h.load(false); assert.equal(first, second); await flush(); assert.equal(h.reads.length, 1); assert.equal(h.loading.value, true)
  pending.resolve(response()); assert.equal(await first, true); assert.equal(h.loading.value, false); assert.equal(h.dirty.value, false)
  assert.deepEqual(Object.keys(h.draft), ['front_custom', 'front_sql', 'posterior_sql', 'front_public', 'front_auth_config'])
  h.draft.front_sql[0].sql.query.new = true; assert.equal(h.record.value.front_sql[0].sql.query.new, undefined); assert.equal(h.dirty.value, true)
})
test('polling updates clean configuration but preserves dirty drafts and current metadata', async t => {
  let name = 'First'; const h = setup({ read: async () => response({ name, front_custom: [{ key: 'key', value: name }] }) }); t.after(h.close)
  await h.load(); name = 'Second'; await h.load(false); assert.equal(h.draft.front_custom[0].value, 'Second')
  h.draft.front_custom[0].value = 'Local'; name = 'Third'; await h.load(false)
  assert.equal(h.record.value.name, 'Third'); assert.equal(h.record.value.front_custom[0].value, 'Third'); assert.equal(h.draft.front_custom[0].value, 'Local'); assert.equal(h.dirty.value, true)
})
test('load failure/invalid response retains current draft, releases loading and can retry', async t => {
  let fail = false; const h = setup({ read: async () => fail ? { code: 403 } : response() }); t.after(h.close); await h.load(); h.draft.front_custom[0].value = 'Local'
  fail = true; assert.equal(await h.load(), false); assert.match(h.loadError.value, /失败/); assert.equal(h.loading.value, false); assert.equal(h.draft.front_custom[0].value, 'Local')
  fail = false; assert.equal(await h.load(), true); assert.equal(h.loadError.value, ''); assert.equal(h.draft.front_custom[0].value, 'Local')
})
test('save freezes submission before microtasks, preserves later edits and sends finite payload with original ID', async t => {
  const pending = deferred(), h = setup({ write: () => pending.promise }); t.after(h.close); await h.load(); h.draft.front_custom[0].value = 'Submitted'
  const saving = h.save(); h.draft.front_custom[0].value = 'Later'; await flush()
  assert.equal(h.writes[0][0].front_custom[0].value, 'Submitted'); assert.equal(h.writes[0][0].id, 0); assert.equal(h.saving.value, true); assert.equal(h.record.value.front_custom[0].value, null)
  pending.resolve({ code: 200 }); assert.equal(await saving, true); assert.equal(h.draft.front_custom[0].value, 'Later'); assert.equal(h.record.value.front_custom[0].value, 'Submitted'); assert.equal(h.dirty.value, true)
})
test('duplicate saves serialize and skip unchanged requests while changed queued drafts retain their own snapshot', async t => {
  const first = deferred(), second = deferred(); let count = 0
  const h = setup({ write: () => ++count === 1 ? first.promise : second.promise }); t.after(h.close); await h.load(); h.draft.front_custom[0].value = 'First'
  const saving = h.save(); const duplicate = h.save(); assert.equal(saving, duplicate); await flush(); assert.equal(h.writes.length, 1)
  h.draft.front_custom[0].value = 'Second'; const queued = h.save(); h.draft.front_custom[0].value = 'Third'
  first.resolve({ code: 200 }); await flush(); assert.equal(h.writes.length, 2); assert.equal(h.writes[1][0].front_custom[0].value, 'Second'); assert.equal(h.saving.value, true)
  second.resolve({ code: 200 }); assert.equal(await queued, true); assert.equal(h.saving.value, false); assert.equal(h.draft.front_custom[0].value, 'Third'); assert.equal(h.messages.length, 1)
})
test('global save submits only selections and leaves other dirty fields unsaved', async t => {
  const h = setup(); t.after(h.close); await h.load(); h.draft.front_custom[0].value = 'Local'; h.draft.front_public = [0, long]
  assert.equal(await h.save('globals'), true); assert.deepEqual(h.writes[0][0], { id: 0, front_public: [0, long], front_auth_config: [] })
  assert.equal(h.draft.front_custom[0].value, 'Local'); assert.equal(h.record.value.front_custom[0].value, null); assert.equal(h.dirty.value, true)
  assert.equal(await h.save(), true); assert.equal(h.dirty.value, false)
})
test('save network/non-success failure retains draft and drops queued writes until explicit retry', async t => {
  const pending = deferred(); let fail = true; const h = setup({ write: () => fail ? pending.promise : Promise.resolve({ code: 200 }) }); t.after(h.close); await h.load(); h.draft.front_custom[0].value = 'First'
  const saving = h.save(); await flush(); h.draft.front_custom[0].value = 'Second'; h.save(); pending.reject(Error('network'))
  assert.equal(await saving, false); assert.equal(h.writes.length, 1); assert.equal(h.saving.value, false); assert.equal(h.dirty.value, true); assert.match(h.saveError.value, /失败/); assert.deepEqual(h.messages, [])
  fail = false; assert.equal(await h.save(), true); assert.equal(h.writes[1][0].front_custom[0].value, 'Second'); assert.equal(h.saveError.value, ''); assert.equal(h.dirty.value, false)
})
test('old GET started during save cannot roll back accepted configuration after save completes', async t => {
  const pendingWrite = deferred(), pendingRead = deferred(); let reads = 0
  const h = setup({ write: () => pendingWrite.promise, read: () => ++reads === 1 ? Promise.resolve(response()) : pendingRead.promise }); t.after(h.close)
  await h.load(); h.draft.front_custom[0].value = 'Saved'; const saving = h.save(); await flush(); const loading = h.load(false); await flush()
  pendingWrite.resolve({ code: 200 }); assert.equal(await saving, true); assert.equal(h.dirty.value, false)
  pendingRead.resolve(response()); assert.equal(await loading, false); assert.equal(h.draft.front_custom[0].value, 'Saved'); assert.equal(h.record.value.front_custom[0].value, 'Saved')
})
test('buffered database JSON keeps row identity during polling and blocks full save without blocking global selections', async t => {
  const h = setup(); t.after(h.close); await h.load(); const operation = h.draft.front_sql[0]
  h.operationDraftChanged(operation, true); assert.equal(h.dirty.value, true); await h.load(false); assert.equal(h.draft.front_sql[0], operation)
  assert.equal(await h.save(), false); assert.match(h.saveError.value, /未提交/); assert.deepEqual(h.writes, [])
  h.draft.front_public = [long]; assert.equal(await h.save('globals'), true); assert.equal(h.dirty.value, true); assert.deepEqual(Object.keys(h.writes[0][0]), ['id', 'front_public', 'front_auth_config'])
  h.operationDraftChanged(operation, false); assert.equal(h.dirty.value, false)
})
test('shared database editor reports pending JSON until valid commit and leaves invalid text uncommitted', () => {
  const file = path.resolve('src/components/forms/DataSourceOperationList.vue'), events = [], item = { sql: { index: 'example', query: {} } }, operationDrafts = vue.ref(new Map())
  const props = { operationField: 'sql', onOperationDraftChange: (...args) => events.push(args) }
  const input = method('onOperationInput', { props, operationDrafts, isElasticsearch: () => true }, file)
  const text = method('operationText', { props, operationDrafts }, file)
  const config = method('operationConfig', { operationText: text, isElasticsearch: () => true }, file)
  const commit = method('commitOperationValue', { props, operationDrafts, operationConfig: config }, file)
  input(item, '{', 0); assert.equal(events[0][1], true); assert.throws(() => commit(item)); assert.equal(events.length, 1); assert.deepEqual(item.sql, { index: 'example', query: {} })
  input(item, '{"index":"example","query":{"match_all":{}}}', 0); commit(item); assert.equal(events.at(-1)[1], false); assert.deepEqual(item.sql, { index: 'example', query: { match_all: {} } })
})
test('non-success save response never changes baseline or reports success', async t => {
  const h = setup({ write: async () => ({ code: 403 }) }); t.after(h.close); await h.load(); h.draft.front_custom[0].value = 'Local'
  assert.equal(await h.save(), false); assert.equal(h.record.value.front_custom[0].value, null); assert.equal(h.dirty.value, true); assert.equal(h.saving.value, false); assert.deepEqual(h.messages, [])
})
const changes = [h => h.state.caseId = 2, h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/other', h => h.route.fullPath += '&other=1', h => { h.state.caseId = 2; h.state.caseId = 0 }]
test('identity/context changes clear private drafts and reject old read including A-B-A', async () => {
  for (const change of changes) {
    const old = deferred(); let reads = 0; const h = setup({ read: params => ++reads === 1 ? old.promise : Promise.resolve(response({ id: params.id, name: 'New' })) })
    try { const loading = h.load(); await flush(); change(h); old.resolve(response()); assert.equal(await loading, false); await flush(); assert.notEqual(h.record.value?.name, 'Example case'); assert.equal(h.loading.value, false) } finally { h.close() }
  }
})
test('identity/context changes keep physical save lock and suppress old success and queued writes', async () => {
  for (const change of changes) {
    const pending = deferred(), h = setup({ write: () => pending.promise })
    try { await h.load(); h.draft.front_custom[0].value = 'Save'; const saving = h.save(); await flush(); change(h); await flush(); assert.equal(h.saving.value, true); assert.equal(await h.save(), false); pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.equal(h.saving.value, false); assert.equal(h.writes.length, 1); assert.deepEqual(h.messages, []) } finally { h.close() }
  }
})
test('background and KeepAlive preserve unsaved draft, pause feedback and resume silent reads', async () => {
  for (const leave of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn())]) {
    const pending = deferred(), h = setup({ write: () => pending.promise })
    try { h.mount(); await h.load(); h.draft.front_custom[0].value = 'Local'; const saving = h.save(); await flush(); leave(h); pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.deepEqual(h.messages, []); assert.equal(h.draft.front_custom[0].value, 'Local'); h.visibility('visible'); h.callbacks.activate.forEach(fn => fn()); await flush(); assert.equal(h.draft.front_custom[0].value, 'Local'); assert.equal(h.loading.value, false) } finally { h.close() }
  }
})
test('unmount discards private data and invalidates in-flight responses', async t => {
  const pending = deferred(), h = setup({ write: () => pending.promise }); t.after(h.close); await h.load(); h.draft.front_custom[0].value = 'Local'; const saving = h.save(); await flush()
  h.callbacks.unmount.forEach(fn => fn()); assert.equal(h.record.value, null); assert.deepEqual(h.draft.front_custom, []); pending.resolve({ code: 200 }); assert.equal(await saving, false); assert.deepEqual(h.messages, [])
})
test('parent optional/default selections match numeric/string IDs, deduplicate and retain zero', () => {
  const file = path.resolve(base, 'index.vue'), filter = method('filterOptionalOptionValues', {}, file), merge = method('mergeCheckedOptionValues', {}, file)
  assert.deepEqual(filter([0, long, '2'], [{ value: '0', disabled: true }, { value: 2, disabled: true }]), [long])
  assert.deepEqual(merge([0, '0', long], [{ value: 0, disabled: true }, { value: 2, disabled: false }]), [0, long])
})
test('parent uses private draft/load/save workflow and compiles actual template without shared page record writes', () => {
  const filename = path.resolve(base, 'index.vue'), source = readFileSync(filename, 'utf8'), { descriptor, errors } = parse(source); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'case-configuration' }), template = compileTemplate({ source: descriptor.template.content, filename, id: 'case-configuration', compilerOptions: { bindingMetadata: script.bindings } }); assert.deepEqual(template.errors, [])
  assert.match(source, /:data-list="caseDraft.front_custom"/); assert.match(source, /caseConfigurationSaveError/); assert.match(source, /saveCaseConfiguration\('globals'\)/); assert.doesNotMatch(source, /pageData\.record|setRecord\(/)
})
test('finite SQL item types satisfy the actual shared database editor prop contract', () => {
  const source = parse(readFileSync('src/components/forms/DataSourceOperationList.vue', 'utf8')).descriptor.scriptSetup.content
  const tree = ts.createSourceFile('component.ts', source, ts.ScriptTarget.Latest, true), declaration = tree.statements.find(node => ts.isInterfaceDeclaration(node) && node.name.text === 'DataSourceOperationItem')
  const directory = mkdtempSync(path.join(tmpdir(), 'ui-case-sql-prop-')), filename = path.join(directory, 'contract.ts')
  try {
    writeFileSync(filename, `import type { UiCaseFrontSqlItem, UiCasePosteriorSqlItem } from ${JSON.stringify(path.resolve('src/types/ui-test/case'))}\n${declaration.getText(tree)}\ndeclare const frontRows: UiCaseFrontSqlItem[]\ndeclare const posteriorRows: UiCasePosteriorSqlItem[]\nconst front: DataSourceOperationItem[] = frontRows\nconst posterior: DataSourceOperationItem[] = posteriorRows\n`)
    const program = ts.createProgram([filename], { noEmit: true, skipLibCheck: true, strictNullChecks: true, moduleResolution: ts.ModuleResolutionKind.NodeJs, target: ts.ScriptTarget.ES2022, baseUrl: process.cwd(), paths: { '@/*': ['src/*'] } })
    const diagnostics = ts.getPreEmitDiagnostics(program).filter(value => value.file?.fileName === filename)
    assert.equal(diagnostics.length, 0, ts.formatDiagnosticsWithColorAndContext(diagnostics, { getCurrentDirectory: () => process.cwd(), getCanonicalFileName: value => value, getNewLine: () => '\n' }))
  } finally { rmSync(directory, { recursive: true, force: true }) }
})
