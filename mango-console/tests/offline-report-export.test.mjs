import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { ref } from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

const filename = 'src/components/reports/OfflineReportExportDialog.vue'
const source = readFileSync(filename, 'utf8')
const descriptor = parse(source).descriptor
const ast = ts.createSourceFile('export.ts', descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)

function handlers(api = {}) {
  const state = {
    props: { visible: true, sourceKind: 'group', sourceId: 11, selectReport: true },
    options: ref([]), selectedId: ref(), page: ref(0), total: ref(0), optionsLoading: ref(false),
    optionsError: ref(''), downloading: ref(false), downloaded: ref(false), error: ref(''), links: ref(null),
    getOfflineReportOptions: api.options || (async () => ({ items: [], count: 0 })),
    downloadOfflineReport: api.download || (async () => {}),
    generateOfflineReport: api.generate || (async () => ({ preview_url: 'https://reports.example.com/view', download_url: 'https://reports.example.com/download' })),
    isApiBusinessError: error => error?.name === 'ApiBusinessError',
  }
  const functions = ast.statements.filter(node => ts.isFunctionDeclaration(node)
    && ['loadOptions', 'loadMoreOptions', 'retryOptions', 'generate', 'cancelRequest'].includes(node.name.text))
  const code = ts.transpileModule(functions.map(node => node.getText(ast)).join('\n'), {
    compilerOptions: { target: ts.ScriptTarget.ES2022 },
  }).outputText
  return { ...state, ...new Function(...Object.keys(state),
    `let controller, optionsController; ${code}; return {loadOptions, loadMoreOptions, retryOptions, generate, cancelRequest}`)(...Object.values(state)) }
}

test('all three export surfaces compile and task actions explicitly require report export', () => {
  for (const file of [filename, 'src/views/timing/tasks/index.vue', 'src/views/timing/tasks/components/TaskGroupManager.vue']) {
    const content = readFileSync(file, 'utf8')
    const { descriptor } = parse(content)
    const script = compileScript(descriptor, { id: 'offline-export' })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename: file,
      id: 'offline-export', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    if (file !== filename) {
      assert.match(content, /permission: 'report:read', label: '导出离线 HTML'/)
      assert.match(content, /<OfflineReportExportDialog[^>]+select-report/)
    }
  }
})

test('late option responses cannot restore a previous task selection', async () => {
  const pending = []
  const state = handlers({ options: (...args) => new Promise(resolve => pending.push({ args, resolve })) })
  const first = state.loadOptions()
  state.props.sourceId = 12
  const second = state.loadOptions()
  assert.equal(pending[0].args[3].aborted, true)
  assert.equal(pending[1].args[1], 12)
  assert.equal(pending[1].args[2], 1)
  pending[1].resolve({ items: [{ id: 22 }], count: 21 })
  await second
  pending[0].resolve({ items: [{ id: 1 }], count: 21 })
  await first
  assert.equal(state.options.value[0].id, 22)
  assert.equal(state.optionsLoading.value, false)
  assert.equal(state.selectedId.value, undefined)
})

test('scroll loading appends older reports, preserves selection and stops at the last page', async () => {
  const pending = []
  const calls = []
  const state = handlers({ options: (...args) => {
    calls.push(args)
    return new Promise(resolve => pending.push(resolve))
  } })
  const first = state.loadOptions()
  pending.shift()({ items: Array.from({ length: 20 }, (_, i) => ({ id: 45 - i })), count: 45 })
  await first
  state.selectedId.value = 45
  const second = state.loadOptions(true)
  await state.loadOptions(true)
  assert.equal(calls.length, 2)
  assert.equal(state.options.value.length, 20)
  assert.equal(state.selectedId.value, 45)
  pending.shift()({ items: Array.from({ length: 20 }, (_, i) => ({ id: 25 - i })), count: 45 })
  await second
  const third = state.loadOptions(true)
  pending.shift()({ items: Array.from({ length: 5 }, (_, i) => ({ id: 5 - i })), count: 45 })
  await third
  await state.loadOptions(true)
  assert.deepEqual(calls.map(call => call[2]), [1, 2, 3])
  assert.equal(state.options.value.length, 45)
  assert.equal(state.options.value[0].id, 45)
  assert.equal(state.selectedId.value, 45)
  assert.doesNotMatch(source, /<a-pagination/)
  assert.match(source, /@dropdown-reach-bottom="loadMoreOptions"/)
})

test('failed next page keeps loaded reports and retries the same page without duplicates', async () => {
  let failed = true
  const pages = []
  const state = handlers({ options: async (kind, id, page) => {
    pages.push(page)
    if (page === 1) return { items: [{ id: 2 }], count: 21 }
    if (failed) throw new Error('next page failed')
    return { items: [{ id: 2 }, { id: 1 }], count: 21 }
  } })
  await state.loadOptions()
  state.selectedId.value = 2
  await state.loadOptions(true)
  assert.equal(state.page.value, 1)
  assert.equal(state.options.value.length, 1)
  assert.equal(state.selectedId.value, 2)
  failed = false
  await state.loadOptions(true)
  assert.deepEqual(pages, [1, 2, 2])
  assert.deepEqual(state.options.value.map(item => item.id), [2, 1])
  assert.equal(state.optionsError.value, '')
})

