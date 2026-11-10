import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import * as vue from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/gray/feature')
const record = (id = 1) => ({
  id,
  name: `Feature ${id}`,
  gray_code: 'example',
  feature_key: 'example.enabled',
  config_type: 1,
  status: 0,
  default_restore: false,
  path_config: [{ path: 'example.enabled', value: false }],
  project_product: { id: 2, name: 'Product', project: { id: 3, name: 'Project' } },
  module: { id: 4, full_path: 'One / Two / Three' },
  yaml_file: { id: 5, name: 'File', file_path: 'example.yml' },
  datasource_alias: null,
  database: null,
})
const page = (rows = [record()], totalSize = rows.length) => ({ code: 200, data: rows, totalSize })
function fixture(api = {}) {
  const hooks = { mounted: [], activate: [], deactivate: [], unmount: [] },
    messages = [],
    dialogs = [],
    table = {}
  const f = harness('FeatureEditor', 'form', {
    base,
    api: {
      getGrayFeature: async () => page(),
      getGrayYamlFile: async () => ({ code: 200, data: [{ id: 5, name: 'File' }] }),
      putGrayFeature: async (p) => ({ code: 200, data: p }),
      deleteGrayFeature: async () => ({ code: 200 }),
      ...api,
    },
    modules: {
      vue: {
        ...vue,
        onMounted: (fn) => hooks.mounted.push(fn),
        onActivated: (fn) => hooks.activate.push(fn),
        onDeactivated: (fn) => hooks.deactivate.push(fn),
        onBeforeUnmount: (fn) => hooks.unmount.push(fn),
      },
      '@/hooks/table': table,
      '@arco-design/web-vue': {
        Message: Object.fromEntries(
          ['success', 'error', 'warning'].map((k) => [k, (text) => messages.push([k, text])])
        ),
        Modal: {
          confirm(config) {
            const dialog = {
              config,
              closed: false,
              close() {
                this.closed = true
                config.onClose?.()
              },
            }
            dialogs.push(dialog)
            return dialog
          },
        },
      },
    },
  })
  Object.assign(table, f.load('../../../hooks/table.ts'))
  const context = vue.ref('A'),
    blocked = vue.ref(false),
    scope = vue.effectScope()
  const query = vue.reactive(f.load('records.ts').createQuery())
  const list = scope.run(() =>
    f.load('composables/useFeatureList.ts').useFeatureList(query, () => context.value)
  )
  const updates = []
  const actions = scope.run(() =>
    f
      .load('composables/useFeatureMutations.ts')
      .useFeatureMutations({
        contextKey: () => context.value,
        blocked: () => blocked.value,
        applied: () => list.search(),
        statusApplied: (id, status) => updates.push([id, status]),
      })
  )
  return {
    ...list,
    ...actions,
    f,
    query,
    context,
    blocked,
    updates,
    dialogs,
    messages,
    hooks,
    cleanup() {
      hooks.unmount.forEach((fn) => fn())
      scope.stop()
      f.close()
    },
  }
}
test('query mapping preserves zero status, cascade leaf IDs and empty array reset', () => {
  const f = fixture()
  const q = f.query
  q.project_product = [1, 2]
  q.module = '__all__'
  q.status = [0, 1]
  q.config_type = [2, 3]
  q.yaml_file = [4, 5]
  assert.deepEqual(f.f.load('records.ts').requestParams(q, 2, 20), {
    page: 2,
    pageSize: 20,
    project_product: 2,
    status__in: '0,1',
    config_type__in: '2,3',
    yaml_file__in: '4,5',
  })
  Object.assign(q, f.f.load('records.ts').createQuery())
  assert.deepEqual(f.f.load('records.ts').requestParams(q, 1, 20), { page: 1, pageSize: 20 })
  f.cleanup()
})
test('finite rows preserve paths, false values and detached preview data', () => {
  const f = fixture(),
    source = record(),
    result = f.f.load('records.ts').featurePage(page([source]))
  assert.equal(result.rows[0].status, 0)
  assert.equal(result.rows[0].default_restore, false)
  assert.equal(result.rows[0].module.full_path, 'One / Two / Three')
  assert.equal(result.rows[0].yaml_file.file_path, 'example.yml')
  result.rows[0].path_config[0].value = true
  assert.equal(source.path_config[0].value, false)
  assert.deepEqual(f.f.load('records.ts').featurePage({ code: 200, data: [] }), {
    rows: [],
    total: 0,
  })
  f.cleanup()
})
for (const response of [
  { code: 500, data: [] },
  page([record(), record()]),
  page([record()], 0),
  page([{ ...record(), status: 8 }]),
  page([{ ...record(), config_type: '1' }]),
  page([{ ...record(), path_config: {} }]),
]) {
  test('invalid or duplicate page is rejected: ' + JSON.stringify(response), () => {
    const f = fixture()
    assert.throws(() => f.f.load('records.ts').featurePage(response))
    f.cleanup()
  })
}
test('list and options load independently and retain independent retry errors', async () => {
  const pending = deferred()
  let fail = true
  const f = fixture({
    getGrayFeature: () => pending.promise,
    getGrayYamlFile: async () => {
      if (fail) throw Error('offline')
      return { code: 200, data: [{ id: 8, name: 'New' }] }
    },
  })
  f.hooks.mounted.forEach((fn) => fn())
  await flush()
  assert.equal(f.loading.value, true)
  assert.equal(f.optionsLoading.value, false)
  assert.ok(f.optionsError.value)
  fail = false
  assert.equal(await f.loadOptions(), true)
  assert.equal(f.yamlOptions.value[0].value, 8)
  pending.resolve(page())
  await flush()
  assert.equal(f.loading.value, false)
  assert.equal(f.rows.value.length, 1)
  f.cleanup()
})
test('newer search owns rows, errors and loading after older request resolves', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const f = fixture({ getGrayFeature: () => (++count === 1 ? a.promise : b.promise) })
  const one = f.search(),
    two = f.search()
  a.resolve(page([record(1)]))
  await one
  assert.equal(f.loading.value, true)
  assert.equal(f.rows.value.length, 0)
  b.resolve(page([record(2)]))
  assert.equal(await two, true)
  assert.equal(f.rows.value[0].id, 2)
  f.cleanup()
})
for (const lifecycle of ['context', 'deactivate', 'unmount'])
  test('late reads ignored after ' + lifecycle, async () => {
    const pending = deferred()
    const f = fixture({ getGrayFeature: () => pending.promise })
    const promise = f.search()
    if (lifecycle === 'context') {
      f.context.value = 'B'
      f.context.value = 'A'
    } else f.hooks[lifecycle].forEach((fn) => fn())
    pending.resolve(page())
    assert.equal(await promise, false)
    assert.equal(f.rows.value.length, 0)
    assert.equal(f.loading.value, false)
    f.cleanup()
  })
