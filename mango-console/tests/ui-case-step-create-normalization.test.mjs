import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
import { loadModule } from './helpers/auth-config-harness.mjs'

const base = path.resolve('src/components/business'), filename = path.join(base, 'UiCaseStepCreateDialog.vue')
const productResponse = () => ({ code: 200, data: [{ value: 'project:7', label: 'Example project', children: [{ value: 0, label: 'Example product' }] }] })
const moduleResponse = (id = 0, product = 0) => ({ code: 200, data: [{ value: id, label: 'Example module', project_product_id: product }] })
const stepResponse = (id = 0, module = 0, product = 0) => ({ code: 200, data: [{ step_id: id, step_name: 'Example step', page_id: 0, page_name: 'Example page', module_id: module, project_product_id: product }] })
function setup(overrides = {}) {
  const previous = globalThis.document, doc = Object.assign(new EventTarget(), { visibilityState: 'visible' }); globalThis.document = doc
  const callbacks = { mount: [], activate: [], deactivate: [], unmount: [] }, reads = [], writes = [], messages = []
  const route = vue.reactive({ path: '/uitest/case/details', fullPath: '/uitest/case/details?id=0' }), user = vue.reactive({ userId: 1, roleId: 2, token: 'example-session', selected_environment: 0 }), permission = vue.reactive({ permissionKeys: ['ui.case:read'] })
  const api = Object.fromEntries(Object.entries({
    getUiPageStepAssetProducts: overrides.products || (async () => productResponse()), getUiPageStepAssetModules: overrides.modules || (async product => moduleResponse(0, product)), getUiPageStepAssetSteps: overrides.steps || (async (product, module) => stepResponse(0, module, product)),
    postUiCaseStepsDetailed: overrides.create || (async () => ({ code: 200, data: { id: 0 } })), getUiCaseStepsRefreshCacheData: overrides.initialize || (async () => ({ code: 200 })),
  }).map(([name, fn]) => [name, (...args) => { (name === 'postUiCaseStepsDetailed' || name === 'getUiCaseStepsRefreshCacheData' ? writes : reads).push([name, ...args]); return fn(...args) }]))
  const shell = { visible: false, loading: false, async show() { this.visible = true; if (overrides.show) await overrides.show(); return true }, async close() { this.visible = false; this.loading = false; return false }, setConfirmLoading(value) { this.loading = value } }
  const h = harness('UiCaseStepCreateDialog', 'visible,saving,saveError,createdStepId,creationAccepted,form,options,loading,errors,productId,pageStepOptions,locked,optionErrors,dialogRef,open,closeDialog:close,loadProducts,loadModules,loadSteps,onProductChange,onModuleChange,submit', {
    base, filename, props: { caseId: 0, caseStepCount: 3 }, api, modules: {
      vue: { ...vue, onMounted: fn => callbacks.mount.push(fn), onActivated: fn => callbacks.activate.push(fn), onDeactivated: fn => callbacks.deactivate.push(fn), onBeforeUnmount: fn => callbacks.unmount.push(fn) },
      '@/hooks/use-latest-request': loadModule('src/hooks/use-latest-request.ts'), 'vue-router': { useRoute: () => route }, '@/store/modules/user': { default: () => user }, '@/store/modules/permission': { default: () => permission },
      '@arco-design/web-vue': { Message: { success: message => messages.push(message) } },
    },
  }); h.dialogRef.value = shell
  return { ...h, shell, callbacks, reads, writes, messages, route, user, permission,
    mount() { callbacks.mount.forEach(fn => fn()) }, visibility(value) { doc.visibilityState = value; doc.dispatchEvent(new Event('visibilitychange')) },
    close() { callbacks.unmount.forEach(fn => fn()); h.close(); globalThis.document = previous },
  }
}
async function ready(h) { await h.open(); h.form.projectProduct = ['project:7', 0]; await h.onProductChange(); h.form.module = 0; await h.onModuleChange(); h.form.pageStep = ['page:0', 0] }

