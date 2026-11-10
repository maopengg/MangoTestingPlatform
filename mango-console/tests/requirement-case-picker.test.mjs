import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/requirement/details')
const row = (id = 3) => ({ id, case_no: `CASE-${id}`, title: 'Example case', priority: 0, owner: { name: 'Example owner' } })
function setup(overrides = {}) {
  const hooks = { stop: [], activate: [], unmount: [] }, calls = [], notices = []
  const f = harness('RequirementCasePicker', 'open,reset,loadCases,save,selectRows,onVisibleChange,canCancel,visible,loading,saving,rows,selectedKeys,subject,readError,saveError', {
    base, props: { contextKey: 'A', requirementId: 1, productId: 2, available: true, boundIds: [4], priorityOptions: [] },
    api: {
      getManualCase: async query => { calls.push(['read', query]); return overrides.read ? overrides.read(query) : { data: [row(), row(4)] } },
      bindFunctionalRequirementCases: async (id, ids) => { calls.push(['bind', id, ids]); return overrides.write ? overrides.write(id, ids) : { data: { bound_count: 1 } } },
    },
    modules: {
      vue: { ...vue, onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'warning', 'error'].map(kind => [kind, text => notices.push([kind, text])])) },
    },
  })
  return { ...f, hooks, calls, notices, cleanup() { hooks.unmount.forEach(fn => fn()); f.close() } }
}
test('opening captures target and excludes bound cases without adding a new status filter', async () => {
  const f = setup()
  try {
    f.open(); assert.equal(f.visible.value, true); assert.equal(f.loading.value, true); await flush()
    assert.deepEqual(f.calls, [['read', { project_product: 2, page: 1, pageSize: 500 }]])
    assert.deepEqual(f.rows.value, [row()]); assert.equal(f.loading.value, false)
    f.props.boundIds.push(9); assert.deepEqual(f.subject.value.boundIds, [4])
    f.selectRows([3, '3', 4, 99, -1]); assert.deepEqual(f.selectedKeys.value, [3])
    await f.save(); assert.deepEqual(f.calls.at(-1), ['bind', 1, [3]])
    assert.equal(f.visible.value, false); assert.deepEqual(f.events, [['changed', 1]])
    assert.deepEqual(f.selectedKeys.value, [])
  } finally { f.cleanup() }
})
test('cancel and reopening clear old rows, selection and errors', async () => {
  const f = setup()
  try {
    f.open(); await flush(); f.selectRows([3]); f.saveError.value = true; f.onVisibleChange(false)
    assert.equal(f.visible.value, false); assert.deepEqual(f.rows.value, []); assert.deepEqual(f.selectedKeys.value, [])
    f.open(); await flush(); assert.equal(f.saveError.value, false); assert.deepEqual(f.selectedKeys.value, [])
  } finally { f.cleanup() }
})
test('read failure retains rows and selection and retries independently', async () => {
  let fail = false; const f = setup({ read: async () => { if (fail) throw Error('Offline'); return { data: [row()] } } })
  try {
    f.open(); await flush(); f.selectRows([3]); fail = true; await f.loadCases()
    assert.equal(f.readError.value, true); assert.equal(f.loading.value, false); assert.deepEqual(f.selectedKeys.value, [3]); assert.deepEqual(f.rows.value, [row()])
    fail = false; await f.loadCases(); assert.equal(f.readError.value, false)
    f.props.boundIds = [3]; await f.loadCases(); assert.deepEqual(f.rows.value, []); assert.deepEqual(f.selectedKeys.value, [])
  } finally { f.cleanup() }
})
test('out-of-order reads and reads from an earlier opening cannot replace current candidates', async () => {
  const a = deferred(), b = deferred(); let count = 0
  const f = setup({ read: () => ++count === 1 ? a.promise : b.promise })
  try {
    f.open(); const second = f.loadCases(); b.resolve({ data: [row(5)] }); await second
    a.resolve({ data: [row()] }); await flush(); assert.deepEqual(f.rows.value.map(x => x.id), [5])
    const old = deferred(); const g = setup({ read: () => old.promise })
    try { g.open(); g.onVisibleChange(false); old.resolve({ data: [row()] }); await flush(); assert.deepEqual(g.rows.value, []) } finally { g.cleanup() }
  } finally { f.cleanup() }
})
for (const data of [{}, [null], [{ id: 0 }], [{ id: '3' }]]) {
  test(`invalid candidate response ${JSON.stringify(data)} leaves a retryable error`, async () => {
    const f = setup({ read: async () => ({ data }) })
    try { f.open(); await flush(); assert.equal(f.readError.value, true); assert.equal(f.loading.value, false); assert.deepEqual(f.rows.value, []) } finally { f.cleanup() }
  })
}
test('empty selections, unknown IDs, loading and newly bound IDs cannot submit', async () => {
  const pending = deferred(), f = setup({ read: () => pending.promise })
  try {
    f.open(); f.selectRows([3]); await f.save(); assert.deepEqual(f.selectedKeys.value, [])
    pending.resolve({ data: [row()] }); await flush(); await f.save()
    f.selectedKeys.value = [999]; await f.save(); f.selectRows([3]); f.props.boundIds = [3]; await f.save()
    assert.equal(f.calls.filter(([kind]) => kind === 'bind').length, 0)
  } finally { f.cleanup() }
})
test('save failure and unconfirmed responses keep the window and draft open for retry', async () => {
  let response = Error('Offline'); const f = setup({ write: async () => { if (response instanceof Error) throw response; return response } })
  try {
    f.open(); await flush(); f.selectRows([3])
    for (const value of [Error('Offline'), { data: {} }, { data: { bound_count: -1 } }, { data: { bound_count: 1.5 } }]) {
      response = value; await f.save(); assert.equal(f.visible.value, true); assert.equal(f.saveError.value, true); assert.equal(f.saving.value, false); assert.deepEqual(f.selectedKeys.value, [3]); assert.deepEqual(f.events, [])
    }
    response = { data: { bound_count: 0 } }; await f.save(); assert.equal(f.visible.value, false); assert.deepEqual(f.events, [['changed', 1]])
  } finally { f.cleanup() }
})
test('physical save lock prevents duplicate requests, cancellation and reads until settlement', async () => {
  const pending = deferred(), f = setup({ write: () => pending.promise })
  try {
    f.open(); await flush(); f.selectRows([3]); const save = f.save(); await f.save(); f.open(); f.onVisibleChange(false); f.selectRows([]); await f.loadCases()
    assert.equal(f.canCancel(), false); assert.equal(f.visible.value, true); assert.deepEqual(f.selectedKeys.value, [3]); assert.equal(f.calls.length, 2)
    pending.resolve({ data: { bound_count: 1 } }); await save; assert.equal(f.canCancel(), true); assert.equal(f.visible.value, false)
  } finally { f.cleanup() }
})
for (const key of ['contextKey', 'requirementId', 'productId', 'available']) {
  test(`${key} A-B-A clears the opening and suppresses old reads`, async () => {
    const pending = deferred(), f = setup({ read: () => pending.promise })
    try {
      f.open(); const original = f.props[key]; f.props[key] = typeof original === 'string' ? 'B' : typeof original === 'boolean' ? false : 9; f.props[key] = original
      pending.resolve({ data: [row()] }); await flush(); assert.equal(f.visible.value, false); assert.deepEqual(f.rows.value, []); assert.equal(f.readError.value, false)
    } finally { f.cleanup() }
  })
}
for (const event of ['context', 'stop', 'unmount']) {
  test(`${event} closes the window, suppresses late writes and retains the physical lock`, async () => {
    const pending = deferred(), f = setup({ write: () => pending.promise })
    try {
      f.open(); await flush(); f.selectRows([3]); const save = f.save()
      if (event === 'context') f.props.contextKey = 'B'; else f.hooks[event].forEach(fn => fn())
      assert.equal(f.visible.value, false); assert.equal(f.exposed.isSaving(), true); f.open(); assert.equal(f.visible.value, false)
      pending.resolve({ data: { bound_count: 1 } }); await save
      assert.equal(f.saving.value, false); assert.deepEqual(f.events, []); assert.deepEqual(f.notices, [])
      if (event === 'stop') { f.hooks.activate.forEach(fn => fn()); f.open(); await flush(); assert.equal(f.visible.value, true) }
    } finally { f.cleanup() }
  })
}
test('invalid targets and unavailable context never request candidates', async () => {
  const f = setup()
  try {
    for (const [key, value] of [['requirementId', null], ['requirementId', 0], ['productId', null], ['available', false]]) {
      const old = f.props[key]; f.props[key] = value; f.open(); assert.equal(f.visible.value, false); f.props[key] = old
    }
    assert.deepEqual(f.calls, [])
  } finally { f.cleanup() }
})
test('late read and write failures from a closed context do not show stale errors', async () => {
  const read = deferred(), f = setup({ read: () => read.promise })
  try { f.open(); f.props.contextKey = 'B'; read.reject(Error('Offline')); await flush(); assert.equal(f.readError.value, false) } finally { f.cleanup() }
  const write = deferred(), g = setup({ write: () => write.promise })
  try { g.open(); await flush(); g.selectRows([3]); const save = g.save(); g.props.contextKey = 'B'; write.reject(Error('Offline')); await save; assert.equal(g.saveError.value, false); assert.deepEqual(g.notices, []) } finally { g.cleanup() }
})
test('parent and picker compile scripts, templates and scoped styles', async () => {
  for (const filename of [path.join(base, 'index.vue'), path.join(base, 'components/RequirementCasePicker.vue')]) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename }); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: 'requirement42' })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'requirement42', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ source: style.content, filename, id: 'requirement42', scoped: style.scoped, preprocessLang: style.lang })).errors, [])
  }
})
