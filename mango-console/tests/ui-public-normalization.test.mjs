import test from 'node:test'
import assert from 'node:assert/strict'
import {
  publicHarness,
  publicRecords as dto,
  publicConfig,
  publicList,
  publicRow,
} from './helpers/ui-public-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { loadModule } from './helpers/auth-config-harness.mjs'
const longId = '9007199254740993123'
const sql = () =>
  publicRow({ type: 1, datasource_alias: { id: 0, name: 'Example SQL' }, test_envs: [0] })

test('successful empty variable lists may omit totalSize without showing a load failure', async () => {
  assert.deepEqual(dto.readPublicList({ code: 200, data: [] }), { rows: [], total: 0 })
  assert.throws(() => dto.readPublicList({ code: 500, data: [] }))
  assert.throws(() => dto.readPublicList({ code: 200, data: [publicRow()] }))
  assert.throws(() => dto.readPublicList({ code: 200, data: [], totalSize: 'invalid' }))
  const h = publicHarness({ api: { getUiPublic: async () => ({ code: 200, data: [] }) } })
  try {
    await h.doRefresh()
    assert.deepEqual(h.rows.value, [])
    assert.equal(h.listError.value, '')
  } finally { h.cleanup() }
})

test('UI API keeps endpoints, verbs and zero/long identifier payloads unchanged', async () => {
  const calls = []
  const http = Object.fromEntries(
    ['get', 'post', 'put', 'deleted'].map((verb) => [
      verb,
      async (options) => {
        calls.push([verb, options.url, options.data()])
        return { code: 200 }
      },
    ])
  )
  const api = loadModule('src/api/uitest/public.ts', { '@/api/http': http })
  await api.getUiPublic({ page: 1, pageSize: 20 })
  await api.postUiPublic({ project_product: 0 })
  await api.putUiPublic({ id: longId })
  await api.deleteUiPublic(longId)
  await api.putUiPublicPutStatus(0, 0)
  assert.deepEqual(calls, [
    ['get', '/ui/public', { page: 1, pageSize: 20 }],
    ['post', '/ui/public', { project_product: 0 }],
    ['put', '/ui/public', { id: longId }],
    ['deleted', '/ui/public', { id: longId }],
    ['put', '/ui/public/status', { id: 0, status: 0 }],
  ])
})

test('users and enum failures retry independently without masking loaded list', async () => {
  let fail = true
  const h = publicHarness({
    api: {
      getUserName: async () => {
        if (fail) throw Error()
        return { code: 200, data: [{ key: 0, title: 'Example' }] }
      },
    },
    enums: {
      getEnum: async () => {
        if (fail) throw Error()
      },
    },
  })
  try {
    h.mount()
    await flush()
    assert.equal(h.rows.value.length, 1)
    assert.ok(h.usersError.value)
    assert.ok(h.enumsError.value)
    assert.equal(h.usersLoading.value, false)
    assert.equal(h.enumsLoading.value, false)
    fail = false
    await Promise.all([h.loadUsers(), h.loadEnums()])
    assert.equal(h.usersError.value, '')
    assert.equal(h.enumsError.value, '')
    assert.equal(h.typeOptions.value.length, 3)
  } finally {
    h.cleanup()
  }
})

test('editor options can retry in place and loading/failure cannot dispatch a write', async () => {
  const h = publicHarness({ component: true })
  try {
    h.open(dto.readPublicRow(publicRow()))
    h.props.optionsLoading = true
    assert.equal(await h.save(), false)
    h.props.optionsLoading = false
    h.props.optionsError = '读取失败'
    assert.equal(await h.save(), false)
    assert.equal(h.writes.length, 0)
    assert.equal(h.visible.value, true)
    h.props.optionsError = ''
    assert.equal(await h.save(), true)
  } finally {
    h.cleanup()
  }
})

