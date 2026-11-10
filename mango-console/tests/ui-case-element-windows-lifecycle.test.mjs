import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { harness, deferred, flush, method } from './helpers/case-details-harness.mjs'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { ref } from 'vue'
const assets = loadModule('src/components/business/ui-case-step-create.ts')
function component(name, bindings, api = {}) {
  return harness('index', bindings, { filename: path.resolve(`src/components/business/${name}.vue`), api, modules: { '@arco-design/web-vue/es/icon': {}, '@/hooks/use-live-workbench-scope': { useLiveWorkbenchScope: () => ({ available: () => true, capture: () => () => true }) } } })
}
test('AI element metadata cannot reopen a panel after its owning step is unmounted', async () => {
  const pending = deferred(), h = component('UiElementAiHealPanel', 'open,visible,currentElement', { getUiElementAiInfo: () => pending.promise })
  const opening = h.open({ id: 0, name: 'Example element' }); h.close(); pending.resolve({ code: 200, data: { element: { id: 0 } } }); assert.equal(await opening, false); assert.equal(h.visible.value, false); assert.equal(h.currentElement.value, null)
})
test('AI candidate write stays physically locked and cannot refresh or emit after window closes', async t => {
  const pending = deferred(); let writes = 0
  const h = component('UiElementAiHealPanel', 'open,visible,applyCandidate,applyingKey', { putUiElementAiHealApply: () => { writes++; return pending.promise } }); t.after(h.close)
  await h.open({ id: 0, name: 'Example element' }); const saving = h.applyCandidate({ record_id: 1 }, 0, 1); h.visible.value = false; await h.applyCandidate({ record_id: 1 }, 0, 1); assert.equal(writes, 1); pending.resolve({ code: 200 }); await saving; assert.equal(h.events.some(event => event[0] === 'applied'), false); assert.equal(h.applyingKey.value, '')
})
test('baseline and heal history details accept zero IDs and discard responses after parent unmount', async () => {
  for (const [name, apiName] of [['UiElementBaselineDetailPanel', 'getUiElementAiSnapshotDetail'], ['UiElementHealRecordDetailPanel', 'getUiElementAiHealRecordDetail']]) {
    const pending = deferred(), h = component(name, 'open,visible,detail', { [apiName]: () => pending.promise })
    const opening = h.open(0, 0); h.close(); pending.resolve({ code: 200, data: { id: 0 } }); assert.equal(await opening, false); assert.equal(h.visible.value, false); assert.equal(h.detail.value, null)
  }
})
test('element editing write cannot close or update a replacement editor and normal/continuous saves share pending', async t => {
  const pending = deferred(); let writes = 0
  const h = component('UiElementEditPanel', 'openEdit,form,visible,save,saving', { putUiElement: () => { writes++; return pending.promise } }); t.after(h.close)
  await h.openEdit({ id: 0, name: 'Example element', category: 'Example category', page: 1, location_description: 'Example element description' }); const saving = h.save(false); await flush(); assert.equal(writes, 1)
  await h.openEdit({ id: 2, name: 'Replacement element', category: 'Example category', page: 1, location_description: 'Replacement element description' }); await h.save(true); assert.equal(writes, 1); pending.resolve({ code: 200, data: { id: 1 } }); await saving; assert.equal(h.visible.value, true); assert.equal(h.form.id, 2); assert.equal(h.events.some(event => event[0] === 'saved'), false); assert.equal(h.saving.value, false)
})
test('embedded node metadata rejects a response after the selection changes, including zero node IDs', async () => {
  const pending = deferred(); let current = true; const requests = []
  const load = method('loadSelectedNodeElement', { nodeDraft: ref({ id: 0 }), uiCaseAssetId: assets.uiCaseAssetId, captureElementContext: () => () => current, getUiPageStepsDetailedById: id => { requests.push(id); return pending.promise }, Message: { error() {} } }, path.resolve('src/views/uitest/page-steps/details/index.vue'))
  const loading = load(); current = false; pending.resolve({ data: [{ ele_name: { id: 1 } }] }); assert.equal(await loading, null); assert.deepEqual(requests, [0])
})
test('case inputs are captured before awaiting unrelated standalone flow persistence', async () => {
  const values = [], pending = deferred(), form = { 'example-ope_value': 'before' }
  const save = method('saveFormData', { selectedNode: ref({ id: 'example-node' }), formSaving: ref(false), stepResources: { capture: () => () => true }, methodsLoading: ref(false), methodsError: ref(''), nodeDuplicating: ref(false), nodeDeleting: ref(false), nodeType: ref(0), nodeFields: ref([]), sqlOperationRows: ref([]), caseNodeInputs: { saving: ref(false), save: value => { values.push(value); return pending.promise } }, isExcelAssertionMethod: ref(false), isCaseInheritedConfigItem: () => false, props: { caseInputMode: true }, getFormItems: () => ({ ...form }) }, path.resolve('src/views/uitest/page-steps/details/index.vue'))
  const saving = save(); form['example-ope_value'] = 'after'; assert.deepEqual(values, [{ 'example-ope_value': 'before' }]); pending.resolve(true); await saving
})
