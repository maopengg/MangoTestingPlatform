import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import * as vue from 'vue'

const helper = readFileSync(
  new URL('../src/components/forms/site-search.ts', import.meta.url),
  'utf8'
)
const exports = {}
new Function(
  'exports',
  ts.transpileModule(helper, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
)(exports)
const { searchSources, buildSearchQueries, collectSearchMenus, toSearchRow } = exports
const source = readFileSync(
  new URL('../src/components/forms/SearchContent.vue', import.meta.url),
  'utf8'
)

test('business search maps names to the actual endpoint fields and bounds each query', () => {
  for (const item of searchSources) {
    assert.deepEqual(buildSearchQueries(item, ' 登录 ', 2), [
      { page: 2, pageSize: 8, [item.nameField]: '登录' },
    ])
    assert.ok(item.detail.endsWith('/details'))
  }
  assert.equal(searchSources.find((item) => item.key === 'report').nameField, 'execution_name')
})

test('IDs stay strings, preserving snowflake precision; interface paths query URL', () => {
  const api = searchSources.find((item) => item.key === 'api-info')
  assert.deepEqual(buildSearchQueries(api, '9007199254740993'), [
    { page: 1, pageSize: 8, id: '9007199254740993' },
  ])
  assert.deepEqual(buildSearchQueries(api, '/v1/example'), [
    { page: 1, pageSize: 8, url: '/v1/example' },
  ])
})

test('menu indexing resolves relative routes and excludes hidden branches', () => {
  const routes = [
    {
      path: '/apitest',
      meta: { title: 'API 自动化' },
      children: [
        { path: 'case/index', meta: { title: '测试用例' } },
        {
          path: '/hidden',
          meta: { title: '隐藏', hidden: true },
          children: [{ path: 'child', meta: { title: '隐藏子页' } }],
        },
      ],
    },
  ]
  assert.deepEqual(collectSearchMenus(routes), [
    { title: '测试用例', path: '/apitest/case/index', context: 'API 自动化 / 测试用例' },
  ])
  assert.deepEqual(collectSearchMenus([]), [])
})

test('result context uses canonical module full_path and handles empty relationships', () => {
  assert.deepEqual(
    toSearchRow({
      id: '9007199254740993',
      name: '接口',
      project_product: { name: '产品' },
      module: { name: '三级', full_path: '一级 / 二级 / 三级' },
      url: '/v1/example',
    }),
    { id: '9007199254740993', title: '接口', context: '产品 / 一级 / 二级 / 三级 / /v1/example' }
  )
  assert.equal(toSearchRow({ id: 4, execution_name: '回归任务' }).title, '回归任务')
  assert.equal(toSearchRow(null), null)
  assert.equal(toSearchRow({ name: 'invalid' }), null)
})

test('search modal compiles; no unrelated project or enum prefetch', () => {
  const filename = 'SearchContent.vue'
  const { descriptor } = parse(source, { filename })
  const script = compileScript(descriptor, { id: 'site-search' })
  assert.deepEqual(
    compileTemplate({
      source: descriptor.template.content,
      filename,
      id: 'site-search',
      compilerOptions: { bindingMetadata: script.bindings },
    }).errors,
    []
  )
  assert.doesNotMatch(source, /getEnum|getProject|tree-select/)
})

function harness() {
  const descriptor = parse(source, { filename: 'SearchContent.vue' }).descriptor
  const script = compileScript(descriptor, { id: 'site-search' }).content
  const output = ts.transpileModule(script, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 },
  }).outputText
  const store = vue.reactive({
    getPermissionSideBar: [{ path: '/apitest/case/index', meta: { title: 'API 用例' } }],
  })
  const requests = []
  const errors = []
  const user = vue.reactive({ userId: 1, roleId: 1, selected_environment: 1 })
  let scheduled
  const modules = {
    vue: { ...vue, onBeforeUnmount() {} },
    'vue-router': { useRouter: () => ({ push: async () => undefined }) },
    '@/store/modules/permission': { default: () => store },
    '@/store/modules/user': { default: () => user },
    '@/api/http': {
      get: (options) =>
        new Promise((resolve, reject) => requests.push({ options, resolve, reject })),
    },
    '@/utils/load-error': { reportLoadError: (...args) => errors.push(args) },
    './site-search': exports,
  }
  const compiled = {}
  new Function('require', 'exports', 'setTimeout', 'clearTimeout', output)(
    (key) => modules[key],
    compiled,
    (callback, delay) => {
      scheduled = { callback, delay }
      return 1
    },
    () => {
      scheduled = undefined
    }
  )
  const state = compiled.default.setup({}, { expose() {} })
  return { state, requests, errors, store, user, schedule: () => scheduled }
}

test('debounces input and only queries sources from the current sidebar', async () => {
  const h = harness()
  h.state.show()
  h.state.keyword.value = '登录'
  await vue.nextTick()
  assert.equal(h.schedule().delay, 500)
  assert.equal(h.requests.length, 0)
  const searching = h.state.searchNow()
  assert.equal(h.requests.length, 1)
  assert.equal(h.requests[0].options.url, '/api/case')
  assert.equal(h.state.loading.value, true)
  h.requests[0].resolve({ code: 200, data: [{ id: 7, name: '登录' }], totalSize: 1 })
  await searching
  assert.equal(h.state.loading.value, false)
  assert.equal(h.state.groups.value[0].rows[0].id, '7')
  h.state.close()
})

test('late responses cannot repopulate results after a keyword change or permission change', async () => {
  const h = harness()
  h.state.show()
  h.state.keyword.value = '旧关键词'
  await vue.nextTick()
  const old = h.state.searchNow()
  h.state.keyword.value = '新关键词'
  await vue.nextTick()
  const latest = h.state.searchNow()
  h.requests[0].resolve({ code: 200, data: [{ id: 1, name: '旧内容' }], totalSize: 1 })
  await old
  assert.equal(h.state.groups.value.length, 0)
  h.requests[1].resolve({ code: 200, data: [{ id: 2, name: '新内容' }], totalSize: 1 })
  await latest
  assert.equal(h.state.groups.value[0].rows[0].id, '2')
  h.store.getPermissionSideBar = []
  await vue.nextTick()
  assert.equal(h.state.groups.value.length, 0)
  assert.equal(h.state.availableSources.value.length, 0)
  h.state.close()
})

test('search failures use shared feedback and release loading; closing discards pending results', async () => {
  const h = harness()
  h.state.show()
  h.state.keyword.value = '搜索'
  await vue.nextTick()
  const failed = h.state.searchNow()
  h.requests[0].reject(new Error('test failure'))
  await failed
  assert.equal(h.errors.length, 1)
  assert.equal(h.state.searchFailed.value, true)
  assert.equal(h.state.loading.value, false)
  const pending = h.state.searchNow()
  h.state.close()
  h.requests[1].resolve({ code: 200, data: [{ id: 9, name: '内容' }], totalSize: 1 })
  await pending
  assert.equal(h.state.groups.value.length, 0)
  assert.equal(h.state.loading.value, false)
})

test('identity and environment changes close the search and discard pending requests immediately', async () => {
  const h = harness()
  h.state.show()
  h.state.keyword.value = '搜索'
  await vue.nextTick()
  const pending = h.state.searchNow()
  h.user.roleId = 2
  assert.equal(h.state.visible.value, false)
  assert.equal(h.state.keyword.value, '')
  h.requests[0].resolve({ code: 200, data: [{ id: 9, name: '内容' }], totalSize: 1 })
  await pending
  assert.equal(h.state.groups.value.length, 0)
})
