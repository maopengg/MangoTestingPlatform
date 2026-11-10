import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

function harness(respond) {
  const exports = {}, requests = []
  const source = readFileSync('src/api/apitest/info.ts', 'utf8')
  const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  new Function('exports', 'require', compiled)(exports, () => ({
    get: async request => {
      const params = request.data()
      requests.push(params)
      return respond(params)
    },
  }))
  return { ...exports, requests }
}

const batch = (start, count) => Array.from({ length: count }, (_, index) => ({ id: start + index, name: '示例接口' }))

test('API options load complete lightweight pages without oversized requests', async () => {
  const api = harness(({ page }) => ({ data: page === 1 ? batch(1, 200) : batch(201, 5), totalSize: 205 }))
  assert.equal((await api.getApiInfoOptions(2)).length, 205)
  assert.deepEqual(api.requests.map(({ page, pageSize, summary, project_product }) => [page, pageSize, summary, project_product]),
    [[1, 200, true, 2], [2, 200, true, 2]])
})

test('empty options and repeated last pages stop, even when total is absent', async () => {
  const empty = harness(() => ({ data: [] }))
  assert.deepEqual(await empty.getApiInfoOptions(2), [])
  assert.equal(empty.requests.length, 1)
  const repeated = harness(() => ({ data: batch(1, 200) }))
  assert.equal((await repeated.getApiInfoOptions(2)).length, 200)
  assert.equal(repeated.requests.length, 2)
})

test('a product switch cancels stale option pagination', async () => {
  let current = true
  const api = harness(() => { current = false; return { data: batch(1, 200), totalSize: 400 } })
  assert.deepEqual(await api.getApiInfoOptions(2, () => current), [])
  assert.equal(api.requests.length, 1)
})

test('summary refresh and editing remain separate, with loading on edit', () => {
  const source = readFileSync('src/views/apitest/info/index.vue', 'utf8')
  assert.match(source, /value\['summary'\] = true/)
  assert.match(source, /editorRef\.value\?\.openEdit\(record\.id\)/)
  assert.match(source, /label: '编辑',\s*loading: editingId/)
  const editor = readFileSync('src/views/apitest/info/components/ApiInfoEditor.vue', 'utf8')
  assert.match(editor, /await getApiInfo\(\{ id \}\)/)
  assert.match(editor, /:loading="detailLoading"/)
  assert.match(editor, /saving\.value\s*\|\|\s*detailLoading\.value\s*\|\|\s*loadFailed\.value/)
})

test('modified Vue pages compile without changing their layout', () => {
  for (const path of ['apitest/info', 'apitest/auth-config', 'uitest/auth-config']) {
    const filename = `src/views/${path}/index.vue`
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: path })
    const template = compileTemplate({ source: descriptor.template.content, filename, id: path,
      compilerOptions: { bindingMetadata: script.bindings } })
    assert.deepEqual(template.errors, [])
  }
})
