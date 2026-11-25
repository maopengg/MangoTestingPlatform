import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { createServer } from 'node:http'
import { once } from 'node:events'
import { gzipSync } from 'node:zlib'
import * as vue from 'vue'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/system/execution-result')
const detail = (id, value = { steps: [] }, patch = {}) => ({ code: 200,
  data: { id, result_data: value, result_cleaned: false, has_result_data: true, result_too_large: false, ...patch } })

function setup(read = async id => detail(id)) {
  const hooks = [], calls = [], messages = []
  const h = harness('ExecutionResultJsonDrawer', 'open,drawerClose:close,visible,selectedId,result,loading,failed,loadResult', {
    base, props: { contextKey: 'fixture-account-a' },
    modules: {
      vue: { ...vue, onBeforeUnmount: fn => hooks.push(fn), onDeactivated: fn => hooks.push(fn) },
      '@/api/system/execution_result': { getExecutionResultDetailResolved: id => { calls.push(id); return read(id) } },
      '@/utils/load-error': { reportLoadError: (...args) => messages.push(args) },
      '@/hooks/table': { useTable: () => ({ indexColumn: { key: 'index' } }), useTableColumn: v => v },
    },
  })
  return { ...h, calls, messages, hooks, destroy() { hooks.forEach(fn => fn()); h.close() } }
}

test('opening queries the exact record and preserves JSON arrays, empty objects, false and zero', async () => {
  let value = { steps: [{ passed: false, count: 0 }] }
  const h = setup(async id => detail(id, value))
  try {
    for (value of [{ steps: [] }, [], {}, false, 0, '']) {
      await h.open('9007199254740993')
      assert.equal(h.selectedId.value, '9007199254740993')
      assert.deepEqual(h.result.value, { state: 'available', value })
      assert.equal(h.loading.value, false)
    }
    assert.equal(h.calls.length, 6)
  } finally { h.destroy() }
})

test('duplicate clicks coalesce and switching record rejects old results', async () => {
  const a = deferred(), b = deferred()
  const h = setup(id => id === 1 ? a.promise : b.promise)
  try {
    const first = h.open(1)
    await h.open(1)
    assert.deepEqual(h.calls, [1])
    const second = h.open(2)
    b.resolve(detail(2, { current: true }))
    await second
    a.resolve(detail(1, { old: true }))
    await first
    assert.deepEqual(h.result.value.value, { current: true })
    assert.equal(h.loading.value, false)
  } finally { h.destroy() }
})

test('close, context change and deactivation discard pending content without reopening the drawer', async () => {
  const requests = []
  const h = setup(() => { const pending = deferred(); requests.push(pending); return pending.promise })
  try {
    for (const stop of [() => h.drawerClose(), () => { h.props.contextKey += '-new' }, () => h.hooks[1]()]) {
      const read = h.open(1)
      stop()
      requests.at(-1).resolve(detail(1))
      await read
      assert.equal(h.visible.value, false)
      assert.equal(h.result.value, null)
      assert.equal(h.loading.value, false)
    }
  } finally { h.destroy() }
})

test('cleaned and unsaved records show explicit empty states; unavailable files and wrong records are retryable', async () => {
  let response = detail(1, null, { result_cleaned: true })
  const h = setup(async () => response)
  try {
    await h.open(1)
    assert.deepEqual(h.result.value, { state: 'cleaned' })
    response = detail(1, null, { has_result_data: false })
    await h.open(1)
    assert.deepEqual(h.result.value, { state: 'empty' })
    for (response of [detail(1, null), detail(2), { code: 200, data: null }, { code: 403, data: null }]) {
      await h.open(1)
      assert.equal(h.failed.value, true)
      assert.equal(h.result.value, null)
      assert.equal(h.loading.value, false)
    }
    response = detail(1, { recovered: true })
    await h.loadResult()
    assert.equal(h.failed.value, false)
    assert.deepEqual(h.result.value.value, { recovered: true })
  } finally { h.destroy() }
})

test('storage read rejection shows feedback and can be retried', async () => {
  let fail = true
  const h = setup(async id => { if (fail) throw Error('offline'); return detail(id) })
  try {
    await h.open(1)
    assert.equal(h.failed.value, true)
    assert.equal(h.messages.length, 1)
    fail = false
    await h.loadResult()
    assert.equal(h.failed.value, false)
    assert.equal(h.loading.value, false)
  } finally { h.destroy() }
})

function loadApi(dependencies) {
  const exports = {}
  const code = ts.transpileModule(readFileSync('src/api/system/execution_result.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  new Function('exports', 'require', code)(exports, name => dependencies[name])
  return exports
}

test('large results use authenticated same-origin content, never the storage URL or business error envelope', async () => {
  const calls = []
  let headers = { 'content-disposition': 'inline; filename="result.json"' }
  const api = loadApi({
    '@/api/http': { get: async () => detail(1, null, { result_too_large: true, download_url: 'https://example.com/private' }) },
    '@/api/axios.config': { default: { get: async (url, options) => {
      calls.push({ url, options })
      return { headers, data: headers['content-disposition'] ? [{ status: 1 }] : { code: 403, msg: 'denied' } }
    } } },
  })
  const response = await api.getExecutionResultDetailResolved(1)
  assert.deepEqual(response.data.result_data, [{ status: 1 }])
  assert.equal(calls[0].url, 'system/execution/result/content')
  assert.deepEqual(calls[0].options.params, { id: 1 })
  headers = {}
  await assert.rejects(api.getExecutionResultDetailResolved(1), /完整结果文件读取失败/)
})

test('HTTP gzip is transparently decoded before the unchanged JSON result resolver', async t => {
  const payload = [{status:1,response:{json:{message:'中文',items:Array(1000).fill('example')}}}]
  const raw = Buffer.from(JSON.stringify(payload))
  const compressed = gzipSync(raw)
  const server = createServer((req, res) => {
    const legacy = req.url.includes('id=2')
    res.setHeader('Content-Type', 'application/json')
    res.setHeader('Content-Disposition', 'inline; filename="result.json"')
    if (!legacy) res.setHeader('Content-Encoding', 'gzip')
    res.end(legacy ? raw : compressed)
  })
  server.listen(0, '127.0.0.1'); await once(server, 'listening')
  t.after(() => { server.closeAllConnections(); server.close() })
  const api = loadApi({
    '@/api/http': {get: async () => detail(1, null, {result_too_large:true,result_compression:'gzip'})},
    '@/api/axios.config': {default: {get: async (_url, options) => {
      assert.equal(options.responseType, 'json')
      const response = await fetch(`http://127.0.0.1:${server.address().port}/content?id=${options.params.id}`)
      return {headers:Object.fromEntries(response.headers),data:await response.json()}
    }}},
  })
  assert.deepEqual((await api.getExecutionResultDetailResolved(1)).data.result_data, payload)
  assert.ok(compressed.length < raw.length / 10)
})

test('result drawer template compiles and operations use a compact fixed column', () => {
  const file = path.join(base, 'components/ExecutionResultJsonDrawer.vue')
  const { descriptor } = parse(readFileSync(file, 'utf8'), { filename: file })
  const script = compileScript(descriptor, { id: file })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename: file, id: file,
    compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
  const h = setup()
  try {
    const actions = h.load('config.ts').tableColumns.at(-1)
    assert.equal(actions.key, 'actions')
    assert.equal(actions.fixed, 'right')
    assert.equal(actions.width, 120)
  } finally { h.destroy() }
})
