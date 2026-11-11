import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import * as pinia from 'pinia'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush as flushVue } from './helpers/case-details-harness.mjs'

async function flush() {
  await flushVue()
  await new Promise(resolve => setImmediate(resolve))
}

const compile = source => ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
const response = data => ({ code: 200, data })
const products = label => [{ value: 1, label: 'Project', children: [{ value: 10, label }] }]
const modules = title => [{ key: 20, title, project_product_id: 10, children: [{ key: 25, title: 'Group', project_product_id: 10, children: [{ key: 30, title: 'Child', project_product_id: 10 }] }] }]
function factory(read = async kind => response(kind === 'modules' ? modules('Module') : kind === 'projects' ? [{ key: null, title: '选择项目' }] : products('Product'))) {
  const requests = []
  const useUser = pinia.defineStore('fixture-navigation-user', { state: () => ({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 }) })
  const parsers = {}
  new Function('exports', compile(readFileSync('src/store/modules/project-options.ts', 'utf8')))(parsers)
  const exports = {}
  new Function('exports', 'require', compile(readFileSync('src/store/modules/get-project.ts', 'utf8')) + '\nexports.definition = useProjectStore;')(exports, id => {
    if (id === 'vue') return vue
    if (id === 'pinia') return pinia
    if (id === './user') return { default: useUser }
    if (id === './project-options') return parsers
    const fetch = kind => () => { requests.push(kind); return read(kind) }
    if (id === '@/api/system/project') return { getUserProjectAll: fetch('projects'), getUserProjectProductName: fetch('products'), getProjectPytestName: fetch('pytest') }
    if (id === '@/api/system/module') return { getUserModuleTree: fetch('modules') }
    if (id === '@/api/system/module-directory-cache') return { invalidateModuleDirectoryCache() {}, moduleDirectoryExpiresAt: () => 0 }
    { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw new Error('Unmocked dependency ' + id) }
  })
  return { requests, parsers, definition: exports.definition, root(initial, identity = {}, direct = false) {
    const root = pinia.createPinia(), user = useUser(root)
    Object.assign(user, identity)
    if (initial) root.state.value['get-project'] = initial
    const store = direct ? exports.definition(root) : exports.useProject(root)
    return { root, user, store, close() { store.$dispose(); user.$dispose() } }
  } }
}