test('each generation uploads again using selected execution id and exposes both URLs', async () => {
  const calls = []
  const state = handlers({ generate: async (...args) => { calls.push(args); return { preview_url: 'https://reports.example.com/view', download_url: 'https://reports.example.com/download' } } })
  await state.generate()
  assert.equal(calls.length, 0)
  state.selectedId.value = 32
  await state.generate()
  await state.generate()
  assert.deepEqual(calls.map(call => call.slice(0, 2)), [['group', 32], ['group', 32]])
  assert.equal(state.links.value.preview_url, 'https://reports.example.com/view')
  assert.equal(state.downloaded.value, false)
  state.props.selectReport = false
  state.props.sourceKind = 'suite'
  state.props.sourceId = 44
  await state.generate()
  assert.deepEqual(calls[2].slice(0, 2), ['suite', 44])
})

test('only explicit local-storage errors fall back to direct download', async () => {
  let count = 0
  const failure = { name: 'ApiBusinessError', code: 40047 }
  const state = handlers({ generate: async () => { throw failure }, download: async () => { count++ } })
  state.selectedId.value = 32
  await state.generate()
  assert.equal(count, 1)
  assert.equal(state.links.value, null)
  assert.equal(state.downloaded.value, true)
  failure.code = 40042
  await state.generate()
  assert.equal(count, 1)
  assert.ok(state.error.value)
  assert.equal(state.downloaded.value, false)
})

test('closing ignores a late upload response and a new failure clears old links', async () => {
  let resolve
  const state = handlers({ generate: () => new Promise(done => { resolve = done }) })
  state.selectedId.value = 32
  state.links.value = { preview_url: 'https://reports.example.com/old' }
  const pending = state.generate()
  assert.equal(state.links.value, null)
  state.cancelRequest()
  resolve({ preview_url: 'https://reports.example.com/late' })
  await pending
  assert.equal(state.links.value, null)
  assert.equal(state.downloading.value, false)
})

test('failed history load can be retried and closing cancels both requests', async () => {
  let fail = true
  let signal
  const state = handlers({ options: async (...args) => {
    signal = args[3]
    if (fail) throw new Error('load failed')
    return { items: [{ id: 2 }], count: 1 }
  } })
  await state.loadOptions()
  assert.equal(state.optionsError.value, 'load failed')
  assert.equal(state.optionsLoading.value, false)
  fail = false
  await state.loadOptions()
  assert.equal(state.optionsError.value, '')
  assert.equal(state.options.value[0].id, 2)
  const pendingState = handlers({ options: (...args) => {
    signal = args[3]
    return new Promise(resolve => signal.addEventListener('abort', () => resolve({ items: [], count: 0 })))
  } })
  const pending = pendingState.loadOptions()
  pendingState.cancelRequest()
  await pending
  assert.equal(signal.aborted, true)
  assert.equal(pendingState.optionsLoading.value, false)
})

function publishApi(post) {
  const content = readFileSync('src/api/system/offline_report.ts', 'utf8')
  const file = ts.createSourceFile('api.ts', content, ts.ScriptTarget.Latest, true)
  const method = file.statements.find(node => ts.isFunctionDeclaration(node) && node.name.text === 'generateOfflineReport')
  const code = ts.transpileModule(method.getText(file).replace(/^export /, ''), {
    compilerOptions: { target: ts.ScriptTarget.ES2022 },
  }).outputText
  class ApiBusinessError extends Error { constructor(message, code) { super(message); this.code = code } }
  return new Function('request', 'ApiBusinessError', `${code};return generateOfflineReport`)({ post }, ApiBusinessError)
}

test('publish API posts execution identity and returns links rather than a blob', async () => {
  let captured
  const result = { preview_url: 'https://reports.example.com/preview', download_url: 'https://reports.example.com/download', expires_at: '2026-11-04T00:00:00Z' }
  const api = publishApi(async (...args) => { captured = args; return { data: { code: 200, data: result } } })
  const signal = new AbortController().signal
  assert.equal(await api('group', 32, signal), result)
  assert.deepEqual(captured, ['/system/test/suite/offline/links', { source_kind: 'group', source_id: 32 }, { signal }])
})

test('publish API preserves business error codes and rejects unsafe returned URLs', async () => {
  const local = publishApi(async () => ({ data: { code: 40047, msg: '本地存储' } }))
  await assert.rejects(local('suite', 1), error => error.code === 40047)
  for (const preview_url of ['javascript:alert(1)', 'https://user:password@reports.example.com', '', 'not a url']) {
    const api = publishApi(async () => ({ data: { code: 200, data: { preview_url, download_url: 'https://reports.example.com/download', expires_at: '2026-11-04T00:00:00Z' } } }))
    await assert.rejects(api('suite', 1), /报告访问地址或有效期无效/)
  }
})
