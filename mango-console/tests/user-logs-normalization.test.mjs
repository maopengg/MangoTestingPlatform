import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { deferred, flush, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/system/user-logs')
const ok = (data, totalSize = 1) => ({ code: 200, data, totalSize })
const row = (values = {}) => ({ id: 0, user: { id: 0, name: 'Example', username: 'example@example.com' }, source_type: '0',
  create_time: '2026-11-09 10:00:00', ip: null, url: '/example', method: 'GET', status_code: '0', request_data: '{ "value": 0 }', response_data: 'false', ...values })
function actual(filename, dependencies) {
  const exports = {}, source = ts.transpileModule(readFileSync(filename, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
  new Function('exports', 'require', source)(exports, name => { if (name in dependencies) return dependencies[name]; { if (['@/utils/load-error', '@/utils/api-response'].includes(name)) return loadFeedbackModule(name); throw Error('Unexpected dependency ' + name) } })
  return exports
}
function setup(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, calls = []
  const route = vue.reactive({ path: '/system/user-logs/index', fullPath: '/system/user-logs/index' })
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['system.user_logs:read'] })
  const enums = vue.reactive({ cline_type: [{ key: 0, title: 'Example source' }, { key: 1, title: 'Other' }], colors: ['blue', 'gold'], getEnum: () => { calls.push(['enum']); return overrides.enum?.() ?? Promise.resolve() } })
  const h = harness('index', 'rows,listLoading,listError,userOptions,sourceOptions,userOptionsLoading,sourceOptionsLoading,userOptionsError,sourceOptionsError,pagination,conditionItems,doRefresh,onSearch,onResetSearch,loadUserOptions,loadSourceOptions,buildQuery,sourceTypeText,sourceTypeColor,selectOptions', { base,
    api: { getUserLogs: query => { calls.push(['logs', structuredClone(query)]); return overrides.logs?.(query) ?? Promise.resolve(ok([row()])) },
      getUserName: () => { calls.push(['users']); return overrides.users?.() ?? Promise.resolve(ok([{ key: 0, title: 'Example' }])) } },
    modules: { vue: { ...vue, onMounted: f => callbacks.mount.push(f), onActivated: f => callbacks.activate.push(f), onDeactivated: f => callbacks.deactivate.push(f), onBeforeUnmount: f => callbacks.unmount.push(f) },
      'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@/store/modules/get-enum': { useEnum: () => enums }, '@/hooks/table': actual('src/hooks/table.ts', { vue }), '@/hooks/use-latest-request': actual('src/hooks/use-latest-request.ts', {}) } })
  return { ...h, calls, route, user, permission, enums, callbacks,
    mount() { callbacks.mount.forEach(f => f()); callbacks.activate.forEach(f => f()) },
    visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(f => f()); h.close(); globalThis.document = previous } }
}