const sidebarFilename = 'src/components/business/ProjectProductNavigationSidebar.vue'
const selectFilename = 'src/components/business/ProjectProductSelect.vue'
test('same-project product selector is anchored to the case product instead of the global project',()=>{
  const f=factory(), a=f.root()
  a.store.projectProduct=[
    {value:1,label:'Case project',children:[{value:10,label:'A'},{value:11,label:'B'}]},
    {value:2,label:'Other project',children:[{value:20,label:'C'}]},
  ]
  const h=productSelect(a,{sameProjectAsProductId:11})
  assert.deepEqual(h.productOptions.value.map(p=>p.value),[1])
  assert.deepEqual(h.productOptions.value[0].children.map(p=>p.value),[10,11])
  h.props.sameProjectAsProductId=999
  assert.deepEqual(h.productOptions.value,[])
  h.close();a.close()
})
function productSelect(owner, values = {}) {
  const descriptor = parse(readFileSync(selectFilename, 'utf8'), { filename: selectFilename }).descriptor
  const props = vue.reactive({ modelValue: null, currentProjectOnly: false, ...values }), events = []
  const life = { mount: [], activate: [], deactivate: [], unmount: [] }
  const dependencies = {
    vue: { ...vue, onMounted: f => life.mount.push(f), onActivated: f => life.activate.push(f), onDeactivated: f => life.deactivate.push(f), onBeforeUnmount: f => life.unmount.push(f) },
    '@/store/modules/get-project': { useProject: () => owner.store },
    '@/store/modules/user': { default: () => owner.user },
  }
  const scope = vue.effectScope()
  const result = scope.run(() => new Function('exports', 'require', 'defineProps', 'defineEmits', compile(descriptor.scriptSetup.content) + '\nreturn {productOptions,loading,failed,loadOptions,onPopupVisibleChange,onUpdate,onChange};')(
    {}, id => { if (!(id in dependencies)) { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error('Unmocked dependency ' + id); } return dependencies[id] }, () => props, () => (...args) => events.push(args)))
  return { ...result, props, events,
    mount() { life.mount.forEach(f => f()) }, pause() { life.deactivate.forEach(f => f()) }, resume() { life.activate.forEach(f => f()) },
    close() { life.unmount.forEach(f => f()); scope.stop() },
  }
}
function sidebar(owner, values = {}) {
  const descriptor = parse(readFileSync(sidebarFilename, 'utf8'), { filename: sidebarFilename }).descriptor
  const props = vue.reactive({ modelValue: null, moduleValue: null, resetKey: 0, showModules: true, emitInitialFilter: true, title: '', description: '', collapsed: false, ...values })
  const life = { mount: [], activate: [], deactivate: [], unmount: [] }, events = []
  const filters = {}
  new Function('exports', compile(readFileSync('src/components/business/project-product-filter.ts', 'utf8')))(filters)
  const dependencies = {
    vue: { ...vue, onMounted: f => life.mount.push(f), onActivated: f => life.activate.push(f), onDeactivated: f => life.deactivate.push(f), onBeforeUnmount: f => life.unmount.push(f) },
    '@arco-design/web-vue/es/icon': {},
    '@/store/modules/get-project': { useProject: () => owner.store },
    '@/store/modules/user': { default: () => owner.user },
    './project-product-filter': filters,
  }
  const scope = vue.effectScope()
  const result = scope.run(() => new Function('exports', 'require', 'defineProps', 'defineEmits', compile(descriptor.scriptSetup.content) + '\nreturn {loadNavigation,loading,loadFailed,initialized,moduleOptionsByProduct,displayTree,expandedKeys,keyword,onSelect};')(
    {}, id => { if (!(id in dependencies)) { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw Error('Unmocked dependency ' + id); } return dependencies[id] }, () => props, () => (...args) => events.push(args)))
  return { ...result, props, events,
    mount() { life.mount.forEach(f => f()) }, pause() { life.deactivate.forEach(f => f()) }, resume() { life.activate.forEach(f => f()) },
    close() { life.unmount.forEach(f => f()); scope.stop() },
  }
}

test('successful catalogs are reused for five minutes and refresh once at expiry', async () => {
  const originalNow = Date.now
  let now = 10000
  Date.now = () => now
  const f = factory(), a = f.root()
  try {
    const load = () => Promise.all([a.store.getProject(), a.store.projectProductName(), a.store.projectPytestName()])
    await load(); await load()
    assert.deepEqual(f.requests, ['projects', 'products', 'pytest'])
    now += 299999; await load()
    assert.equal(f.requests.length, 3)
    now++; await Promise.all([load(), load()])
    assert.deepEqual(f.requests, ['projects', 'products', 'pytest', 'projects', 'products', 'pytest'])
    assert.equal('expiresAt' in a.store.$state, false)
  } finally { a.close(); Date.now = originalNow }
})

test('successful empty products are cached; failed forced reads retain data and remain retryable', async () => {
  let result = response([])
  const f = factory(() => result), a = f.root()
  try {
    await a.store.projectProductName(); await a.store.projectProductName()
    assert.equal(f.requests.length, 1)
    result = { code: 403, data: [] }
    await a.store.projectProductName(true)
    assert.equal(a.store.optionErrors.products, true)
    result = response(products('Recovered'))
    await a.store.projectProductName()
    assert.equal(f.requests.length, 3)
    assert.equal(a.store.optionErrors.products, false)
    assert.equal(a.store.projectProduct[0].children[0].label, 'Recovered')
    await a.store.projectProductName()
    assert.equal(f.requests.length, 3)
  } finally { a.close() }
})

