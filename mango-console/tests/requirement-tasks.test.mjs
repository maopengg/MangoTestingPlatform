import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyleAsync } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/requirement/details')
const task = (fields = {}) => ({ id: 3, requirement_version: 1, name: 'Example task', task_type: 0, status: 0,
  owner: { id: 4, name: 'Example owner' }, planned_start_date: '2026-11-01', planned_end_date: '2026-11-02',
  estimated_person_days: '0.00', actual_person_days: null, self_test_status: 0, sort_order: 0, remark: 'Retained server note', update_user: { id: 9 }, ...fields })
const acknowledgement = body => task({ ...body, id: body.id ?? 5, owner: body.owner ? { id: body.owner, name: 'Example owner' } : null })
const settle = async () => { await flush(); await new Promise(resolve => setImmediate(resolve)); await flush() }
function setup(overrides = {}) {
  const hooks = { mount: [], stop: [], activate: [], unmount: [] }, calls = [], dialogs = [], notices = []
  const f = harness('RequirementTasks', 'rows,loading,readError,needsLoad,canEdit,workers,deletingKeys,dialogs,loadTasks,addTask,saveTask,removeTask,isSaving,isBlocked,ownerOptions,persistedCount,completedCount', {
    base, props: { contextKey: 'A', requirementId: 1, enabled: true, users: [] },
    api: {
      getFunctionalRequirementTasks: async id => { calls.push(['read', id]); return overrides.read ? overrides.read(id) : { data: [task()] } },
      postFunctionalRequirementTask: async body => { calls.push(['post', body]); return overrides.write ? overrides.write(body) : { data: acknowledgement(body) } },
      putFunctionalRequirementTask: async body => { calls.push(['put', body]); return overrides.write ? overrides.write(body) : { data: acknowledgement(body) } },
      deleteFunctionalRequirementTask: async id => { calls.push(['delete', id]); return overrides.remove ? overrides.remove(id) : {} },
    },
    modules: {
      vue: { ...vue, onMounted: fn => hooks.mount.push(fn), onDeactivated: fn => hooks.stop.push(fn), onActivated: fn => hooks.activate.push(fn), onBeforeUnmount: fn => hooks.unmount.push(fn) },
      '@arco-design/web-vue': { Message: Object.fromEntries(['success', 'warning', 'error'].map(kind => [kind, text => notices.push([kind, text])])), Modal: { warning(config) { const handle = { closed: false, close() { handle.closed = true } }; dialogs.push({ config, handle }); return handle } } },
      ...(overrides.modules || {}),
    },
  })
  return { ...f, hooks, calls, confirmations: dialogs, notices, cleanup() { hooks.unmount.forEach(fn => fn()); f.close() } }
}
test('mount reads independently, keeps typed drafts separate and preserves zero and nullable fields', async () => {
  const original = task(), f = setup({ read: async () => ({ data: [original] }) })
  try {
    f.hooks.mount.forEach(fn => fn()); f.hooks.activate.forEach(fn => fn()); await settle()
    assert.deepEqual(f.calls, [['read', 1]]); const row = f.rows.value[0]
    assert.equal(row.form.owner, 4); assert.equal(row.form.estimated_person_days, 0); assert.equal(row.form.actual_person_days, null)
    row.form.name = 'Draft'; assert.equal(original.name, 'Example task'); assert.equal(row.confirmed.name, 'Example task')
    assert.equal(f.persistedCount.value, 1); assert.equal(f.completedCount.value, 0)
    assert.deepEqual(f.ownerOptions(row), [{ key: 4, title: 'Example owner' }])
    f.props.users = [{ key: 4, title: 'Loaded owner' }]; assert.equal(f.ownerOptions(row)[0].title, 'Loaded owner')
  } finally { f.cleanup() }
})
test('bad or failed reads retain current rows and permit retry', async () => {
  let response = { data: [task()] }, f = setup({ read: async () => { if (response instanceof Error) throw response; return response } })
  try {
    await f.loadTasks()
    for (const data of [Error('Offline'), { data: {} }, { data: [task({ requirement_version: 9 })] }, { data: [task(), task()] }]) {
      response = data; assert.equal(await f.loadTasks(), false); assert.equal(f.readError.value, true); assert.equal(f.rows.value.length, 1); assert.equal(f.loading.value, false)
    }
    response = { data: [] }; await f.loadTasks(); assert.deepEqual(f.rows.value, []); assert.equal(f.readError.value, false)
  } finally { f.cleanup() }
})
test('out-of-order list responses and old failures cannot overwrite current task data', async () => {
  const a = deferred(), b = deferred(); let count = 0
  const f = setup({ read: () => ++count === 1 ? a.promise : b.promise })
  try {
    const first = f.loadTasks(), second = f.loadTasks(); b.resolve({ data: [task({ id: 6 })] }); await second
    a.reject(Error('Late')); await first; assert.equal(f.rows.value[0].id, 6); assert.equal(f.readError.value, false)
  } finally { f.cleanup() }
})
test('unsaved or failed drafts are never discarded by a list refresh', async () => {
  const f = setup()
  try {
    await f.loadTasks(); const row = f.rows.value[0]; row.form.name = 'Unsaved'
    assert.equal(await f.loadTasks(), false); assert.equal(f.rows.value[0].form.name, 'Unsaved'); assert.equal(f.calls.length, 1)
    f.addTask(); assert.equal(await f.loadTasks(), false); assert.equal(f.rows.value.length, 2)
  } finally { f.cleanup() }
})
test('new local rows get distinct stable keys and deleting unsaved rows sends no request', async () => {
  const f = setup()
  try {
    await f.loadTasks(); f.addTask(); f.addTask(); assert.equal(new Set(f.rows.value.map(row => row.key)).size, 3)
    const row = f.rows.value[1]; assert.equal(row.id, null); assert.equal(row.form.sort_order, 2)
    f.removeTask(row); assert.equal(f.rows.value.length, 2); assert.equal(f.confirmations.length, 0); assert.equal(f.calls.length, 1)
  } finally { f.cleanup() }
})
test('save sends a whitelist, maps owner and clears dates, never submitting server metadata', async () => {
  const f = setup()
  try {
    await f.loadTasks(); const row = f.rows.value[0]; Object.assign(row.form, { name: 'Changed', owner: null, planned_start_date: null, planned_end_date: '', actual_person_days: 0, unexpected: 'not submitted' })
    assert.equal(await f.saveTask(row), true)
    assert.deepEqual(f.calls.at(-1), ['put', { id: 3, requirement_version: 1, name: 'Changed', task_type: 0, status: 0, owner: null, planned_start_date: null, planned_end_date: null, estimated_person_days: 0, actual_person_days: 0, self_test_status: 0, sort_order: 0 }])
    assert.equal(row.confirmed.name, 'Changed'); assert.equal(row.confirmed.owner, null); assert.equal(row.error, false)
  } finally { f.cleanup() }
})
test('unchanged fields and duplicate blur events do not submit repeated updates', async () => {
  const pending = deferred(), f = setup({ write: () => pending.promise })
  try {
    await f.loadTasks(); const row = f.rows.value[0]; await f.saveTask(row); assert.equal(f.calls.length, 1)
    row.form.name = 'Changed'; const first = f.saveTask(row), second = f.saveTask(row)
    assert.equal(first, second); assert.equal(f.calls.length, 2)
    pending.resolve({ data: task({ name: 'Changed' }) }); await first; assert.equal(f.calls.length, 2); assert.equal(f.isSaving(), false)
  } finally { f.cleanup() }
})
test('rapid edits serialize per row and earlier acknowledgements do not overwrite newer drafts', async () => {
  const first = deferred(), second = deferred(); let count = 0
  const f = setup({ write: () => ++count === 1 ? first.promise : second.promise })
  try {
    await f.loadTasks(); const row = f.rows.value[0]; row.form.name = 'First'; const save = f.saveTask(row)
    row.form.name = 'Latest'; row.form.status = 2; f.saveTask(row)
    assert.equal(count, 1); assert.equal(f.completedCount.value, 0)
    first.resolve({ data: task({ name: 'First' }) }); await settle()
    assert.equal(count, 2); assert.equal(row.form.name, 'Latest'); assert.equal(f.calls.at(-1)[1].status, 2)
    second.resolve({ data: task({ name: 'Latest', status: 2 }) }); await save
    assert.equal(f.completedCount.value, 1); assert.equal(row.confirmed.name, 'Latest')
  } finally { f.cleanup() }
})
test('creating then editing a pending draft uses one POST followed by PUT with the confirmed ID', async () => {
  const pending = deferred(); let count = 0
  const f = setup({ write: body => ++count === 1 ? pending.promise : Promise.resolve({ data: acknowledgement(body) }) })
  try {
    await f.loadTasks(); f.addTask(); const row = f.rows.value[1], key = row.key; row.form.name = 'New'; const save = f.saveTask(row)
    row.form.name = 'Updated new'; f.saveTask(row)
    pending.resolve({ data: acknowledgement(f.calls[1][1]) }); await save
    assert.deepEqual(f.calls.slice(1).map(([kind]) => kind), ['post', 'put']); assert.equal(f.calls.at(-1)[1].id, 5)
    assert.equal(row.id, 5); assert.equal(row.key, key); assert.equal(f.persistedCount.value, 2)
  } finally { f.cleanup() }
})
test('failed writes keep current draft, restore controls, and retry with the latest value', async () => {
  let fail = true, f = setup({ write: async body => { if (fail) throw Error('Offline'); return { data: acknowledgement(body) } } })
  try {
    await f.loadTasks(); const row = f.rows.value[0]; row.form.name = 'Failed draft'
    assert.equal(await f.saveTask(row), false); assert.equal(row.error, true); assert.equal(f.isSaving(), false); assert.equal(row.confirmed.name, 'Example task')
    row.form.name = 'Retry draft'; fail = false; assert.equal(await f.saveTask(row), true); assert.equal(row.confirmed.name, 'Retry draft'); assert.equal(row.error, false)
  } finally { f.cleanup() }
})
test('synchronous request setup failure releases the already registered write lock', async () => {
  const f = setup({ modules: { '@/api/functional-test': { getFunctionalRequirementTasks: async () => ({ data: [task()] }), putFunctionalRequirementTask() { throw Error('Setup failed') } } } })
  try {
    await f.loadTasks(); const row = f.rows.value[0]; row.form.name = 'Draft'; assert.equal(await f.saveTask(row), false)
    assert.equal(f.isSaving(), false); assert.equal(row.error, true); assert.equal(f.workers.size, 0)
  } finally { f.cleanup() }
})
test('independent rows save concurrently while each row keeps its own acknowledgement and lock', async () => {
  const a = deferred(), b = deferred(), f = setup({ read: async () => ({ data: [task(), task({ id: 6 })] }), write: body => body.id === 3 ? a.promise : b.promise })
  try {
    await f.loadTasks(); const [first, second] = f.rows.value; first.form.status = 2; second.form.name = 'Second'
    const saveA = f.saveTask(first), saveB = f.saveTask(second); assert.equal(f.workers.size, 2)
    b.resolve({ data: task({ id: 6, name: 'Second' }) }); await saveB; assert.equal(f.workers.size, 1); assert.equal(second.confirmed.name, 'Second'); assert.equal(f.completedCount.value, 0)
    a.resolve({ data: task({ status: 2 }) }); await saveA; assert.equal(f.completedCount.value, 1); assert.equal(f.workers.size, 0)
  } finally { f.cleanup() }
})
test('a failed earlier write preserves newer queued edits without silently retrying them', async () => {
  const pending = deferred(); let retry = false
  const f = setup({ write: body => retry ? Promise.resolve({ data: acknowledgement(body) }) : pending.promise })
  try {
    await f.loadTasks(); const row = f.rows.value[0]; row.form.name = 'First'; const save = f.saveTask(row)
    row.form.name = 'Latest'; f.saveTask(row); pending.reject(Error('Offline')); await save
    assert.equal(row.form.name, 'Latest'); assert.equal(row.confirmed.name, 'Example task'); assert.equal(row.error, true); assert.equal(f.calls.length, 2)
    retry = true; await f.saveTask(row); assert.equal(row.confirmed.name, 'Latest')
  } finally { f.cleanup() }
})
for (const bad of [{}, task({ id: 99 }), task({ requirement_version: 99 })]) {
  test(`unconfirmed write ${JSON.stringify(bad)} cannot update confirmed values`, async () => {
    const f = setup({ write: async () => ({ data: bad }) })
    try { await f.loadTasks(); const row = f.rows.value[0]; row.form.status = 2; await f.saveTask(row); assert.equal(row.error, true); assert.equal(f.completedCount.value, 0); assert.equal(row.form.status, 2) } finally { f.cleanup() }
  })
}
test('delete confirmation captures target and blocks edits and duplicate confirmation while writing', async () => {
  const pending = deferred(), f = setup({ remove: () => pending.promise })
  try {
    await f.loadTasks(); const row = f.rows.value[0]; f.removeTask(row); f.removeTask(row)
    const { config } = f.confirmations[0]; assert.equal(f.confirmations.length, 1); assert.match(config.content, /Example task/)
    assert.equal(f.isBlocked(row), true); row.form.name = 'Later'; const deletion = config.onBeforeOk(); await config.onBeforeOk(); await f.saveTask(row)
    assert.equal(config.onBeforeCancel(), false); assert.deepEqual(f.calls.at(-1), ['delete', 3]); assert.equal(f.calls.filter(([kind]) => kind === 'delete').length, 1)
    pending.resolve({}); assert.equal(await deletion, true); assert.equal(f.rows.value.length, 0); assert.equal(f.persistedCount.value, 0)
  } finally { f.cleanup() }
})
test('delete failure keeps the confirmation and row for retry and normal cancel releases the row', async () => {
  let fail = true, f = setup({ remove: async () => { if (fail) throw Error('Offline'); return {} } })
  try {
    await f.loadTasks(); const row = f.rows.value[0]; f.removeTask(row); const dialog = f.confirmations[0].config
    assert.equal(await dialog.onBeforeOk(), false); assert.equal(f.rows.value.length, 1); assert.equal(f.isSaving(), false); assert.equal(dialog.onBeforeCancel(), true)
    fail = false; assert.equal(await dialog.onBeforeOk(), true); assert.equal(f.rows.value.length, 0)
    await f.loadTasks(); f.removeTask(f.rows.value[0]); f.confirmations[1].config.onCancel(); assert.equal(f.isBlocked(f.rows.value[0]), false)
  } finally { f.cleanup() }
})
test('a saving row cannot be deleted, and stale or foreign row references cannot trigger writes', async () => {
  const pending = deferred(), f = setup({ write: () => pending.promise })
  try {
    await f.loadTasks(); const row = f.rows.value[0]; row.form.name = 'Saving'; const save = f.saveTask(row)
    f.removeTask(row); assert.equal(f.confirmations.length, 0)
    const foreign = { ...row }; await f.saveTask(foreign); f.removeTask(foreign); assert.equal(f.calls.length, 2)
    pending.resolve({ data: task({ name: 'Saving' }) }); await save
  } finally { f.cleanup() }
})
for (const key of ['contextKey', 'requirementId', 'enabled']) {
  test(`${key} A-B-A invalidates reads and clears local drafts`, async () => {
    const pending = deferred(), f = setup({ read: () => pending.promise })
    try {
      const read = f.loadTasks(), original = f.props[key]; f.props[key] = key === 'contextKey' ? 'B' : key === 'enabled' ? false : 9; f.props[key] = original
      pending.resolve({ data: [task()] }); await read; assert.deepEqual(f.rows.value, []); assert.equal(f.readError.value, false)
    } finally { f.cleanup() }
  })
}
test('identity change during write suppresses acknowledgements and defers current reads until physical completion', async () => {
  const pending = deferred(), f = setup({ write: () => pending.promise })
  try {
    f.hooks.mount.forEach(fn => fn()); await settle(); const row = f.rows.value[0]; row.form.name = 'Old write'; const save = f.saveTask(row)
    f.props.contextKey = 'B'; assert.deepEqual(f.rows.value, []); assert.equal(f.canEdit.value, false); assert.equal(f.needsLoad.value, true)
    f.addTask(); assert.deepEqual(f.rows.value, []); pending.resolve({ data: task({ name: 'Old write' }) }); await save; await settle()
    assert.equal(f.calls.filter(([kind]) => kind === 'read').length, 2); assert.equal(f.rows.value[0].form.name, 'Example task'); assert.equal(f.canEdit.value, true); assert.deepEqual(f.notices, [])
  } finally { f.cleanup() }
})
for (const event of ['stop', 'unmount']) {
  test(`${event} closes delete confirmation, suppresses late result and holds physical lock`, async () => {
    const pending = deferred(), f = setup({ remove: () => pending.promise })
    try {
      f.hooks.mount.forEach(fn => fn()); await settle(); f.removeTask(f.rows.value[0]); const deletion = f.confirmations[0].config.onBeforeOk()
      f.hooks[event].forEach(fn => fn()); assert.equal(f.confirmations[0].handle.closed, true); assert.deepEqual(f.rows.value, []); assert.equal(f.isSaving(), true)
      if (event === 'stop') f.hooks.activate.forEach(fn => fn())
      pending.resolve({}); await deletion; await settle(); assert.deepEqual(f.notices, []); assert.equal(f.isSaving(), false)
      assert.equal(f.rows.value.length, event === 'stop' ? 1 : 0)
    } finally { f.cleanup() }
  })
}
test('inactive and invalid contexts do not create or read tasks and activation restores once', async () => {
  const f = setup()
  try {
    f.props.enabled = false; f.hooks.mount.forEach(fn => fn()); f.addTask(); await f.loadTasks(); assert.deepEqual(f.calls, [])
    f.props.enabled = true; await settle(); assert.equal(f.calls.length, 1)
    f.hooks.stop.forEach(fn => fn()); f.addTask(); await f.loadTasks(); assert.deepEqual(f.rows.value, [])
    f.hooks.activate.forEach(fn => fn()); await settle(); assert.equal(f.calls.length, 2)
  } finally { f.cleanup() }
})
test('task panel and parent compile scripts, templates and scoped styles', async () => {
  for (const filename of [path.join(base, 'index.vue'), path.join(base, 'components/RequirementTasks.vue')]) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename }); assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: 'requirement42tasks' })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: 'requirement42tasks', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    for (const style of descriptor.styles) assert.deepEqual((await compileStyleAsync({ source: style.content, filename, id: 'requirement42tasks', scoped: style.scoped, preprocessLang: style.lang })).errors, [])
  }
})