test('log DTO preserves raw audit text, zero, long IDs and missing/deleted user without retaining extra user data', t => {
  const h = setup(); t.after(h.close); const m = h.load('log-records.ts'), original = row()
  original.user.extra = 'omit'; const copied = m.parseUserLogRecord(original)
  copied.user.name = 'Changed'; assert.equal(original.user.name, 'Example'); assert.equal('extra' in copied.user, false)
  assert.equal(copied.id, 0); assert.equal(copied.user.id, 0); assert.equal(copied.status_code, '0'); assert.equal(copied.ip, '')
  assert.equal(copied.request_data, '{ "value": 0 }'); assert.equal(copied.response_data, 'false')
  const missing = m.parseUserLogRecord(row({ id: '90071992547409931234', user: null, source_type: null, response_data: null }))
  assert.equal(missing.id, '90071992547409931234'); assert.equal(missing.user, null); assert.equal(missing.source_type, ''); assert.equal(missing.response_data, '')
})
test('invalid and error responses remain failures rather than successful empty logs', t => {
  const h = setup(); t.after(h.close); const m = h.load('log-records.ts')
  for (const value of [{ code: 403, data: [] }, ok({}), ok([row()], '1'), ok([row(), row()], 2), ok([row({ id: Number.MAX_SAFE_INTEGER + 1 })]),
    ok([row({ user: [] })]), ok([row({ request_data: {} })]), ok([row({ status_code: false })]), ok([row()], -1)]) assert.throws(() => m.parseUserLogs(value))
  assert.deepEqual(m.parseUserLogs(ok([], 0)), { rows: [], total: 0 })
})
test('finite source/user options preserve zero, accept MCP source and reject malformed/duplicate keys', t => {
  const h = setup(); t.after(h.close); const m = h.load('log-records.ts')
  assert.deepEqual(m.parseLogOptions([{ key: 0, title: 'Example', extra: 'omit' }, { key: 'MCP', title: 'MCP' }]), [{ key: 0, title: 'Example' }, { key: 'MCP', title: 'MCP' }])
  assert.equal(m.parseUserLogOptions(ok([{ key: '90071992547409931234', title: 'Example' }]))[0].key, '90071992547409931234')
  for (const options of [null, [{ key: false, title: 'Bad' }], [{ key: NaN, title: 'Bad' }], [{ key: 0, title: 'A' }, { key: '0', title: 'B' }], [{ key: 1, title: {} }]]) assert.throws(() => m.parseLogOptions(options))
  assert.throws(() => m.parseUserLogOptions(ok([{ key: 'MCP', title: 'Bad user' }]))); assert.throws(() => m.parseUserLogOptions({ code: 403, data: [] }))
})
test('search instances are independent, all collection filters use __in and reset to arrays', t => {
  const h = setup(); t.after(h.close); const a = h.load('config.ts').createConditionItems(), b = h.load('config.ts').createConditionItems()
  for (const key of ['user', 'source_type', 'method']) {
    const item = a.find(item => item.key === key); assert.equal(item.multiple, true); assert.equal(item.searchOperator, 'in')
    item.value.push(key === 'method' ? 'GET' : 0); assert.deepEqual(b.find(item => item.key === key).value, [])
    item.reset(); assert.deepEqual(item.value, [])
  }
  const url = a.find(item => item.key === 'url'); url.value = '/example'; url.reset(); assert.equal(url.value, '')
})
test('actual form/query mapper preserves zero, method collections and body search verbatim while omitting empties', t => {
  const h = setup(); t.after(h.close)
  for (const [key, value] of Object.entries({ user: [0, '90071992547409931234'], source_type: [0, 'MCP'], method: ['GET', 'POST'], request_data: '  { "x": 0 }  ' })) h.conditionItems.find(item => item.key === key).value = value
  assert.deepEqual(h.buildQuery(), { user__in: '0,90071992547409931234', source_type__in: '0,MCP', method__in: 'GET,POST', request_data: '  { "x": 0 }  ' })
  const m = h.load('log-records.ts'); assert.deepEqual(m.userLogQuery({ url: '/example', method__in: null, response_data: '', unrelated: 4, status_code: '不等于200' }), { url: '/example' })
  assert.throws(() => m.userLogQuery({ request_data: {} }))
})
test('list, users and source reads start independently and coalesce duplicate mount/activation calls', async t => {
  const a = deferred(), b = deferred(), c = deferred(), h = setup({ logs: () => a.promise, users: () => b.promise, enum: () => c.promise }); t.after(h.close)
  h.mount(); const first = h.doRefresh(), users = h.loadUserOptions(), sources = h.loadSourceOptions()
  assert.equal(h.doRefresh(), first); assert.equal(h.loadUserOptions(), users); assert.equal(h.loadSourceOptions(), sources); await flush()
  assert.deepEqual(h.calls.map(([name]) => name), ['logs', 'users', 'enum'])
  a.resolve(ok([row()])); await first; assert.equal(h.listLoading.value, false); assert.equal(h.userOptionsLoading.value, true); assert.equal(h.sourceOptionsLoading.value, true)
  b.resolve(ok([{ key: 0, title: 'Example' }])); await users; assert.equal(h.userOptionsLoading.value, false); assert.equal(h.sourceOptionsLoading.value, true)
  c.resolve(); await sources; assert.equal(h.sourceOptionsLoading.value, false)
})
test('enum failure cannot block list or user options and failed source read retries separately', async t => {
  let n = 0; const h = setup({ enum: async () => { if (++n === 1) throw Error('offline') } }); t.after(h.close)
  h.mount(); await flush(); assert.equal(h.rows.value.length, 1); assert.equal(h.userOptions.value.length, 1); assert.match(h.sourceOptionsError.value, /重试/)
  await h.loadSourceOptions(); assert.equal(h.sourceOptionsError.value, ''); assert.equal(h.sourceTypeText('0'), 'Example source')
  assert.equal(h.calls.filter(([name]) => name === 'logs').length, 1)
})
test('user option failure keeps same-context options, releases local loading and retries without reloading logs', async t => {
  let n = 0; const h = setup({ users: async () => ++n === 2 ? { code: 403 } : ok([{ key: 0, title: 'Example' }]) }); t.after(h.close)
  h.mount(); await flush(); await h.loadUserOptions(); assert.equal(h.userOptions.value.length, 1); assert.match(h.userOptionsError.value, /重试/); assert.equal(h.userOptionsLoading.value, false)
  await h.loadUserOptions(); assert.equal(h.userOptionsError.value, ''); assert.equal(h.calls.filter(([name]) => name === 'logs').length, 1)
})
test('source rendering preserves MCP special style, enum zero and unknown historical values', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush()
  assert.equal(h.sourceTypeText('0'), 'Example source'); assert.equal(h.sourceTypeColor('0'), 'blue')
  assert.equal(h.sourceTypeText('MCP'), 'MCP'); assert.equal(h.sourceTypeColor('MCP'), 'purple')
  assert.equal(h.sourceTypeText('historical-source'), 'historical-source'); assert.equal(h.sourceTypeColor('historical-source'), 'gray'); assert.equal(h.sourceTypeText(null), '-')
})
test('search resets page and latest conditions win over delayed old response', async t => {
  const a = deferred(), b = deferred(); let n = 0; const h = setup({ logs: () => ++n === 1 ? a.promise : b.promise }); t.after(h.close)
  h.mount(); await flush(); h.pagination.page = 4; h.conditionItems.find(item => item.key === 'user').value = [0]
  const latest = h.onSearch(); await flush(); assert.equal(h.calls.filter(([name]) => name === 'logs').at(-1)[1].page, 1)
  b.resolve(ok([row({ id: 2 })])); await latest; a.resolve(ok([row({ id: 1 })])); await flush(); assert.equal(h.rows.value[0].id, 2); assert.equal(h.listLoading.value, false)
})
test('reset empties collections/text, returns first page and uses page/pageSize with no empty keys', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush(); h.pagination.page = 2
  h.conditionItems.find(item => item.key === 'method').value = ['GET']; h.conditionItems.find(item => item.key === 'url').value = '/example'
  await h.onResetSearch(); assert.equal(h.pagination.page, 1)
  assert.deepEqual(h.calls.filter(([name]) => name === 'logs').at(-1)[1], { page: 1, pageSize: 20 })
  for (const item of h.conditionItems) assert.deepEqual(item.value, item.multiple ? [] : '')
})
test('list errors and malformed payload keep same-context rows, finish loading, and allow retry', async t => {
  let n = 0; const h = setup({ logs: async () => { n++; if (n === 2) throw Error('offline'); if (n === 3) return ok({}); return ok([row()]) } }); t.after(h.close)
  h.mount(); await flush(); await h.doRefresh(); assert.equal(h.rows.value.length, 1); assert.match(h.listError.value, /重试/); assert.equal(h.listLoading.value, false)
  await h.doRefresh(); assert.match(h.listError.value, /重试/); await h.doRefresh(); assert.equal(h.listError.value, '')
})
test('page count shrink refetches final valid page, empty data preserves actual total zero', async t => {
  const h = setup({ logs: async () => ok([], 0) }); t.after(h.close); h.mount(); await flush(); h.pagination.page = 3; await h.doRefresh()
  assert.equal(h.pagination.page, 1); assert.equal(h.pagination.pageCount, 0); assert.deepEqual(h.rows.value, [])
  assert.equal(h.calls.filter(([name]) => name === 'logs').at(-1)[1].page, 1)
})
test('all identity and permission dimensions invalidate old reads and clear old filters/options', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush()
  for (const change of [() => h.user.userId++, () => h.user.roleId++, () => { h.user.token = 'next-session' }, () => h.user.selected_environment++, () => h.permission.permissionKeys.push('system.user_logs:change')]) {
    h.conditionItems.find(item => item.key === 'method').value = ['GET']; change()
    assert.deepEqual(h.rows.value, []); assert.deepEqual(h.userOptions.value, []); assert.deepEqual(h.sourceOptions.value, []); assert.deepEqual(h.conditionItems.find(item => item.key === 'method').value, [])
    await flush(); assert.equal(h.rows.value.length, 1)
  }
})
test('late old list and user option results cannot populate a different identity', async t => {
  const list = deferred(), users = deferred(); let n = 0, u = 0
  const h = setup({ logs: () => ++n === 1 ? list.promise : Promise.resolve(ok([row({ id: 2 })])), users: () => ++u === 1 ? users.promise : Promise.resolve(ok([{ key: 2, title: 'New' }])) }); t.after(h.close)
  h.mount(); await flush(); h.user.userId = 2; await flush(); list.resolve(ok([row({ id: 1 })])); users.resolve(ok([{ key: 1, title: 'Old' }])); await flush()
  assert.equal(h.rows.value[0].id, 2); assert.equal(h.userOptions.value[0].key, 2)
})
test('background invalidates all three readers; visible return resumes and old loading cannot overwrite new data', async t => {
  const list = deferred(), users = deferred(), sources = deferred(); let n = 0, u = 0, e = 0
  const h = setup({ logs: () => ++n === 1 ? list.promise : Promise.resolve(ok([row({ id: 2 })])), users: () => ++u === 1 ? users.promise : Promise.resolve(ok([{ key: 2, title: 'New' }])), enum: () => ++e === 1 ? sources.promise : Promise.resolve() }); t.after(h.close)
  h.mount(); await flush(); h.visibility('hidden'); assert.equal(h.listLoading.value, false); assert.equal(h.userOptionsLoading.value, false); assert.equal(h.sourceOptionsLoading.value, false)
  h.visibility('visible'); await flush(); list.resolve(ok([row({ id: 1 })])); users.resolve(ok([{ key: 1, title: 'Old' }])); sources.resolve(); await flush()
  assert.equal(h.rows.value[0].id, 2); assert.equal(h.userOptions.value[0].key, 2); assert.equal(h.listLoading.value, false)
})
test('KeepAlive pause keeps visible data, does not fetch while inactive, then resumes needed reads on activation', async t => {
  const h = setup(); t.after(h.close); h.mount(); await flush(); const before = h.calls.length
  h.callbacks.deactivate.forEach(f => f()); await h.doRefresh(); await h.loadUserOptions(); await h.loadSourceOptions(); assert.equal(h.calls.length, before); assert.equal(h.rows.value.length, 1)
  h.callbacks.activate.forEach(f => f()); await flush(); assert.equal(h.calls.length, before + 3)
})
test('route leave and unmount invalidate scheduled/inflight requests and cannot revive old logs', async t => {
  const request = deferred(); const h = setup({ logs: () => request.promise }); t.after(h.close); h.mount(); await flush()
  h.route.path = '/index/home'; h.route.fullPath = '/index/home'; const before = h.calls.length
  await h.doRefresh(); request.resolve(ok([row()])); await flush(); assert.deepEqual(h.rows.value, []); assert.equal(h.calls.length, before)
  h.callbacks.unmount.forEach(f => f()); h.visibility('visible'); await flush(); assert.equal(h.calls.length, before)
})
test('invalid search prevents stale request writes and can recover through reset', async t => {
  const request = deferred(); let n = 0; const h = setup({ logs: () => ++n === 1 ? request.promise : Promise.resolve(ok([row({ id: 2 })])) }); t.after(h.close)
  h.mount(); await flush(); h.conditionItems.find(item => item.key === 'url').value = {}
  await h.onSearch(); assert.match(h.listError.value, /条件格式/); request.resolve(ok([row({ id: 1 })])); await flush(); assert.deepEqual(h.rows.value, [])
  await h.onResetSearch(); assert.equal(h.rows.value[0].id, 2); assert.equal(h.listError.value, '')
})
test('actual SFC scripts, template and scoped style compile', async () => {
  const filename = path.join(base, 'index.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
  assert.deepEqual(errors, []); const script = compileScript(descriptor, { id: filename })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ source: style.content, filename, id: filename, scoped: true })).errors, [])
})