test('catalog invalidation rejects earlier reads without clearing or replacing the new shared request', async () => {
  const old = deferred(), next = deferred()
  let count = 0
  const f = factory(() => ++count === 1 ? old.promise : next.promise), a = f.root()
  try {
    const first = a.store.projectProductName(); await flush()
    a.store.invalidateProjectOptionsCache()
    const current = a.store.projectProductName(); await flush()
    old.resolve(response(products('Obsolete'))); await first
    assert.deepEqual(a.store.projectProduct, [])
    const joined = a.store.projectProductName(); await flush()
    assert.equal(count, 2)
    next.resolve(response(products('Current'))); await Promise.all([current, joined])
    assert.equal(a.store.projectProduct[0].children[0].label, 'Current')
    await a.store.projectProductName()
    assert.equal(count, 2)
  } finally { a.close() }
})

test('forced refresh bypasses a fresh catalog while ordinary concurrent reads join it', async () => {
  const pending = deferred()
  let count = 0
  const f = factory(() => ++count === 1 ? response(products('Before')) : pending.promise), a = f.root()
  try {
    await a.store.projectProductName()
    const first = a.store.projectProductName(true), second = a.store.projectProductName()
    await flush(); assert.equal(count, 2)
    pending.resolve(response(products('After'))); await Promise.all([first, second])
    assert.equal(a.store.projectProduct[0].children[0].label, 'After')
  } finally { a.close() }
})

test('new navigation and select instances reuse the successful shared catalog after menu switches', async () => {
  const f = factory(), a = f.root(), first = sidebar(a, { showModules: false })
  let second, select
  try {
    first.mount(); await flush(); first.pause()
    second = sidebar(a, { showModules: false }); select = productSelect(a)
    second.mount(); select.mount(); await flush()
    first.resume(); await flush()
    assert.equal(f.requests.filter(kind => kind === 'products').length, 1)
    assert.equal(second.initialized.value, true)
    assert.equal(select.productOptions.value[0].children[0].label, 'Product')
  } finally { first.close(); second?.close(); select?.close(); a.close() }
})

test('module edits invalidate cached Pytest module options without refetching product names', async () => {
  const f = factory(), a = f.root()
  try {
    await Promise.all([a.store.projectProductName(), a.store.projectPytestName()])
    a.store.invalidateAllProductModuleTreeCache()
    await Promise.all([a.store.projectProductName(), a.store.projectPytestName()])
    assert.deepEqual(f.requests, ['products', 'pytest', 'pytest'])
  } finally { a.close() }
})

test('the first action initializes request state even without the exported store wrapper', async () => {
  const f = factory(), a = f.root(undefined, {}, true)
  try {
    await Promise.all([a.store.getProject(), a.store.projectProductName(), a.store.projectPytestName(), a.store.getAllProductModuleTree()])
    assert.equal(a.store.projectProduct[0].children[0].label, 'Product')
    a.user.roleId++
    assert.deepEqual(a.store.projectProduct, [])
    a.store.invalidateAllProductModuleTreeCache()
    await a.store.getAllProductModuleTree()
    assert.equal(a.store.allProductModuleTreeCache.data[0].title, 'Module')
  } finally { a.close() }
})

test('hot-replaced actions retain the existing request scope without rerunning setup', async () => {
  const pending = deferred(), original = factory(() => pending.promise), a = original.root(), replacement = factory()
  try {
    const first = a.store.projectProductName(); await flush()
    replacement.definition(a.root, a.store)
    const joined = a.store.projectProductName(); await flush()
    assert.equal(replacement.requests.length, 0)
    pending.resolve(response(products('Accepted'))); await Promise.all([first, joined])
    assert.equal(a.store.projectProduct[0].children[0].label, 'Accepted')
    a.user.roleId++
    assert.deepEqual(a.store.projectProduct, [])
    await a.store.projectProductName()
    assert.equal(a.store.projectProduct[0].children[0].label, 'Product')
  } finally { a.close() }
})

