import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush as flushVue, harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/pytest/repository'),
  response = (data) => ({ code: 200, data })
const repository = (id = 0, patch = {}) => ({
  id,
  name: 'Fixture ' + id,
  provider: 'gitlab',
  repo_url: 'https://example.com/group/repository.git',
  api_base_url: null,
  remote_project: 'group/repository',
  default_branch: 'main',
  active_branch: 'main',
  current_commit: 'a',
  sync_status: 0,
  last_sync_time: null,
  last_sync_error: null,
  project_count: 0,
  case_count: 0,
  credential: { auth_type: 'token', username: null, configured: true },
  ...patch,
})
const tree = (path = 'tests/test_example.py') =>
  response({
    entries: [
      { type: 'directory', path: 'tests' },
      { type: 'file', path },
    ],
    directory_count: 1,
    file_count: 1,
  })
async function flush() {
  await flushVue()
  await new Promise((resolve) => setImmediate(resolve))
}
function setup(kind = 'page', api = {}) {
  const user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 }),
    route = vue.reactive({ fullPath: '/pytest/repository/index' })
  const calls = [],
    messages = [],
    confirmations = [],
    life = { mount: [], unmount: [], activate: [], deactivate: [] },
    polling = { enabled: false, callback: null }
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
    kind === 'page' ? 'index' : 'PytestRepositoryEditor',
    kind === 'page'
      ? 'repositories,loading,listFailed,editor,busyIds,actionIds,editorBusyIds,editorBusy,selectedRepositoryId,selectedRepository,selectedTreeKey,selectedTreeStats,selectedTreeLoading,selectedTreeFailed,repositoryTree,selectedFileNode,filePreviewContent,filePreviewLoading,filePreviewFailed,branchVisible,branchForm,branchOptions,branchLoading,branchFailed,branchSwitching,repositoryMetrics,loadRepositories,loadRepositoryTree,selectRepository,onTreeNodeSelect,loadFilePreview,retryFilePreview,retryTree,returnToRepositoryList,openEditor,openBranch,closeBranch,loadBranchOptions,confirmSwitchBranch,removeRepository,runAction,refreshAfterWrite'
      : 'visible,saving,draft,open,closeDialog:close,save',
    {
      base,
      props: { busyIds: [] },
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
        '@/store/modules/app-config': { default: () => ({ theme: 'dark' }) },
        'md-editor-v3': { MdPreview: {} },
        'md-editor-v3/lib/preview.css': {},
        '@/hooks/table': { useTableColumn: (values) => values },
        '@/hooks/use-page-polling': {
          usePagePolling: (callback) => {
            polling.callback = callback
            return {
              start() {
                polling.enabled = true
              },
              stop() {
                polling.enabled = false
              },
            }
          },
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
                closed: false,
                close() {
                  this.closed = true
                },
              }
              confirmations.push({ ...options, modal })
              return modal
            },
          },
        },
        '@/api/pytest/repository': {
          getPytestRepositories: () => invoke('list', [], response([repository(), repository(2)])),
          getPytestRepositoryTree: (id) => invoke('tree', [id], tree()),
          getPytestRepositoryFile: (id, path) =>
            invoke('file', [id, path], response({ path, content: 'fixture source' })),
          getPytestRepositoryBranches: (id) =>
            invoke(
              'branches',
              [id],
              response([
                { name: 'main', default: true },
                { name: 'other', default: false },
              ])
            ),
          savePytestRepository: (payload) => invoke('save', [payload], response({})),
          switchPytestRepositoryBranch: (id, branch) =>
            invoke('switch', [id, branch], response({})),
          pullPytestRepository: (id) => invoke('pull', [id], response({})),
          testPytestRepository: (id) => invoke('test', [id], response({})),
          deletePytestRepository: (id) => invoke('delete', [id], response({})),
        },
      },
    }
  )
  return {
    ...h,
    user,
    route,
    calls,
    messages,
    confirmations,
    listeners,
    polling,
    boundary: h.load('records.ts'),
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
const files = (roots) =>
  roots.flatMap((node) => (node.type === 'file' ? [node] : files(node.children)))

test('finite records remove unknown/secret fields and preserve zero/null/false', () => {
  const h = setup(),
    raw = repository(0, {
      credential: { auth_type: 'token', username: null, configured: false, secret: 'discard' },
      extra: 'discard',
    })
  const row = h.boundary.readRepository(raw)
  assert.equal(row.id, 0)
  assert.equal(row.case_count, 0)
  assert.equal(row.api_base_url, null)
  assert.equal(row.credential.configured, false)
  assert.equal('extra' in row, false)
  assert.equal('secret' in row.credential, false)
  raw.credential.auth_type = 'none'
  assert.equal(row.credential.auth_type, 'token')
  for (const value of [
    false,
    { ...repository(), case_count: false },
    { ...repository(), credential: { configured: 'yes' } },
  ])
    assert.throws(() => h.boundary.readRepository(value))
  assert.throws(() => h.boundary.readRepositories(response([repository(), repository()])))
  h.close()
})

test('owned draft and whitelist preserve blank-secret reuse and explicit credential removal', () => {
  const h = setup('editor'),
    draft = h.boundary.repositoryDraft(repository())
  assert.equal(draft.credential_secret, '')
  const payload = h.boundary.repositoryPayload({
    ...draft,
    current_commit: 'discard',
    credential_secret: '',
  })
  assert.equal(payload.id, 0)
  assert.equal(payload.credential_auth_type, 'token')
  assert.equal(payload.credential_secret, '')
  assert.equal('current_commit' in payload, false)
  const cleared = h.boundary.repositoryPayload({
    ...draft,
    credential_auth_type: undefined,
    credential_username: 'ignored',
    credential_secret: 'ignored',
  })
  assert.equal(cleared.credential_auth_type, 'none')
  assert.equal(cleared.credential_username, '')
  assert.equal(cleared.credential_secret, '')
  for (const patch of [{ name: ' ' }, { repo_url: '' }, { default_branch: ' ' }])
    assert.throws(() => h.boundary.repositoryPayload({ ...draft, ...patch }))
  h.close()
})

test('tree parser rejects malformed paths/types/duplicates and file-parent collisions; build preserves ancestry/counts', () => {
  const h = setup(),
    data = h.boundary.readRepositoryTree(tree()),
    original = structuredClone(data)
  const nodes = h.boundary.buildRepositoryTree(repository(), data.entries)
  assert.equal(nodes[0].title, 'tests')
  assert.equal(nodes[0].count, 1)
  assert.deepEqual(files(nodes)[0].children, [])
  assert.equal(files(nodes)[0].repository_id, 0)
  assert.deepEqual(data, original)
  for (const entries of [
    [{ path: '../bad', type: 'file' }],
    [{ path: 'one', type: 'bad' }],
    [
      { path: 'one', type: 'file' },
      { path: 'one/two', type: 'file' },
    ],
    [
      { path: 'one', type: 'file' },
      { path: 'one', type: 'file' },
    ],
  ])
    assert.throws(() =>
      h.boundary.readRepositoryTree(response({ entries, directory_count: 0, file_count: 0 }))
    )
  assert.equal(h.boundary.readRepositoryFile(response({ path: 'empty', content: '' }), 'empty'), '')
  assert.throws(() =>
    h.boundary.readRepositoryFile(response({ path: 'other', content: 'wrong' }), 'empty')
  )
  assert.throws(() => h.boundary.readBranches(response([{ name: 'a' }, { name: 'a' }])))
  h.close()
})

test('editor handles new/edit/reset/reopen and clears secret on auth change and cancel', async () => {
  const h = setup('editor')
  h.open(repository())
  assert.equal(h.draft.id, 0)
  h.draft.credential_secret = 'fixture-secret'
  h.draft.credential_auth_type = 'username_password'
  assert.equal(h.draft.credential_secret, '')
  h.draft.credential_secret = 'fixture-password'
  h.closeDialog()
  assert.equal(h.draft.credential_secret, '')
  h.open(repository(2))
  assert.equal(h.draft.id, 2)
  assert.equal(h.draft.credential_secret, '')
  h.open()
  assert.equal(h.draft.id, null)
  assert.equal(h.draft.default_branch, 'master')
  assert.equal(h.draft.credential_auth_type, 'none')
  assert.equal(await h.save(), false)
  h.close()
})

test('editor captures safe payload once, owns physical lock after cancel and can retry failed saves', async () => {
  const pending = deferred()
  let result = pending.promise
  const h = setup('editor', { save: () => result })
  h.open(repository())
  h.draft.credential_secret = 'fixture-secret'
  const task = h.save()
  assert.equal(h.saving.value, true)
  assert.equal(await h.save(), false)
  h.draft.name = 'Later'
  assert.equal(h.calls[0][1].name, 'Fixture 0')
  pending.resolve({ code: 403 })
  assert.equal(await task, false)
  assert.equal(h.draft.name, 'Later')
  assert.equal(h.visible.value, true)
  const late = deferred()
  result = late.promise
  const second = h.save()
  h.closeDialog()
  h.open(repository(2))
  assert.equal(h.visible.value, false)
  assert.equal(h.saving.value, true)
  late.resolve(response({}))
  assert.equal(await second, false)
  assert.equal(
    h.events.some((event) => event[0] === 'saved'),
    false
  )
  result = Promise.resolve(response({}))
  h.open(repository())
  assert.equal(await h.save(), true)
  assert.deepEqual(h.events.at(-2), ['saved', 0])
  assert.deepEqual(h.events.at(-1), ['busy', 0, false])
  h.close()
})

test('editor honors shared repository physical locks without role hiding', async () => {
  const h = setup('editor')
  h.props.busyIds = [0]
  h.open(repository())
  assert.equal(h.visible.value, false)
  h.props.busyIds = []
  h.open(repository())
  h.props.busyIds = [0]
  assert.equal(await h.save(), false)
  assert.equal(h.calls.length, 0)
  h.close()
})

test('editor invalidates identity/environment/route A-B-A and clears credentials before late writes settle', async () => {
  for (const key of ['userId', 'roleId', 'token', 'selected_environment', 'fullPath']) {
    const pending = deferred(),
      h = setup('editor', { save: () => pending.promise })
    h.open(repository())
    h.draft.credential_secret = 'fixture-secret'
    const task = h.save()
    const target = key === 'fullPath' ? h.route : h.user,
      old = target[key]
    target[key] = typeof old === 'number' ? old + 1 : old + '-b'
    target[key] = old
    assert.equal(h.visible.value, false)
    assert.equal(h.draft.credential_secret, '')
    assert.equal(h.saving.value, true)
    pending.resolve(response({}))
    assert.equal(await task, false)
    assert.equal(
      h.events.some((event) => event[0] === 'saved'),
      false
    )
    h.close()
  }
})

test('list and directory loading are independent, same reads coalesce, cached tree reuses current source', async () => {
  const pending = deferred(),
    h = setup('page', { tree: () => pending.promise })
  const first = h.loadRepositories()
  assert.equal(h.loadRepositories(), first)
  await first
  assert.equal(h.loading.value, false)
  assert.equal(h.selectedRepositoryId.value, 0)
  assert.equal(h.selectedTreeLoading.value, true)
  const treeTask = h.loadRepositoryTree(0)
  assert.equal(h.calls.filter((call) => call[0] === 'tree').length, 1)
  pending.resolve(tree())
  await treeTask
  assert.equal(h.selectedTreeStats.value.file_count, 1)
  await h.loadRepositories()
  assert.equal(h.calls.filter((call) => call[0] === 'tree').length, 1)
  assert.equal(h.repositoryMetrics.value.projects, 0)
  h.close()
})

test('tree force-reload invalidates old success/failure/finalizer and exposes retry', async () => {
  const pending = [deferred(), deferred()]
  let i = 0
  const h = setup('page', { tree: () => pending[i++].promise })
  await h.loadRepositories()
  const latest = h.loadRepositoryTree(0, true)
  pending[0].resolve(tree('tests/old.py'))
  await flush()
  assert.equal(h.selectedTreeLoading.value, true)
  assert.equal(files(h.repositoryTree.value).length, 0)
  pending[1].reject(Error('failure'))
  await latest
  assert.equal(h.selectedTreeFailed.value, true)
  assert.equal(h.selectedTreeLoading.value, false)
  h.close()
})

test('file A-B-A rejects stale contents, wrong response path and late finalizer, with independent retry', async () => {
  const pending = [deferred(), deferred(), deferred()]
  let i = 0
  const h = setup('page', { file: () => pending[i++].promise })
  await h.loadRepositories()
  await flush()
  const file = files(h.repositoryTree.value).find((node) => node.repository_id === 0),
    first = h.loadFilePreview(file)
  h.returnToRepositoryList()
  const second = h.loadFilePreview(file)
  pending[0].resolve(response({ path: file.path, content: 'old' }))
  await first
  assert.equal(h.filePreviewContent.value, '')
  assert.equal(h.filePreviewLoading.value, true)
  pending[1].resolve(response({ path: 'wrong', content: 'bad' }))
  await second
  assert.equal(h.filePreviewFailed.value, true)
  h.retryFilePreview()
  pending[2].resolve(response({ path: file.path, content: '' }))
  await flush()
  assert.equal(h.filePreviewFailed.value, false)
  assert.equal(h.filePreviewContent.value, '')
  h.close()
})

test('tree selection is restricted to current nodes; repository zero is selectable and stale nodes cannot read arbitrary files', async () => {
  const h = setup()
  await h.loadRepositories()
  await flush()
  const file = files(h.repositoryTree.value)[0]
  h.onTreeNodeSelect({ ...file, key: 'invalid' })
  assert.equal(
    h.calls.some((call) => call[0] === 'file'),
    false
  )
  h.onTreeNodeSelect(file)
  await flush()
  assert.equal(h.selectedRepositoryId.value, 0)
  assert.equal(h.filePreviewContent.value, 'fixture source')
  await h.selectRepository(2)
  await flush()
  assert.equal(h.selectedFileNode.value, null)
  assert.equal(h.filePreviewLoading.value, false)
  h.onTreeNodeSelect(h.repositoryTree.value[0])
  await flush()
  assert.equal(h.selectedRepositoryId.value, 0)
  h.close()
})

test('source/branch/commit changes invalidate cached trees and in-flight previews and close stale configuration', async () => {
  let source = 'a'
  const pending = deferred(),
    closed = []
  const h = setup('page', {
    list: () => Promise.resolve(response([repository(0, { current_commit: source })])),
    file: () => pending.promise,
  })
  h.editor.value = {
    open() {},
    close() {
      closed.push(true)
    },
  }
  await h.loadRepositories()
  await flush()
  h.openEditor(repository())
  const old = files(h.repositoryTree.value)[0],
    task = h.loadFilePreview(old)
  source = 'b'
  await h.loadRepositories()
  await flush()
  assert.equal(h.selectedFileNode.value, null)
  assert.equal(h.selectedTreeKey.value, 'repository:0')
  assert.equal(closed.length > 0, true)
  pending.resolve(response({ path: old.path, content: 'stale source' }))
  await task
  assert.equal(h.filePreviewContent.value, '')
  assert.equal(h.calls.filter((call) => call[0] === 'tree').length, 2)
  h.close()
})

test('list errors preserve current rows with explicit retry; malformed values cannot become successful emptiness', async () => {
  let fail = false
  const h = setup('page', { list: () => Promise.resolve(response(fail ? 'bad' : [repository()])) })
  await h.loadRepositories()
  await flush()
  fail = true
  await h.loadRepositories()
  assert.equal(h.listFailed.value, true)
  assert.equal(h.repositories.value.length, 1)
  assert.equal(h.loading.value, false)
  fail = false
  await h.loadRepositories()
  assert.equal(h.listFailed.value, false)
  h.close()
})

test('branch A-B-A options and finalizers are window-scoped; failed options retry without closing window', async () => {
  const pending = [deferred(), deferred(), deferred()]
  let i = 0
  const h = setup('page', { branches: () => pending[i++].promise })
  await h.loadRepositories()
  await flush()
  const first = h.openBranch(repository())
  h.closeBranch()
  const second = h.openBranch(repository(2))
  pending[0].resolve(response([{ name: 'old' }]))
  await first
  assert.equal(h.branchLoading.value, true)
  assert.deepEqual(h.branchOptions.value, [])
  pending[1].reject(Error('failure'))
  await second
  assert.equal(h.branchFailed.value, true)
  assert.equal(await h.confirmSwitchBranch(), false)
  const retry = h.loadBranchOptions()
  pending[2].resolve(response([{ name: 'main' }]))
  await retry
  assert.equal(h.branchFailed.value, false)
  assert.equal(h.branchForm.repositoryId, 2)
  h.close()
})

test('branch switch captures repository/branch and physical lock survives cancellation; invalid branches never submit', async () => {
  const pending = deferred(),
    h = setup('page', { switch: () => pending.promise })
  await h.loadRepositories()
  await flush()
  await h.openBranch(repository())
  h.branchForm.branch = 'invented'
  assert.equal(await h.confirmSwitchBranch(), false)
  h.branchForm.branch = 'other'
  const task = h.confirmSwitchBranch()
  h.branchForm.branch = 'later'
  assert.equal(await h.confirmSwitchBranch(), false)
  assert.deepEqual(
    h.calls.find((call) => call[0] === 'switch'),
    ['switch', 0, 'other']
  )
  h.closeBranch()
  await h.openBranch(repository(2))
  assert.equal(h.branchVisible.value, false)
  assert.equal(h.branchSwitching.value, true)
  pending.resolve(response({}))
  assert.equal(await task, false)
  assert.deepEqual(h.actionIds.value, [])
  assert.equal(
    h.messages.some((message) => message[0] === 'success'),
    false
  )
  h.close()
})

test('successful branch switching refreshes and invalidates tree; failed save keeps draft for retry', async () => {
  let fail = true
  const h = setup('page', { switch: () => Promise.resolve(fail ? { code: 403 } : response({})) })
  await h.loadRepositories()
  await flush()
  await h.openBranch(repository())
  h.branchForm.branch = 'other'
  assert.equal(await h.confirmSwitchBranch(), false)
  assert.equal(h.branchForm.branch, 'other')
  assert.equal(h.branchVisible.value, true)
  fail = false
  assert.equal(await h.confirmSwitchBranch(), true)
  await flush()
  assert.equal(h.branchVisible.value, false)
  assert.equal(h.calls.filter((call) => call[0] === 'list').length, 2)
  assert.equal(h.calls.filter((call) => call[0] === 'tree').length, 2)
  h.close()
})

test('pull/test/delete share per-repository locks with editor; late actions never notify a changed context', async () => {
  const pending = deferred(),
    h = setup('page', { pull: () => pending.promise })
  await h.loadRepositories()
  await flush()
  h.editorBusy(0, true)
  assert.equal(await h.runAction(repository(), 'test'), false)
  h.editorBusy(0, false)
  const task = h.runAction(repository(), 'pull')
  assert.equal(await h.runAction(repository(), 'test'), false)
  h.removeRepository(repository())
  assert.equal(h.confirmations.length, 0)
  h.user.roleId = 2
  assert.deepEqual(h.actionIds.value, [0])
  pending.resolve(response({}))
  assert.equal(await task, false)
  assert.equal(
    h.messages.some((message) => message[0] === 'success'),
    false
  )
  assert.deepEqual(h.actionIds.value, [])
  h.close()
})

test('deletion replacement/cancel/failure never closes wrong window or releases pending physical lock', async () => {
  let result = Promise.resolve({ code: 403 })
  const h = setup('page', { delete: () => result })
  await h.loadRepositories()
  await flush()
  h.removeRepository(repository())
  const first = h.confirmations.at(-1)
  assert.equal(await first.onBeforeOk(), false)
  h.removeRepository(repository())
  assert.equal(first.modal.closed, true)
  assert.equal(await first.onBeforeOk(), false)
  const second = h.confirmations.at(-1),
    pending = deferred()
  result = pending.promise
  const task = second.onBeforeOk()
  second.onCancel()
  assert.deepEqual(h.actionIds.value, [0])
  assert.equal(await second.onBeforeOk(), false)
  pending.resolve(response({}))
  assert.equal(await task, false)
  assert.deepEqual(h.actionIds.value, [])
  h.close()
})

test('successful delete refreshes list and clears removed selection/evidence without deleting local files', async () => {
  let removed = false
  const h = setup('page', {
    list: () => Promise.resolve(response(removed ? [] : [repository()])),
    delete: () => {
      removed = true
      return Promise.resolve(response({}))
    },
  })
  await h.loadRepositories()
  await flush()
  h.onTreeNodeSelect(files(h.repositoryTree.value)[0])
  await flush()
  h.removeRepository(repository())
  assert.equal(await h.confirmations.at(-1).onBeforeOk(), true)
  assert.equal(h.selectedRepositoryId.value, null)
  assert.equal(h.selectedFileNode.value, null)
  assert.equal(h.repositoryTree.value.length, 0)
  h.close()
})

test('known-deleted records stay removed if the follow-up list fails; changed source requires fresh confirmation', async () => {
  let source = 'a',
    failed = false
  const h = setup('page', {
    list: () =>
      failed
        ? Promise.reject(Error('list failure'))
        : Promise.resolve(response([repository(0, { current_commit: source })])),
    delete: () => {
      failed = true
      return Promise.resolve(response({}))
    },
  })
  await h.loadRepositories()
  await flush()
  h.removeRepository(repository())
  const first = h.confirmations.at(-1)
  source = 'b'
  await h.loadRepositories()
  await flush()
  assert.equal(await first.onBeforeOk(), false)
  assert.equal(
    h.calls.some((call) => call[0] === 'delete'),
    false
  )
  h.removeRepository(repository())
  assert.equal(await h.confirmations.at(-1).onBeforeOk(), true)
  assert.deepEqual(h.repositories.value, [])
  assert.equal(h.listFailed.value, true)
  assert.equal(h.selectedRepositoryId.value, null)
  h.close()
})

test('list identity/role/token/environment/route A-B-A invalidates old reads and clears evidence synchronously', async () => {
  for (const key of ['userId', 'roleId', 'token', 'selected_environment', 'fullPath']) {
    const pending = [],
      h = setup('page', {
        list: () => {
          const d = deferred()
          pending.push(d)
          return d.promise
        },
      }),
      first = h.loadRepositories()
    const target = key === 'fullPath' ? h.route : h.user,
      old = target[key]
    target[key] = typeof old === 'number' ? old + 1 : old + '-b'
    target[key] = old
    pending[0].resolve(response([repository(99)]))
    await first
    assert.deepEqual(h.repositories.value, [])
    pending.at(-1).resolve(response([repository(2)]))
    await flush()
    assert.equal(h.selectedRepositoryId.value, 2)
    pending[1].reject(Error('old failure'))
    await flush()
    assert.equal(h.listFailed.value, false)
    h.close()
  }
})

test('page polling only runs for sync status 1, remains silent on retries and stops after terminal status', async () => {
  let status = 1,
    result
  const h = setup('page', {
    list: () => result ?? Promise.resolve(response([repository(0, { sync_status: status })])),
  })
  await h.loadRepositories()
  await flush()
  assert.equal(h.polling.enabled, true)
  const pending = deferred()
  result = pending.promise
  const task = h.polling.callback({ isCurrent: () => true })
  assert.equal(h.loading.value, false)
  pending.reject(Error('failure'))
  await task
  assert.equal(h.polling.enabled, true)
  status = 2
  result = undefined
  await h.polling.callback({ isCurrent: () => true })
  assert.equal(h.polling.enabled, false)
  const count = h.calls.length
  await h.polling.callback({ isCurrent: () => false })
  assert.equal(h.calls.length, count)
  h.close()
})

test('both windows/page close and fence background, KeepAlive and unmount; listeners are removed', async () => {
  for (const kind of ['page', 'editor']) {
    const h = setup(kind)
    h.mount()
    await flush()
    assert.equal(h.listeners.size, 1)
    if (kind === 'editor') {
      h.open(repository())
      h.draft.credential_secret = 'fixture-secret'
    }
    h.hide()
    if (kind === 'editor') {
      assert.equal(h.visible.value, false)
      assert.equal(h.draft.credential_secret, '')
      h.open()
      assert.equal(h.visible.value, false)
    } else {
      const count = h.calls.length
      await h.loadRepositories()
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

test('actual SFC scripts/templates compile and configuration contains static options with compact actions', () => {
  for (const file of ['index.vue', 'components/PytestRepositoryEditor.vue']) {
    const { descriptor } = parse(readFileSync(path.join(base, file), 'utf8')),
      script = compileScript(descriptor, { id: file })
    const template = compileTemplate({
      id: file,
      source: descriptor.template.content,
      filename: file,
      compilerOptions: { bindingMetadata: script.bindings },
    })
    assert.deepEqual(template.errors, [])
  }
  const h = setup(),
    config = h.load('config.ts')
  assert.equal(config.tableColumns.at(-1).width, 120)
  assert.equal(config.providerOptions.length, 3)
  h.close()
})
