import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/config/test-files')
const record = (id = 1, extra = {}) => ({
  id,
  name: `file-${id}.txt`,
  project_product: { id: 10, name: 'Product' },
  allow_download: false,
  ...extra,
})
function setupFile(name, bindings, api = {}, props = {}) {
  const lifecycle = {},
    route = vue.reactive({
      path: '/config/test-files/index',
      query: { id: '10', name: 'Project' },
    }),
    user = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-session' }),
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
    dialogs,
    notices,
    dispose() {
      lifecycle.unmount?.()
      state.close()
    },
  }
}
const page = (api = {}) =>
  setupFile(
    'index',
    'rows,listLoading,loadError,pagination,conditionItems,doRefresh,onSearch,onResetSearch,onNavigationFilterChange,loadUsers,usersLoading,usersError,onDelete,onDownload,onUpdate,onOpenUploadModal,editorRef,uploadRef,navigationCreateRef,deletingIds,downloadingIds,onEditorSaving',
    api
  )
const editor = (api = {}) =>
  setupFile('TestFileEditor', 'draft,open,save,visible,saving,editingId', api)
const upload = (api = {}) =>
  setupFile(
    'TestFileUploadDialog',
    'draft,open,upload,visible,uploading,fileList,selectedFile,changeFile,removeFile',
    api
  )
const nativeFile = () => new File(['fixture'], 'fixture.txt', { type: 'text/plain' })
function selectFile(s) {
  const file = nativeFile()
  s.changeFile([{ uid: '1', name: file.name, file }])
  return file
}

