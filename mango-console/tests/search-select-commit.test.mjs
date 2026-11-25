import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import * as vue from 'vue'
import { reactive } from 'vue'
import { harness, flush } from './helpers/case-details-harness.mjs'

function setup(t) {
  const previous = { document: globalThis.document, Element: globalThis.Element }
  globalThis.document = { visibilityState: 'visible', addEventListener() {}, removeEventListener() {} }
  class Target { constructor(popup = false) { this.popup = popup } closest() { return this.popup } }
  globalThis.Element = Target
  const attrs = reactive({ modelValue: [] })
  const state = harness('MangoSearchSelect', 'popupChanged,changed,leave,blurred,pointerMoved,search', {
    filename: path.resolve('src/components/business/MangoSearchSelect.vue'),
    modules: { vue: { ...vue, onMounted() {}, onActivated() {}, onBeforeUnmount() {}, onDeactivated() {}, useAttrs: () => attrs, getCurrentInstance: () => ({ uid: 1 }) } },
  })
  t.after(() => { state.close(); Object.assign(globalThis, previous) })
  return { ...state, attrs, Target, async wait() { await flush(); await new Promise(resolve => setTimeout(resolve, 550)); await flush() }, changes() { return state.events.filter(([name]) => name === 'change') } }
}

test('multiple selections remain local until the dropdown closes, then submit once', async t => {
  const h = setup(t)
  h.popupChanged(true)
  h.attrs.modelValue = [1]; h.changed()
  h.attrs.modelValue = [1, 2]; h.changed()
  await h.wait(); assert.equal(h.changes().length, 0)
  h.popupChanged(false); await h.wait()
  assert.deepEqual(h.changes(), [['change', [1, 2]]])
  h.blurred({}); h.leave(); await h.wait()
  assert.equal(h.changes().length, 1)
})

test('moving into the popup cancels search; leaving the entire control commits the latest values', async t => {
  const h = setup(t)
  h.popupChanged(true); h.attrs.modelValue = [1]; h.changed()
  h.pointerMoved({ target: new h.Target() })
  h.pointerMoved({ target: new h.Target(true) })
  await h.wait(); assert.equal(h.changes().length, 0)
  h.attrs.modelValue = [1, 2, 3]; h.changed()
  h.pointerMoved({ target: new h.Target() }); await h.wait()
  assert.deepEqual(h.changes(), [['change', [1, 2, 3]]])
})

test('clearing closed controls is debounced and unchanged dropdowns do not search', async t => {
  const h = setup(t)
  h.popupChanged(true); h.popupChanged(false); await h.wait()
  assert.equal(h.changes().length, 0)
  h.attrs.modelValue = [1]; h.changed(); await h.wait()
  h.attrs.modelValue = []; h.changed(); await h.wait()
  assert.deepEqual(h.changes(), [['change', [1]], ['change', []]])
})