test('asset DTOs retain finite options and zero/long IDs while rejecting wrong scopes and malformed responses', t => {
  const h = setup(); t.after(h.close); const dto = h.load('ui-case-step-create.ts'), long = '90071992547409930000'
  assert.equal(dto.readUiCaseAssetProducts(productResponse())[0].children[0].value, 0); assert.equal(dto.readUiCaseAssetModules(moduleResponse(), 0)[0].value, 0)
  assert.equal(dto.readUiCaseAssetSteps(stepResponse(long), 0, 0)[0].stepId, long); assert.equal(dto.uiCaseAssetId(['project:7', 0]), 0)
  for (const value of [false, {}, -1, Number.MAX_SAFE_INTEGER + 1]) assert.throws(() => dto.uiCaseAssetId(value))
  assert.throws(() => dto.readUiCaseAssetProducts({ code: 403 })); assert.throws(() => dto.readUiCaseAssetModules(moduleResponse(0, 1), 0)); assert.throws(() => dto.readUiCaseAssetSteps(stepResponse(0, 1), 0, 0))
  const steps = dto.readUiCaseAssetSteps(stepResponse(), 0, 0); assert.equal(dto.uiCaseAssetStepOptions(steps)[0].value, 'page:0')
  assert.deepEqual(dto.uiCaseAssetCreatePayload(0, steps[0], 3), { case: 0, module: 0, page: 0, page_step: 0, case_cache_data: [], case_cache_ass: [], case_sort: 3 })
})
test('open, cancel and reopen reset private selections and options without sharing drafts', async t => {
  const h = setup(); t.after(h.close); await ready(h); assert.equal(h.productId.value, 0); assert.equal(h.pageStepOptions.value[0].children[0].value, 0)
  h.closeDialog(); assert.equal(h.visible.value, false); assert.equal(h.form.module, null); assert.deepEqual(h.options.steps, [])
  await h.open(); assert.deepEqual(h.form.projectProduct, []); assert.deepEqual(h.form.pageStep, []); assert.equal(h.createdStepId.value, null)
})
test('old show completion cannot start loading options for a replacement window', async t => {
  const pending = deferred(); let calls = 0; const h = setup({ show: () => ++calls === 1 ? pending.promise : Promise.resolve() }); t.after(h.close)
  const old = h.open(); h.closeDialog(); await h.open(); assert.equal(h.reads.length, 1); pending.resolve(); assert.equal(await old, false); assert.equal(h.reads.length, 1)
})
test('independent option failures retain retry controls and release loading', async t => {
  let failure = true; const h = setup({ products: async () => ({ code: failure ? 403 : 200, data: productResponse().data }), modules: async () => { if (failure) throw Error('network'); return moduleResponse() }, steps: async () => ({ code: failure ? 403 : 200, data: stepResponse().data }) }); t.after(h.close)
  await h.open(); assert.match(h.errors.products, /失败/); assert.equal(h.loading.products, false); failure = false; await h.loadProducts(); assert.equal(h.errors.products, '')
  h.form.projectProduct = ['project:7', 0]; failure = true; await h.onProductChange(); assert.match(h.errors.modules, /失败/); failure = false; await h.loadModules(); assert.equal(h.errors.modules, '')
  h.form.module = 0; failure = true; await h.onModuleChange(); assert.match(h.errors.steps, /失败/); failure = false; await h.loadSteps(); assert.equal(h.errors.steps, '')
})
test('product changes clear dependent selections and reject old module results and finally', async t => {
  const old = deferred(), current = deferred(), h = setup({ modules: product => product === 0 ? old.promise : current.promise }); t.after(h.close); await h.open()
  h.form.projectProduct = ['project:7', 0]; const first = h.onProductChange(); h.form.projectProduct = ['project:7', 2]; const second = h.onProductChange()
  old.resolve(moduleResponse()); await first; assert.equal(h.loading.modules, true); assert.deepEqual(h.options.modules, [])
  current.resolve(moduleResponse(2, 2)); await second; assert.equal(h.options.modules[0].value, 2); assert.equal(h.loading.modules, false); assert.deepEqual(h.form.pageStep, [])
})
test('module changes reject stale step results without ending the newer loading', async t => {
  const old = deferred(), current = deferred(), h = setup({ steps: (_product, module) => module === 0 ? old.promise : current.promise }); t.after(h.close); await h.open(); h.form.projectProduct = ['project:7', 0]; await h.onProductChange()
  h.form.module = 0; const first = h.onModuleChange(); h.form.module = 2; const second = h.onModuleChange(); old.resolve(stepResponse()); await first
  assert.equal(h.loading.steps, true); assert.deepEqual(h.options.steps, []); current.resolve(stepResponse(2, 2)); await second; assert.equal(h.options.steps[0].stepId, 2)
})
test('validation rejects missing selections and invalid case without writes and releases shell loading', async t => {
  const h = setup(); t.after(h.close); await h.open(); h.shell.loading = true; assert.equal(await h.submit(), false); assert.equal(h.shell.loading, false); assert.match(h.saveError.value, /项目/)
  h.props.caseId = 'bad'; await h.open(); assert.equal(await h.submit(), false); assert.match(h.saveError.value, /用例ID/); assert.deepEqual(h.writes, [])
})
test('save snapshots original case/asset/sort before awaiting POST and blocks duplicate submission', async t => {
  const pending = deferred(), h = setup({ create: () => pending.promise }); t.after(h.close); await ready(h)
  const saving = h.submit(); assert.equal(h.saving.value, true); assert.equal(await h.submit(), false); h.form.pageStep = ['page:2', 2]; h.props.caseStepCount = 9
  assert.deepEqual(h.writes[0], ['postUiCaseStepsDetailed', { case: 0, module: 0, page: 0, page_step: 0, case_cache_data: [], case_cache_ass: [], case_sort: 3 }, 0])
  pending.resolve({ code: 200, data: { id: 0 } }); assert.equal(await saving, true); assert.deepEqual(h.writes[1], ['getUiCaseStepsRefreshCacheData', 0]); assert.deepEqual(h.events, [['created']]); assert.equal(h.visible.value, false)
})
test('creation failure retains editable draft and retries POST without false success', async t => {
  let fail = true; const h = setup({ create: async () => ({ code: fail ? 403 : 200, data: { id: 0 } }) }); t.after(h.close); await ready(h)
  assert.equal(await h.submit(), false); assert.equal(h.visible.value, true); assert.equal(h.locked.value, false); assert.equal(h.creationAccepted.value, false); assert.deepEqual(h.events, [])
  fail = false; assert.equal(await h.submit(), true); assert.equal(h.writes.filter(x => x[0] === 'postUiCaseStepsDetailed').length, 2)
})
test('cache initialization failure retains the created ID and retries only initialization even when options disappear', async t => {
  let fail = true; const h = setup({ initialize: async () => { if (fail) throw Error('network'); return { code: 200 } } }); t.after(h.close); await ready(h)
  assert.equal(await h.submit(), false); assert.equal(h.createdStepId.value, 0); assert.equal(h.locked.value, true); assert.match(h.saveError.value, /不会重复创建/); assert.deepEqual(h.messages, [])
  h.options.steps = []; fail = false; assert.equal(await h.submit(), true); assert.equal(h.writes.filter(x => x[0] === 'postUiCaseStepsDetailed').length, 1); assert.equal(h.writes.filter(x => x[0] === 'getUiCaseStepsRefreshCacheData').length, 2)
})
test('accepted creation with malformed ID blocks blind resubmission and prompts reloading', async t => {
  const h = setup({ create: async () => ({ code: 200, data: {} }) }); t.after(h.close); await ready(h)
  assert.equal(await h.submit(), false); assert.equal(h.creationAccepted.value, true); assert.equal(h.createdStepId.value, null); assert.match(h.saveError.value, /已创建.*重新加载/)
  assert.equal(await h.submit(), false); assert.equal(h.writes.length, 1); assert.deepEqual(h.events, [['created']])
})
test('cancel during POST retains physical lock, completes original initialization and refreshes without reopening/toast', async t => {
  const pending = deferred(), h = setup({ create: () => pending.promise }); t.after(h.close); await ready(h)
  const saving = h.submit(); h.closeDialog(); assert.equal(await h.open(), false); assert.equal(h.saving.value, true)
  pending.resolve({ code: 200, data: { id: 0 } }); assert.equal(await saving, true); assert.equal(h.visible.value, false); assert.deepEqual(h.messages, []); assert.deepEqual(h.events, [['created']])
})
test('every identity and case change suppresses follow-up writes and stale feedback after POST', async () => {
  for (const change of [h => h.user.userId++, h => h.user.roleId++, h => h.user.token = 'example-new', h => h.user.selected_environment++, h => h.permission.permissionKeys.push('example:read'), h => h.route.path = '/other', h => h.route.fullPath += '&other=1', h => h.props.caseId = 2]) {
    const pending = deferred(), h = setup({ create: () => pending.promise })
    try { await ready(h); const saving = h.submit(); change(h); assert.equal(h.visible.value, false); pending.resolve({ code: 200, data: { id: 0 } }); assert.equal(await saving, false); assert.equal(h.writes.length, 1); assert.deepEqual(h.messages, []); assert.deepEqual(h.events, []) } finally { h.close() }
  }
})
test('background, KeepAlive and unmount close the window and invalidate pending metadata', async () => {
  for (const leave of [h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn()), h => h.callbacks.unmount.forEach(fn => fn())]) {
    const pending = deferred(), h = setup({ products: () => pending.promise })
    try { h.mount(); const opening = h.open(); await flush(); leave(h); pending.resolve(productResponse()); await opening; assert.equal(h.visible.value, false); assert.deepEqual(h.options.products, []); assert.equal(h.loading.products, false) } finally { h.close() }
  }
})
test('creation dialog SFC compiles with horizontal form, local errors/loading and guarded explicit footer', async () => {
  const { descriptor, errors } = parse(readFileSync(filename, 'utf8')); assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'ui-case-create' }), template = compileTemplate({ source: descriptor.template.content, filename, id: 'ui-case-create', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, []); assert.deepEqual((await compileStyleAsync({ source: descriptor.styles[0].content, filename, id: 'ui-case-create', scoped: true })).errors, [])
  assert.match(descriptor.template.content, /layout="horizontal"/); assert.match(descriptor.template.content, /:loading="saving"/); assert.match(descriptor.template.content, /重试初始化/); assert.doesNotMatch(descriptor.scriptSetup.content, /any\[\]|console\.log/)
})
test('step API preserves parent_id and refresh protocol with zero/long IDs', () => {
  const calls = [], api = loadModule('src/api/uitest/case-steps-detailed.ts', { '@/api/http': { get: value => calls.push(['get', value]), post: value => calls.push(['post', value]), put() {}, deleted() {} } })
  api.postUiCaseStepsDetailed({ case: 0, page_step: 0 }, 0); api.getUiCaseStepsRefreshCacheData('90071992547409930000')
  assert.equal(calls[0][1].url, '/ui/case/steps/detailed'); assert.deepEqual(calls[0][1].data(), { case: 0, page_step: 0, parent_id: 0 })
  assert.equal(calls[1][1].url, '/ui/case/steps/detailed/refresh'); assert.deepEqual(calls[1][1].data(), { id: '90071992547409930000', case_id: null })
})
