import assert from 'node:assert/strict'
import test from 'node:test'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { loadModule } from './helpers/auth-config-harness.mjs'
import { liveHarness, models, lossless } from './helpers/ui-live-workbench-harness.mjs'

const setup = api => liveHarness({ component: 'UiElementEditPanel', bindings: 'openEdit,openEditById,openCreate,form,visible,save,saving,saveError,readError,loading,runIdentityCheck,identityCheck,buildPayload', api })
test('element draft maps only editable fields, preserving zero IDs and independent event values', () => {
  const { readElementEditor } = loadModule('src/components/business/ui-element-editor.ts', { '@/utils/lossless-json': lossless, './ui-live-workbench': models })
  const record = { id: 0, page: { id: 0 }, name: 'Example', category: 'Example', exp: 0, expected_event: { ope_key: 'example', ope_value: [{ f: 'x', v: { flag: false, count: 0, value: null } }] }, extra: 'not-editable' }
  const draft = readElementEditor(record); draft.expected_event.ope_value[0].v.count = 2
  assert.equal(draft.id, 0); assert.equal(draft.page, 0); assert.equal(draft.exp, 0); assert.equal(draft.extra, undefined); assert.equal(record.expected_event.ope_value[0].v.count, 0)
})
test('editing preserves long IDs, fixed payload and excludes audit/runtime evidence', async t => {
  const pending = deferred(), h = setup({ putUiElement: () => pending.promise }); t.after(h.cleanup)
  await h.openEdit({ id: '900719925474099399', page: 0, name: 'Before', category: 'Example', location_description: 'Example', update_user: 5, latest_runtime_snapshot: { name: 'evidence' } }); const saving = h.save(false)
  assert.equal(h.writes[0][1].id, '900719925474099399'); assert.equal(h.writes[0][1].page, 0); assert.equal(h.writes[0][1].update_user, undefined); assert.equal(h.writes[0][1].latest_runtime_snapshot, undefined)
  h.form.name = 'After'; assert.equal(h.writes[0][1].name, 'Before'); pending.resolve({ data: { id: '900719925474099399' } }); await saving
})
test('name identity check rejects old responses after closing, including A-B-A reopen', async t => {
  const pending = deferred(), h = setup({ getUiElementIdentity: () => pending.promise }); t.after(h.cleanup)
  h.openCreate(0, 'Example', { name: 'Example', location_description: 'Example' }); await flush(); const checking = h.runIdentityCheck(true); h.visible.value = false; h.openCreate(0, 'Example', { name: 'Example', location_description: 'Example' }); await flush()
  pending.resolve({ data: { exists: true, element: { id: 2 }, match_count: 1 } }); assert.equal(await checking, false); assert.equal(h.identityCheck.record, null)
})
test('failed read clears previous record and cannot submit it; retry loads the requested zero ID', async t => {
  let fail = true; const h = setup({ getUiElement: async () => { if (fail) throw Error('Example unavailable'); return { data: [{ id: 0, page: 0, name: 'Current', category: 'Example', location_description: 'Example' }] } } }); t.after(h.cleanup)
  await h.openEdit({ id: 9, page: 1, name: 'Old', category: 'Old', location_description: 'Old' }); await h.openEditById(0); assert.equal(h.form.name, ''); assert.equal(h.readError.value, 'Example unavailable'); await h.save(false); assert.equal(h.writes.length, 0)
  fail = false; await h.openEditById(0); assert.equal(h.form.id, 0); assert.equal(h.form.name, 'Current'); assert.equal(h.loading.value, false); assert.equal(h.readError.value, '')
})
test('failed save retains private draft and supports explicit retry', async t => {
  let fail = true; const h = setup({ putUiElement: async () => { if (fail) throw Error('Example failure'); return { data: { id: 0 } } } }); t.after(h.cleanup)
  await h.openEdit({ id: 0, page: 0, name: 'Example', category: 'Example', location_description: 'Example' }); await h.save(false); assert.equal(h.visible.value, true); assert.equal(h.form.id, 0); assert.equal(h.saving.value, false); assert.equal(h.saveError.value, 'Example failure')
  fail = false; await h.save(false); assert.equal(h.visible.value, false); assert.equal(h.writes.length, 2)
})
test('identity and background invalidate editor saves synchronously before a parent remount', async () => {
  for (const change of [h => h.user.roleId++, h => h.user.token = 'example-next', h => h.visibility('hidden'), h => h.callbacks.deactivate.forEach(fn => fn())]) {
    const pending = deferred(), h = setup({ putUiElement: () => pending.promise })
    try { h.mount(); await h.openEdit({ id: 0, page: 0, name: 'Example', category: 'Example', location_description: 'Example' }); const saving = h.save(false); change(h); assert.equal(h.visible.value, false); pending.resolve({ data: { id: 0 } }); await saving; assert.equal(h.events.some(([name]) => name === 'saved'), false); assert.equal(h.saving.value, false) } finally { h.cleanup() }
  }
})
