import assert from 'node:assert/strict'
import test from 'node:test'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { setupExecution } from './helpers/factory-execution-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'

const setup = (api) => setupExecution('CleanupCompensationDrawer',
  'open,visible,busy,form,confirmation,preview,execute', api)

test('compensation component compiles and does not introduce a permission-based hidden action', () => {
  const filename = 'src/views/data-factory/execution/components/CleanupCompensationDrawer.vue'
  const source = readFileSync(filename, 'utf8')
  const { descriptor, errors } = parse(source)
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: filename })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename,
    compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  assert.doesNotMatch(source, /v-permission/)
})

test('execution requires matching preview and carries only original item and mapping, not caller IDs', async () => {
  const calls = []
  const s = setup({ postDataFactoryExecutionCleanup: async (value) => {
    calls.push(value)
    return { data: value.preview ? { preview_token: 'fixture-confirmation', confirm_text: 'fixture-text' } : { fail: 0 } }
  } })
  try {
    s.open(5, { item_id: 4, snapshot_index: 0 })
    s.form.reason = 'AUTO approved recovery'
    await flush()
    await s.execute()
    assert.equal(calls.length, 0)
    await s.preview()
    await s.execute()
    assert.equal(calls.length, 2)
    assert.equal(calls[1].preview_token, 'fixture-confirmation')
    assert.equal(calls[1].compensation.item_id, 4)
    assert.equal(calls[1].compensation.document_id, undefined)
    assert.equal(s.visible.value, false)
  } finally { s.dispose() }
})

test('editing compensation invalidates preview; late preview cannot reopen a closed role session', async () => {
  const pending = deferred(), calls = []
  const s = setup({ postDataFactoryExecutionCleanup: async (value) => {
    calls.push(value)
    if (calls.length === 1) return { data: { preview_token: 'fixture', confirm_text: 'fixture' } }
    return pending.promise
  } })
  try {
    s.open(5, { item_id: 4, snapshot_index: 0 })
    s.form.reason = 'AUTO initial'
    await flush()
    await s.preview()
    s.form.reason = 'AUTO changed'
    await flush()
    await s.execute()
    assert.equal(calls.length, 1)
    const loading = s.preview()
    s.user.roleId = 2
    await flush()
    pending.resolve({ data: { preview_token: 'obsolete', confirm_text: 'obsolete' } })
    await loading
    assert.equal(s.visible.value, false)
    assert.equal(s.confirmation.value, null)
    assert.equal(s.busy.value, false)
  } finally { s.dispose() }
})