test('KeepAlive activation resumes both data sources', async () => {
  let calls = 0
  const f = fixture({
    getGrayFeature: async () => {
      ++calls
      return page()
    },
  })
  f.hooks.mounted.forEach((fn) => fn())
  await flush()
  assert.equal(calls, 1)
  f.hooks.deactivate.forEach((fn) => fn())
  assert.equal(f.rows.value.length, 0)
  f.hooks.activate.forEach((fn) => fn())
  await flush()
  assert.equal(calls, 2)
  assert.equal(f.rows.value.length, 1)
  f.cleanup()
})
test('failed search retains visible data and can retry', async () => {
  let fail = false
  const f = fixture({
    getGrayFeature: async () => {
      if (fail) throw Error('offline')
      return page()
    },
  })
  await f.search()
  fail = true
  assert.equal(await f.search(), false)
  assert.equal(f.rows.value.length, 1)
  assert.ok(f.error.value)
  assert.equal(f.loading.value, false)
  fail = false
  assert.equal(await f.search(), true)
  assert.equal(f.error.value, '')
  f.cleanup()
})
test('deletion on final page clamps to actual final page', async () => {
  const calls = []
  const f = fixture({
    getGrayFeature: async (p) => {
      calls.push(p)
      return p.page > 1 ? page([], 1) : page()
    },
  })
  f.pagination.page = 2
  assert.equal(await f.search(), true)
  assert.equal(f.pagination.page, 1)
  assert.equal(f.rows.value[0].id, 1)
  assert.equal(calls.length, 2)
  f.cleanup()
})
test('status update locks all mutations until network and refresh finish', async () => {
  const pending = deferred()
  let calls = 0
  const f = fixture({
    putGrayFeature: () => {
      ++calls
      return pending.promise
    },
  })
  const first = f.onModifyStatus(true, 1)
  assert.equal(f.actionLoading.value, 'status-1')
  assert.equal(await f.onModifyStatus(false, 2), false)
  f.onDelete(record())
  assert.equal(f.dialogs.length, 0)
  pending.resolve({ code: 200, data: { id: 1, status: 1 } })
  assert.equal(await first, true)
  assert.deepEqual(f.updates, [[1, 1]])
  assert.equal(calls, 1)
  assert.equal(f.actionLoading.value, '')
  f.cleanup()
})
for (const data of [{ id: 2, status: 1 }, { id: 1, status: 0 }, {}])
  test('status acknowledgment mismatch does not update row: ' + JSON.stringify(data), async () => {
    const f = fixture({ putGrayFeature: async () => ({ code: 200, data }) })
    assert.equal(await f.onModifyStatus(true, 1), false)
    assert.equal(f.updates.length, 0)
    assert.equal(f.actionLoading.value, '')
    f.cleanup()
  })
