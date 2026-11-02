import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(new URL('../src/views/system/department/index.vue', import.meta.url), 'utf8')
const handler = source.slice(source.indexOf('  function onDelete('), source.indexOf('  function onDataForm('))
const compiled = ts.transpileModule(handler, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText

function setup(request) {
  let modal, refreshed = 0, messages = 0
  const onDelete = new Function('Modal', 'deleteUserDepartment', 'Message', 'doRefresh',
    `${compiled}; return onDelete`)(
    { confirm(options) { modal = options } }, request,
    { success() { messages++; return { close() {} } } }, () => { refreshed++ },
  )
  onDelete({ id: 42 })
  return { confirm: () => modal.onBeforeOk(), counts: () => ({ refreshed, messages }) }
}

test('department deletion resolves true after success, not the message handle', async () => {
  let resolve
  const state = setup(id => {
    assert.equal(id, 42)
    return new Promise(done => { resolve = done })
  })
  const pending = state.confirm()
  assert.deepEqual(state.counts(), { refreshed: 0, messages: 0 })
  resolve({ msg: '删除成功' })
  assert.equal(await pending, true)
  assert.deepEqual(state.counts(), { refreshed: 1, messages: 1 })
})

test('department deletion resolves false after failure so the modal can stop loading and remain open', async () => {
  const state = setup(() => Promise.reject(new Error('example failure')))
  assert.equal(await state.confirm(), false)
  assert.deepEqual(state.counts(), { refreshed: 1, messages: 0 })
})
