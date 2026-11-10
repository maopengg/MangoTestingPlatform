import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush as flushVue, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/pytest/product'),
  response = (data) => ({ code: 200, data })
const row = (id = 1, patch = {}) => ({
  id,
  name: 'Fixture ' + id,
  file_name: 'project',
  auto_type: 0,
  test_dir: ['tests'],
  case_count: 0,
  project_product: { id: 10, name: 'Product', project: { id: 20, name: 'Project' } },
  repository: { id: 0, name: 'Repository', active_branch: 'main', default_branch: 'main' },
  ...patch,
})
async function flush() {
  await flushVue()
  await new Promise((resolve) => setImmediate(resolve))
}
function setup(kind = 'editor', api = {}) {
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 }),
    route = vue.reactive({ fullPath: '/pytest/product/index' })
  const projects = vue.reactive({
    projectProduct: [{ value: 20, label: 'Project', children: [{ value: 10, label: 'Product' }] }],
    optionErrors: { products: false },
    projectProductName: () => (api.projects ? api.projects(projects) : Promise.resolve()),
    projectPytestName: () => Promise.resolve(),
  })
  const calls = [],
    messages = [],
    confirmations = [],
    life = { mount: [], unmount: [], activate: [], deactivate: [] }
  const originalDocument = globalThis.document,
    doc = Object.assign(new EventTarget(), { hidden: false }),
    listeners = new Set()
  const add = doc.addEventListener.bind(doc),
    remove = doc.removeEventListener.bind(doc)
  doc.addEventListener = (type, fn) => {
    listeners.add(fn)
    add(type, fn)
  }
  doc.removeEventListener = (type, fn) => {
    listeners.delete(fn)
    remove(type, fn)
  }
  globalThis.document = doc
  const invoke = (name, args, fallback) => {
    calls.push([name, ...args])
    return api[name] ? api[name](...args) : Promise.resolve(fallback)
  }
  const h = harness(
    kind === 'editor' ? 'PytestBindingEditor' : 'index',
    kind === 'editor'
      ? 'visible,saving,record,draft,projectLoading,projectFailed,repositoryLoading,repositoryFailed,directoryLoading,directoryFailed,testLoading,testFailed,repositoryOptions,repositoryDirectoryOptions,testDirectoryOptions,open,closeDialog:close,save,loadProjects,loadRepositories,loadRepositoryDirectories,loadTestDirectories'
      : 'editor,rows,selectedBinding,selectedId,selectedProjectProduct,pagination,tableLoading,listFailed,deletingIds,bindingMetrics,doRefresh,onAdd,onUpdate,onSaved,onDelete,onNavigationFilterChange,selectBinding',
    {
      base,
      modules: {
        vue: {
          ...vue,
          onMounted: (fn) => life.mount.push(fn),
          onBeforeUnmount: (fn) => life.unmount.push(fn),
          onActivated: (fn) => life.activate.push(fn),
          onDeactivated: (fn) => life.deactivate.push(fn),
        },
        'vue-router': { useRoute: () => route },
        '@/store/modules/user': { default: () => user },
        '@/store/modules/get-project': { useProject: () => projects },
        '@/store/modules/get-enum': {
          useEnum: () => ({ test_case_type: [{ key: 0, title: 'API' }], colors: {} }),
        },
        '@/hooks/table': {
          useTableColumn: (values) => values,
          usePagination: (callback) =>
            vue.reactive({
              page: 1,
              pageSize: 20,
              pageCount: 0,
              setTotalSize(value) {
                this.pageCount = value
              },
              onChange: callback,
            }),
        },
        '@arco-design/web-vue': {
          Message: Object.fromEntries(
            ['success', 'error', 'warning'].map((key) => [
              key,
              (value) => messages.push([key, value]),
            ])
          ),
          Modal: {
            confirm: (options) => {
              const modal = {
                destroyed: false,
                close() {
                  this.destroyed = true
                },
              }
              confirmations.push({ ...options, modal })
              return modal
            },
          },
        },
        '@/api/pytest/product': {
          getPytestProduct: (query) =>
            invoke('list', [query], { ...response([row()]), totalSize: 1 }),
          deletePytestProduct: (id) => invoke('delete', [id], response({})),
          postPytestProductImport: (payload) => invoke('import', [payload], response({})),
          putPytestProduct: (payload) => invoke('save', [payload], response({})),
          getPytestProductTestDirectories: (...args) =>
            invoke('tests', args, response([{ value: 'tests', file_count: 1 }])),
        },
        '@/api/pytest/repository': {
          getPytestRepositories: () =>
            invoke(
              'repositories',
              [],
              response([
                { id: 0, name: 'Repository' },
                { id: 2, name: 'Other' },
              ])
            ),
          getPytestRepositoryDirectories: (id) =>
            invoke('directories', [id], response([{ value: '.' }, { value: 'project' }])),
        },
      },
    }
  )
  return {
    ...h,
    user,
    route,
    projects,
    calls,
    messages,
    confirmations,
    listeners,
    boundary: h.load('binding.ts'),
    mount() {
      life.mount.forEach((fn) => fn())
    },
    pause() {
      life.deactivate.forEach((fn) => fn())
    },
    resume() {
      life.activate.forEach((fn) => fn())
    },
    hide() {
      doc.hidden = true
      doc.dispatchEvent(new Event('visibilitychange'))
    },
    show() {
      doc.hidden = false
      doc.dispatchEvent(new Event('visibilitychange'))
    },
    close() {
      life.unmount.forEach((fn) => fn())
      h.close()
      globalThis.document = originalDocument
    },
  }
}