test('successful write with failed refresh remains successful and reports read failure', async () => {
  const f = fixture({
    getGrayFeature: async () => {
      throw Error('offline')
    },
  })
  assert.equal(await f.onModifyStatus(false, 1), true)
  assert.deepEqual(f.updates, [[1, 0]])
  assert.ok(f.messages.some(([, text]) => text.includes('操作已完成')))
  f.cleanup()
})
test('delete confirmation snapshots target and closes explicitly after success', async () => {
  let deleted
  const f = fixture({
      deleteGrayFeature: async (id) => {
        deleted = id
        return { code: 200 }
      },
    }),
    source = record()
  f.onDelete(source)
  source.id = 99
  source.name = 'changed'
  const dialog = f.dialogs[0]
  assert.equal(f.actionLoading.value, 'confirm-1')
  assert.equal(await f.onModifyStatus(true, 2), false)
  assert.equal(await dialog.config.onBeforeOk(), false)
  assert.equal(deleted, 1)
  assert.equal(dialog.closed, true)
  assert.equal(f.actionLoading.value, '')
  f.cleanup()
})
test('failed delete keeps confirmation and supports explicit retry', async () => {
  let fail = true
  const f = fixture({ deleteGrayFeature: async () => ({ code: fail ? 500 : 200 }) })
  f.onDelete(record())
  const dialog = f.dialogs[0]
  await dialog.config.onBeforeOk()
  assert.equal(dialog.closed, false)
  assert.equal(f.actionLoading.value, 'confirm-1')
  fail = false
  await dialog.config.onBeforeOk()
  assert.equal(dialog.closed, true)
  f.cleanup()
})
for (const action of ['status', 'delete'])
  test('A-B-A invalidates ' + action + ' result while retaining physical lock', async () => {
    const pending = deferred(),
      f = fixture({
        putGrayFeature: () => pending.promise,
        deleteGrayFeature: () => pending.promise,
      })
    let promise
    if (action === 'delete') {
      f.onDelete(record())
      promise = f.dialogs[0].config.onBeforeOk()
    } else promise = f.onModifyStatus(true, 1)
    f.context.value = 'B'
    f.context.value = 'A'
    assert.ok(f.actionLoading.value)
    assert.equal(await f.onModifyStatus(true, 2), false)
    pending.resolve({ code: 200, data: { id: 1, status: 1 } })
    assert.equal(await promise, false)
    assert.equal(f.updates.length, 0)
    assert.equal(f.messages.length, 0)
    assert.equal(f.actionLoading.value, '')
    f.cleanup()
  })
test('stale confirmation cannot delete after environment changed', async () => {
  let calls = 0
  const f = fixture({
    deleteGrayFeature: async () => {
      ++calls
      return { code: 200 }
    },
  })
  f.onDelete(record())
  const dialog = f.dialogs[0]
  f.context.value = 'B'
  assert.equal(dialog.closed, true)
  await dialog.config.onBeforeOk()
  assert.equal(calls, 0)
  f.cleanup()
})
test('active editor or preview blocks mutations without role gating', async () => {
  const f = fixture()
  f.blocked.value = true
  assert.equal(await f.onModifyStatus(true, 1), false)
  f.onDelete(record())
  assert.equal(f.dialogs.length, 0)
  f.cleanup()
})
for (const lifecycle of ['deactivate', 'unmount'])
  test('physical mutation survives logical ' + lifecycle + ' until HTTP settles', async () => {
    const pending = deferred(),
      f = fixture({ putGrayFeature: () => pending.promise })
    const promise = f.onModifyStatus(true, 1)
    f.hooks[lifecycle].forEach((fn) => fn())
    assert.equal(f.actionLoading.value, 'status-1')
    if (lifecycle === 'deactivate') f.hooks.activate.forEach((fn) => fn())
    assert.equal(await f.onModifyStatus(false, 2), false)
    pending.resolve({ code: 200, data: { id: 1, status: 1 } })
    assert.equal(await promise, false)
    assert.equal(f.actionLoading.value, '')
    assert.equal(f.updates.length, 0)
    assert.equal(f.messages.length, 0)
    f.cleanup()
  })