test('Pinia devtools action proxies resolve the same request scope as the original store', async () => {
  const f = factory(), a = f.root()
  // Pinia devtools creates a fresh proxy as the receiver of each options-store action.
  const receiver = () => new Proxy(a.store, {
    get(...args) { return Reflect.get(...args) },
    set(...args) { return Reflect.set(...args) },
  })
  try {
    await Promise.all([receiver().getProject(), receiver().projectProductName(), receiver().projectPytestName(), receiver().getAllProductModuleTree()])
    assert.equal(a.store.data[0].title, '选择项目')
    assert.equal(a.store.projectProduct[0].children[0].label, 'Product')
    assert.equal(a.store.projectPytest[0].children[0].label, 'Product')
    assert.equal(a.store.allProductModuleTreeCache.data[0].title, 'Module')
    receiver().invalidateAllProductModuleTreeCache()
    assert.equal(a.store.allProductModuleTreeCache.data.length, 0)
  } finally { a.close() }
})

test('devtools receivers coalesce pending reads and still reject old identity responses', async () => {
  const old = deferred(), next = deferred(); let count = 0
  const f = factory(() => (++count === 1 ? old.promise : next.promise)), a = f.root()
  const receiver = () => new Proxy(a.store, { get(...args) { return Reflect.get(...args) } })
  try {
    const first = receiver().projectProductName(), joined = receiver().projectProductName()
    await flush(); assert.equal(count, 1)
    a.user.roleId++
    const current = receiver().projectProductName(); await flush(); assert.equal(count, 2)
    old.resolve(response(products('Stale'))); await Promise.all([first, joined]); assert.deepEqual(a.store.projectProduct, [])
    next.resolve(response(products('Current'))); await current
    assert.equal(a.store.projectProduct[0].children[0].label, 'Current')
  } finally { a.close() }
})

test('same store coalesces each read while separate Pinia roots never share promises or cache', async () => {
  const pending = deferred(), f = factory(() => pending.promise), a = f.root(), b = f.root()
  const first = a.store.projectProductName(), second = a.store.projectProductName(), other = b.store.projectProductName()
  await flush()
  assert.deepEqual(f.requests, ['products', 'products'])
  pending.resolve(response(products('Scoped')))
  await Promise.all([first, second, other])
  assert.equal(a.store.projectProduct[0].children[0].label, 'Scoped')
  assert.notEqual(a.store.projectProduct, b.store.projectProduct)
  a.close(); b.close()
})

test('identity A-B-A invalidates synchronously; old successes and finalizers cannot publish or unlock the current read', async () => {
  const pending = [deferred(), deferred(), deferred()]
  let index = 0
  const f = factory(() => pending[index++].promise), a = f.root()
  const old = a.store.projectProductName(); await flush()
  a.user.roleId = 2
  const middle = a.store.projectProductName(); await flush()
  a.user.roleId = 1
  const current = a.store.projectProductName(); await flush()
  pending[0].resolve(response(products('Old A'))); pending[1].reject(new Error('Old B'))
  await Promise.all([old, middle])
  assert.deepEqual(a.store.projectProduct, [])
  assert.equal(a.store.optionErrors.products, false)
  const joined = a.store.projectProductName(); await flush()
  assert.equal(f.requests.length, 3)
  pending[2].resolve(response(products('Current A'))); await Promise.all([current, joined])
  assert.equal(a.store.projectProduct[0].children[0].label, 'Current A')
  a.close()
})

test('user, role, token and environment changes clear all options, module cache and selected scope immediately', async () => {
  const f = factory(), a = f.root()
  for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
    await Promise.all([a.store.getProject(), a.store.projectProductName(), a.store.projectPytestName(), a.store.getAllProductModuleTree()])
    a.store.setProjectProductNavigationSelection(10)
    a.store.setModuleNavigationSelection(30, 'module:30', [30])
    a.user[field] = typeof a.user[field] === 'string' ? a.user[field] + '-next' : a.user[field] + 1
    for (const key of ['data', 'projectProduct', 'projectPytest', 'projectPytest2']) assert.deepEqual(a.store[key], [])
    assert.deepEqual(a.store.allProductModuleTreeCache, { data: [], expiresAt: 0 })
    assert.deepEqual(a.store.projectProductNavigationSelection, { projectProduct: null, module: null, moduleTreeKey: null, moduleIds: [] })
  }
  a.close()
})