test('finite binding boundary detaches lists, preserves zero/null and whitelists submitted fields', () => {
  const h = setup(),
    raw = row(),
    parsed = h.boundary.readBinding(raw),
    draft = h.boundary.bindingDraft(parsed)
  raw.test_dir.push('other')
  assert.deepEqual(draft.test_dir, ['tests'])
  assert.equal(parsed.case_count, 0)
  assert.equal(h.boundary.readBinding(row(0, { project_product: null, repository: null })).id, 0)
  const payload = h.boundary.bindingPayload(
    { ...draft, audit: 'discard' },
    h.projects.projectProduct,
    1
  )
  assert.deepEqual(
    Object.keys(payload).sort(),
    [
      'project_product',
      'repository',
      'file_name',
      'name',
      'auto_type',
      'test_dir',
      'pytest_config_path',
      'id',
    ].sort()
  )
  assert.equal(payload.repository, 0)
  assert.equal(payload.auto_type, 0)
  assert.equal(payload.project_product, 10)
  assert.equal(
    h.boundary.bindingPayload(
      { ...draft, project_product: [20, 10] },
      h.projects.projectProduct,
      null
    ).project_product,
    10
  )
  for (const patch of [
    { name: ' ' },
    { project_product: 20 },
    { project_product: null },
    { repository: null },
    { test_dir: [] },
    { auto_type: null },
  ])
    assert.throws(() =>
      h.boundary.bindingPayload({ ...draft, ...patch }, h.projects.projectProduct, 1)
    )
  for (const value of [
    { code: 403, data: [] },
    { code: 200, data: [row(), row()], totalSize: 2 },
    { code: 200, data: [row()], totalSize: false },
  ])
    assert.throws(() => h.boundary.readBindingList(value))
  h.close()
})

test('directory tree includes repository root, ancestors and stale configured directories without mutating input', () => {
  const h = setup(),
    input = [
      { value: '.', file_count: 0 },
      { value: 'tests/unit', file_count: 2 },
    ],
    original = structuredClone(input)
  const tree = h.boundary.directoryTree(input, ['missing', 'tests'], true)
  assert.equal(tree[0].value, '.')
  assert.equal(tree.find((node) => node.value === 'tests').fileCount, 2)
  assert.equal(tree.find((node) => node.value === 'missing').stale, true)
  assert.deepEqual(input, original)
  assert.deepEqual(h.boundary.directoryTree([], ['.'], true), [{ label: '项目根目录', value: '.' }])
  assert.throws(() => h.boundary.readDirectories(response([{ value: '../bad' }])))
  h.close()
})

