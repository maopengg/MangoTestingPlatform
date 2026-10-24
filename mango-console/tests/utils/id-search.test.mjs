import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import { runInNewContext } from 'node:vm'
import test from 'node:test'
import ts from 'typescript'

const require = createRequire(import.meta.url)
const source = readFileSync('src/utils/id-search.ts', 'utf8')
const exports = {}
const warnings = []
runInNewContext(ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
}).outputText, {
  exports,
  require(name) {
    if (name === '@arco-design/web-vue') return { Message: { warning: value => warnings.push(value) } }
    return require(name)
  },
})

test('ID input accepts comma separated values and intermediate trailing comma', () => {
  const input = exports.createIdSearchValue()
  for (const value of ['2054', '2054,', '2054,2', '2054,2014']) {
    input.value = value
    assert.equal(input.value, value)
  }
  input.value = '２０５４， ２０１４'
  assert.equal(input.value, '2054,2014')
  for (const value of ['0', '-1', '1.5', '2054,,2014', '2054,abc', '20 54']) {
    input.value = value
    assert.equal(input.value, '2054,2014')
  }
  input.value = ''
  assert.equal(input.value, '')
})

test('multiple IDs become an IN query without numeric precision loss or source mutation', () => {
  const original = { id: '9007199254740993123,2014,2014,', page: 2, pageSize: 20 }
  const result = exports.normalizeIdSearchParams(original)
  assert.equal(result.id, undefined)
  assert.equal(result.id__in, '9007199254740993123,2014')
  assert.equal(result.page, 2)
  assert.equal(original.id, '9007199254740993123,2014,2014,')
  for (const params of [{ id: '2054' }, { id: 2054 }, { id: '' }, { id: '1,abc' },
    { name: '2054,2014' }, { id: '2054,2014', id__in: '2054' }]) {
    assert.equal(exports.normalizeIdSearchParams(params), params)
  }
})

test('ideographic commas normalize user-provided ID lists for input and IN queries', () => {
  const pasted = '5574、5577、5578、5579、5580、5585、5601、5746、5748、5749'
  const expected = '5574,5577,5578,5579,5580,5585,5601,5746,5748,5749'
  const input = exports.createIdSearchValue()
  input.value = pasted
  assert.equal(input.value, expected)
  assert.equal(exports.normalizeIdSearchParams({ id: pasted }).id__in, expected)
  input.value = '２０５４ 、 ２０１４，2054,5749、'
  assert.equal(input.value, '2054,2014,2054,5749,')
  assert.equal(exports.normalizeIdSearchParams({ id: input.value }).id__in, '2054,2014,5749')
  for (const invalid of ['2054、、2014', '2054、abc', '2054、0', '2054、-1']) {
    assert.equal(exports.normalizeIdSearchValue(invalid), null)
  }
})

test('special single-ID inputs keep their scalar validation', () => {
  const input = exports.createIdSearchValue('2054', false)
  input.value = '2054,2014'
  assert.equal(input.value, '2054')
  input.value = '2054、2014'
  assert.equal(input.value, '2054')
  assert.ok(warnings.length > 0)
})

test('GET interceptor converts queries but leaves writes unchanged', () => {
  const source = readFileSync('src/api/axios.config.ts', 'utf8')
  const start = source.indexOf('  (config) => {', source.indexOf('service.interceptors.request.use('))
  const end = source.indexOf('\n  },', start)
  const body = source.slice(start + '  (config) => {'.length, end)
  const interceptor = new Function('config', 'normalizeIdSearchParams', 'URLSearchParams',
    'CONTENT_TYPE', 'APPLICATION_JSON', 'FORM_URLENCODED', 'qs', 'CustomRequestInterceptor', body)
  function run(config) {
    return interceptor(config, exports.normalizeIdSearchParams, URLSearchParams,
      'Content-Type', 'application/json', 'form', {}, value => value)
  }
  assert.equal(run({ method: 'get', params: { id: '2054,2014' } }).params.id__in, '2054,2014')
  assert.equal(run({ method: 'get', params: { id: '2054、2014' } }).params.id__in, '2054,2014')
  for (const method of ['post', 'put', 'delete']) {
    assert.equal(run({ method, params: { id: '2054,2014' } }).params.id, '2054,2014')
  }
})
