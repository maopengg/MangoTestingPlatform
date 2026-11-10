import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/config/product/module')
const row = (id = 1, extra = {}) => ({
  id,
  name: `Module ${id}`,
  level: 1,
  parent: null,
  full_path: `Module ${id}`,
  ...extra,
})
export function setupModule(name, bindings, api = {}, props = {}) {
  const lifecycle = {},
    route = vue.reactive({ path: '/config/product/module', query: { id: '10', name: 'Product' } }),
    user = vue.reactive({ token: 'fixture-session', roleId: 1 }),
    dialogs = [],
    notices = [],
    cache = { count: 0 }
  const state = harness(name, bindings, {
    base,
    api,
    props,
    modules: {
      vue: {
        ...vue,
        onMounted: (f) => (lifecycle.mount = f),
        onActivated: (f) => (lifecycle.activate = f),
        onDeactivated: (f) => (lifecycle.deactivate = f),
        onBeforeUnmount: (f) => (lifecycle.unmount = f),
      },
      'vue-router': { useRoute: () => route },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-project': {
        useProject: () => ({
          invalidateAllProductModuleTreeCache() {
            cache.count++
          },
        }),
      },
      '@arco-design/web-vue': {
        Message: { success: (m) => notices.push(m), error: (m) => notices.push(m) },
        Modal: {
          confirm: (config) => {
            const dialog = {
              config,
              closed: false,
              close() {
                dialog.closed = true
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
  return {
    ...state,
    route,
    user,
    lifecycle,
    dialogs,
    notices,
    cache,
    dispose() {
      lifecycle.unmount?.()
      state.close()
    },
  }
}
const editor = (api) =>
  setupModule('ModuleEditor', 'moduleForm,visible,saving,create,edit,saveModule', api, {
    productId: 10,
  })
const page = (api) =>
  setupModule(
    'index',
    'modules,loading,loadError,projectProductId,loadModules,removeModule,openCreate,openModule,moduleEditorRef,detailId,detailRecord',
    api
  )
const tree = (modules = []) =>
  setupModule(
    'ModuleTree',
    'keyword,tree,visibleTree,expandedKeys,nodeActions',
    {},
    { modules, loading: false, error: '' }
  )

test('page, module editor and relocated tree compile', () => {
  for (const file of ['index.vue', 'components/ModuleEditor.vue', 'components/ModuleTree.vue']) {
    const filename = path.join(base, file),
      { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file })
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename,
        id: file,
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
  }
})
test('create fixes each parent and level; third level never creates a fourth', async () => {
  const calls = [],
    s = editor({
      postUserModule: async (payload) => {
        calls.push(payload)
        return { msg: 'ok' }
      },
    })
  try {
    for (const parent of [undefined, row(1), row(2, { level: 2 })]) {
      s.create(parent)
      s.moduleForm.name = ' New module '
      assert.equal(await s.saveModule(), true)
    }
    assert.deepEqual(calls, [
      { project_product: 10, parent: null, name: 'New module' },
      { project_product: 10, parent: 1, name: 'New module' },
      { project_product: 10, parent: 2, name: 'New module' },
    ])
    s.create(row(3, { level: 3 }))
    assert.equal(s.visible.value, false)
    assert.equal(s.cache.count, 3)
  } finally {
    s.dispose()
  }
})
test('rename only submits ID/name, never parent, level, path or audit fields', async () => {
  const calls = [],
    s = editor({
      putUserModule: async (payload) => {
        calls.push(payload)
        return { msg: 'ok' }
      },
    })
  try {
    const original = row(3, { level: 3, parent: { id: 2, name: 'Parent' }, update_time: 'audit' })
    s.edit(original)
    s.moduleForm.name = ' Renamed '
    assert.equal(await s.saveModule(), true)
    assert.deepEqual(calls, [{ id: 3, name: 'Renamed' }])
    assert.equal(original.name, 'Module 3')
    assert.equal(s.cache.count, 1)
  } finally {
    s.dispose()
  }
})
test('editor instances isolate drafts and switching edit/create resets every field', () => {
  const a = editor(),
    b = editor()
  try {
    a.edit(row(2, { parent: { id: 1, name: 'Parent' }, level: 2 }))
    a.moduleForm.name = 'Changed'
    assert.equal(b.moduleForm.name, '')
    a.exposed.close()
    a.create()
    assert.deepEqual(a.moduleForm, { id: null, name: '', parent: null, parentName: '', level: 1 })
  } finally {
    a.dispose()
    b.dispose()
  }
})
test('empty name blocks requests; save failure retains draft and can retry', async () => {
  let fail = true,
    count = 0
  const s = editor({
    postUserModule: async () => {
      count++
      if (fail) throw Error()
      return { msg: 'ok' }
    },
  })
  try {
    s.create()
    s.moduleForm.name = ' '
    assert.equal(await s.saveModule(), false)
    assert.equal(count, 0)
    s.moduleForm.name = 'Keep'
    assert.equal(await s.saveModule(), false)
    assert.equal(s.moduleForm.name, 'Keep')
    assert.equal(s.visible.value, true)
    assert.equal(s.saving.value, false)
    fail = false
    assert.equal(await s.saveModule(), true)
  } finally {
    s.dispose()
  }
})
test('pending save is deduplicated and freezes its product, parent and name', async () => {
  const gate = deferred(),
    calls = [],
    s = editor({
      postUserModule: (payload) => {
        calls.push(payload)
        return gate.promise
      },
    })
  try {
    s.create(row())
    s.moduleForm.name = 'First'
    const pending = s.saveModule()
    s.moduleForm.parent = 99
    s.moduleForm.name = 'Later'
    assert.equal(await s.saveModule(), false)
    s.create()
    assert.equal(s.moduleForm.parent, 99)
    assert.deepEqual(calls, [{ project_product: 10, parent: 1, name: 'First' }])
    gate.resolve({ msg: 'ok' })
    assert.equal(await pending, true)
  } finally {
    s.dispose()
  }
})
test('product change rejects late save UI but still invalidates physically changed module cache', async () => {
  const gate = deferred(),
    s = editor({ putUserModule: () => gate.promise })
  try {
    s.edit(row())
    const pending = s.saveModule()
    s.props.productId = 11
    assert.equal(s.visible.value, false)
    gate.resolve({ msg: 'ok' })
    assert.equal(await pending, false)
    assert.deepEqual(s.events, [])
    assert.equal(s.cache.count, 1)
    assert.equal(s.saving.value, false)
  } finally {
    s.dispose()
  }
})
test('cache deactivation closes draft and reactivation allows a fresh edit after pending write', async () => {
  const gate = deferred(),
    s = editor({ putUserModule: () => gate.promise })
  try {
    s.edit(row())
    const pending = s.saveModule()
    s.lifecycle.deactivate()
    s.lifecycle.activate()
    s.edit(row(2))
    assert.equal(s.visible.value, false)
    gate.resolve({ msg: 'ok' })
    await pending
    s.edit(row(2))
    assert.equal(s.moduleForm.id, 2)
    assert.equal(s.visible.value, true)
  } finally {
    s.dispose()
  }
})
test('valid numeric product routes are canonicalized, malformed routes issue no requests', async () => {
  let reads = 0
  const s = page({
    getUserModule: async () => {
      reads++
      return { data: [] }
    },
  })
  try {
    for (const id of [undefined, '', '0', '-1', 'NaN', '1e2', ['10', '11'], '9007199254740993']) {
      s.route.query.id = id
      await s.loadModules()
      assert.equal(s.projectProductId.value, null)
    }
    assert.equal(reads, 0)
    assert.match(s.loadError.value, /缺少产品 ID/)
    s.route.query.id = '0010'
    await flush()
    assert.equal(s.projectProductId.value, 10)
    assert.ok(reads >= 1)
  } finally {
    s.dispose()
  }
})
test('A→B→A requests cannot publish earlier product data or finish newer loading', async () => {
  const gates = [deferred(), deferred(), deferred()]
  let index = 0
  const s = page({ getUserModule: () => gates[index++].promise })
  try {
    const first = s.loadModules()
    s.route.query.id = '11'
    s.route.query.id = '10'
    gates[0].resolve({ data: [row(99)] })
    await first
    assert.deepEqual(s.modules.value, [])
    assert.equal(s.loading.value, true)
    gates[2].resolve({ data: [row(3)] })
    gates[1].resolve({ data: [row(2)] })
    await flush()
    assert.equal(s.modules.value[0].id, 3)
    assert.equal(s.loading.value, false)
  } finally {
    s.dispose()
  }
})
test('loading failure releases controls and explicit retry publishes rows', async () => {
  let fail = true
  const s = page({
    getUserModule: async () => {
      if (fail) throw Error()
      return { data: [row()] }
    },
  })
  try {
    await s.loadModules()
    assert.equal(s.loading.value, false)
    assert.equal(s.loadError.value, '')
    fail = false
    await s.loadModules()
    assert.equal(s.modules.value.length, 1)
    assert.equal(s.loadError.value, '')
  } finally {
    s.dispose()
  }
})
test('first activation does not duplicate mount load; cached return reloads and ignores old results', async () => {
  const gate = deferred()
  let count = 0
  const s = page({
    getUserModule: () => (++count === 1 ? gate.promise : Promise.resolve({ data: [row(2)] })),
  })
  try {
    s.lifecycle.mount()
    s.lifecycle.activate()
    assert.equal(count, 1)
    s.lifecycle.deactivate()
    gate.resolve({ data: [row(99)] })
    await flush()
    assert.deepEqual(s.modules.value, [])
    s.lifecycle.activate()
    await flush()
    assert.equal(count, 2)
    assert.equal(s.modules.value[0].id, 2)
  } finally {
    s.dispose()
  }
})
test('identity change closes detail/editor/delete state and rejects old confirmation', async () => {
  let writes = 0
  const s = page({
    deleteUserModule: async () => {
      writes++
      return { msg: 'ok' }
    },
  })
  try {
    s.modules.value = [row()]
    s.detailId.value = 1
    let closes = 0
    s.moduleEditorRef.value = {
      close() {
        closes++
      },
    }
    s.removeModule(row())
    s.user.roleId = 2
    assert.equal(s.detailId.value, null)
    assert.equal(s.detailRecord.value, null)
    assert.ok(closes > 0)
    assert.equal(s.dialogs[0].closed, true)
    assert.equal(await s.dialogs[0].config.onBeforeOk(), false)
    assert.equal(writes, 0)
  } finally {
    s.dispose()
  }
})
test('delete fixes ID, guards duplicate confirmation writes and keeps failure retryable', async () => {
  const gate = deferred(),
    calls = []
  let fail = true
  const s = page({
    deleteUserModule: (id) => {
      calls.push(id)
      return fail ? gate.promise : Promise.resolve({ msg: 'ok' })
    },
  })
  try {
    const record = row()
    s.removeModule(record)
    record.id = 9
    const d = s.dialogs[0],
      pending = d.config.onBeforeOk()
    assert.equal(await d.config.onBeforeOk(), false)
    gate.reject(Error())
    assert.equal(await pending, false)
    assert.equal(s.cache.count, 0)
    fail = false
    assert.equal(await d.config.onBeforeOk(), true)
    assert.deepEqual(calls, [1, 1])
    assert.equal(s.cache.count, 1)
    assert.equal(d.config.okButtonProps.status, 'danger')
  } finally {
    s.dispose()
  }
})
test('detail references current rows and disappears when refreshed record is deleted', async () => {
  const s = page()
  try {
    s.modules.value = [row()]
    s.detailId.value = 1
    assert.equal(s.detailRecord.value.name, 'Module 1')
    s.modules.value = [row(1, { name: 'Updated', full_path: 'Parent/Updated' })]
    await flush()
    assert.equal(s.detailRecord.value.name, 'Updated')
    s.modules.value = []
    await flush()
    assert.equal(s.detailId.value, null)
    s.modules.value = [row()]
    assert.equal(s.detailRecord.value, null)
  } finally {
    s.dispose()
  }
})
test('tree initially collapses all branches; search expands ancestors without mutating records', async () => {
  const rows = [
      row(),
      row(2, { level: 2, parent: { id: 1 }, name: 'Parent' }),
      row(3, { level: 3, parent: { id: 2 }, name: 'Leaf' }),
    ],
    s = tree(rows)
  try {
    assert.deepEqual(s.expandedKeys.value, [])
    s.keyword.value = 'Leaf'
    await flush()
    assert.deepEqual(s.expandedKeys.value, [1, 2])
    assert.equal(s.visibleTree.value[0].children[0].children[0].key, 3)
    assert.deepEqual(rows[2].parent, { id: 2 })
    assert.equal(rows.length, 3)
  } finally {
    s.dispose()
  }
})
test('active search expands matching branches after a replacement tree is loaded', async () => {
  const s = tree()
  try {
    s.keyword.value = 'Leaf'
    await flush()
    s.props.modules = [row(), row(2, { level: 2, parent: { id: 1 }, name: 'Leaf' })]
    await flush()
    assert.deepEqual(s.expandedKeys.value, [1])
    assert.equal(s.visibleTree.value[0].children[0].title, 'Leaf')
  } finally {
    s.dispose()
  }
})
test('tree actions keep level limits, danger delete and typed business events', () => {
  const s = tree([row()])
  try {
    const root = s.nodeActions(row())
    assert.deepEqual(
      root.map((action) => action.label),
      ['新增下级', '编辑', '删除']
    )
    assert.equal(root[2].danger, true)
    root[0].onClick()
    assert.equal(s.events[0][0], 'add')
    assert.deepEqual(
      s.nodeActions(row(3, { level: 3 })).map((action) => action.label),
      ['编辑', '删除']
    )
    s.props.loading = true
    assert.equal(
      s.nodeActions(row()).every((action) => action.disabled),
      true
    )
  } finally {
    s.dispose()
  }
})