test('editing opens synchronously with owned drafts; readonly repository/path need no privileged directory enumeration', async () => {
  const h = setup(),
    raw = row()
  h.open(raw)
  assert.equal(h.record.value.id, 1)
  assert.deepEqual(h.draft.test_dir, ['tests'])
  await flush()
  h.draft.test_dir.push('other')
  assert.deepEqual(raw.test_dir, ['tests'])
  assert.equal(
    h.calls.filter((call) => ['repositories', 'directories'].includes(call[0])).length,
    0
  )
  h.closeDialog()
  h.open(row(2, { test_dir: ['legacy'], file_name: '.' }))
  await flush()
  assert.deepEqual(h.draft.test_dir, ['legacy'])
  assert.equal(h.repositoryDirectoryOptions.value[0].value, '.')
  assert.equal(h.testDirectoryOptions.value.find((node) => node.value === 'legacy').stale, true)
  h.close()
})

test('repository A-B-A invalidates successes, failures and finalizers; changing path invalidates old test discovery', async () => {
  const directory = [deferred(), deferred(), deferred()],
    tests = [deferred(), deferred()]
  let d = 0,
    t = 0
  const h = setup('editor', {
    directories: () => directory[d++].promise,
    tests: () => tests[t++].promise,
  })
  h.open()
  await flush()
  assert.equal(h.draft.repository, 0)
  h.draft.repository = 2
  h.draft.repository = 0
  directory[0].resolve(response([{ value: 'old' }]))
  directory[1].reject(Error('old failure'))
  await flush()
  assert.equal(h.directoryLoading.value, true)
  assert.deepEqual(h.repositoryDirectoryOptions.value, [])
  directory[2].resolve(response([{ value: 'project' }]))
  await flush()
  h.draft.file_name = 'first'
  h.draft.file_name = 'second'
  tests[0].resolve(response([{ value: 'old', file_count: 1 }]))
  await flush()
  assert.equal(h.testLoading.value, true)
  tests[1].resolve(response([{ value: 'current', file_count: 1 }]))
  await flush()
  assert.equal(h.draft.name, 'second')
  assert.equal(
    h.testDirectoryOptions.value.some((node) => node.value === 'old'),
    false
  )
  h.close()
})

test('discovery failure preserves configured directories and exposes independent retries', async () => {
  let failed = true
  const h = setup('editor', {
    tests: () =>
      failed
        ? Promise.reject(Error('failure'))
        : Promise.resolve(response([{ value: 'tests', file_count: 1 }])),
  })
  h.open(row())
  await flush()
  assert.equal(h.testFailed.value, true)
  assert.equal(h.testLoading.value, false)
  assert.deepEqual(h.draft.test_dir, ['tests'])
  assert.equal(h.testDirectoryOptions.value[0].value, 'tests')
  failed = false
  await h.loadTestDirectories()
  assert.equal(h.testFailed.value, false)
  h.close()
})

test('project-store swallowed failures block save and retry; malformed repository options expose errors', async () => {
  const h = setup('editor', {
    projects: (store) => {
      store.optionErrors.products = true
      return Promise.resolve()
    },
    repositories: () => Promise.resolve(response([false])),
  })
  h.open()
  await flush()
  assert.equal(h.projectFailed.value, true)
  assert.equal(h.repositoryFailed.value, true)
  assert.equal(await h.save(), false)
  h.projects.projectProductName = () => {
    h.projects.optionErrors.products = false
    return Promise.resolve()
  }
  await h.loadProjects()
  assert.equal(h.projectFailed.value, false)
  h.close()
})

test('save captures whitelist once, retains failed draft, rejects malformed success and supports retry', async () => {
  const pending = deferred()
  let result = pending.promise
  const h = setup('editor', { save: () => result })
  h.open(row())
  await flush()
  const task = h.save()
  h.draft.name = 'Later'
  assert.equal(h.saving.value, true)
  assert.equal(await h.save(), false)
  assert.equal(h.calls.find((call) => call[0] === 'save')[1].name, 'Fixture 1')
  pending.resolve({ code: 403 })
  assert.equal(await task, false)
  assert.equal(h.visible.value, true)
  assert.equal(h.draft.name, 'Later')
  result = Promise.resolve(response({}))
  assert.equal(await h.save(), true)
  assert.deepEqual(h.events, [['saved']])
  h.close()
})

test('new import submits a platform product leaf, selected repository, root project path and independent test directories', async () => {
  const h = setup()
  h.open()
  await flush()
  h.draft.file_name = '.'
  await flush()
  h.draft.project_product = [20, 10]
  h.draft.name = 'Root'
  h.draft.auto_type = 0
  h.draft.test_dir = ['.']
  assert.equal(await h.save(), true)
  const payload = h.calls.find((call) => call[0] === 'import')[1]
  assert.equal(payload.file_name, '.')
  assert.equal(payload.repository, 0)
  assert.equal(payload.project_product, 10)
  assert.equal('id' in payload, false)
  h.close()
})

