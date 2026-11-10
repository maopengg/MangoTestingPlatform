import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { readFileSync } from 'node:fs'
import { compileScript, compileStyle, compileTemplate, parse } from '@vue/compiler-sfc'
import { harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/iteration')
function setup() {
  const hooks = { stop: [], activate: [], unmount: [] }
  const f = harness('RequirementKanban', 'dragging,dragStart,drop', {
    base, props: { columns: [{ status: 3, title: 'Developing', items: [{ id: 11, status: 3 }] }, { status: 4, title: 'Pending', items: [] }], loading: false, busyIds: [], contextKey: 'A' },
    modules: { vue: { ...vue, onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) } },
  })
  return { ...f, hooks, cleanup: () => { hooks.unmount.forEach(fn => fn()); f.close() } }
}
test('drop emits the owned row once, leaves parent data unchanged, and clears dragging', () => {
  const f = setup()
  try {
    const row = f.props.columns[0].items[0]; f.dragStart(row); f.drop(4); f.drop(4)
    assert.equal(f.events.length, 1); assert.equal(f.events[0][0], 'move'); assert.equal(f.events[0][1].item, row)
    assert.equal(row.status, 3); assert.equal(f.props.columns[0].items.length, 1); assert.equal(f.dragging.value, null)
  } finally { f.cleanup() }
})
test('same status, unknown column, foreign row and busy row never emit writes', () => {
  const f = setup()
  try {
    const row = f.props.columns[0].items[0]
    f.dragStart(row); f.drop(3); f.dragStart(row); f.drop(999)
    f.dragStart({ ...row }); f.drop(4)
    f.props.busyIds = [11]; f.dragStart(row); f.drop(4)
    assert.deepEqual(f.events, [])
  } finally { f.cleanup() }
})
test('data reload, loading or context changes invalidate an in-progress drag', () => {
  const f = setup()
  try {
    f.dragStart(f.props.columns[0].items[0]); f.props.contextKey = 'B'; f.props.contextKey = 'A'; f.drop(4)
    f.dragStart(f.props.columns[0].items[0]); f.props.loading = true; f.drop(4)
    f.props.loading = false; f.dragStart(f.props.columns[0].items[0]); f.props.columns = [...f.props.columns]; f.drop(4)
    assert.deepEqual(f.events, [])
  } finally { f.cleanup() }
})
test('deactivation and unmount cancel drags; activation permits a fresh drag', () => {
  const f = setup()
  try {
    const row = f.props.columns[0].items[0]
    f.dragStart(row); f.hooks.stop.forEach(fn => fn()); f.drop(4); f.dragStart(row); f.drop(4)
    assert.deepEqual(f.events, [])
    f.hooks.activate.forEach(fn => fn()); f.dragStart(row); f.drop(4); assert.equal(f.events.length, 1)
    f.hooks.unmount.forEach(fn => fn()); f.dragStart(row); f.drop(4); assert.equal(f.events.length, 1)
  } finally { f.cleanup() }
})
test('kanban SFC script, template and scoped styles compile', () => {
  const filename = path.join(base, 'components/RequirementKanban.vue'), { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'kanban' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'kanban', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  for (const style of descriptor.styles) assert.deepEqual(compileStyle({ source: style.content, filename, id: 'kanban', scoped: style.scoped, preprocessLang: style.lang }).errors, [])
})