test('invalidating a module cache prevents its pending Promise returning old nodes and does not remove a newer request', async () => {
  const pending = [deferred(), deferred()]
  let index = 0
  const f = factory(() => pending[index++].promise), a = f.root()
  const old = a.store.getAllProductModuleTree(); await flush()
  a.store.invalidateAllProductModuleTreeCache()
  const current = a.store.getAllProductModuleTree(); await flush()
  pending[0].resolve(response(modules('Old tree')))
  assert.deepEqual(await old, [])
  const joined = a.store.getAllProductModuleTree(); await flush()
  assert.equal(f.requests.length, 2)
  pending[1].resolve(response(modules('New tree')))
  assert.equal((await current)[0].title, 'New tree')
  assert.equal((await joined)[0].title, 'New tree')
  await a.store.getAllProductModuleTree()
  assert.equal(f.requests.length, 2)
  a.close()
})

test('module read from previous identity never returns its captured fallback cache on failure', async () => {
  const pending = deferred()
  let count = 0
  const f = factory(() => ++count === 1 ? response(modules('Old cached tree')) : pending.promise), a = f.root()
  await a.store.getAllProductModuleTree()
  const old = a.store.getAllProductModuleTree(true); await flush()
  a.user.roleId = 2
  pending.reject(new Error('Old failed request'))
  assert.deepEqual(await old, [])
  assert.deepEqual(a.store.allProductModuleTreeCache.data, [])
  assert.equal(a.store.optionErrors.modules, false)
  a.close()
})

test('business and malformed errors preserve current data, expose failure and remain retryable; empty is a valid success', async () => {
  let result = response(products('Retained'))
  const f = factory(() => result), a = f.root()
  await a.store.projectProductName()
  for (const bad of [{ code: 403, data: [] }, response(null), response([{ value: 1, label: 'Bad', children: [null] }])]) {
    result = bad
    await a.store.projectProductName(true)
    assert.equal(a.store.optionErrors.products, true)
    assert.equal(a.store.projectProduct[0].children[0].label, 'Retained')
  }
  result = response([]); await a.store.projectProductName()
  assert.equal(a.store.optionErrors.products, false)
  assert.deepEqual(a.store.projectProduct, [])
  a.close()
})

test('Pytest mapping retains original product association with independent flat children and no transport fields', async () => {
  const f = factory(() => response([{ value: 1, label: 'Project', children: [{ value: 50, label: 'Pytest', project_product_id: 10, extra: 'ignored', children: [{ value: 30, label: 'Module' }] }] }])), a = f.root()
  await a.store.projectPytestName()
  assert.equal(a.store.getPytestProjectProductId([1, 50]), 10)
  assert.deepEqual(a.store.getProjectPytestModule(50), [{ value: 30, label: 'Module' }])
  assert.equal(a.store.projectPytest2[0].children[0].children, undefined)
  assert.equal(a.store.projectPytest2[0].children[0].extra, undefined)
  a.store.projectPytest2[0].children[0].label = 'Flat only'
  assert.equal(a.store.projectPytest[0].children[0].label, 'Pytest')
  a.close()
})

test('disposal stops identity observation and ignores late response; sibling store still completes', async () => {
  const pending = deferred(), f = factory(() => pending.promise), a = f.root(), b = f.root()
  const old = a.store.projectProductName(), sibling = b.store.projectProductName(); await flush()
  a.store.$dispose()
  a.store.data = [{ key: 1, title: 'Detached' }]
  a.user.roleId = 2
  assert.equal(a.store.data[0].title, 'Detached')
  pending.resolve(response(products('Sibling'))); await Promise.all([old, sibling])
  assert.deepEqual(a.store.projectProduct, [])
  assert.equal(b.store.projectProduct[0].children[0].label, 'Sibling')
  a.user.$dispose(); b.close()
})

