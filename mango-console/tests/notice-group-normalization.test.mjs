import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/config/project/notice')
const record = (id = 1, extra = {}) => ({
  id,
  name: `Group ${id}`,
  mail: ['first@example.org'],
  work_weixin: 'https://example.com/hooks/first',
  feishu: null,
  dingding: null,
  project: { id: 10, name: 'Project' },
  ...extra,
})
function setupNotice(name, bindings, api = {}, props = {}) {
  const lifecycle = {},
    route = vue.reactive({ path: '/config/project/notice', query: { id: '10', name: 'Project' } }),
    user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-session' }),
    pageData = vue.reactive({ record: { id: 4, name: 'Stored project' } }),
    dialogs = [],
    notices = []
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
      '@/store/page-data': { usePageData: () => pageData },
      '@/hooks/table': {
        useTableIndexColumn: () => ({ key: 'index' }),
        useTableColumn: (columns) => columns,
        usePagination: (callback, loading) =>
          vue.reactive({
            page: 1,
            pageSize: 20,
            pageCount: 0,
            setTotalSize(total) {
              this.pageCount = total
            },
            onChange() {
              loading.value = true
              return callback()
            },
          }),
      },
      '@arco-design/web-vue': {
        Message: {
          success: (m) => notices.push(['success', m]),
          error: (m) => notices.push(['error', m]),
        },
        Modal: {
          confirm: (config) => {
            const d = {
              config,
              closed: false,
              close() {
                d.closed = true
                config.onClose?.()
              },
            }
            dialogs.push(d)
            return d
          },
        },
      },
    },
  })
  return {
    ...state,
    lifecycle,
    route,
    user,
    pageData,
    dialogs,
    notices,
    dispose() {
      lifecycle.unmount?.()
      state.close()
    },
  }
}
const page = (api = {}) =>
  setupNotice(
    'index',
    'rows,listLoading,loadError,projectId,noticeDetailTitle,pagination,doRefresh,onAdd,onUpdate,onDelete,onTest,onEditorSaving,editorRef,editorSaving,testingIds,deletingIds,editingIds',
    api
  )
const editor = (api = {}) =>
  setupNotice('NoticeGroupEditor', 'draft,open,close,save,visible,saving,editingId', api, {
    projectId: 10,
  })

