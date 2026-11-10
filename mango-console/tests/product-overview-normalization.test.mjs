import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/config/product')
const record = (id = 1) => ({
  id,
  name: 'Example',
  project: { id: 4, name: 'Project' },
  owners: [{ id: 7 }],
  ui_client_type: 0,
  api_client_type: 0,
})
function setup(name, bindings, api = {}, props = {}) {
  const life = {},
    user = vue.reactive({ token: 'fixture', roleId: 1 }),
    dialogs = [], cache = { invalidations: 0 }
  const s = harness(name, bindings, {
    base,
    api,
    props,
    modules: {
      vue: {
        ...vue,
        onMounted: (f) => (life.mount = f),
        onActivated: (f) => (life.activate = f),
        onDeactivated: (f) => (life.deactivate = f),
        onBeforeUnmount: (f) => (life.unmount = f),
      },
      'vue-router': {
        useRoute: () => ({ path: '/config/product/index' }),
        useRouter: () => ({ push: async () => {} }),
      },
      '@/store/modules/user': { default: () => user },
      '@/store/modules/get-project': {
        useProject: () => ({
          invalidateProjectOptionsCache() { cache.invalidations++ },
          projectProductName: async () => {},
        }),
      },
      '@/hooks/table': {
        useTableIndexColumn: () => ({ key: 'index' }),
        useTableColumn: (rows) => rows,
      },
    },
    Modal: {
      confirm: (config) => {
        const d = {
          config,
          close() {
            config.onClose?.()
          },
        }
        dialogs.push(d)
        return d
      },
    },
  })
  return {
    ...s,
    life,
    user,
    dialogs,
    cache,
    dispose() {
      life.unmount?.()
      s.close()
    },
  }
}
const edit = (api) =>
  setup(
    'ProductEditor',
    'draft,formItems,open,save,visible,saving,editingId,editorProjectOptions',
    api,
    { projects: [], users: [] }
  )
const page = (api) =>
  setup(
    'index',
    'table,conditionItems,doRefresh,onDelete,userOptions,productProjectOptions,refreshUserOptions,refreshProductProjectOptions,optionLoading',
    api
  )