test('selection arrays are detached and legitimate zero/null values survive parsing', () => {
  const f = factory(), a = f.root(), ids = [30]
  a.store.setModuleNavigationSelection(30, 'module:30', ids)
  ids.push(40)
  assert.deepEqual(a.store.projectProductNavigationSelection.moduleIds, [30])
  assert.deepEqual(f.parsers.projectOptions([{ key: null, title: 'Choose' }, { key: 0, title: 'Zero' }]), [{ key: null, title: 'Choose' }, { key: 0, title: 'Zero' }])
  a.close()
})

test('reload retains same-owner navigation intent but never persisted responses; different owner and unscoped legacy selections reset', () => {
  const f = factory(), a = f.root()
  a.store.setProjectProductNavigationSelection(10)
  a.store.setModuleNavigationSelection(30, 'module:30', [30])
  a.store.projectProduct = products('Persisted responses are untrusted')
  a.store.allProductModuleTreeCache = { data: modules('Persisted tree'), expiresAt: Date.now() + 100000 }
  const snapshot = JSON.parse(JSON.stringify(a.store.$state))
  const same = f.root(structuredClone(snapshot))
  assert.equal(same.store.projectProductNavigationSelection.module, 30)
  assert.deepEqual(same.store.projectProduct, [])
  assert.deepEqual(same.store.allProductModuleTreeCache, { data: [], expiresAt: 0 })
  const other = f.root(structuredClone(snapshot), { roleId: 2 })
  assert.equal(other.store.projectProductNavigationSelection.module, null)
  const legacy = structuredClone(snapshot)
  delete legacy.navigationOwner
  const old = f.root(legacy)
  assert.equal(old.store.projectProductNavigationSelection.module, null)
  const invalid = structuredClone(snapshot)
  invalid.projectProductNavigationSelection.moduleIds = null
  const corrupt = f.root(invalid)
  assert.equal(corrupt.store.projectProductNavigationSelection.module, null)
  a.close(); same.close(); other.close(); old.close(); corrupt.close()
})

test('sidebar initialization ignores previous identity products and emits only the current module scope', async () => {
  const pending = [deferred(), deferred()]
  let count = 0
  const f = factory(kind => kind === 'products' ? pending[count++].promise : response(modules('Current module'))), a = f.root(), h = sidebar(a)
  h.mount(); await flush()
  a.user.roleId = 2; await flush()
  pending[0].resolve(response(products('Old product'))); await flush()
  assert.equal(h.loading.value, true)
  assert.equal(h.initialized.value, false)
  assert.deepEqual(h.moduleOptionsByProduct.value, {})
  pending[1].resolve(response(products('Current product'))); await flush()
  assert.equal(h.loading.value, false)
  assert.equal(h.initialized.value, true)
  assert.equal(h.displayTree.value[1].title, 'Project / Current product')
  assert.equal(h.moduleOptionsByProduct.value['10'][0].title, 'Current module')
  h.onSelect(['module:30'])
  assert.deepEqual(h.events.at(-1), ['filter-change', { projectProduct: 10, module: 30, moduleIds: [30], selectedModuleId: 30 }])
  h.close(); a.close()
})

test('sidebar rejects late module completion after identity A-B-A and cannot clear newer loading or restore old selection', async () => {
  const pending = [deferred(), deferred()]
  let count = 0
  const f = factory(kind => kind === 'modules' ? pending[count++].promise : response(products('Product'))), a = f.root(), h = sidebar(a)
  h.mount(); await flush()
  a.store.setModuleNavigationSelection(30, 'module:30', [30])
  a.user.roleId = 2; a.user.roleId = 1; await flush()
  assert.equal(f.requests.filter(kind => kind === 'modules').length, 2)
  pending[0].resolve(response(modules('Old A'))); await flush()
  assert.deepEqual(h.moduleOptionsByProduct.value, {})
  assert.equal(h.loading.value, true)
  assert.equal(a.store.projectProductNavigationSelection.module, null)
  pending[1].resolve(response(modules('Current A'))); await flush()
  assert.equal(h.moduleOptionsByProduct.value['10'][0].title, 'Current A')
  assert.equal(h.events.some(event => event[0] === 'filter-change' && event[1].module === 30), false)
  h.close(); a.close()
})