test('page and upload/editor SFCs compile', () => {
  for (const file of [
    'index.vue',
    'components/TestFileEditor.vue',
    'components/TestFileUploadDialog.vue',
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
test('search instances are isolated, comma IDs and updater multiselect keep collection protocol', async () => {
  const calls = [],
    s = page({
      getUserFile: async (p) => {
        calls.push(p)
        return { data: [], totalSize: 0 }
      },
    }),
    other = page()
  try {
    s.conditionItems.find((i) => i.key === 'id').value = '5574、5577'
    s.conditionItems.find((i) => i.key === 'update_user').value = [1, 2]
    s.conditionItems.find((i) => i.key === 'project_product').value = [3, 10]
    s.pagination.page = 4
    await s.onSearch()
    assert.equal(calls[0].id, '5574,5577')
    assert.equal(calls[0].update_user__in, '1,2')
    assert.equal(calls[0].project_product, 10)
    assert.equal(calls[0].page, 1)
    assert.equal(calls[0].pageSize, 20)
    assert.equal(calls[0].type, 0)
    assert.equal(other.conditionItems.find((i) => i.key === 'id').value, '')
    await s.onResetSearch()
    assert.deepEqual(calls.at(-1), { page: 1, pageSize: 20, type: 0 })
    assert.deepEqual(s.conditionItems.find((i) => i.key === 'update_user').value, [])
  } finally {
    s.dispose()
    other.dispose()
  }
})
test('latest list response wins and older finally cannot remove newer loading', async () => {
  const a = deferred(),
    b = deferred()
  let count = 0
  const s = page({ getUserFile: () => (++count === 1 ? a.promise : b.promise) })
  try {
    const first = s.doRefresh(),
      second = s.doRefresh()
    a.resolve({ data: [record(1)], totalSize: 1 })
    await first
    assert.equal(s.listLoading.value, true)
    assert.deepEqual(s.rows.value, [])
    b.resolve({ data: [record(2)], totalSize: 3 })
    await second
    assert.equal(s.rows.value[0].id, 2)
    assert.equal(s.pagination.pageCount, 3)
    assert.equal(s.listLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('list failure has local retry and independent users loading', async () => {
  const userRequest = deferred()
  let count = 0
  const s = page({
    getUserFile: async () => {
      if (++count === 1) throw Error('fixture')
      return { data: [record()], totalSize: 1 }
    },
    getUserName: () => userRequest.promise,
  })
  try {
    const pending = s.loadUsers()
    await s.doRefresh()
    assert.equal(s.listLoading.value, false)
    assert.match(s.loadError.value, /加载失败/)
    assert.equal(s.usersLoading.value, true)
    await s.doRefresh()
    assert.equal(s.loadError.value, '')
    assert.equal(s.rows.value.length, 1)
    userRequest.reject(Error('fixture'))
    await pending
    assert.equal(s.usersLoading.value, false)
    assert.equal(s.usersError.value, true)
  } finally {
    s.dispose()
  }
})
test('deactivation discards list/options replies and activation refreshes both', async () => {
  const a = deferred(),
    b = deferred()
  let lists = 0,
    users = 0
  const s = page({
    getUserFile: () =>
      ++lists === 1 ? a.promise : Promise.resolve({ data: [record(2)], totalSize: 1 }),
    getUserName: () => (++users === 1 ? b.promise : Promise.resolve({ data: [] })),
  })
  try {
    const first = s.doRefresh(),
      options = s.loadUsers()
    s.lifecycle.deactivate()
    a.resolve({ data: [record()], totalSize: 9 })
    b.resolve({ data: [{ key: 1, title: 'Old' }] })
    await Promise.all([first, options])
    assert.deepEqual(s.rows.value, [])
    assert.deepEqual(s.conditionItems.find((i) => i.key === 'update_user').optionItems, [])
    s.lifecycle.activate()
    await flush()
    assert.equal(lists, 2)
    assert.equal(users, 2)
    assert.equal(s.rows.value[0].id, 2)
  } finally {
    s.dispose()
  }
})
test('editor copies only product, sends snapshot leaf ID and blocks duplicates', async () => {
  const pending = deferred(),
    calls = [],
    s = editor({
      putUserFile: (p) => {
        calls.push(p)
        return pending.promise
      },
    })
  try {
    const row = record(7)
    s.open(row)
    s.draft.project_product = [3, 0]
    const saving = s.save()
    assert.equal(s.saving.value, true)
    assert.equal(await s.save(), false)
    s.draft.project_product = 99
    assert.deepEqual(calls, [{ id: 7, project_product: 0 }])
    assert.equal(row.project_product.id, 10)
    pending.resolve({ msg: 'ok' })
    assert.equal(await saving, true)
    assert.equal(s.visible.value, false)
    assert.equal(s.editingId.value, null)
    assert.equal(s.events.filter((e) => e[0] === 'saved').length, 1)
  } finally {
    s.dispose()
  }
})
test('editor validates empty product and retains failed draft for retry', async () => {
  let calls = 0
  const s = editor({
    putUserFile: async () => {
      calls++
      throw Error('fixture')
    },
  })
  try {
    s.open(record())
    s.draft.project_product = null
    assert.equal(await s.save(), false)
    assert.equal(calls, 0)
    assert.equal(s.saving.value, false)
    s.draft.project_product = 12
    assert.equal(await s.save(), false)
    assert.equal(s.visible.value, true)
    assert.equal(s.draft.project_product, 12)
    assert.equal(s.saving.value, false)
    s.exposed.close()
    s.open(record(2))
    assert.equal(s.draft.project_product, 10)
  } finally {
    s.dispose()
  }
})
test('editor stale success after role change cannot close/repopulate or emit saved', async () => {
  const pending = deferred(),
    s = editor({ putUserFile: () => pending.promise })
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
    assert.equal(s.saving.value, false)
    s.open(record(2))
    assert.equal(s.editingId.value, 2)
  } finally {
    s.dispose()
  }
})
test('upload validates file/product, handles removal and captures navigation default without late overwrite', async () => {
  const s = upload()
  try {
    s.open(10)
    assert.equal(s.draft.project_product, 10)
    assert.equal(await s.upload(), false)
    selectFile(s)
    s.draft.project_product = []
    assert.equal(await s.upload(), false)
    assert.equal(s.removeFile(), true)
    assert.equal(s.selectedFile.value, null)
    s.draft.allow_download = false
    s.exposed.close()
    s.open()
    assert.equal(s.draft.project_product, null)
    assert.equal(s.draft.allow_download, true)
  } finally {
    s.dispose()
  }
})
test('upload native FormData preserves original five fields, leaf ID 0 and false flag; prevents duplicates', async () => {
  const pending = deferred(),
    calls = [],
    s = upload({
      postUserFile: (p) => {
        calls.push(p)
        return pending.promise
      },
    })
  try {
    s.open()
    const file = selectFile(s)
    s.draft.project_product = [1, 0]
    s.draft.allow_download = false
    const saving = s.upload()
    assert.equal(await s.upload(), false)
    assert.equal(s.removeFile(), false)
    s.changeFile([])
    assert.equal(s.selectedFile.value, file)
    assert.deepEqual(
      [...calls[0].keys()],
      ['test_file', 'type', 'name', 'project_product', 'allow_download']
    )
    assert.equal(calls[0].get('project_product'), '0')
    assert.equal(calls[0].get('allow_download'), 'false')
    assert.equal(calls[0].get('type'), '0')
    assert.equal(calls[0].get('name'), file.name)
    assert.equal(await calls[0].get('test_file').text(), 'fixture')
    pending.resolve({ msg: 'ok' })
    assert.equal(await saving, true)
    assert.equal(s.visible.value, false)
    assert.equal(s.selectedFile.value, null)
    assert.equal(s.uploading.value, false)
  } finally {
    s.dispose()
  }
})
test('upload failure retains file and draft and can retry', async () => {
  let count = 0
  const s = upload({
    postUserFile: async () => {
      if (++count === 1) throw Error('fixture')
      return { msg: 'ok' }
    },
  })
  try {
    s.open(10)
    const file = selectFile(s)
    assert.equal(await s.upload(), false)
    assert.equal(s.selectedFile.value, file)
    assert.equal(s.draft.project_product, 10)
    assert.equal(s.visible.value, true)
    assert.equal(s.uploading.value, false)
    assert.equal(await s.upload(), true)
    assert.equal(count, 2)
  } finally {
    s.dispose()
  }
})
test('deactivated upload drops native file reference and ignores late success, cannot reopen until settled', async () => {
  const pending = deferred(),
    s = upload({ postUserFile: () => pending.promise })
  try {
    s.open(10)
    selectFile(s)
    const saving = s.upload()
    s.lifecycle.deactivate()
    assert.equal(s.fileList.value.length, 0)
    assert.equal(s.visible.value, false)
    s.lifecycle.activate()
    s.open(11)
    assert.equal(s.visible.value, false)
    pending.resolve({ msg: 'ok' })
    assert.equal(await saving, false)
    assert.equal(
      s.events.some((e) => e[0] === 'saved'),
      false
    )
    s.open(11)
    assert.equal(s.draft.project_product, 11)
  } finally {
    s.dispose()
  }
})
test('upload defaults are synchronous product snapshot; navigation closes both dialogs and resets page', async () => {
  const s = page()
  const defaults = { projectProduct: 10, module: null },
    opens = [],
    closed = []
  try {
    s.navigationCreateRef.value = { getCreateDefaults: () => defaults }
    s.uploadRef.value = { open: (id) => opens.push(id), close: () => closed.push('upload') }
    s.editorRef.value = { open() {}, close: () => closed.push('editor') }
    s.onOpenUploadModal()
    defaults.projectProduct = 11
    assert.deepEqual(opens, [10])
    s.pagination.page = 5
    await s.onNavigationFilterChange({ projectProduct: 11 })
    assert.equal(s.pagination.page, 1)
    assert.deepEqual(closed, ['editor', 'upload'])
  } finally {
    s.dispose()
  }
})
test('delete snapshots ID, locks competing actions, retries failure and decrements last-row page', async () => {
  const pending = deferred(),
    deleted = [],
    downloaded = [],
    s = page({
      deleteUserFile: (id) => {
        deleted.push(id)
        return deleted.length === 1 ? pending.promise : Promise.resolve({ msg: 'ok' })
      },
      getUserFileDownloadUrl: async (id) => {
        downloaded.push(id)
        return { data: 'https://example.com/file' }
      },
    })
  try {
    const row = record(7)
    s.rows.value = [row]
    s.pagination.page = 2
    s.onDelete(row)
    row.id = 8
    const config = s.dialogs[0].config,
      saving = config.onBeforeOk()
    assert.deepEqual(deleted, [7])
    assert.equal(await config.onBeforeOk(), false)
    await s.onDownload(record(7))
    assert.deepEqual(downloaded, [])
    pending.reject(Error('fixture'))
    assert.equal(await saving, false)
    assert.equal(s.deletingIds.size, 0)
    assert.equal(await config.onBeforeOk(), true)
    assert.deepEqual(deleted, [7, 7])
  } finally {
    s.dispose()
  }
  const t = page({ deleteUserFile: async () => ({ msg: 'ok' }) })
  try {
    t.rows.value = [record(7)]
    t.pagination.page = 2
    t.onDelete(record(7))
    assert.equal(await t.dialogs[0].config.onBeforeOk(), true)
    assert.equal(t.pagination.page, 1)
    t.dialogs[0].close()
    t.onDelete(record(8))
    assert.equal(t.dialogs.length, 2)
  } finally {
    t.dispose()
  }
})
test('navigation and role changes invalidate delete confirmation and pending success', async () => {
  let calls = 0
  const pending = deferred(),
    s = page({
      deleteUserFile: () => {
        calls++
        return pending.promise
      },
    })
  try {
    s.onDelete(record())
    await s.onNavigationFilterChange({ projectProduct: 20 })
    assert.equal(s.dialogs[0].closed, true)
    assert.equal(await s.dialogs[0].config.onBeforeOk(), false)
    assert.equal(calls, 0)
    s.onDelete(record())
    const saving = s.dialogs[1].config.onBeforeOk()
    s.user.roleId = 2
    pending.resolve({ msg: 'ok' })
    await saving
    assert.equal(
      s.notices.some((n) => n[0] === 'success'),
      false
    )
    assert.equal(s.deletingIds.size, 0)
  } finally {
    s.dispose()
  }
})
function browserFixture() {
  const originalWindow = globalThis.window,
    originalDocument = globalThis.document,
    effects = []
  globalThis.window = { open: (...args) => effects.push(['open', ...args]) }
  globalThis.document = {
    createElement: () => ({
      click() {
        effects.push(['click', this.href, this.download])
      },
      remove() {
        effects.push(['remove'])
      },
    }),
    body: { appendChild() {} },
  }
  return {
    effects,
    restore() {
      globalThis.window = originalWindow
      globalThis.document = originalDocument
    },
  }
}
test('restricted tag is not frontend authorization; backend URL governs download with local pending guard', async () => {
  const browser = browserFixture(),
    pending = deferred(),
    calls = [],
    s = page({
      getUserFileDownloadUrl: (id) => {
        calls.push(id)
        return pending.promise
      },
    })
  try {
    const row = record(7),
      saving = s.onDownload(row)
    row.name = 'changed.png'
    await s.onDownload(record(7))
    assert.deepEqual(calls, [7])
    assert.equal(s.downloadingIds.has(7), true)
    pending.resolve({ data: 'https://example.com/file' })
    await saving
    assert.deepEqual(browser.effects, [
      ['click', 'https://example.com/file', 'file-7.txt'],
      ['remove'],
    ])
    assert.equal(s.downloadingIds.size, 0)
  } finally {
    s.dispose()
    browser.restore()
  }
})
test('backend download denial restores retry and late URL after navigation starts no browser action', async () => {
  const browser = browserFixture(),
    pending = deferred()
  let count = 0
  const s = page({
    getUserFileDownloadUrl: () => {
      if (++count === 1) return Promise.reject(Error('denied'))
      return pending.promise
    },
  })
  try {
    await s.onDownload(record())
    assert.equal(s.downloadingIds.size, 0)
    const saving = s.onDownload(record())
    await s.onNavigationFilterChange({ projectProduct: 20 })
    pending.resolve({ data: 'https://example.com/file' })
    await saving
    assert.deepEqual(browser.effects, [])
    assert.equal(s.downloadingIds.size, 0)
  } finally {
    s.dispose()
    browser.restore()
  }
})
test('image download preserves existing browser preview behavior', async () => {
  const browser = browserFixture(),
    s = page({ getUserFileDownloadUrl: async () => ({ data: 'https://example.org/file.png' }) })
  try {
    await s.onDownload(record(1, { name: 'image.png' }))
    assert.deepEqual(browser.effects, [['open', 'https://example.org/file.png', '_blank']])
  } finally {
    s.dispose()
    browser.restore()
  }
})
test('size and readonly flag formatting handle null, legacy booleans and invalid sizes', () => {
  const s = page()
  try {
    const { formatFileSize, isAllowDownload } = s.load('file.ts')
    for (const value of [true, 1, 'TRUE', 'yes', 'on'])
      assert.equal(isAllowDownload({ allow_download: value }), true)
    for (const value of [false, null, 0, 'false', undefined])
      assert.equal(isAllowDownload({ allow_download: value }), false)
    assert.equal(formatFileSize(1024), '1.0 KB')
    assert.equal(formatFileSize(12), '12 B')
    for (const value of [null, 0, -1, 'invalid']) assert.equal(formatFileSize(value), '-')
  } finally {
    s.dispose()
  }
})
