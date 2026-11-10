import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/gray/repository')
const record = (extra = {}) => ({
  id: 11,
  name: 'Example repository',
  repo_url: 'https://example.com/team/repository.git',
  provider: 'gitlab',
  api_base_url: 'https://example.com',
  branch: 'main',
  test_env: 0,
  config_dirs: ['app/config'],
  status: 0,
  access_token: '已配置',
  ...extra,
})
const page = (rows = [record()], totalSize = rows.length) => ({ code: 200, data: rows, totalSize })
function fixture(kind = 'editor', overrides = {}, enumApi = async () => {}) {
  const hooks = { mounted: [], activate: [], deactivate: [], unmount: [] },
    messages = [],
    dialogs = [],
    calls = []
  const user = vue.reactive({
      userId: 1,
      roleId: 2,
      token: 'example-session',
      selected_environment: 0,
    }),
    route = vue.reactive({ fullPath: '/gray/repository/index' })
  const modules = {
    vue: {
      ...vue,
      onMounted: (fn) => hooks.mounted.push(fn),
      onActivated: (fn) => hooks.activate.push(fn),
      onDeactivated: (fn) => hooks.deactivate.push(fn),
      onBeforeUnmount: (fn) => hooks.unmount.push(fn),
    },
    '@/store/modules/get-enum': {
      useEnum: () => ({
        environment_type: [
          { key: 0, title: 'Development' },
          { key: 2, title: 'Test' },
        ],
        colors: { 0: 'gray', 1: 'blue', 2: 'green' },
        getEnum: enumApi,
      }),
    },
    '@/store/modules/user': { default: () => user },
    'vue-router': { useRoute: () => route },
    '@arco-design/web-vue': {
      Message: Object.fromEntries(
        ['warning', 'error', 'success'].map((k) => [k, (message) => messages.push([k, message])])
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
  }
  const api = {
    getGrayRepository: async () => page(),
    postGrayRepository: async (p) => {
      calls.push(p)
      return { code: 200, data: { ...p, id: 12 } }
    },
    putGrayRepository: async (p) => {
      calls.push(p)
      return { code: 200, data: p }
    },
    postGrayRepositoryTest: async (p) => {
      calls.push(p)
      return { code: 200, data: { id: 42, username: 'example' } }
    },
    postGrayRepositorySync: async (p) => {
      calls.push(p)
      return {
        code: 200,
        data: {
          repository_id: p.repository_id,
          provider: 'gitlab',
          repo_url: record().repo_url,
          branch: 'main',
          file_count: 0,
          files: [],
        },
      }
    },
    deleteGrayRepository: async (id) => {
      calls.push(id)
      return { code: 200 }
    },
    ...overrides,
  }
  let f
  if (kind === 'page') {
    const loader = harness('RepositoryEditor', 'form', { base, modules, api })
    modules['@/hooks/table'] = loader.load('../../../hooks/table.ts')
    loader.close()
    f = harness(
      'index',
      'query,rows,loading,loadError,enumLoading,enumError,editorVisible,editorSaving,editorRef,pagination,actionLoading,interactionBlocked,onSearch,onSearchRefresh,onReset,onAdd,onEdit,onSaved,onTest,onSync,onModifyStatus,onDelete,loadEnums,contextKey,formatEnvironmentText',
      { base, modules, api }
    )
  } else
    f = harness(
      'RepositoryEditor',
      'open,save,canCancel,onVisibleChange,visible,saving,saveError,form,recordId,enumError,enumLoading,loadEnums',
      { base, modules, api, props: { contextKey: 'A', blocked: false } }
    )
  return {
    ...f,
    hooks,
    user,
    route,
    messages,
    dialogs,
    calls,
    cleanup() {
      hooks.unmount.forEach((fn) => fn())
      f.close()
    },
  }
}
test('edit drafts are isolated, zero environment/status preserved and token is never echoed', () => {
  const e = fixture(),
    source = record()
  e.open(source)
  assert.equal(e.form.test_env, 0)
  assert.equal(e.form.status, 0)
  assert.equal(e.form.access_token, '')
  e.form.config_dirs.push('another')
  e.form.name = 'Changed'
  assert.deepEqual(source.config_dirs, ['app/config'])
  assert.equal(source.name, 'Example repository')
  e.cleanup()
})
test('cancel, reopen and create reset drafts without retaining credentials', () => {
  const e = fixture()
  e.open(record())
  e.form.access_token = 'example-replacement'
  e.onVisibleChange(false)
  e.open()
  assert.equal(e.form.access_token, '')
  assert.equal(e.form.name, '')
  assert.equal(e.form.provider, 'gitlab')
  assert.equal(e.form.test_env, '__common__')
  assert.deepEqual(e.form.config_dirs, [])
  assert.equal(e.form.status, 1)
  e.cleanup()
})
test('edit save omits blank token and all audit/display fields', async () => {
  const e = fixture()
  e.open(record({ description: 'Keep existing description', last_update_user: { id: 1 } }))
  await e.save()
  assert.equal(e.calls.length, 1)
  assert.equal('access_token' in e.calls[0], false)
  assert.equal('description' in e.calls[0], false)
  assert.equal('last_update_user' in e.calls[0], false)
  assert.equal(e.calls[0].test_env, 0)
  assert.equal(e.calls[0].status, 0)
  assert.equal(e.visible.value, false)
  assert.ok(e.events.some(([name, id]) => name === 'saved' && id === 11))
  e.cleanup()
})
test('replacement token is submitted explicitly and original source label remains unchanged', async () => {
  const e = fixture(),
    source = record()
  e.open(source)
  e.form.access_token = 'example-replacement'
  await e.save()
  assert.equal(e.calls[0].access_token, 'example-replacement')
  assert.equal(source.access_token, '已配置')
  e.cleanup()
})
test('create saves common environment as null and accepts optional blank token', async () => {
  const e = fixture()
  e.open()
  Object.assign(e.form, { ...record(), test_env: '__common__', access_token: '' })
  await e.save()
  assert.equal(e.calls[0].test_env, null)
  assert.equal(e.calls[0].access_token, '')
  assert.equal('id' in e.calls[0], false)
  assert.ok(e.events.some(([name, id]) => name === 'saved' && id === 12))
  e.cleanup()
})
for (const field of [
  'name',
  'repo_url',
  'provider',
  'api_base_url',
  'test_env',
  'branch',
  'config_dirs',
])
  test('required ' + field + ' is validated without a request', async () => {
    const e = fixture()
    e.open(record())
    e.form[field] = field === 'config_dirs' ? [] : ''
    await e.save()
    assert.equal(e.calls.length, 0)
    assert.ok(e.messages.some(([kind]) => kind === 'warning'))
    e.cleanup()
  })
test('directory normalization follows relative path semantics and keeps parent traversal for backend rejection', () => {
  const e = fixture(),
    h = e.load('records.ts')
  assert.deepEqual(
    h.normalizeDirs([' /app\\config/ ', 'app/config', 'app/./config', 'a//b', '../unsafe']),
    ['app/config', 'a/b', '../unsafe']
  )
  assert.deepEqual(h.normalizeDirs(['.', './', './.', '/', '']), ['.'])
  e.cleanup()
})
test('save prevents duplicate writes, close and reopen until HTTP settles', async () => {
  const pending = deferred()
  let body,
    count = 0
  const e = fixture('editor', {
    putGrayRepository: (p) => {
      body = p
      ++count
      return pending.promise
    },
  })
  e.open(record())
  const first = e.save()
  assert.equal(e.saving.value, true)
  assert.equal(e.canCancel(), false)
  e.onVisibleChange(false)
  e.open(record({ id: 22 }))
  await e.save()
  assert.equal(e.recordId.value, 11)
  assert.equal(count, 1)
  pending.resolve({ code: 200, data: body })
  await first
  assert.equal(e.saving.value, false)
  assert.equal(e.visible.value, false)
  e.cleanup()
})
test('failed save retains drafts and replacement credential for retry', async () => {
  let fail = true
  const e = fixture('editor', {
    putGrayRepository: async (p) => (fail ? { code: 500 } : { code: 200, data: p }),
  })
  e.open(record())
  e.form.access_token = 'example-replacement'
  await e.save()
  assert.equal(e.saveError.value, true)
  assert.equal(e.form.access_token, 'example-replacement')
  assert.equal(e.saving.value, false)
  fail = false
  await e.save()
  assert.equal(e.visible.value, false)
  e.cleanup()
})
for (const field of [
  'id',
  'name',
  'repo_url',
  'provider',
  'api_base_url',
  'test_env',
  'branch',
  'status',
  'config_dirs',
])
  test('mismatched save acknowledgment ' + field + ' cannot claim success', async () => {
    const e = fixture('editor', {
      putGrayRepository: async (p) => ({
        code: 200,
        data: {
          ...p,
          [field]:
            field === 'config_dirs'
              ? []
              : field === 'id' || field === 'status' || field === 'test_env'
              ? 99
              : 'mismatch',
        },
      }),
    })
    e.open(record())
    await e.save()
    assert.equal(e.saveError.value, true)
    assert.equal(e.visible.value, true)
    assert.equal(
      e.events.some(([name]) => name === 'saved'),
      false
    )
    e.cleanup()
  })
for (const transition of ['context', 'deactivate', 'unmount'])
  test('editor ' + transition + ' ignores late saves and retains physical lock', async () => {
    const pending = deferred()
    let body
    const e = fixture('editor', {
      putGrayRepository: (p) => {
        body = p
        return pending.promise
      },
    })
    const context = vue.ref('A')
    e.props.contextKey = () => context.value
    e.open(record())
    const work = e.save()
    if (transition === 'context') {
      context.value = 'B'
      context.value = 'A'
    } else e.hooks[transition].forEach((fn) => fn())
    if (transition === 'deactivate') e.hooks.activate.forEach((fn) => fn())
    assert.equal(e.saving.value, true)
    e.open(record())
    assert.equal(e.visible.value, false)
    pending.resolve({ code: 200, data: body })
    await work
    assert.equal(
      e.events.some(([name]) => name === 'saved'),
      false
    )
    assert.equal(e.saving.value, false)
    e.cleanup()
  })
test('editor enum load failure is local, retryable and does not overwrite draft environment', async () => {
  let fail = true
  const e = fixture('editor', {}, async () => {
    if (fail) throw Error('offline')
  })
  e.open(record())
  await flush()
  assert.equal(e.enumError.value, true)
  assert.equal(e.form.test_env, 0)
  fail = false
  await e.loadEnums()
  assert.equal(e.enumError.value, false)
  e.cleanup()
})
test('search preserves multi status zero and exact nullable environment protocol', () => {
  const e = fixture(),
    h = e.load('records.ts'),
    q = h.createQuery()
  assert.deepEqual(h.requestParams(q, 1, 20), { page: 1, pageSize: 20 })
  q.provider = ['gitlab', 'github']
  q.status = [0, 1]
  q.test_env = '__common__'
  assert.deepEqual(h.requestParams(q, 2, 50), {
    page: 2,
    pageSize: 50,
    provider__in: 'gitlab,github',
    status__in: '0,1',
    test_env__isnull: true,
  })
  q.test_env = 0
  assert.equal(h.requestParams(q, 1, 20).test_env, 0)
  q.test_env = undefined
  assert.equal('test_env' in h.requestParams(q, 1, 20), false)
  e.cleanup()
})
test('finite list DTO retains only token presence and preserves detached directories', () => {
  const e = fixture(),
    source = record(),
    h = e.load('records.ts'),
    result = h.repositoryPage(page([source]))
  result.rows[0].config_dirs.push('other')
  assert.deepEqual(source.config_dirs, ['app/config'])
  assert.equal(result.rows[0].access_token, '已配置')
  assert.deepEqual(h.repositoryPage({ code: 200, data: [] }), { rows: [], total: 0 })
  assert.throws(() =>
    h.repositoryPage(page([{ ...source, access_token: 'unexpected-raw-credential' }]))
  )
  e.cleanup()
})
for (const response of [
  { code: 500, data: [] },
  page([record(), record()]),
  page([record()], 0),
  page([record({ test_env: '0' })]),
  page([record({ status: 9 })]),
])
  test('invalid list response is rejected ' + JSON.stringify(response), () => {
    const e = fixture()
    assert.throws(() => e.load('records.ts').repositoryPage(response))
    e.cleanup()
  })
test('main list and enums start independently with separate loading and retry', async () => {
  const pending = deferred()
  let fail = true
  const e = fixture('page', { getGrayRepository: () => pending.promise }, async () => {
    if (fail) throw Error('offline')
  })
  e.hooks.mounted.forEach((fn) => fn())
  await flush()
  assert.equal(e.loading.value, true)
  assert.equal(e.enumLoading.value, false)
  assert.equal(e.enumError.value, true)
  fail = false
  await e.loadEnums()
  assert.equal(e.enumError.value, false)
  pending.resolve(page())
  await flush()
  assert.equal(e.rows.value.length, 1)
  assert.equal(e.loading.value, false)
  e.cleanup()
})
test('search failure keeps visible rows and can retry', async () => {
  let fail = false
  const e = fixture('page', {
    getGrayRepository: async () => {
      if (fail) throw Error('offline')
      return page()
    },
  })
  await e.onSearch()
  fail = true
  assert.equal(await e.onSearch(), false)
  assert.equal(e.rows.value.length, 1)
  assert.ok(e.loadError.value)
  assert.equal(e.loading.value, false)
  fail = false
  assert.equal(await e.onSearch(), true)
  assert.equal(e.loadError.value, '')
  e.cleanup()
})
test('latest search owns rows/loading while older request fails', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const e = fixture('page', { getGrayRepository: () => (++count === 1 ? a.promise : b.promise) })
  const first = e.onSearch(),
    second = e.onSearch()
  a.reject(Error('old'))
  await first
  assert.equal(e.loading.value, true)
  assert.equal(e.loadError.value, '')
  b.resolve(page([record({ id: 12 })]))
  await second
  assert.equal(e.rows.value[0].id, 12)
  e.cleanup()
})
for (const field of ['roleId', 'userId', 'token', 'selected_environment'])
  test(field + ' A-B-A discards old read', async () => {
    const pending = deferred(),
      e = fixture('page', { getGrayRepository: () => pending.promise }),
      first = e.onSearch(),
      old = e.user[field]
    e.user[field] = field === 'token' ? 'example-other' : 99
    e.user[field] = old
    pending.resolve(page())
    assert.equal(await first, false)
    assert.deepEqual(e.rows.value, [])
    e.cleanup()
  })
test('route change and cached activation clear stale data and resume independent reads', async () => {
  let calls = 0
  const e = fixture('page', {
    getGrayRepository: async () => {
      ++calls
      return page()
    },
  })
  e.hooks.mounted.forEach((fn) => fn())
  await flush()
  assert.equal(calls, 1)
  e.hooks.deactivate.forEach((fn) => fn())
  assert.deepEqual(e.rows.value, [])
  e.hooks.activate.forEach((fn) => fn())
  await flush()
  assert.equal(calls, 2)
  e.route.fullPath = '/gray/repository/index?view=new'
  await flush()
  assert.equal(calls, 3)
  e.cleanup()
})
test('search reset clears arrays and env; pagination clamps after last row removed', async () => {
  const e = fixture('page', { getGrayRepository: async (p) => (p.page > 1 ? page([], 1) : page()) })
  e.query.provider = ['github']
  e.query.status = [0]
  e.query.test_env = '__common__'
  await e.onReset()
  assert.deepEqual(e.query.provider, [])
  assert.deepEqual(e.query.status, [])
  assert.equal(e.query.test_env, null)
  e.pagination.page = 3
  await e.onSearch()
  assert.equal(e.pagination.page, 1)
  e.cleanup()
})
test('parent add/edit respect sibling operation and editor physical save guards', () => {
  const opened = [],
    e = fixture('page')
  e.editorRef.value = { open: (value) => opened.push(value) }
  e.onAdd()
  e.editorSaving.value = true
  e.onEdit(record())
  assert.deepEqual(opened, [undefined])
  e.editorSaving.value = false
  e.onEdit(record())
  assert.equal(opened[1].id, 11)
  e.cleanup()
})
test('connection response is provider user identity, not repository identity', async () => {
  const e = fixture('page')
  assert.equal(await e.onTest(record()), true)
  assert.deepEqual(e.calls, [{ repository_id: 11 }])
  assert.ok(e.messages.some(([, value]) => value === '连接测试成功'))
  e.cleanup()
})
test('sync validates the fixed source and file count including explicit zero', async () => {
  const e = fixture('page')
  assert.equal(await e.onSync(record()), true)
  assert.deepEqual(e.calls, [{ repository_id: 11 }])
  e.cleanup()
})
for (const bad of [
  { repository_id: 12 },
  { branch: 'other' },
  { provider: 'github' },
  { repo_url: 'https://example.org/other.git' },
  { file_count: 1 },
  { file_count: undefined },
  { files: null },
])
  test('mismatched sync result ' + JSON.stringify(bad) + ' cannot claim success', async () => {
    const e = fixture('page', {
      postGrayRepositorySync: async () => ({
        code: 200,
        data: {
          repository_id: 11,
          provider: 'gitlab',
          repo_url: record().repo_url,
          branch: 'main',
          file_count: 0,
          files: [],
          ...bad,
        },
      }),
    })
    assert.equal(await e.onSync(record()), false)
    assert.equal(
      e.messages.some(([kind]) => kind === 'success'),
      false
    )
    assert.equal(e.actionLoading.value, '')
    e.cleanup()
  })
test('sync snapshots source before request while source row can change externally', async () => {
  const pending = deferred(),
    e = fixture('page', { postGrayRepositorySync: () => pending.promise }),
    source = record(),
    work = e.onSync(source)
  source.branch = 'changed'
  source.id = 90
  pending.resolve({
    code: 200,
    data: {
      repository_id: 11,
      provider: 'gitlab',
      repo_url: record().repo_url,
      branch: 'main',
      file_count: 1,
      files: ['app/config/example.yml'],
    },
  })
  assert.equal(await work, true)
  e.cleanup()
})
test('status is committed only after matching acknowledgment', async () => {
  const pending = deferred()
  let storedStatus = 0
  const e = fixture('page', {
    getGrayRepository: async () => page([record({ status: storedStatus })]),
    putGrayRepository: (p) => {
      e.calls.push(p)
      return pending.promise
    },
  })
  await e.onSearch()
  assert.equal(e.rows.value[0].status, 0)
  const work = e.onModifyStatus(true, 11)
  assert.equal(e.rows.value[0].status, 0)
  storedStatus = 1
  pending.resolve({ code: 200, data: { id: 11, status: 1 } })
  await work
  assert.equal(e.calls[0].status, 1)
  assert.equal(e.rows.value[0].status, 1)
  assert.equal(e.actionLoading.value, '')
  e.cleanup()
})
for (const bad of [
  { id: 12, status: 1 },
  { id: 11, status: 0 },
])
  test(
    'mismatched status response does not mutate displayed status ' + JSON.stringify(bad),
    async () => {
      const e = fixture('page', { putGrayRepository: async () => ({ code: 200, data: bad }) })
      await e.onSearch()
      assert.equal(await e.onModifyStatus(true, 11), false)
      assert.equal(e.rows.value[0].status, 0)
      e.cleanup()
    }
  )
test('delete confirmation snapshots source, awaits request and closes explicitly', async () => {
  const pending = deferred(),
    e = fixture('page', {
      deleteGrayRepository: (id) => {
        e.calls.push(id)
        return pending.promise
      },
    }),
    source = record()
  e.onDelete(source)
  source.id = 99
  const dialog = e.dialogs[0],
    work = dialog.config.onBeforeOk()
  assert.equal(e.actionLoading.value, 'delete-11')
  assert.equal(dialog.config.onBeforeCancel(), false)
  assert.equal(await e.onTest(record()), false)
  pending.resolve({ code: 200 })
  await work
  assert.deepEqual(e.calls, [11])
  assert.equal(dialog.closed, true)
  assert.equal(e.actionLoading.value, '')
  e.cleanup()
})
test('failed deletion keeps confirmation open and permits retry', async () => {
  let fail = true
  const e = fixture('page', { deleteGrayRepository: async () => ({ code: fail ? 500 : 200 }) })
  e.onDelete(record())
  const dialog = e.dialogs[0]
  await dialog.config.onBeforeOk()
  assert.equal(dialog.closed, false)
  fail = false
  await dialog.config.onBeforeOk()
  assert.equal(dialog.closed, true)
  e.cleanup()
})
for (const action of ['onTest', 'onSync', 'onModifyStatus', 'onDelete'])
  test(action + ' physical operation survives context A-B-A and ignores late result', async () => {
    const pending = deferred(),
      apiKey = {
        onTest: 'postGrayRepositoryTest',
        onSync: 'postGrayRepositorySync',
        onModifyStatus: 'putGrayRepository',
        onDelete: 'deleteGrayRepository',
      }[action],
      e = fixture('page', { [apiKey]: () => pending.promise })
    let work
    if (action === 'onDelete') {
      e.onDelete(record())
      work = e.dialogs[0].config.onBeforeOk()
    } else work = action === 'onModifyStatus' ? e.onModifyStatus(true, 11) : e[action](record())
    e.user.roleId = 99
    e.user.roleId = 2
    assert.ok(e.actionLoading.value)
    assert.equal(await e.onTest(record()), false)
    pending.resolve({ code: 200, data: { id: 11, status: 1 } })
    assert.equal(await work, false)
    assert.equal(e.actionLoading.value, '')
    assert.equal(e.messages.length, 0)
    e.cleanup()
  })
test('stale confirmation cannot send delete after environment switch', async () => {
  const e = fixture('page')
  e.onDelete(record())
  const dialog = e.dialogs[0]
  e.user.selected_environment = 2
  assert.equal(dialog.closed, true)
  await dialog.config.onBeforeOk()
  assert.equal(e.calls.length, 0)
  e.cleanup()
})
test('sync/status write success remains distinguishable from subsequent read failure', async () => {
  const e = fixture('page', {
    getGrayRepository: async () => {
      throw Error('offline')
    },
  })
  assert.equal(await e.onSync(record()), true)
  assert.ok(e.messages.some(([, text]) => text.includes('操作已完成')))
  e.cleanup()
})
test('page and editor script/template/style compile with actual bindings', () => {
  for (const relative of ['index.vue', 'components/RepositoryEditor.vue']) {
    const filename = path.join(base, relative),
      { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: filename })
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename,
        id: filename,
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
    for (const style of descriptor.styles)
      assert.deepEqual(
        compileStyle({
          source: style.content,
          filename,
          id: filename,
          scoped: style.scoped,
          preprocessLang: style.lang,
        }).errors,
        []
      )
  }
})
for (const action of ['onSync', 'onTest', 'onModifyStatus', 'onDelete'])
  for (const transition of ['deactivate', 'unmount'])
    test(action + ' retains physical lock after ' + transition, async () => {
      const pending = deferred(),
        apiKey = {
          onSync: 'postGrayRepositorySync',
          onTest: 'postGrayRepositoryTest',
          onModifyStatus: 'putGrayRepository',
          onDelete: 'deleteGrayRepository',
        }[action]
      const e = fixture('page', { [apiKey]: () => pending.promise })
      let work
      if (action === 'onDelete') {
        e.onDelete(record())
        work = e.dialogs[0].config.onBeforeOk()
      } else work = action === 'onModifyStatus' ? e.onModifyStatus(true, 11) : e[action](record())
      e.hooks[transition].forEach((fn) => fn())
      if (transition === 'deactivate') e.hooks.activate.forEach((fn) => fn())
      assert.ok(e.actionLoading.value)
      assert.equal(await e.onTest(record()), false)
      pending.resolve({ code: 200, data: { id: 42 } })
      assert.equal(await work, false)
      assert.equal(e.actionLoading.value, '')
      assert.equal(e.messages.length, 0)
      e.cleanup()
    })
test('connection network failure releases loading and supports retry', async () => {
  let fail = true
  const e = fixture('page', {
    postGrayRepositoryTest: async () => {
      if (fail) throw Error('offline')
      return { code: 200, data: { id: 42 } }
    },
  })
  assert.equal(await e.onTest(record()), false)
  assert.equal(e.actionLoading.value, '')
  fail = false
  assert.equal(await e.onTest(record()), true)
  e.cleanup()
})
test('saved repository with failed list read reports read failure without another write', async () => {
  const e = fixture('page', {
    getGrayRepository: async () => {
      throw Error('offline')
    },
  })
  await e.onSaved()
  assert.ok(e.messages.some(([, text]) => text.includes('仓库已保存')))
  assert.equal(e.calls.length, 0)
  e.cleanup()
})