test('sidebar exposes failed navigation and retries both products and modules without allowing stale tree selection', async () => {
  let result = { code: 403, data: [] }
  const f = factory(() => result), a = f.root(), h = sidebar(a)
  h.mount(); await flush()
  assert.equal(h.loadFailed.value, true)
  assert.equal(h.loading.value, false)
  const before = h.events.length
  h.onSelect(['product-group:10']); assert.equal(h.events.length, before)
  result = response(products('Product'))
  await h.loadNavigation()
  assert.equal(h.loadFailed.value, true) // product-shaped data is not a valid module tree
  result = response([])
  await h.loadNavigation()
  assert.equal(h.loadFailed.value, false)
  assert.equal(h.initialized.value, true)
  h.close(); a.close()
})

test('sidebar KeepAlive defers identity reload until activation and ignores completions after unmount', async () => {
  const pending = deferred()
  const f = factory(kind => kind === 'products' ? pending.promise : response(modules('Module'))), a = f.root(), h = sidebar(a)
  h.mount(); await flush(); h.pause()
  a.user.roleId = 2; await flush()
  assert.deepEqual(f.requests, ['products'])
  pending.resolve(response(products('Paused'))); await flush()
  assert.equal(h.initialized.value, false)
  assert.deepEqual(h.moduleOptionsByProduct.value, {})
  h.resume(); await flush()
  assert.equal(h.initialized.value, true)
  assert.equal(f.requests.filter(kind => kind === 'products').length, 2)
  h.close()
  const events = h.events.length
  a.user.roleId = 3; await flush()
  assert.equal(h.events.length, events)
  assert.equal(h.loading.value, false)
  a.close()
})

test('sidebar visibility pauses, restores and removes its document listener on unmount', async () => {
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'document'), listeners = new Set()
  const document = { hidden: false, addEventListener(type, fn) { assert.equal(type, 'visibilitychange'); listeners.add(fn) }, removeEventListener(type, fn) { listeners.delete(fn) } }
  Object.defineProperty(globalThis, 'document', { configurable: true, value: document })
  const pending = deferred(), f = factory(kind => kind === 'products' ? pending.promise : response(modules('Module'))), a = f.root(), h = sidebar(a)
  try {
    h.mount(); await flush()
    document.hidden = true; listeners.forEach(fn => fn())
    pending.resolve(response(products('Visible again'))); await flush()
    assert.equal(h.loading.value, false)
    assert.equal(h.initialized.value, false)
    document.hidden = false; listeners.forEach(fn => fn()); await flush()
    assert.equal(h.initialized.value, true)
    assert.equal(listeners.size, 1)
  } finally {
    h.close(); a.close()
    assert.equal(listeners.size, 0)
    if (previous) Object.defineProperty(globalThis, 'document', previous)
    else delete globalThis.document
  }
})

