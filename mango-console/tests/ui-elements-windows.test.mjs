import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { liveHarness } from './helpers/ui-live-workbench-harness.mjs'
import { editor } from './helpers/ui-elements-harness.mjs'

const ai = (api = {}) => liveHarness({ component: 'UiElementAiHealPanel', bindings: 'open,visible,currentElement,data,loading,infoLoading,snapshotsLoading,healsLoading,infoError,snapshotsError,applyError,applyCandidate,applyingKey,readResource,candidateRows,baselineDetailPanelRef,openSnapshotDetail', props: { testEnv: 0, contextKey: 0 }, api: { getUiElementAiInfo: async () => ({ code: 200, data: { element: { id: 0 }, latest_heal_record: { id: 0, candidates: [{ verified: true, loc: '//button', candidate_index: 0 }] } } }), getUiElementAiSnapshots: async () => ({ code: 200, data: { items: [{ id: 0, element_id: 0 }] } }), getUiElementAiHealRecords: async () => ({ code: 200, data: { items: [] } }), putUiElementAiHealApply: async () => ({ code: 200 }), ...api } })
test('AI window loads regions independently, retains partial data and retries only failed resource', async t => {
  const pending = deferred(); let fail = true; const h = ai({ getUiElementAiInfo: () => pending.promise, getUiElementAiSnapshots: async () => { if (fail) throw Error('Example snapshot unavailable'); return { data: { items: [{ id: 0 }] } } } }); t.after(h.cleanup)
  const opening = h.open({ id: 0, name: 'Example' }); await flush(); assert.equal(h.visible.value, true); assert.equal(h.infoLoading.value, true); assert.equal(h.healsLoading.value, false); assert.equal(h.snapshotsLoading.value, false); assert.equal(h.snapshotsError.value, 'Example snapshot unavailable')
  pending.resolve({ data: { element: { id: 0 }, statistics: { snapshot_count: 1 } } }); assert.equal(await opening, false); assert.equal(h.data.value.element.id, 0); fail = false; await h.readResource('snapshots'); assert.equal(h.data.value.snapshots[0].id, 0); assert.equal(h.reads.filter(([name]) => name === 'getUiElementAiInfo').length, 1)
})
test('AI identity and A-B-A replacement reject late data without reopening the previous window', async t => {
  const pending = deferred(), h = ai({ getUiElementAiInfo: () => pending.promise }); t.after(h.cleanup)
  const opening = h.open({ id: 0 }); h.props.contextKey = 2; h.props.contextKey = 0; pending.resolve({ data: { element: { id: 0 } } }); assert.equal(await opening, false); assert.equal(h.visible.value, false); assert.equal(h.currentElement.value, null)
})
test('AI candidate write preserves zero record/index and prevents replay after accepted write and failed refresh', async t => {
  let fail = false; const h = ai({ getUiElementAiSnapshots: async () => { if (fail) throw Error('Example refresh failure'); return { data: { items: [] } } } }); t.after(h.cleanup)
  await h.open({ id: 0 }); fail = true; const candidate = h.candidateRows.value[0]; await h.applyCandidate(candidate, 0, 1); await h.applyCandidate(candidate, 0, 1)
  assert.deepEqual(h.writes[0][1], { record_id: 0, candidate_index: 0, target_slot: 1 }); assert.equal(h.writes.length, 1); assert.deepEqual(h.candidateRows.value[0].applied_slots, [1]); assert.equal(h.snapshotsError.value, 'Example refresh failure')
})
test('AI write remains physically locked after closing and cannot emit into replacement context', async t => {
  const pending = deferred(), h = ai({ putUiElementAiHealApply: () => pending.promise }); t.after(h.cleanup); await h.open({ id: 0 })
  const writing = h.applyCandidate(h.candidateRows.value[0], 0, 1); h.visible.value = false; await h.open({ id: 0 }); await h.applyCandidate(h.candidateRows.value[0], 0, 2); assert.equal(h.writes.length, 1); pending.resolve({ code: 200 }); await writing; assert.equal(h.events.some(([name]) => name === 'applied'), false); assert.equal(h.applyingKey.value, '')
})
test('AI history accepts zero snapshot and element IDs', async t => {
  const h = ai(); t.after(h.cleanup); await h.open({ id: 0 }); const calls = []; h.baselineDetailPanelRef.value = { open: async (...args) => calls.push(args) }; await h.openSnapshotDetail({ id: 0 }); assert.deepEqual(calls, [[0, 0]])
})
for (const [component, apiName] of [['UiElementBaselineDetailPanel', 'getUiElementAiSnapshotDetail'], ['UiElementHealRecordDetailPanel', 'getUiElementAiHealRecordDetail']]) {
  test(`${component} rejects stale reads and allows retry after local failure`, async t => {
    const pending = deferred(); let count = 0
    const h = liveHarness({ component, bindings: 'open,visible,detail,error,loading', api: { [apiName]: () => ++count === 1 ? pending.promise : Promise.resolve({ code: 200, data: { id: 2, element_id: 0 } }) } }); t.after(h.cleanup)
    const first = h.open(0, 0); await h.open(2, 0); pending.resolve({ data: { id: 0, element_id: 0 } }); assert.equal(await first, false); assert.equal(h.detail.value.id, 2); assert.equal(h.loading.value, false); h.user.roleId++; assert.equal(h.visible.value, false); assert.equal(h.detail.value, null)
  })
}
const importer = (api = {}) => liveHarness({ filename: path.resolve('src/views/uitest/page/elements/components/ElementBatchImportModal.vue'), bindings: 'upload,downloadTemplate,uploading,downloading,error,selectedFile', props: { pageId: 0, visible: true }, api, modules: { '@/components/business/ui-element-editor': editor } })
test('batch import freezes zero page ID and file, blocks duplicates and retains file on failure', async t => {
  const pending = deferred(), h = importer({ getUiElementUpload: () => pending.promise }); t.after(h.cleanup)
  const file = new File(['Example'], 'example.xlsx'), uploading = h.upload(file); await h.upload(file); const calls = h.reads.filter(([name]) => name === 'getUiElementUpload'); assert.equal(calls.length, 1); assert.equal(calls[0][1].get('page_id'), '0'); assert.equal(calls[0][1].get('file').name, 'example.xlsx')
  pending.reject(Error('Example rejection')); await uploading; assert.equal(h.error.value, 'Example rejection'); assert.equal(h.selectedFile.value, file); assert.equal(h.uploading.value, false)
})
test('batch import context replacement preserves physical lock and rejects stale success', async t => {
  const pending = deferred(), h = importer({ getUiElementUpload: () => pending.promise }); t.after(h.cleanup); const file = new File(['Example'], 'example.xlsx')
  const uploading = h.upload(file); h.props.pageId = 2; await h.upload(file); assert.equal(h.reads.filter(([name]) => name === 'getUiElementUpload').length, 1); pending.resolve({ code: 200 }); await uploading; assert.equal(h.events.some(([name]) => name === 'saved'), false); assert.equal(h.uploading.value, false)
})
test('accepted import refreshes parent but does not close a reopened window', async t => {
  const pending = deferred(), h = importer({ getUiElementUpload: () => pending.promise }); t.after(h.cleanup)
  const uploading = h.upload(new File(['Example'], 'example.xlsx')); h.props.visible = false; h.props.visible = true; pending.resolve({ code: 200 }); await uploading
  assert.equal(h.events.some(([name]) => name === 'saved'), true); assert.equal(h.events.some(([name, value]) => name === 'update:visible' && value === false), false)
})
test('download failure is local and always ends button loading', async t => {
  const before = globalThis.fetch, h = importer(); t.after(() => { globalThis.fetch = before; h.cleanup() }); globalThis.fetch = async () => ({ ok: false })
  await h.downloadTemplate(); assert.match(h.error.value, /下载失败/); assert.equal(h.downloading.value, false)
})
test('workbench toggle locks asynchronous preparation and rejects a late open after closing', async t => {
  const h = liveHarness(); t.after(h.cleanup); const approval = deferred(), workbench = h.workbenchHook.useUiLiveWorkbench(() => approval.promise)
  const opening = workbench.open(); assert.equal(await workbench.open(), false); assert.equal(workbench.opening.value, true); workbench.close(); approval.resolve(true); assert.equal(await opening, false); assert.equal(workbench.visible.value, false); assert.equal(workbench.opening.value, false)
})
test('workbench preparation failure releases loading and KeepAlive deactivation closes the owned view', async t => {
  const h = liveHarness(); t.after(h.cleanup); let fail = true; const workbench = h.workbenchHook.useUiLiveWorkbench(async () => { if (fail) throw Error('Example failure'); return true })
  assert.equal(await workbench.open(), false); assert.equal(workbench.opening.value, false); fail = false; assert.equal(await workbench.open(), true); h.callbacks.deactivate.forEach(fn => fn()); assert.equal(workbench.visible.value, false)
})
test('element API preserves delete IDs and the existing open-browser POST contract', () => {
  const calls = [], api = loadModule('src/api/uitest/element.ts', { '@/api/http': { deleted: value => calls.push(['delete', value]), post: value => calls.push(['post', value]), get() {}, put() {} } })
  api.deleteUiElement('900719925474099399'); api.deleteUiElement([0, '900719925474099399']); api.postUiElementOpenBrowser({ page_id: 0, test_env: 0 })
  assert.deepEqual(calls.map(([method, request]) => [method, request.url, request.data()]), [
    ['delete', '/ui/element', { id: '900719925474099399' }], ['delete', '/ui/element', { id: [0, '900719925474099399'] }], ['post', '/ui/element/browser/open', { page_id: 0, test_env: 0 }],
  ])
})
test('upload adapter sends the original multipart FormData using POST despite its historical get-prefixed name', () => {
  const calls = [], api = loadModule('src/api/uitest/element.ts', { '@/api/http': { deleted() {}, post: value => calls.push(value), get() {}, put() {} } }), body = new FormData()
  body.append('page_id', '0'); api.getUiElementUpload(body); assert.equal(calls[0].url, '/ui/element/upload'); assert.equal(calls[0].headers['Content-Type'], 'multipart/form-data'); assert.equal(calls[0].data(), body)
})