test('alias close/reopen rejects old errors and finally without clearing new request loading', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const h = publicHarness({
    component: true,
    api: { getDataFactoryDatasourceAlias: () => (++count === 1 ? a : b).promise },
  })
  try {
    h.open(dto.readPublicRow(sql()))
    h.close()
    h.open(dto.readPublicRow(sql()))
    a.reject(Error())
    await flush()
    assert.equal(h.aliasesLoading.value, true)
    assert.equal(h.aliasesFailed.value, false)
    b.resolve({ code: 200, data: [] })
    await flush()
    assert.equal(h.aliasesLoading.value, false)
  } finally {
    h.cleanup()
  }
})

test('new variable saves common environment and default status without hidden SQL binding', async () => {
  const h = publicHarness({ component: true })
  try {
    h.open(null, 0)
    h.draft.type = 0
    h.draft.name = 'Example'
    h.draft.key = 'key'
    h.draft.value = 'false'
    h.draft.datasource_alias = longId
    assert.equal(await h.save(), true)
    assert.deepEqual(h.writes[0], [
      'postUiPublic',
      {
        project_product: 0,
        type: 0,
        test_envs: [],
        name: 'Example',
        tags: [],
        key: 'key',
        value: 'false',
        datasource_alias: null,
        status: 1,
      },
    ])
  } finally {
    h.cleanup()
  }
})

