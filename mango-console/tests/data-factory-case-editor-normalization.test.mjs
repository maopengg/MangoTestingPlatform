import assert from 'node:assert/strict'
import test from 'node:test'
import { factoryEditor, factoryRecord, factoryDto, lossless, template } from './helpers/factory-editor-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { loadModule } from './helpers/auth-config-harness.mjs'
const dto = loadModule('src/components/DataFactory/case-config-editor.ts', { '@/utils/lossless-json': lossless, './case-config-record': factoryDto })
test('preview DTO preserves backend values, validity, missing-field messages and dependency evidence', () => {
  const field = { name: 'example', value: { id: '90071992547409930000' }, valid: false, message: 'Missing reference', deferred: true }
  const value = dto.readFactoryPreview({ fields: [field], dependency_tree: { template_id: 0, value: field.value, message: 'Missing reference', strategy: 'create', fields: [field], missing_fields: [{ field: 'example', message: 'Missing reference' }] } })
  assert.deepEqual(value.fields[0].value, field.value); assert.equal(value.fields[0].valid, false); assert.equal(value.fields[0].deferred, true); assert.equal(value.dependency_tree.missing_fields[0].message, field.message); assert.equal(value.dependency_tree.template_id, 0)
  assert.throws(() => dto.readFactoryPreview({ fields: [{ name: 'bad', valid: 'false' }] }))
})
test('readonly panel loads the shared fields and case overrides without dispatching writes', async t => {
  const h = factoryEditor({ props: { readonly: true } }); t.after(h.cleanup)
  const record = factoryRecord(); await h.openReadonly(record)
  assert.equal(h.visible.value, true); assert.equal(h.form.template, 7); assert.equal(h.fieldRows.value[0].name, 'name'); assert.deepEqual(h.form.field_overrides, record.field_overrides); assert.notEqual(h.form.field_overrides, record.field_overrides); assert.equal(h.previewResult.value.fields[0].value, 'example'); assert.equal(await h.save(), false); assert.equal(h.calls.length, 0)
})
test('old preview cannot replace a new template and old finally cannot clear the newer loading state', async t => {
  const old = deferred(), next = deferred(); let count = 0
  const h = factoryEditor({ api: { postDataFactoryCaseConfigPreview: () => ++count === 1 ? old.promise : next.promise } }); t.after(h.cleanup)
  h.visible.value = true; h.form.template = 7; const first = h.loadCasePreview(); h.form.template = 8; const second = h.loadCasePreview()
  old.resolve({ code: 200, data: { fields: [{ name: 'old', value: 'old' }] } }); assert.equal(await first, false); assert.equal(h.previewLoading.value, 'form'); assert.equal(h.previewResult.value.fields.length, 0)
  next.resolve({ code: 200, data: { fields: [{ name: 'new', value: 'new' }] } }); assert.equal(await second, true); assert.equal(h.previewLoading.value, null); assert.equal(h.previewResult.value.fields[0].name, 'new')
})
test('preview payload is a fixed private snapshot and changing overrides rejects the old response', async t => {
  const pending = deferred(); let payload
  const h = factoryEditor({ api: { postDataFactoryCaseConfigPreview: value => { payload = value; return pending.promise } } }); t.after(h.cleanup)
  h.visible.value = true; h.form.template = 0; h.form.field_overrides = { name: { generator_type: 1, generator_config: { value: 'before' } } }; const request = h.loadCasePreview(); h.form.field_overrides.name.generator_config.value = 'after'
  assert.equal(payload.template_id, 0); assert.equal(payload.preview_mode, 'configuration'); assert.equal(payload.field_overrides.name.generator_config.value, 'before'); pending.resolve({ code: 200, data: { fields: [{ name: 'old' }] } }); assert.equal(await request, false); assert.equal(h.previewResult.value.fields.length, 0)
})
test('closed/reopened editor and changed identities invalidate pending responses including A-B-A', async () => {
  for (const change of [h => { h.visible.value = false; h.visible.value = true }, h => { h.user.selected_environment = 1; h.user.selected_environment = 0 }, h => h.permission.permissionKeys.push('example:read'), h => h.props.caseId = 1, h => h.visibility('hidden')]) {
    const pending = deferred(), h = factoryEditor({ api: { postDataFactoryCaseConfigPreview: () => pending.promise } })
    try { h.visible.value = true; h.form.template = 7; const request = h.loadCasePreview(); change(h); pending.resolve({ code: 200, data: { fields: [{ name: 'stale' }] } }); assert.equal(await request, false); assert.equal(h.previewResult.value.fields.length, 0); assert.equal(h.previewLoading.value, null) } finally { h.cleanup() }
  }
})
test('failed resources expose independent retry without resetting the edited draft', async t => {
  let fail = true; const h = factoryEditor({ api: { postDataFactoryCaseConfigPreview: async () => { if (fail) throw Error('network'); return { code: 200, data: { fields: [{ name: 'new', value: 0 }] } } } } }); t.after(h.cleanup)
  h.visible.value = true; h.form.template = 7; h.form.name = 'Keep draft'; assert.equal(await h.loadCasePreview(), false); assert.equal(h.editorFailures.value.length, 1); assert.equal(h.editorPending.fields, false); fail = false; assert.equal(await h.editorFailures.value[0].retry(), true); assert.equal(h.editorFailures.value.length, 0); assert.equal(h.form.name, 'Keep draft'); assert.equal(h.previewResult.value.fields[0].value, 0)
})
test('changing project rejects old aliases and selected-template responses', async t => {
  const pending = deferred(), h = factoryEditor({ api: { getDataFactoryDatasourceAlias: () => pending.promise } }); t.after(h.cleanup)
  h.visible.value = true; h.form.project_product = 0; const request = h.loadDatasourceAliases(0); h.form.project_product = 1; h.onProjectProductChange(); pending.resolve({ code: 200, data: [{ id: 0, name: 'old' }] }); assert.equal(await request, false); await flush(); assert.equal(h.form.template, null)
})