test('page and independent editor compile with horizontal guarded modal and local action loading', () => {
  for (const file of ['index.vue', 'components/NoticeGroupEditor.vue']) {
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
    assert.doesNotMatch(
      descriptor.scriptSetup.content,
      /reactive<any>|as any|console\.log|getUserName/
    )
  }
})
test('route id/name outrank stale page data; direct links do not inherit another project title', async () => {
  const s = page()
  try {
    assert.equal(s.projectId.value, 10)
    assert.equal(s.noticeDetailTitle.value, '通知组配置 / 10 / Project')
    delete s.route.query.name
    assert.equal(s.noticeDetailTitle.value, '通知组配置 / 10 / -')
    s.pageData.record = { id: 10, name: 'Matching project' }
    assert.equal(s.noticeDetailTitle.value, '通知组配置 / 10 / Matching project')
    s.route.query.name = 'Fresh'
    assert.equal(s.noticeDetailTitle.value, '通知组配置 / 10 / Fresh')
  } finally {
    s.dispose()
  }
})
test('legacy missing route id falls back to page data and rejects explicit invalid ids', async () => {
  const calls = [],
    s = page({
      getSystemNotice: async (p) => {
        calls.push(p)
        return { data: [], totalSize: 0 }
      },
    })
  try {
    delete s.route.query.id
    delete s.route.query.name
    assert.equal(s.projectId.value, 4)
    assert.equal(s.noticeDetailTitle.value, '通知组配置 / 4 / Stored project')
    for (const id of ['', null, [], ['10', '11'], '-1', '0', '1e2', '9007199254740993']) {
      s.route.query.id = id
      const before = calls.length
      await s.doRefresh()
      assert.equal(s.projectId.value, null)
      assert.equal(calls.length, before)
      assert.match(s.loadError.value, /缺少有效项目 ID/)
    }
    s.route.query.id = '0010'
    await flush()
    assert.equal(s.projectId.value, 10)
  } finally {
    s.dispose()
  }
})
test('mail draft conversion copies arrays, accepts legacy comma strings and normalizes empty values', () => {
  const s = editor(),
    other = editor()
  try {
    const original = record()
    s.open(original)
    s.draft.mail.push('second@example.net')
    assert.deepEqual(original.mail, ['first@example.org'])
    assert.deepEqual(other.draft.mail, [])
    s.exposed.close()
    s.open(record(2, { mail: 'first@example.org, second@example.net, ,', work_weixin: null }))
    assert.deepEqual(s.draft.mail, ['first@example.org', 'second@example.net'])
    assert.equal(s.draft.work_weixin, '')
    s.exposed.close()
    s.open(record(3, { mail: null }))
    assert.deepEqual(s.draft.mail, [])
  } finally {
    s.dispose()
    other.dispose()
  }
})
test('create, edit, cancel and reopen reset all notice fields without sharing values', () => {
  const s = editor()
  try {
    s.open(record())
    s.draft.feishu = 'https://example.net/hooks/draft'
    assert.equal(s.editingId.value, 1)
    s.exposed.close()
    s.open()
    assert.equal(s.editingId.value, null)
    assert.deepEqual(s.draft, { name: '', mail: [], work_weixin: '', feishu: '', dingding: '' })
    assert.equal(s.visible.value, true)
  } finally {
    s.dispose()
  }
})
test('create payload keeps project/name/mail/webhook protocol, empty optionals and no audit fields', async () => {
  const calls = [],
    s = editor({
      postSystemNotice: async (p) => {
        calls.push(p)
        return { msg: 'ok' }
      },
    })
  try {
    s.open()
    s.draft.name = 'New'
    s.draft.mail = ['', 'mail@example.org']
    assert.equal(await s.save(), true)
    assert.deepEqual(calls, [
      {
        name: 'New',
        mail: ['mail@example.org'],
        work_weixin: null,
        feishu: null,
        dingding: null,
        project: 10,
      },
    ])
    assert.deepEqual(s.events, [
      ['saving-change', null, true],
      ['saved'],
      ['saving-change', null, false],
    ])
  } finally {
    s.dispose()
  }
})
test('edit only submits ID and whitelisted fields with a frozen email array snapshot', async () => {
  const gate = deferred(),
    calls = [],
    s = editor({
      putSystemNotice: (p) => {
        calls.push(p)
        return gate.promise
      },
    })
  try {
    const original = record(5, { update_time: 'audit' })
    s.open(original)
    const pending = s.save()
    s.draft.mail.push('later@example.net')
    s.draft.name = 'Later'
    assert.equal(await s.save(), false)
    assert.deepEqual(calls[0], {
      id: 5,
      name: 'Group 5',
      mail: ['first@example.org'],
      work_weixin: 'https://example.com/hooks/first',
      feishu: null,
      dingding: null,
    })
    assert.equal('project' in calls[0], false)
    assert.equal('update_time' in calls[0], false)
    gate.resolve({ msg: 'ok' })
    assert.equal(await pending, true)
  } finally {
    s.dispose()
  }
})
test('name validation and failed saves retain user input and allow explicit retry', async () => {
  let fail = true,
    count = 0
  const s = editor({
    postSystemNotice: async () => {
      count++
      if (fail) throw Error()
      return { msg: 'ok' }
    },
  })
  try {
    s.open()
    assert.equal(await s.save(), false)
    assert.equal(count, 0)
    s.draft.name = 'Keep'
    s.draft.mail = ['keep@example.net']
    assert.equal(await s.save(), false)
    assert.equal(s.visible.value, true)
    assert.deepEqual(s.draft.mail, ['keep@example.net'])
    assert.equal(s.saving.value, false)
    fail = false
    assert.equal(await s.save(), true)
  } finally {
    s.dispose()
  }
})
test('pending save after project change cannot emit saved or reopen before physical completion', async () => {
  const gate = deferred(),
    s = editor({ putSystemNotice: () => gate.promise })
  try {
    s.open(record())
    const pending = s.save()
    s.props.projectId = 11
    assert.equal(s.visible.value, false)
    s.open(record(2))
    assert.equal(s.visible.value, false)
    gate.resolve({ msg: 'ok' })
    assert.equal(await pending, false)
    assert.deepEqual(s.events, [
      ['saving-change', 1, true],
      ['saving-change', 1, false],
    ])
    s.open(record(2))
    assert.equal(s.editingId.value, 2)
  } finally {
    s.dispose()
  }
})
test('cached editor closes and ignores old success; null project cannot create or save', async () => {
  const gate = deferred(),
    s = editor({ postSystemNotice: () => gate.promise })
  try {
    s.props.projectId = null
    s.open()
    assert.equal(s.visible.value, false)
    s.props.projectId = 10
    s.open()
    s.draft.name = 'Draft'
    const pending = s.save()
    s.lifecycle.deactivate()
    s.lifecycle.activate()
    gate.resolve({ msg: 'ok' })
    assert.equal(await pending, false)
    assert.equal(
      s.events.some((event) => event[0] === 'saved'),
      false
    )
  } finally {
    s.dispose()
  }
})
test('list request snapshots project/page/pageSize and uses server total with local loading', async () => {
  const gate = deferred(),
    calls = [],
    s = page({
      getSystemNotice: (p) => {
        calls.push(p)
        return gate.promise
      },
    })
  try {
    s.pagination.page = 2
    s.pagination.pageSize = 50
    const pending = s.pagination.onChange()
    assert.equal(s.listLoading.value, true)
    assert.deepEqual(calls, [{ project: 10, page: 2, pageSize: 50 }])
    gate.resolve({ data: [record()], totalSize: 73 })
    await pending
    assert.equal(s.pagination.pageCount, 73)
    assert.equal(s.listLoading.value, false)
    assert.equal(s.rows.value[0].id, 1)
  } finally {
    s.dispose()
  }
})
test('same-project latest request controls rows and loading; failure is locally retryable', async () => {
  const a = deferred(),
    b = deferred()
  let reads = 0
  const s = page({ getSystemNotice: () => (++reads === 1 ? a.promise : b.promise) })
  try {
    const old = s.doRefresh(),
      fresh = s.doRefresh()
    a.resolve({ data: [record(1)], totalSize: 1 })
    await old
    assert.deepEqual(s.rows.value, [])
    assert.equal(s.listLoading.value, true)
    b.resolve({ data: [record(2)], totalSize: 2 })
    await fresh
    assert.equal(s.rows.value[0].id, 2)
  } finally {
    s.dispose()
  }
  let fail = true
  const f = page({
    getSystemNotice: async () => {
      if (fail) throw Error()
      return { data: [record()], totalSize: 1 }
    },
  })
  try {
    await f.doRefresh()
    assert.equal(f.listLoading.value, false)
    assert.equal(f.loadError.value, '通知组加载失败，请重试')
    fail = false
    await f.doRefresh()
    assert.equal(f.loadError.value, '')
  } finally {
    f.dispose()
  }
})
test('project A→B→A resets pagination and windows; first A cannot replace current A', async () => {
  const gates = [deferred(), deferred(), deferred()]
  let reads = 0
  const s = page({ getSystemNotice: () => gates[reads++].promise })
  try {
    s.pagination.page = 3
    s.pagination.setTotalSize(100)
    const old = s.doRefresh()
    let closes = 0
    s.editorRef.value = {
      close() {
        closes++
      },
      open() {},
    }
    s.route.query.id = '11'
    assert.equal(s.pagination.page, 1)
    assert.equal(s.pagination.pageCount, 0)
    s.route.query.id = '10'
    gates[0].resolve({ data: [record(99)], totalSize: 1 })
    await old
    assert.deepEqual(s.rows.value, [])
    assert.equal(s.listLoading.value, true)
    gates[2].resolve({ data: [record(3)], totalSize: 1 })
    gates[1].resolve({ data: [record(2)], totalSize: 1 })
    await flush()
    assert.equal(s.rows.value[0].id, 3)
    assert.ok(closes >= 2)
  } finally {
    s.dispose()
  }
})
test('delete captures ID, blocks duplicate operations and keeps failure retryable', async () => {
  const gate = deferred(),
    ids = []
  let fail = true
  const s = page({
    deleteSystemNotice: (id) => {
      ids.push(id)
      return fail ? gate.promise : Promise.resolve({ msg: 'ok' })
    },
  })
  try {
    const row = record()
    s.onDelete(row)
    row.id = 99
    const d = s.dialogs[0],
      pending = d.config.onBeforeOk()
    assert.equal(await d.config.onBeforeOk(), false)
    await s.onTest(record())
    assert.equal(s.testingIds.size, 0)
    gate.reject(Error())
    assert.equal(await pending, false)
    fail = false
    assert.equal(await d.config.onBeforeOk(), true)
    assert.deepEqual(ids, [1, 1])
    assert.equal(d.config.okButtonProps.status, 'danger')
  } finally {
    s.dispose()
  }
})
test('delete final row on a later page requests previous page and releases pending state', async () => {
  const calls = [],
    s = page({
      getSystemNotice: async (p) => {
        calls.push(p)
        return { data: [], totalSize: 20 }
      },
    })
  try {
    s.rows.value = [record()]
    s.pagination.page = 2
    s.onDelete(record())
    assert.equal(await s.dialogs[0].config.onBeforeOk(), true)
    assert.equal(calls[0].page, 1)
    assert.equal(s.deletingIds.size, 0)
  } finally {
    s.dispose()
  }
})
test('old delete confirmation cannot run after identity switch or interfere with a newer dialog', async () => {
  let writes = 0
  const s = page({
    deleteSystemNotice: async () => {
      writes++
      return { msg: 'ok' }
    },
  })
  try {
    s.onDelete(record())
    const old = s.dialogs[0]
    s.user.roleId = 2
    assert.equal(old.closed, true)
    assert.equal(await old.config.onBeforeOk(), false)
    s.onDelete(record(2))
    const fresh = s.dialogs[1]
    old.close()
    s.onDelete(record(3))
    assert.equal(s.dialogs.length, 2)
    assert.equal(writes, 0)
    assert.equal(await fresh.config.onBeforeOk(), true)
  } finally {
    s.dispose()
  }
})
test('test send is per-row, freezes ID, prevents duplicates and never starts automatically', async () => {
  const a = deferred(),
    b = deferred(),
    calls = [],
    s = page({
      getSystemNoticeTest: (id) => {
        calls.push(id)
        return id === 1 ? a.promise : b.promise
      },
    })
  try {
    s.lifecycle.mount()
    s.lifecycle.activate()
    await flush()
    assert.deepEqual(calls, [])
    const original = record(),
      one = s.onTest(original)
    original.id = 99
    await s.onTest(record())
    const two = s.onTest(record(2))
    assert.deepEqual(calls, [1, 2])
    assert.deepEqual([...s.testingIds], [1, 2])
    a.resolve({ msg: 'first' })
    await one
    assert.deepEqual([...s.testingIds], [2])
    b.resolve({ msg: 'second' })
    await two
    assert.equal(s.testingIds.size, 0)
  } finally {
    s.dispose()
  }
})
test('test failure displays current error once, releases loading and retries only on another user action', async () => {
  let fail = true,
    count = 0
  const s = page({
    getSystemNoticeTest: async () => {
      count++
      if (fail) throw Error('fixture send failure')
      return { msg: 'ok' }
    },
  })
  try {
    await s.onTest(record())
    assert.deepEqual(s.notices, [['error', 'fixture send failure']])
    assert.equal(s.testingIds.size, 0)
    assert.equal(count, 1)
    fail = false
    await s.onTest(record())
    assert.equal(count, 2)
    assert.deepEqual(s.notices.at(-1), ['success', 'ok'])
  } finally {
    s.dispose()
  }
})
test('test send survives physical request but never toasts or resends after cached leave and return', async () => {
  const gate = deferred()
  let sends = 0
  const s = page({
    getSystemNoticeTest: () => {
      sends++
      return gate.promise
    },
  })
  try {
    const pending = s.onTest(record())
    s.lifecycle.deactivate()
    s.lifecycle.activate()
    await flush()
    assert.equal(sends, 1)
    gate.reject(Error('old failure'))
    await pending
    assert.deepEqual(s.notices, [])
    assert.equal(s.testingIds.size, 0)
  } finally {
    s.dispose()
  }
})
test('saving event coordinates editor with tests/deletes and opens only one editor at a time', async () => {
  let sends = 0,
    opens = 0
  const s = page({
    getSystemNoticeTest: async () => {
      sends++
      return { msg: 'ok' }
    },
  })
  try {
    s.editorRef.value = {
      open() {
        opens++
      },
      close() {},
    }
    s.onEditorSaving(1, true)
    s.onAdd()
    s.onUpdate(record())
    s.onDelete(record())
    await s.onTest(record())
    assert.equal(opens, 0)
    assert.equal(s.dialogs.length, 0)
    assert.equal(sends, 0)
    s.onEditorSaving(1, false)
    s.onUpdate(record())
    assert.equal(opens, 1)
    await s.onTest(record())
    assert.equal(sends, 1)
  } finally {
    s.dispose()
  }
})
test('a pending test blocks deleting or editing the tested row', async () => {
  const gate = deferred(),
    s = page({ getSystemNoticeTest: () => gate.promise })
  let opens = 0
  try {
    s.editorRef.value = {
      open() {
        opens++
      },
      close() {},
    }
    const pending = s.onTest(record())
    s.onUpdate(record())
    s.onDelete(record())
    assert.equal(opens, 0)
    assert.equal(s.dialogs.length, 0)
    gate.resolve({ msg: 'ok' })
    await pending
    s.onUpdate(record())
    assert.equal(opens, 1)
  } finally {
    s.dispose()
  }
})
test('initial activation deduplicates loading; cached reactivation reloads same page without test send', async () => {
  const old = deferred()
  let reads = 0,
    sends = 0
  const s = page({
    getSystemNotice: () =>
      ++reads === 1 ? old.promise : Promise.resolve({ data: [record(2)], totalSize: 50 }),
    getSystemNoticeTest: async () => {
      sends++
      return { msg: 'ok' }
    },
  })
  try {
    s.pagination.page = 2
    s.lifecycle.mount()
    s.lifecycle.activate()
    assert.equal(reads, 1)
    s.lifecycle.deactivate()
    old.resolve({ data: [record(99)], totalSize: 1 })
    await flush()
    assert.deepEqual(s.rows.value, [])
    s.lifecycle.activate()
    await flush()
    assert.equal(reads, 2)
    assert.equal(s.pagination.page, 2)
    assert.equal(s.rows.value[0].id, 2)
    assert.equal(sends, 0)
  } finally {
    s.dispose()
  }
})
test('navigation away and login change discard pending list and test success', async () => {
  const list = deferred(),
    send = deferred(),
    s = page({ getSystemNotice: () => list.promise, getSystemNoticeTest: () => send.promise })
  try {
    const load = s.doRefresh(),
      testSend = s.onTest(record())
    s.route.path = '/config/project/index'
    s.user.token = 'new-fixture-session'
    list.resolve({ data: [record()], totalSize: 1 })
    send.resolve({ msg: 'old success' })
    await load
    await testSend
    assert.deepEqual(s.rows.value, [])
    assert.deepEqual(s.notices, [])
    assert.equal(s.listLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('notice test API wrapper preserves GET endpoint/id and delegates guarded error feedback to caller', async () => {
  const exports = {},
    calls = []
  const code = ts.transpileModule(readFileSync('src/api/system/notice_group.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS },
  }).outputText
  new Function('exports', 'require', code)(exports, () => ({
    get: async (options) => {
      calls.push(options)
      return { code: 200, msg: 'fixture' }
    },
  }))
  await exports.getSystemNoticeTest(7)
  assert.equal(calls[0].url, 'system/notice/test')
  assert.deepEqual(calls[0].data(), { id: 7 })
  assert.equal(calls[0].silentError, true)
})