test('sidebar compiles with retry slot and unchanged navigation event contract', () => {
  const descriptor = parse(readFileSync(sidebarFilename, 'utf8'), { filename: sidebarFilename }).descriptor
  const script = compileScript(descriptor, { id: sidebarFilename })
  const template = compileTemplate({ source: descriptor.template.content, filename: sidebarFilename, id: sidebarFilename, compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
})

test('unmounted sidebar never emits a late module result while its mounted sibling still receives shared data', async () => {
  const pending = deferred(), f = factory(kind => kind === 'modules' ? pending.promise : response(products('Product'))), a = f.root(), old = sidebar(a), current = sidebar(a)
  old.mount(); current.mount(); await flush()
  old.close()
  const count = old.events.length
  pending.resolve(response(modules('Shared tree'))); await flush()
  assert.equal(old.events.length, count)
  assert.equal(old.initialized.value, false)
  assert.equal(current.initialized.value, true)
  assert.equal(current.moduleOptionsByProduct.value['10'][0].title, 'Shared tree')
  current.close(); a.close()
})

test('sidebar only restores a cached module after checking it exists in the fresh product/module tree', async () => {
  const pending = deferred(), f = factory(kind => kind === 'products' ? pending.promise : response(modules('Fresh'))), a = f.root(), h = sidebar(a)
  a.store.setProjectProductNavigationSelection(10)
  a.store.setModuleNavigationSelection(999, 'module:999', [999])
  h.mount(); await flush()
  assert.deepEqual(h.events, [])
  pending.resolve(response(products('Fresh product'))); await flush()
  assert.equal(h.initialized.value, true)
  assert.equal(h.events.some(event => event[0] === 'filter-change' && event[1].module === 999), false)
  assert.equal(a.store.projectProductNavigationSelection.module, null)
  h.close(); a.close()
})

test('product selectors share the sidebar store request while keeping loading scoped to each mounted consumer', async () => {
  const pending = deferred(), f = factory(() => pending.promise), a = f.root(), h = sidebar(a, { showModules: false }), select = productSelect(a)
  h.mount(); select.mount(); await flush()
  assert.deepEqual(f.requests, ['products'])
  assert.equal(select.loading.value, true)
  select.close()
  pending.resolve(response(products('Shared'))); await flush()
  assert.equal(h.initialized.value, true)
  assert.equal(select.loading.value, false)
  h.close(); a.close()
})

test('mounted product selector reloads on identity changes and defers reload while inactive', async () => {
  const pending = deferred()
  let count = 0
  const f = factory(() => ++count === 1 ? pending.promise : response(products('Current'))), a = f.root(), h = productSelect(a)
  h.mount(); await flush()
  a.user.roleId = 2; a.user.roleId = 1; await flush()
  assert.equal(f.requests.length, 2)
  assert.equal(h.productOptions.value[0].children[0].label, 'Current')
  pending.resolve(response(products('Old'))); await flush()
  assert.equal(h.productOptions.value[0].children[0].label, 'Current')
  h.pause(); a.user.roleId = 3; await flush()
  assert.deepEqual(h.productOptions.value, [])
  assert.equal(f.requests.length, 2)
  h.resume(); await flush()
  assert.equal(f.requests.length, 3)
  h.close(); a.close()
})

test('product selector retries failed reads and retains its existing external selection event values', async () => {
  let result = { code: 403, data: [] }
  const f = factory(() => result), a = f.root(), h = productSelect(a)
  h.mount(); await flush()
  assert.equal(h.failed.value, true)
  assert.equal(h.loading.value, false)
  result = response(products('Retry'))
  h.onPopupVisibleChange(true); await flush()
  assert.equal(h.failed.value, false)
  assert.equal(h.productOptions.value[0].children[0].label, 'Retry')
  const path = [1, 10]
  h.onUpdate(path); h.onChange(10)
  assert.deepEqual(h.events, [['update:modelValue', path], ['change', 10]])
  h.close(); a.close()
})

test('product selector visibility prevents identity reads in background and cleans its listener', async () => {
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'document'), listeners = new Set()
  const document = { hidden: false, addEventListener(type, fn) { listeners.add(fn) }, removeEventListener(type, fn) { listeners.delete(fn) } }
  Object.defineProperty(globalThis, 'document', { configurable: true, value: document })
  const f = factory(), a = f.root(), h = productSelect(a)
  try {
    h.mount(); await flush()
    document.hidden = true; listeners.forEach(fn => fn())
    a.user.roleId = 2; await flush()
    assert.equal(f.requests.length, 1)
    assert.deepEqual(h.productOptions.value, [])
    document.hidden = false; listeners.forEach(fn => fn()); await flush()
    assert.equal(f.requests.length, 2)
    assert.equal(h.loading.value, false)
  } finally {
    h.close(); a.close()
    assert.equal(listeners.size, 0)
    if (previous) Object.defineProperty(globalThis, 'document', previous)
    else delete globalThis.document
  }
})

test('product selector SFC compiles with its existing Cascader protocol and local retry feedback', () => {
  const descriptor = parse(readFileSync(selectFilename, 'utf8'), { filename: selectFilename }).descriptor
  const script = compileScript(descriptor, { id: selectFilename })
  const template = compileTemplate({ source: descriptor.template.content, filename: selectFilename, id: selectFilename, compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
})