test('cancel keeps physical save lock until settlement; late success cannot emit or reopen a window', async () => {
  const pending = deferred(),
    h = setup('editor', { save: () => pending.promise })
  h.open(row())
  await flush()
  const task = h.save()
  h.closeDialog()
  h.open(row(2))
  assert.equal(h.visible.value, false)
  assert.equal(h.saving.value, true)
  pending.resolve(response({}))
  assert.equal(await task, false)
  assert.equal(h.events.length, 0)
  h.open(row(2))
  await flush()
  assert.equal(h.record.value.id, 2)
  h.close()
})

test('editor synchronously invalidates user, role, token, environment and route A-B-A; late saves never emit', async () => {
  for (const key of ['userId', 'roleId', 'token', 'selected_environment', 'fullPath']) {
    const pending = deferred(),
      h = setup('editor', { save: () => pending.promise })
    h.open(row())
    await flush()
    const task = h.save(),
      target = key === 'fullPath' ? h.route : h.user,
      old = target[key]
    target[key] = typeof old === 'number' ? old + 1 : old + '-b'
    target[key] = old
    assert.equal(h.visible.value, false)
    pending.resolve(response({}))
    assert.equal(await task, false)
    assert.deepEqual(h.events, [])
    h.close()
  }
})

test('list coalesces same query, fences filters and pagination, keeps valid selection and zero metrics', async () => {
  const requests = [deferred(), deferred(), deferred()]
  let i = 0
  const h = setup('page', { list: () => requests[i++].promise })
  const first = h.doRefresh()
  assert.equal(h.doRefresh(), first)
  assert.equal(h.tableLoading.value, true)
  h.onNavigationFilterChange({ projectProduct: 0 })
  requests[0].resolve({ ...response([row(99)]), totalSize: 1 })
  await flush()
  assert.equal(h.rows.value.length, 0)
  assert.equal(h.tableLoading.value, true)
  requests[1].resolve({ ...response([row(1), row(2)]), totalSize: 2 })
  await flush()
  h.selectBinding(row(2))
  assert.equal(h.selectedBinding.value.id, 2)
  assert.equal(h.bindingMetrics.value.repositories, 1)
  assert.equal(h.bindingMetrics.value.cases, 0)
  h.pagination.page = 2
  h.pagination.pageSize = 50
  const task = h.pagination.onChange()
  requests[2].resolve({ ...response([row(2, { name: 'Updated' })]), totalSize: 2 })
  await task
  assert.equal(h.selectedBinding.value.name, 'Updated')
  assert.deepEqual(h.calls.filter((call) => call[0] === 'list').at(-1)[1], {
    page: 2,
    pageSize: 50,
    project_product: 0,
  })
  h.close()
})

test('list failures are local, preserve existing rows and allow retry without claiming malformed data success', async () => {
  let fail = false
  const h = setup('page', {
    list: () =>
      Promise.resolve(
        fail ? { ...response('bad'), totalSize: 1 } : { ...response([row()]), totalSize: 1 }
      ),
  })
  await h.doRefresh()
  fail = true
  await h.doRefresh()
  assert.equal(h.listFailed.value, true)
  assert.equal(h.tableLoading.value, false)
  assert.equal(h.rows.value[0].id, 1)
  fail = false
  await h.doRefresh()
  assert.equal(h.listFailed.value, false)
  h.close()
})

test('delete confirmations return false on failure and retry with physical locks, refresh only after success', async () => {
  let result = { code: 403 }
  const h = setup('page', { delete: () => Promise.resolve(result) })
  await h.doRefresh()
  h.onDelete(row())
  const confirm = h.confirmations.at(-1)
  assert.equal(await confirm.onBeforeOk(), false)
  assert.equal(h.deletingIds.value.length, 0)
  assert.equal(h.calls.filter((call) => call[0] === 'list').length, 1)
  result = response({})
  h.pagination.page = 2
  assert.equal(await confirm.onBeforeOk(), true)
  assert.equal(h.pagination.page, 1)
  assert.equal(h.calls.filter((call) => call[0] === 'list').length, 2)
  h.close()
})

