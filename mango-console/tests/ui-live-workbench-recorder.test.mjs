import assert from 'node:assert/strict'
import test from 'node:test'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { liveHarness } from './helpers/ui-live-workbench-harness.mjs'

const action = (id = 'one') => ({ client_id: id, action: 'manual', name: 'Example', category: 'Example', status: 'ready', detail: { type: 3, custom: [{ key: 'example', value: false }] } })
const setup = options => liveHarness({ component: 'UiStepRecorderPanel', bindings: 'saveRecording,saveVisible,stepName,saving,saveError,loadDatasourceAliases,datasourceAliasOptions,datasourceLoading,datasourceError,inlineEditorItems,syncInlineConfig,scope', ...options })
test('recording save submits a fixed nested snapshot and blocks duplicate requests', async t => {
  const pending = deferred(), h = setup({ props: { actions: [action()] }, api: { postUiPageStepRecordingCommit: () => pending.promise } }); t.after(h.cleanup)
  h.saveVisible.value = true; h.stepName.value = '  Example step  '; const saving = h.saveRecording(); h.props.actions[0].detail.custom[0].value = true; await h.saveRecording()
  assert.equal(h.writes.length, 1); assert.equal(h.writes[0][1].name, 'Example step'); assert.equal(h.writes[0][1].page_id, 0); assert.equal(h.writes[0][1].nodes[0].detail.custom[0].value, false)
  pending.resolve({ data: { id: 0 } }); assert.equal(await saving, true); assert.equal(h.saving.value, false); assert.equal(h.saveVisible.value, false); assert.deepEqual(h.events.find(([event]) => event === 'saved'), ['saved', { id: 0 }, ['one']])
})
test('failed recording save retains draft and window for explicit retry', async t => {
  let fail = true; const h = setup({ props: { actions: [action()] }, api: { postUiPageStepRecordingCommit: async () => { if (fail) throw { msg: 'Example failure' }; return { data: { id: 0 } } } } }); t.after(h.cleanup)
  h.saveVisible.value = true; h.stepName.value = 'Example'; assert.equal(await h.saveRecording(), false); assert.equal(h.saveVisible.value, true); assert.equal(h.saveError.value, 'Example failure'); assert.equal(h.saving.value, false); assert.equal(h.props.actions.length, 1)
  fail = false; assert.equal(await h.saveRecording(), true); assert.equal(h.saveVisible.value, false)
})
test('recording save preserves physical lock and rejects late success after context replacement', async t => {
  const pending = deferred(), h = setup({ props: { actions: [action()] }, api: { postUiPageStepRecordingCommit: () => pending.promise } }); t.after(h.cleanup)
  h.saveVisible.value = true; h.stepName.value = 'Example'; const saving = h.saveRecording(); h.props.pageId = 2; h.saveVisible.value = true; h.stepName.value = 'Next'; await h.saveRecording(); assert.equal(h.writes.length, 1)
  pending.resolve({ data: { id: 0 } }); assert.equal(await saving, false); assert.equal(h.saveVisible.value, true); assert.equal(h.stepName.value, 'Next'); assert.equal(h.events.some(([event]) => event === 'saved'), false); assert.equal(h.saving.value, false)
})
test('empty or invalid recording never writes', async t => {
  const h = setup({ props: { actions: [] } }); t.after(h.cleanup); h.saveVisible.value = true; h.stepName.value = 'Example'; assert.equal(await h.saveRecording(), false)
  h.props.actions = [{ ...action(), detail: { type: 2, sql_execute: [{ datasource_alias: null, sql: '', key_list: '' }] } }]; assert.equal(await h.saveRecording(), false); assert.equal(h.writes.length, 0)
})
test('datasource options preserve zero IDs and reject out-of-order requests', async t => {
  const pending = deferred(); let count = 0
  const h = setup({ props: { projectProductId: 0 }, api: { getDataFactoryDatasourceAlias: () => ++count === 1 ? pending.promise : Promise.resolve({ data: [{ id: 0, name: 'Current', db_type: 0 }] }) } }); t.after(h.cleanup)
  const old = h.loadDatasourceAliases(); await h.loadDatasourceAliases(); pending.resolve({ data: [{ id: 1, name: 'Old', db_type: 1 }] }); await old; assert.deepEqual(h.datasourceAliasOptions.value, [{ value: 0, label: 'Current', dbType: 0 }]); assert.equal(h.datasourceLoading.value, false)
})
test('datasource failure exposes local retry and background invalidates pending requests', async t => {
  const pending = deferred(); let count = 0
  const h = setup({ props: { projectProductId: 0 }, api: { getDataFactoryDatasourceAlias: () => ++count === 1 ? Promise.reject(Error('Example unavailable')) : pending.promise } }); t.after(h.cleanup)
  await h.loadDatasourceAliases(); assert.equal(h.datasourceError.value, 'Example unavailable'); assert.equal(h.datasourceLoading.value, false)
  h.mount(); await flush(); h.visibility('hidden'); pending.resolve({ data: [{ id: 0, name: 'Late', db_type: 0 }] }); await flush(); assert.equal(h.datasourceAliasOptions.value.length, 0)
})
test('inline drafts remain private and preserve false values when emitted', async t => {
  const h = setup({ props: { actions: [action()] } }); t.after(h.cleanup)
  const fields = h.inlineEditorItems(h.props.actions[0]); assert.equal(fields.find(item => item.key === 'value').value, false); fields.find(item => item.key === 'value').value = 0
  assert.equal(h.props.actions[0].detail.custom[0].value, false); h.syncInlineConfig(h.props.actions[0]); assert.equal(h.events.find(([name]) => name === 'update-action')[1].detail.custom[0].value, 0)
})
test('recorder settings have one owner and emit an immutable updated value', async t => {
  const settings = { mergeInput: false, recordScroll: true, recordNavigation: false }
  const h = setup({ props: { recordingSettings: settings }, bindings: 'updateSetting,settings' }); t.after(h.cleanup)
  h.updateSetting('mergeInput', true); assert.equal(settings.mergeInput, false); assert.deepEqual(h.events.find(([event]) => event === 'settings-change')[1], { ...settings, mergeInput: true })
})
