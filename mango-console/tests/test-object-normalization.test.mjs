import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { reactive } from 'vue'
import { setupTarget, targetRecord as record } from './helpers/test-object-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/config/test-object')
const page = (api = {}) =>
  setupTarget(
    'index',
    'rows,listLoading,loadError,pagination,conditionItems,doRefresh,onSearch,onResetSearch,onSidebarFilterChange,loadUsers,usersLoading,usersError,onAdd,onUpdate,onDelete,onTest,onEditorSaving,onTestingChange,editorRef,connectionDialog,navigationCreateRef,editingIds,deletingIds,testingIds',
    api
  )
const editor = (api = {}) =>
  setupTarget(
    'TestObjectEditor',
    'draft,open,save,visible,saving,editingId,useNewTargetConfig',
    api
  )
const probe = (api = {}) =>
  setupTarget(
    'TestConnectionDialog',
    'options,address,objectId,loading,result,error,visible,open,runTest,clearResult',
    api
  )
function validDraft(s) {
  Object.assign(s.draft, {
    project_product: 10,
    name: 'Example',
    environment: 0,
    auto_type: 0,
    targetConfig: { default: 'https://example.com', selector: '', mapping: {} },
  })
}

test('all five page-owned SFCs compile', () => {
  for (const file of [
    'index.vue',
    'components/TestObjectEditor.vue',
    'components/TestConnectionDialog.vue',
    'components/TestTargetEditor.vue',
    'components/TestTargetDisplay.vue',
  ]) {
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
test('search factories isolate fields; enum collections preserve zero and product resolves leaf; reset returns page one', async () => {
  const calls = [],
    s = page({
      getUserTestObject: async (p) => {
        calls.push(p)
        return { data: [], totalSize: 0 }
      },
    }),
    other = page()
  try {
    s.conditionItems.find((i) => i.key === 'id').value = '5574、5577'
    s.conditionItems.find((i) => i.key === 'environment').value = [0, 1]
    s.conditionItems.find((i) => i.key === 'auto_type').value = [0, 2]
    s.conditionItems.find((i) => i.key === 'update_user').value = [1, 3]
    s.conditionItems.find((i) => i.key === 'project_product').value = [2, 10]
    s.pagination.page = 5
    await s.onSearch()
    assert.deepEqual(calls[0], {
      id: '5574,5577',
      environment__in: '0,1',
      auto_type__in: '0,2',
      update_user__in: '1,3',
      project_product: 10,
      page: 1,
      pageSize: 20,
    })
    assert.equal(other.conditionItems.find((i) => i.key === 'id').value, '')
    await s.onResetSearch()
    assert.deepEqual(calls.at(-1), { page: 1, pageSize: 20 })
    for (const key of ['environment', 'auto_type', 'update_user'])
      assert.deepEqual(s.conditionItems.find((i) => i.key === key).value, [])
  } finally {
    s.dispose()
    other.dispose()
  }
})
test('initial mount fetches list even without navigation filter emission', async () => {
  let count = 0
  const s = page({
    getUserTestObject: async () => {
      count++
      return { data: [record()], totalSize: 1 }
    },
  })
  try {
    s.lifecycle.mount()
    await flush()
    assert.equal(count, 1)
    assert.equal(s.rows.value.length, 1)
  } finally {
    s.dispose()
  }
})
test('latest list wins and old finally cannot clear current loading', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = page({ getUserTestObject: () => (++count === 1 ? a.promise : b.promise) })
  try {
    const first = s.doRefresh(),
      second = s.doRefresh()
    a.resolve({ data: [record(1)], totalSize: 1 })
    await first
    assert.equal(s.listLoading.value, true)
    assert.deepEqual(s.rows.value, [])
    b.resolve({ data: [record(2)], totalSize: 4 })
    await second
    assert.equal(s.rows.value[0].id, 2)
    assert.equal(s.pagination.pageCount, 4)
    assert.equal(s.listLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('failed list and option reads recover independently', async () => {
  let count = 0,
    users = 0
  const pending = deferred()
  const s = page({
    getUserTestObject: async () => {
      if (++count === 1) throw Error('fixture')
      return { data: [record()], totalSize: 1 }
    },
    getUserName: () =>
      ++users === 1 ? pending.promise : Promise.resolve({ data: [{ key: 1, title: 'User' }] }),
  })
  try {
    const options = s.loadUsers()
    await s.doRefresh()
    assert.match(s.loadError.value, /加载失败/)
    assert.equal(s.usersLoading.value, true)
    await s.doRefresh()
    assert.equal(s.loadError.value, '')
    assert.equal(s.listLoading.value, false)
    pending.reject(Error('fixture'))
    await options
    assert.equal(s.usersError.value, true)
    assert.equal(s.usersLoading.value, false)
    await s.loadUsers()
    assert.equal(s.usersError.value, false)
    assert.equal(s.conditionItems.find((i) => i.key === 'update_user').optionItems[0].key, 1)
  } finally {
    s.dispose()
  }
})
test('cached deactivation and identity change ignore stale lists/options; activation restores reads', async () => {
  const a = deferred(),
    b = deferred()
  let calls = 0,
    users = 0
  const s = page({
    getUserTestObject: () =>
      ++calls === 1 ? a.promise : Promise.resolve({ data: [record(2)], totalSize: 1 }),
    getUserName: () => (++users === 1 ? b.promise : Promise.resolve({ data: [] })),
  })
  try {
    const list = s.doRefresh(),
      options = s.loadUsers()
    s.lifecycle.deactivate()
    a.resolve({ data: [record()], totalSize: 5 })
    b.resolve({ data: [{ key: 1, title: 'Old' }] })
    await Promise.all([list, options])
    assert.deepEqual(s.rows.value, [])
    assert.equal(s.listLoading.value, false)
    assert.deepEqual(s.conditionItems.find((i) => i.key === 'update_user').optionItems, [])
    s.lifecycle.activate()
    await flush()
    assert.equal(calls, 2)
    assert.equal(users, 2)
    s.user.roleId = 2
    await flush()
    assert.equal(calls, 3)
    assert.equal(s.rows.value[0].id, 2)
  } finally {
    s.dispose()
  }
})
test('editor copies reactive nested config safely and resets create after editing/cancel', () => {
  const s = editor(),
    other = editor()
  try {
    const row = reactive(record())
    s.open(row)
    s.draft.targetConfig.mapping.first = 'https://example.net'
    assert.equal(row.target_config.mapping.first, 'https://example.org')
    assert.deepEqual(other.draft.targetConfig.mapping, {})
    s.exposed.close()
    s.open(undefined, 12)
    assert.equal(s.editingId.value, null)
    assert.equal(s.draft.project_product, 12)
    assert.equal(s.draft.legacyMode, false)
    assert.equal(s.draft.environment, null)
    assert.deepEqual(s.draft.targetConfig.mapping, {})
  } finally {
    s.dispose()
    other.dispose()
  }
})
test('required enum validation rejects null/empty and preserves numeric zero', async () => {
  const calls = [],
    s = editor({
      postUserTestObject: async (p) => {
        calls.push(p)
        return { msg: 'ok' }
      },
    })
  try {
    s.open()
    validDraft(s)
    for (const key of ['project_product', 'name', 'environment', 'auto_type']) {
      const saved = s.draft[key]
      s.draft[key] = key === 'name' ? '' : null
      assert.equal(await s.save(), false)
      assert.equal(s.saving.value, false)
      s.draft[key] = saved
    }
    assert.equal(calls.length, 0)
    assert.equal(await s.save(), true)
    assert.equal(calls[0].environment, 0)
    assert.equal(calls[0].auto_type, 0)
  } finally {
    s.dispose()
  }
})
test('create snapshots only writable fields, product leaf, deep mapping, and suppresses duplicate saves', async () => {
  const pending = deferred(),
    calls = [],
    s = editor({
      postUserTestObject: (p) => {
        calls.push(p)
        return pending.promise
      },
    })
  try {
    s.open()
    validDraft(s)
    s.draft.project_product = [2, 10]
    s.draft.targetConfig = {
      default: 'https://example.com',
      selector: 'tenant',
      mapping: { first: 'https://example.org' },
    }
    const saving = s.save()
    assert.equal(await s.save(), false)
    s.draft.targetConfig.mapping.first = 'https://example.net'
    assert.deepEqual(calls, [
      {
        project_product: 10,
        name: 'Example',
        environment: 0,
        auto_type: 0,
        value: '',
        target_config: {
          default: 'https://example.com',
          selector: 'tenant',
          mapping: { first: 'https://example.org' },
        },
      },
    ])
    pending.resolve({ msg: 'ok' })
    assert.equal(await saving, true)
    assert.equal(s.visible.value, false)
    assert.equal(s.saving.value, false)
    assert.equal(s.events.filter((e) => e[0] === 'saved').length, 1)
  } finally {
    s.dispose()
  }
})
test('legacy edit keeps legacy protocol; explicit conversion retains address and emits new config', async () => {
  const calls = [],
    s = editor({
      putUserTestObject: async (p) => {
        calls.push(p)
        return { msg: 'ok' }
      },
    })
  try {
    s.open(record(9, { value: 'app.example', target_config: null }))
    assert.equal(s.draft.legacyMode, true)
    assert.equal(await s.save(), true)
    assert.equal(calls[0].id, 9)
    assert.equal(calls[0].value, 'app.example')
    assert.equal('target_config' in calls[0], false)
    s.open(record(9, { value: 'app.example', target_config: null }))
    s.useNewTargetConfig()
    assert.equal(s.draft.targetConfig.default, 'app.example')
    assert.equal(s.draft.legacyMode, false)
    assert.equal(await s.save(), true)
    assert.equal(calls[1].value, '')
    assert.equal(calls[1].target_config.default, 'app.example')
  } finally {
    s.dispose()
  }
})
test('invalid mapping and duplicate keys block writes; failed save keeps draft and can retry', async () => {
  let count = 0
  const s = editor({
    putUserTestObject: async () => {
      if (++count === 1) throw Error('fixture')
      return { msg: 'ok' }
    },
  })
  try {
    s.open(record())
    s.draft.targetConfig.mapping = { '': '' }
    assert.equal(await s.save(), false)
    assert.equal(count, 0)
    s.draft.targetConfig.mapping = { first: 'https://example.org' }
    assert.equal(await s.save(), false)
    assert.equal(s.visible.value, true)
    assert.equal(s.saving.value, false)
    assert.equal(s.draft.targetConfig.selector, 'tenant')
    assert.equal(await s.save(), true)
    assert.equal(count, 2)
  } finally {
    s.dispose()
  }
})
test('editor identity change closes old session; physical pending blocks reopen; late success cannot emit saved', async () => {
  const pending = deferred(),
    s = editor({ putUserTestObject: () => pending.promise })
  try {
    s.open(record())
    const saving = s.save()
    s.user.roleId = 2
    assert.equal(s.visible.value, false)
    s.open(record(2))
    assert.equal(s.visible.value, false)
    pending.resolve({ msg: 'ok' })
    assert.equal(await saving, false)
    assert.equal(
      s.events.some((e) => e[0] === 'saved'),
      false
    )
    s.open(record(2))
    assert.equal(s.editingId.value, 2)
  } finally {
    s.dispose()
  }
})
test('mapping editor copies rows, refuses disabled writes and bounds additions to 200', () => {
  const config = record().target_config,
    s = setupTarget(
      'TestTargetEditor',
      'draft,rows,emitConfig,addRow,removeRow',
      {},
      { modelValue: config }
    )
  try {
    s.rows.value[0].value = 'https://example.net'
    assert.equal(config.mapping.first, 'https://example.org')
    s.props.disabled = true
    const before = s.events.length
    s.addRow()
    s.removeRow(0)
    s.emitConfig()
    assert.equal(s.events.length, before)
    assert.equal(s.rows.value.length, 1)
    s.props.disabled = false
    while (s.rows.value.length < 200) s.addRow()
    s.addRow()
    assert.equal(s.rows.value.length, 200)
  } finally {
    s.dispose()
  }
})
test('probe takes copied addresses, never auto-runs, uses selected saved address and serializes pending tests', async () => {
  const pending = deferred(),
    calls = [],
    s = probe({
      testObjectConnection: (...args) => {
        calls.push(args)
        return pending.promise
      },
    })
  try {
    const row = record(7)
    s.open(row)
    row.network_test_addresses[0].value = 'https://example.net'
    assert.equal(s.address.value, 'https://example.com')
    assert.deepEqual(calls, [])
    s.address.value = 'https://example.org'
    const testing = s.runTest()
    await s.runTest()
    assert.deepEqual(calls, [[7, 'https://example.org']])
    assert.equal(s.loading.value, true)
    pending.resolve({
      data: {
        connected: false,
        message: 'DNS error',
        resolved_ips: [],
        elapsed_ms: 2,
        host: 'example.org',
        port: 443,
        address: 'https://example.org',
      },
    })
    await testing
    assert.equal(s.result.value.connected, false)
    assert.equal(s.error.value, '')
    assert.equal(s.loading.value, false)
    assert.deepEqual(s.events, [
      ['testing-change', 7, true],
      ['testing-change', 7, false],
    ])
  } finally {
    s.dispose()
  }
})
test('probe close does not release physical pending lock; late success cannot restore closed window', async () => {
  const pending = deferred(),
    s = probe({ testObjectConnection: () => pending.promise })
  try {
    s.open(record())
    const testing = s.runTest()
    s.exposed.close()
    s.open(record(2))
    assert.equal(s.visible.value, false)
    assert.equal(s.loading.value, true)
    assert.equal(s.objectId.value, null)
    pending.resolve({ data: { connected: true } })
    await testing
    assert.equal(s.result.value, null)
    assert.equal(s.loading.value, false)
    s.open(record(2))
    assert.equal(s.objectId.value, 2)
    assert.equal(s.error.value, '')
  } finally {
    s.dispose()
  }
})
test('probe deactivation and role changes suppress old errors/results; resume never automatically sends', async () => {
  let count = 0
  const pending = deferred(),
    s = probe({
      testObjectConnection: () => {
        count++
        return pending.promise
      },
    })
  try {
    s.open(record())
    const testing = s.runTest()
    s.lifecycle.deactivate()
    s.lifecycle.activate()
    s.user.roleId = 2
    pending.reject(Error('fixture'))
    await testing
    assert.equal(s.error.value, '')
    assert.equal(s.visible.value, false)
    assert.equal(s.loading.value, false)
    assert.equal(count, 1)
  } finally {
    s.dispose()
  }
})
test('probe failure keeps selected address for explicit retry', async () => {
  let count = 0
  const s = probe({
    testObjectConnection: async () => {
      if (++count === 1) throw Error('fixture')
      return { data: { connected: true } }
    },
  })
  try {
    s.open(record())
    await s.runTest()
    assert.match(s.error.value, /稍后重试/)
    assert.equal(s.loading.value, false)
    assert.equal(s.address.value, 'https://example.com')
    await s.runTest()
    assert.equal(count, 2)
    assert.equal(s.result.value.connected, true)
    assert.equal(s.error.value, '')
  } finally {
    s.dispose()
  }
})
test('create defaults snapshot navigation product; switching navigation closes editor/probe and resets pagination', async () => {
  const opens = [],
    closed = [],
    s = page()
  const defaults = { projectProduct: 10, module: null }
  try {
    s.navigationCreateRef.value = { getCreateDefaults: () => defaults }
    s.editorRef.value = { open: (...args) => opens.push(args), close: () => closed.push('editor') }
    s.connectionDialog.value = { open() {}, close: () => closed.push('probe') }
    s.onAdd()
    defaults.projectProduct = 11
    assert.deepEqual(opens, [[undefined, 10]])
    s.pagination.page = 3
    await s.onSidebarFilterChange({ projectProduct: 11 })
    assert.equal(s.pagination.page, 1)
    assert.deepEqual(closed, ['probe', 'editor', 'probe'])
  } finally {
    s.dispose()
  }
})
test('same-record editor, deletion and probe are mutually exclusive; no-address rows never start tests', () => {
  const opens = [],
    s = page()
  try {
    s.connectionDialog.value = { open: (r) => opens.push(r.id), close() {} }
    s.editorRef.value = { open: (r) => opens.push(`edit ${r.id}`), close() {} }
    s.onTestingChange(1, true)
    s.onUpdate(record())
    s.onDelete(record())
    assert.deepEqual(opens, [])
    assert.equal(s.dialogs.length, 0)
    s.onTestingChange(1, false)
    s.onEditorSaving(1, true)
    s.onTest(record())
    s.onDelete(record())
    assert.deepEqual(opens, [])
    s.onEditorSaving(1, false)
    s.onTest(record(2, { network_test_addresses: [] }))
    assert.deepEqual(opens, [])
    s.onTest(record(2))
    assert.deepEqual(opens, [2])
  } finally {
    s.dispose()
  }
})
test('delete snapshots ID, retries on failure, returns previous page after deleting last row', async () => {
  const pending = deferred(),
    calls = [],
    s = page({
      deleteUserTestObject: (id) => {
        calls.push(id)
        return calls.length === 1 ? pending.promise : Promise.resolve({ msg: 'ok' })
      },
    })
  try {
    const row = record(7)
    s.rows.value = [row]
    s.pagination.page = 2
    s.onDelete(row)
    row.id = 8
    const config = s.dialogs[0].config,
      deleting = config.onBeforeOk()
    assert.equal(await config.onBeforeOk(), false)
    pending.reject(Error('fixture'))
    assert.equal(await deleting, false)
    assert.equal(s.deletingIds.size, 0)
    assert.equal(await config.onBeforeOk(), true)
    assert.deepEqual(calls, [7, 7])
    s.dialogs[0].close()
    s.rows.value = [record(9)]
    s.onDelete(record(9))
    assert.equal(await s.dialogs[1].config.onBeforeOk(), true)
    assert.equal(s.pagination.page, 1)
  } finally {
    s.dispose()
  }
})
test('old delete confirmations cannot submit under new product; role change hides late success', async () => {
  const pending = deferred()
  let count = 0
  const s = page({
    deleteUserTestObject: () => {
      count++
      return pending.promise
    },
  })
  try {
    s.onDelete(record())
    await s.onSidebarFilterChange({ projectProduct: 20 })
    assert.equal(s.dialogs[0].closed, true)
    assert.equal(await s.dialogs[0].config.onBeforeOk(), false)
    assert.equal(count, 0)
    s.onDelete(record())
    const deleting = s.dialogs[1].config.onBeforeOk()
    s.user.roleId = 2
    pending.resolve({ msg: 'ok' })
    await deleting
    assert.equal(
      s.notices.some((n) => n[0] === 'success'),
      false
    )
    assert.equal(s.deletingIds.size, 0)
  } finally {
    s.dispose()
  }
})