test('delete lock survives filter invalidation; old confirmations and writes cannot affect new context', async () => {
  const pending = deferred(),
    h = setup('page', { delete: () => pending.promise })
  await h.doRefresh()
  h.onDelete(row())
  const confirm = h.confirmations.at(-1),
    task = confirm.onBeforeOk()
  assert.deepEqual(h.deletingIds.value, [1])
  assert.equal(await confirm.onBeforeOk(), false)
  h.onNavigationFilterChange({ projectProduct: 10 })
  await flush()
  assert.equal(confirm.modal.destroyed, true)
  h.onDelete(row())
  assert.equal(h.confirmations.length, 1)
  pending.resolve(response({}))
  assert.equal(await task, false)
  assert.deepEqual(h.deletingIds.value, [])
  assert.equal(
    h.messages.some((message) => message[0] === 'success'),
    false
  )
  assert.equal(await confirm.onBeforeOk(), false)
  h.close()
})

test('replaced and cancelled confirmations cannot send writes or publish late success', async () => {
  const pending = deferred(),
    h = setup('page', { delete: () => pending.promise })
  await h.doRefresh()
  h.onDelete(row())
  const first = h.confirmations.at(-1)
  h.onDelete(row())
  const second = h.confirmations.at(-1)
  assert.equal(await first.onBeforeOk(), false)
  assert.equal(
    h.calls.some((call) => call[0] === 'delete'),
    false
  )
  const task = second.onBeforeOk()
  second.onCancel()
  assert.deepEqual(h.deletingIds.value, [1])
  pending.resolve(response({}))
  assert.equal(await task, false)
  assert.equal(
    h.messages.some((message) => message[0] === 'success'),
    false
  )
  h.close()
})

test('page identity and route A-B-A synchronously clear selection and ignore stale reads', async () => {
  for (const key of ['userId', 'roleId', 'token', 'selected_environment', 'fullPath']) {
    const pending = [],
      h = setup('page', {
        list: () => {
          const d = deferred()
          pending.push(d)
          return d.promise
        },
      })
    const initial = h.doRefresh(),
      target = key === 'fullPath' ? h.route : h.user,
      old = target[key]
    target[key] = typeof old === 'number' ? old + 1 : old + '-b'
    target[key] = old
    pending[0].resolve({ ...response([row(99)]), totalSize: 1 })
    await initial
    assert.equal(h.rows.value.length, 0)
    pending.at(-1).resolve({ ...response([row(2)]), totalSize: 1 })
    await flush()
    assert.equal(h.selectedBinding.value.id, 2)
    pending[1].reject(Error('old'))
    await flush()
    assert.equal(h.listFailed.value, false)
    h.close()
  }
})

test('both page and editor clean listeners and late effects on background, KeepAlive and unmount', async () => {
  for (const kind of ['page', 'editor']) {
    const h = setup(kind)
    h.mount()
    await flush()
    assert.equal(h.listeners.size, 1)
    if (kind === 'editor') {
      h.open(row())
      await flush()
    }
    h.hide()
    if (kind === 'editor') {
      assert.equal(h.visible.value, false)
      h.open()
      assert.equal(h.visible.value, false)
    } else {
      const count = h.calls.length
      await h.doRefresh()
      assert.equal(h.calls.length, count)
    }
    h.show()
    await flush()
    h.pause()
    if (kind === 'editor') {
      h.open()
      assert.equal(h.visible.value, false)
    }
    h.resume()
    await flush()
    h.close()
    assert.equal(h.listeners.size, 0)
  }
})

test('both actual SFC scripts/templates compile; configuration owns real columns and compact actions', () => {
  for (const file of ['index.vue', 'components/PytestBindingEditor.vue']) {
    const source = readFileSync(path.join(base, file), 'utf8'),
      { descriptor } = parse(source)
    const script = compileScript(descriptor, { id: file }),
      template = compileTemplate({
        id: file,
        source: descriptor.template.content,
        filename: file,
        compilerOptions: { bindingMetadata: script.bindings },
      })
    assert.deepEqual(template.errors, [])
  }
  const h = setup('page'),
    config = h.load('config.ts')
  assert.equal(config.tableColumns.at(-1).width, 120)
  assert.equal(config.tableColumns.at(-2).key, 'project_product')
  assert.equal('formItems' in config, false)
  h.close()
})