test('finite boundary preserves zero and long IDs, exact text and explicit common environments', () => {
  const row = dto.readPublicRow(
    publicRow({ id: longId, value: '  SELECT 1\n', test_envs: [], test_env: 2 })
  )
  assert.equal(row.id, longId)
  assert.equal(row.value, '  SELECT 1\n')
  assert.deepEqual(row.test_envs, [])
  assert.deepEqual(dto.readPublicRow(publicRow({ test_envs: undefined, test_env: 0 })).test_envs, [
    0,
  ])
  assert.equal(dto.publicId(Number(longId)), null)
  assert.throws(() => dto.readPublicList(publicList([publicRow(), publicRow()])))
  assert.throws(() => dto.readPublicList({ code: 500, data: [], totalSize: 0 }))
  assert.throws(() => dto.readPublicRow(publicRow({ type: null })))
})
test('private drafts and payload whitelist preserve SQL ID zero and exclude display/server fields', () => {
  const row = dto.readPublicRow(sql()),
    draft = dto.createPublicDraft(row)
  draft.test_envs.push(2)
  draft.name = 'Changed'
  draft.status = 0
  draft.update_user = 'ignored'
  assert.deepEqual(row.test_envs, [0])
  assert.equal(row.name, 'Example variable')
  const payload = dto.publicPayload(draft, longId)
  assert.equal(payload.datasource_alias, 0)
  assert.equal(payload.id, longId)
  assert.equal(payload.project_product, 0)
  assert.equal('status' in payload, false)
  assert.equal('update_user' in payload, false)
  draft.type = 0
  assert.equal(dto.publicPayload(draft, null).datasource_alias, null)
  assert.equal(dto.publicPayload(draft, null).status, 1)
})
test('common environment is exclusive and real environments remain lossless', () => {
  assert.deepEqual(dto.environmentSelection([]), [dto.COMMON_ENV_VALUE])
  assert.deepEqual(dto.environmentSelection([0, dto.COMMON_ENV_VALUE]), [dto.COMMON_ENV_VALUE])
  assert.deepEqual(dto.environmentSelection([dto.COMMON_ENV_VALUE, 0]), [0])
  const draft = dto.createPublicDraft(dto.readPublicRow(publicRow()))
  assert.deepEqual(dto.publicPayload(draft, 0).test_envs, [])
  draft.test_envs = [longId]
  assert.deepEqual(dto.publicPayload(draft, 0).test_envs, [longId])
})
test('search factories isolate instances and use collection operators while environments retain their protocol', () => {
  const a = publicConfig.createConditionItems(),
    b = publicConfig.createConditionItems()
  a.find((item) => item.key === 'type').value.push(0)
  assert.deepEqual(b.find((item) => item.key === 'type').value, [])
  assert.equal(a.find((item) => item.key === 'type').searchOperator, 'in')
  assert.equal(a.find((item) => item.key === 'test_envs').searchOperator, undefined)
  assert.deepEqual(
    dto.publicQuery(
      {
        project_product: [1, 0],
        type__in: '0,2',
        test_envs: [dto.COMMON_ENV_VALUE, 0],
        update_user__in: '0',
        name: '',
        value: null,
      },
      2,
      20
    ),
    {
      page: 2,
      pageSize: 20,
      project_product: 0,
      type__in: '0,2',
      test_envs: '__common__,0',
      update_user__in: '0',
    }
  )
})
test('list, users and enums load independently and failures recover without losing rows', async () => {
  const wait = deferred()
  let fail = true
  const h = publicHarness({
    api: {
      getUserName: () => wait.promise,
      getUiPublic: async () => {
        if (fail) throw Error()
        return publicList()
      },
    },
  })
  try {
    h.mount()
    await flush()
    assert.ok(h.listError.value)
    assert.equal(h.listLoading.value, false)
    assert.equal(h.usersLoading.value, true)
    assert.equal(h.typeOptions.value.length, 3)
    fail = false
    await h.doRefresh()
    assert.equal(h.rows.value[0].id, 0)
    fail = true
    await h.doRefresh()
    assert.equal(h.rows.value.length, 1)
    wait.resolve({ code: 200, data: [{ key: 0, title: 'Example user' }] })
    await flush()
    assert.equal(h.usersLoading.value, false)
    assert.equal(h.userOptions.value[0].key, 0)
  } finally {
    h.cleanup()
  }
})
test('old list and finally cannot replace a newer search or dismiss its loading', async () => {
  const a = deferred(),
    b = deferred()
  let calls = 0
  const h = publicHarness({ api: { getUiPublic: () => (++calls === 1 ? a : b).promise } })
  try {
    const first = h.doRefresh()
    const second = h.doRefresh()
    a.resolve(publicList([publicRow({ id: 1 })]))
    await first
    assert.equal(h.listLoading.value, true)
    assert.equal(h.rows.value.length, 0)
    b.resolve(publicList([publicRow({ id: 2 })]))
    await second
    assert.equal(h.rows.value[0].id, 2)
    assert.equal(h.listLoading.value, false)
  } finally {
    h.cleanup()
  }
})
test('search resets pagination, maps real product and keeps current default after reset', async () => {
  const h = publicHarness()
  const opens = []
  try {
    h.editorRef.value = { open: (...args) => opens.push(args), close() {} }
    h.pagination.page = 5
    h.onNavigationFilterChange({ projectProduct: [1, 0] })
    await flush()
    assert.equal(h.pagination.page, 1)
    assert.equal(h.reads.at(-1)[1].project_product, 0)
    h.onAdd()
    assert.equal(opens.at(-1)[1], 0)
    h.onResetSearch()
    h.onAdd()
    assert.equal(opens.at(-1)[1], null)
    assert.equal('size' in h.reads.at(-1)[1], false)
  } finally {
    h.cleanup()
  }
})
test('identity change clears search before reloading and ignores A-B-A responses', async () => {
  const old = deferred()
  let calls = 0
  const h = publicHarness({
    api: {
      getUiPublic: () =>
        ++calls === 1 ? old.promise : Promise.resolve(publicList([publicRow({ id: 2 })])),
    },
  })
  try {
    h.conditionItems.find((item) => item.key === 'name').value = 'old-owner'
    h.mount()
    await flush()
    h.user.roleId = 3
    h.user.roleId = 2
    await flush()
    assert.equal(h.reads.filter(([name]) => name === 'getUiPublic').at(-1)[1].name, undefined)
    old.resolve(publicList([publicRow({ id: 1 })]))
    await flush()
    assert.equal(h.rows.value[0].id, 2)
  } finally {
    h.cleanup()
  }
})
for (const change of [
  'hidden',
  'deactivate',
  'unmount',
  'route',
  'environment',
  'permission',
  'token',
]) {
  test(`pending list invalidates on ${change} and cannot leak rows`, async () => {
    const old = deferred()
    let calls = 0
    const h = publicHarness({
      api: {
        getUiPublic: () =>
          ++calls === 1 ? old.promise : Promise.resolve(publicList([publicRow({ id: 2 })])),
      },
    })
    try {
      h.mount()
      await flush()
      if (change === 'hidden') h.visibility('hidden')
      else if (change === 'deactivate') h.callbacks.deactivate.forEach((fn) => fn())
      else if (change === 'unmount') h.callbacks.unmount.forEach((fn) => fn())
      else if (change === 'route') {
        h.route.path = '/elsewhere'
        h.route.fullPath = '/elsewhere'
      } else if (change === 'environment') h.user.selected_environment = 2
      else if (change === 'permission') h.permission.permissionKeys = []
      else h.user.token = 'replacement'
      old.resolve(publicList([publicRow({ id: 1 })]))
      await flush()
      assert.equal(
        h.rows.value.some((row) => row.id === 1),
        false
      )
      if (change === 'hidden' || change === 'deactivate') {
        if (change === 'hidden') h.visibility('visible')
        else h.callbacks.activate.forEach((fn) => fn())
        await flush()
        assert.equal(h.rows.value[0].id, 2)
      }
    } finally {
      h.cleanup()
    }
  })
}
test('delete failure keeps confirmation and rows; accepted deletion never replays after refresh failure', async () => {
  let failDelete = true,
    failRead = false
  const h = publicHarness({
    api: {
      deleteUiPublic: async () => {
        if (failDelete) throw Error()
        return { code: 200 }
      },
      getUiPublic: async () => {
        if (failRead) throw Error()
        return publicList()
      },
    },
  })
  try {
    await h.doRefresh()
    h.onDelete(h.rows.value[0])
    const dialog = h.confirmations[0]
    assert.equal(await dialog.onBeforeOk(), false)
    assert.equal(h.rows.value.length, 1)
    assert.ok(h.actionError.value)
    assert.equal(h.reads.filter(([name]) => name === 'getUiPublic').length, 1)
    failDelete = false
    failRead = true
    assert.equal(await dialog.onBeforeOk(), true)
    assert.equal(h.rows.value.length, 0)
    assert.ok(h.listError.value)
    assert.equal(await dialog.onBeforeOk(), true)
    assert.equal(h.writes.length, 2)
  } finally {
    h.cleanup()
  }
})
test('delete freezes target, prevents duplicates and survives context invalidation with physical lock', async () => {
  const wait = deferred(),
    row = dto.readPublicRow(publicRow({ id: longId }))
  const h = publicHarness({ api: { deleteUiPublic: () => wait.promise } })
  try {
    h.onDelete(row)
    const dialog = h.confirmations[0]
    const pending = dialog.onBeforeOk()
    row.id = 2
    assert.equal(await dialog.onBeforeOk(), false)
    assert.equal(h.writes[0][1], longId)
    h.user.roleId = 3
    assert.equal(dialog.closed, true)
    assert.equal(h.busy(longId), true)
    h.onDelete(dto.readPublicRow(publicRow({ id: longId })))
    assert.equal(h.confirmations.length, 1)
    wait.resolve({ code: 200 })
    await pending
    assert.equal(h.busy(longId), false)
    assert.equal(h.messages.length, 0)
  } finally {
    h.cleanup()
  }
})
test('unconfirmed deletion cannot dispatch after search/context changes', async () => {
  const h = publicHarness()
  try {
    h.onDelete(dto.readPublicRow(publicRow()))
    const dialog = h.confirmations[0]
    h.onResetSearch()
    assert.equal(await dialog.onBeforeOk(), false)
    assert.equal(h.writes.length, 0)
  } finally {
    h.cleanup()
  }
})
test('controlled status commits only after success and locks against delete/double clicks', async () => {
  const wait = deferred(),
    h = publicHarness({
      api: {
        putUiPublicPutStatus: () => wait.promise,
        getUiPublic: async () => publicList([publicRow({ status: 0 })]),
      },
    })
  try {
    h.rows.value = [dto.readPublicRow(publicRow())]
    const pending = h.onModifyStatus(false, 0)
    assert.equal(h.rows.value[0].status, 1)
    assert.equal(await h.onModifyStatus(false, 0), false)
    h.onDelete(h.rows.value[0])
    assert.equal(h.confirmations.length, 0)
    wait.resolve({ code: 200 })
    assert.equal(await pending, true)
    assert.equal(h.rows.value[0].status, 0)
    assert.equal(h.busy(0), false)
  } finally {
    h.cleanup()
  }
})
test('status rejects failed envelopes and late success cannot update another identity', async () => {
  const wait = deferred()
  let response = { code: 500 }
  const h = publicHarness({
    api: {
      putUiPublicPutStatus: () => (response === null ? wait.promise : Promise.resolve(response)),
    },
  })
  try {
    await h.doRefresh()
    assert.equal(await h.onModifyStatus(false, 0), false)
    assert.equal(h.rows.value[0].status, 1)
    response = null
    const pending = h.onModifyStatus(false, 0)
    h.user.roleId = 3
    assert.equal(h.statusIds.value.has('0'), true)
    assert.equal(await h.onModifyStatus(false, 0), false)
    wait.resolve({ code: 200 })
    assert.equal(await pending, false)
    assert.equal(h.statusIds.value.size, 0)
  } finally {
    h.cleanup()
  }
})
test('editor cancel/reopen keeps drafts isolated and preserves empty/new zero semantics', async () => {
  const h = publicHarness({ component: true })
  const row = dto.readPublicRow(sql())
  try {
    h.open(row)
    h.draft.test_envs.push(2)
    h.draft.name = 'Changed'
    h.close()
    h.open(row)
    await flush()
    assert.deepEqual(h.draft.test_envs, [0])
    assert.equal(row.name, 'Example variable')
    assert.equal(h.editingId.value, 0)
    h.close()
    h.open(null, 0)
    assert.equal(h.editingId.value, null)
    assert.equal(h.draft.project_product, 0)
    assert.equal(h.draft.name, '')
  } finally {
    h.cleanup()
  }
})
test('SQL alias options reject old product replies and retain historical alias labels disabled', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const h = publicHarness({
    component: true,
    api: { getDataFactoryDatasourceAlias: () => (++count === 1 ? a : b).promise },
  })
  try {
    h.open(dto.readPublicRow(sql()))
    assert.equal(h.aliasOptions.value[0].disabled, true)
    h.onProductChange(2)
    a.resolve({ code: 200, data: [{ id: 1, name: 'Old', status: 1, db_type: 0 }] })
    await flush()
    assert.equal(h.aliasesLoading.value, true)
    assert.deepEqual(h.aliasOptions.value, [])
    b.resolve({
      code: 200,
      data: [
        { id: 2, name: 'Current', status: 1, db_type: 0 },
        { id: 3, name: 'Disabled', status: 0, db_type: 0 },
        { id: 4, name: 'Non SQL', status: 1, db_type: 3 },
      ],
    })
    await flush()
    assert.deepEqual(
      h.aliasOptions.value.map((row) => row.id),
      [2]
    )
    assert.equal(h.draft.datasource_alias, null)
  } finally {
    h.cleanup()
  }
})
test('alias failure is local, retains draft and blocks save until read retry succeeds', async () => {
  let fail = true
  const h = publicHarness({
    component: true,
    api: {
      getDataFactoryDatasourceAlias: async () => {
        if (fail) throw Error()
        return { code: 200, data: [] }
      },
    },
  })
  try {
    h.open(dto.readPublicRow(sql()))
    await flush()
    assert.equal(h.aliasesFailed.value, true)
    assert.equal(await h.save(), false)
    assert.equal(h.writes.length, 0)
    fail = false
    await h.loadAliases()
    assert.equal(h.aliasesFailed.value, false)
    assert.equal(h.aliasOptions.value[0].disabled, true)
    assert.equal(await h.save(), true)
    assert.equal(h.writes[0][1].datasource_alias, 0)
  } finally {
    h.cleanup()
  }
})
test('changing type preserves custom code and removes only the untouched example', () => {
  const h = publicHarness({ component: true })
  try {
    h.open(null, 0)
    h.onTypeChange(2)
    assert.ok(h.draft.value.includes('def variable(context)'))
    h.onTypeChange(0)
    assert.equal(h.draft.value, '')
    h.onTypeChange(2)
    h.draft.value = 'def variable(context):\n    return {"x": 0}'
    h.onTypeChange(1)
    assert.equal(h.draft.value.includes('"x"'), true)
  } finally {
    h.cleanup()
  }
})
test('save snapshots body before awaiting, blocks duplicate/reopen and keeps failed drafts retryable', async () => {
  const wait = deferred()
  let fail = true
  const h = publicHarness({
    component: true,
    api: { putUiPublic: () => (fail ? wait.promise : Promise.resolve({ code: 200 })) },
  })
  try {
    h.open(dto.readPublicRow(publicRow({ id: longId, test_envs: [0] })))
    const pending = h.save()
    h.draft.test_envs.push(2)
    h.draft.name = 'Changed after dispatch'
    assert.equal(await h.save(), false)
    h.open(null, 2)
    assert.equal(h.editingId.value, longId)
    assert.deepEqual(h.writes[0][1].test_envs, [0])
    assert.equal(h.writes[0][1].id, longId)
    wait.reject(Error())
    assert.equal(await pending, false)
    assert.equal(h.visible.value, true)
    assert.ok(h.error.value)
    fail = false
    assert.equal(await h.save(), true)
    assert.equal(h.visible.value, false)
    assert.equal(h.events.filter(([event]) => event === 'saved').length, 1)
  } finally {
    h.cleanup()
  }
})
test('save fails validation without dispatch and unsuccessful envelope never closes editor', async () => {
  const h = publicHarness({ component: true, api: { postUiPublic: async () => ({ code: 500 }) } })
  try {
    h.open()
    assert.equal(await h.save(), false)
    assert.equal(h.writes.length, 0)
    h.draft.project_product = 0
    h.draft.type = 0
    h.draft.name = 'Example'
    h.draft.key = 'key'
    h.draft.value = '0'
    assert.equal(await h.save(), false)
    assert.equal(h.visible.value, true)
    assert.equal(h.saving.value, false)
  } finally {
    h.cleanup()
  }
})
for (const change of ['hidden', 'deactivate', 'role', 'environment', 'route', 'unmount']) {
  test(`editor pending write retains physical lock and rejects late UI effects on ${change}`, async () => {
    const wait = deferred(),
      h = publicHarness({ component: true, api: { putUiPublic: () => wait.promise } })
    try {
      h.mount()
      h.open(dto.readPublicRow(publicRow()))
      const pending = h.save()
      if (change === 'hidden') h.visibility('hidden')
      else if (change === 'deactivate') h.callbacks.deactivate.forEach((fn) => fn())
      else if (change === 'role') h.user.roleId++
      else if (change === 'environment') h.user.selected_environment++
      else if (change === 'route') {
        h.route.path = '/elsewhere'
        h.route.fullPath = '/elsewhere'
      } else h.callbacks.unmount.forEach((fn) => fn())
      assert.equal(h.visible.value, false)
      assert.equal(h.saving.value, true)
      h.open(null, 0)
      assert.equal(h.visible.value, false)
      wait.resolve({ code: 200 })
      assert.equal(await pending, false)
      assert.equal(h.saving.value, false)
      assert.equal(
        h.events.some(([event]) => event === 'saved'),
        false
      )
      assert.equal(h.messages.length, 0)
    } finally {
      h.cleanup()
    }
  })
}