test('three product SFCs compile', () => {
  for (const file of [
    'index.vue',
    'components/ProductEditor.vue',
    'components/ProductOverview.vue',
  ]) {
    const filename = path.join(base, file),
      { descriptor } = parse(readFileSync(filename, 'utf8'))
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
test('editor isolates drafts and preserves missing project labels and zero types', () => {
  const a = edit(),
    b = edit()
  try {
    const row = record()
    a.open(row)
    a.draft.owners.push(8)
    assert.deepEqual(row.owners, [{ id: 7 }])
    assert.equal(b.draft.name, '')
    assert.equal(a.draft.ui_client_type, 0)
    assert.deepEqual(a.editorProjectOptions.value, [{ key: 4, title: 'Project' }])
    a.exposed.close()
    a.open()
    assert.deepEqual(a.draft.owners, [])
    assert.equal(a.editingId.value, null)
  } finally {
    a.dispose()
    b.dispose()
  }
})
test('save freezes whitelist and blocks duplicates', async () => {
  const gate = deferred(),
    calls = [],
    s = edit({
      putUserProduct: (p) => {
        calls.push(p)
        return gate.promise
      },
    })
  try {
    s.open(record())
    const p = s.save()
    s.draft.owners.push(8)
    assert.equal(await s.save(), false)
    assert.deepEqual(calls[0].owners, [7])
    assert.equal(calls[0].project, 4)
    assert.equal('status' in calls[0], false)
    gate.resolve({ msg: 'ok' })
    assert.equal(await p, true)
    assert.deepEqual(s.events, [['saved']])
  } finally {
    s.dispose()
  }
})
test('failed save keeps input and permits retry', async () => {
  let fail = true
  const s = edit({
    postUserProduct: async () => {
      if (fail) throw Error()
      return { msg: 'ok' }
    },
  })
  try {
    s.open()
    Object.assign(s.draft, {
      project: 0,
      name: 'New',
      owners: [7],
      ui_client_type: 0,
      api_client_type: 0,
    })
    assert.equal(await s.save(), false)
    assert.equal(s.visible.value, true)
    assert.equal(s.draft.name, 'New')
    fail = false
    assert.equal(await s.save(), true)
  } finally {
    s.dispose()
  }
})
test('cleared required type is rejected', async () => {
  const s = edit()
  try {
    s.open(record())
    s.draft.ui_client_type = null
    assert.equal(await s.save(), false)
    assert.equal(s.visible.value, true)
  } finally {
    s.dispose()
  }
})
test('cached editor invalidates late saves', async () => {
  const g = deferred(),
    s = edit({ putUserProduct: () => g.promise })
  try {
    s.open(record())
    const p = s.save()
    s.life.deactivate()
    g.resolve({ msg: 'ok' })
    assert.equal(await p, false)
    assert.equal(s.cache.invalidations, 1)
    assert.deepEqual(s.events, [])
    assert.equal(s.visible.value, false)
  } finally {
    s.dispose()
  }
})
test('search factories isolate selection and reset multi-select defaults', () => {
  const a = page(),
    b = page()
  try {
    a.conditionItems.find((i) => i.key === 'owners').value = [7]
    assert.deepEqual(b.conditionItems.find((i) => i.key === 'owners').value, [])
    assert.equal(a.conditionItems.find((i) => i.key === 'ui_client_type').multiple, true)
  } finally {
    a.dispose()
    b.dispose()
  }
})
test('latest complete list owns loading and rows', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = page({ getUserProduct: () => (++count === 1 ? a.promise : b.promise) })
  try {
    const old = s.doRefresh(),
      fresh = s.doRefresh()
    a.resolve({ data: [record(1)], totalSize: 1 })
    await old
    assert.equal(s.table.tableLoading.value, true)
    assert.equal(s.table.dataList.length, 0)
    b.resolve({ data: [record(2)], totalSize: 1 })
    await fresh
    assert.equal(s.table.dataList[0].id, 2)
  } finally {
    s.dispose()
  }
})
test('delete failure stays retryable and ID snapshot remains fixed', async () => {
  let fail = true
  const calls = [],
    s = page({
      deleteUserProduct: async (id) => {
        calls.push(id)
        if (fail) throw Error()
        return { msg: 'ok' }
      },
    })
  try {
    const row = record()
    s.onDelete(row)
    row.id = 2
    const d = s.dialogs[0]
    assert.equal(await d.config.onBeforeOk(), false)
    assert.equal(s.cache.invalidations, 0)
    fail = false
    assert.equal(await d.config.onBeforeOk(), true)
    assert.equal(s.cache.invalidations, 1)
    assert.deepEqual(calls, [1, 1])
    assert.equal(d.config.okButtonProps.status, 'danger')
  } finally {
    s.dispose()
  }
})
test('option requests discard old role and cache responses', async () => {
  const g = deferred(),
    s = page({ getUserName: () => g.promise })
  try {
    const p = s.refreshUserOptions()
    s.life.deactivate()
    g.resolve({ data: [{ key: 7, title: 'User' }] })
    await p
    assert.deepEqual(s.userOptions.value, [])
    assert.equal(s.optionLoading.users, false)
  } finally {
    s.dispose()
  }
})

test('identity changes discard project options and reject old delete callbacks', async () => {
  const old=deferred(),fresh=deferred();let reads=0,writes=0
  const s=page({getProductProjectOptions:()=>++reads===1?old.promise:fresh.promise,deleteUserProduct:async()=>{writes++;return {msg:'ok'}}})
  try {
    const pending=s.refreshProductProjectOptions();s.onDelete(record())
    s.user.roleId=2
    old.resolve({data:[{key:4,title:'Old'}]});await pending
    assert.deepEqual(s.productProjectOptions.value,[])
    assert.equal(await s.dialogs[0].config.onBeforeOk(),false);assert.equal(writes,0)
    fresh.resolve({data:[{key:5,title:'Fresh'}]});await flush()
    assert.deepEqual(s.productProjectOptions.value,[{key:5,title:'Fresh'}])
  } finally {s.dispose()}
})

test('project selection can be prepared before options arrive and preserves ID type', () => {
  const s=edit()
  try {
    s.open(undefined,'4');assert.equal(s.draft.project,'4')
    s.exposed.close();s.props.projects=[{key:4,title:'Project'}]
    s.open(undefined,'4');assert.equal(s.draft.project,4)
  } finally {s.dispose()}
})
