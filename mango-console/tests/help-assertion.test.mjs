import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { createRequire } from 'node:module'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/help/assertion'),
  require = createRequire(import.meta.url),
  lossless = {}
new Function(
  'exports',
  'require',
  ts.transpileModule(readFileSync('src/utils/lossless-json.ts', 'utf8'), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText
)(lossless, require)
const method = (value = 'equal', extra = {}) => ({
  label: 'Example assertion',
  value,
  scope: 'public',
  testable: true,
  parameter: [
    { f: 'actual', n: 'Actual', d: true, v: 0, value_type: 'number' },
    { f: 'expect', d: true, v: false, value_type: 'boolean' },
  ],
  ...extra,
})
const tree = () => [
  {
    label: 'Basic',
    value: 'basic',
    scope: 'public',
    testable: true,
    children: [
      {
        label: 'Compare',
        value: 'compare',
        children: [
          method(),
          method('runtime', {
            scope: 'web',
            testable: false,
            test_disabled_reason: 'Requires a page',
          }),
        ],
      },
    ],
  },
]
const groups = () => [
  {
    id: 'g',
    name: 'Example group',
    logic: 'AND',
    assertions: [{ id: 'a', method: 'equal', values: { actual: 0, expect: false } }],
  },
]
const result = (request, status = true) => ({
  code: 200,
  data: {
    status,
    message: status ? 'Passed' : 'Failed',
    groups: request.assertions.map((group, index) => ({
      name: group.name || `断言组${index + 1}`,
      logic: group.logic,
      status,
      items: group.items.map((item) => ({
        method: item.method,
        label: 'Example assertion',
        status,
        message: status ? 'Passed' : 'Failed',
        actual: item.actual,
        expect: item.expect,
      })),
    })),
  },
})
function fixture(api = {}, vueOverrides = {}) {
  const hooks = { mounted: [], activate: [], deactivate: [], unmount: [] },
    messages = [],
    calls = [],
    editorCalls = []
  const user = vue.reactive({
      userId: 1,
      roleId: 2,
      token: 'example-session',
      selected_environment: 0,
    }),
    route = vue.reactive({ fullPath: '/help/assertion/index' })
  const f = harness(
    'index',
    'assertionList,assertionGroups,assertionEditorRef,activeGroupValue,classGroups,menuSections,currentClassGroup,flatMethods,testing,testResult,testError,testAvailability,catalogLoading,catalogError,editorBlocked,editorEpoch,loadCatalog,testAssertion,fillExamples,clearValues,selectMethodForTest,tryPanel',
    {
      base,
      api: {
        getSystemAssertionList: async () => ({ code: 200, data: tree() }),
        postSystemAssertionTest: async (p) => {
          calls.push(p)
          return result(p)
        },
        ...api,
      },
      modules: {
        vue: {
          ...vue,
          onMounted: (fn) => hooks.mounted.push(fn),
          onActivated: (fn) => hooks.activate.push(fn),
          onDeactivated: (fn) => hooks.deactivate.push(fn),
          onBeforeUnmount: (fn) => hooks.unmount.push(fn),
          ...vueOverrides,
        },
        '@/store/modules/user': { default: () => user },
        'vue-router': { useRoute: () => route },
        '@/utils/lossless-json': lossless,
        '@arco-design/web-vue': {
          Message: Object.fromEntries(
            ['warning', 'success', 'error'].map((k) => [
              k,
              (message) => messages.push([k, message]),
            ])
          ),
        },
      },
    }
  )
  f.assertionEditorRef.value = {
    fillExamples: () => editorCalls.push('fill'),
    clearValues: () => editorCalls.push('clear'),
    setSingleMethod: (value) => editorCalls.push(value),
  }
  return {
    ...f,
    hooks,
    user,
    route,
    messages,
    calls,
    editorCalls,
    cleanup() {
      hooks.unmount.forEach((fn) => fn())
      f.close()
    },
  }
}
test('catalog loads with initial fill and preserves zero/false method metadata', async () => {
  const e = fixture()
  assert.equal(e.catalogLoading.value, true)
  await e.loadCatalog()
  assert.equal(e.catalogLoading.value, false)
  assert.equal(e.classGroups.value.length, 1)
  assert.equal(e.currentClassGroup.value.menuKey, 'basic:compare')
  assert.equal(e.assertionGroups.value[0].assertions[0].method, 'equal')
  assert.deepEqual(e.editorCalls, ['fill'])
  assert.equal(e.assertionList.value[0].children[0].children[0].parameter[0].v, 0)
  e.cleanup()
})
test('catalog sorting preserves stable categories and puts function assertions last', () => {
  const e = fixture(),
    source = tree(),
    h = e.load('records.ts')
  source.unshift({ ...source[0], value: '函数断言', label: 'Functions' })
  const parsed = h.catalog({ code: 200, data: source })
  assert.deepEqual(
    parsed.map((row) => row.value),
    ['basic', '函数断言']
  )
  assert.equal(source[0].value, '函数断言')
  e.cleanup()
})
for (const data of [
  null,
  {},
  [{ label: 'bad', value: 'bad', children: {} }],
  [
    {
      label: 'bad',
      value: 'bad',
      children: [{ label: 'bad', value: 'bad', children: [{ ...method(), parameter: {} }] }],
    },
  ],
])
  test('invalid catalog retains a retryable failure ' + JSON.stringify(data), async () => {
    const e = fixture({ getSystemAssertionList: async () => ({ code: 200, data }) })
    assert.equal(await e.loadCatalog(), false)
    assert.ok(e.catalogError.value)
    assert.equal(e.catalogLoading.value, false)
    e.cleanup()
  })
test('catalog failure can retry and first fill runs only for initial empty draft', async () => {
  let fail = true
  const e = fixture({
    getSystemAssertionList: async () => {
      if (fail) throw Error('offline')
      return { code: 200, data: tree() }
    },
  })
  await e.loadCatalog()
  assert.ok(e.catalogError.value)
  fail = false
  await e.loadCatalog()
  assert.equal(e.catalogError.value, '')
  e.assertionGroups.value = groups()
  await e.loadCatalog()
  assert.equal(e.assertionGroups.value[0].name, 'Example group')
  assert.deepEqual(e.editorCalls, ['fill'])
  e.cleanup()
})
test('newer catalog owns data/error/loading after older failure', async () => {
  const one = deferred(),
    two = deferred()
  let count = 0
  const e = fixture({ getSystemAssertionList: () => (++count === 1 ? one.promise : two.promise) })
  const first = e.loadCatalog(),
    second = e.loadCatalog()
  one.reject(Error('old'))
  await first
  assert.equal(e.catalogLoading.value, true)
  assert.equal(e.catalogError.value, '')
  two.resolve({ code: 200, data: tree() })
  await second
  assert.equal(e.catalogLoading.value, false)
  assert.equal(e.assertionList.value.length, 1)
  e.cleanup()
})
for (const field of ['roleId', 'userId', 'token', 'selected_environment'])
  test(field + ' A-B-A invalidates late catalog initialization', async () => {
    const pending = deferred(),
      e = fixture({ getSystemAssertionList: () => pending.promise }),
      work = e.loadCatalog(),
      old = e.user[field]
    e.user[field] = field === 'token' ? 'example-other' : 99
    e.user[field] = old
    pending.resolve({ code: 200, data: tree() })
    assert.equal(await work, false)
    assert.equal(e.assertionList.value.length, 0)
    assert.deepEqual(e.editorCalls, [])
    e.cleanup()
  })
test('context change between catalog load and nextTick cannot fill a new editor', async () => {
  const tick = deferred(),
    e = fixture({}, { nextTick: () => tick.promise })
  const work = e.loadCatalog()
  await Promise.resolve()
  e.user.roleId = 99
  tick.resolve()
  assert.equal(await work, false)
  assert.deepEqual(e.editorCalls, [])
  e.cleanup()
})
test('cached activation reloads metadata while preserving same-context sandbox draft', async () => {
  let loads = 0
  const e = fixture({
    getSystemAssertionList: async () => {
      ++loads
      return { code: 200, data: tree() }
    },
  })
  e.hooks.mounted.forEach((fn) => fn())
  await flush()
  e.assertionGroups.value = groups()
  e.assertionGroups.value[0].assertions[0].values.actual = 42
  e.hooks.deactivate.forEach((fn) => fn())
  e.hooks.activate.forEach((fn) => fn())
  await flush()
  assert.equal(loads, 2)
  assert.equal(e.assertionGroups.value[0].assertions[0].values.actual, 42)
  e.cleanup()
})
test('load error after a successful catalog keeps sandbox inputs for retry', async () => {
  let fail = false
  const e = fixture({
    getSystemAssertionList: async () => {
      if (fail) throw Error('offline')
      return { code: 200, data: tree() }
    },
  })
  await e.loadCatalog()
  e.assertionGroups.value = groups()
  fail = true
  await e.loadCatalog()
  assert.equal(e.assertionGroups.value[0].name, 'Example group')
  assert.equal(e.assertionList.value.length, 1)
  assert.equal(e.editorBlocked.value, true)
  e.cleanup()
})
test('fill clear and method actions are blocked during test and catalog loading', async () => {
  const pending = deferred(),
    e = fixture({ postSystemAssertionTest: () => pending.promise })
  e.fillExamples()
  e.clearValues()
  e.selectMethodForTest(method())
  assert.deepEqual(e.editorCalls, [])
  await e.loadCatalog()
  e.assertionGroups.value = groups()
  const work = e.testAssertion(),
    count = e.editorCalls.length
  e.fillExamples()
  e.clearValues()
  e.selectMethodForTest(method())
  assert.equal(e.editorCalls.length, count)
  pending.resolve(result(e.load('records.ts').testPayload(e.assertionGroups.value)))
  await work
  e.cleanup()
})
test('method action selects public or runtime-only method without executing it', async () => {
  const e = fixture()
  await e.loadCatalog()
  e.selectMethodForTest(method())
  e.selectMethodForTest(method('runtime'))
  e.selectMethodForTest(method('missing'))
  assert.deepEqual(e.editorCalls, ['fill', 'equal', 'runtime'])
  assert.equal(e.calls.length, 0)
  e.cleanup()
})
test('test payload owns a snapshot and preserves native JSON values and selected method', () => {
  const e = fixture(),
    source = groups()
  source[0].assertions[0].values = {
    actual: { value: 0, list: [false, null] },
    expect: [],
    method: 'wrong',
  }
  const body = e.load('records.ts').testPayload(source)
  source[0].assertions[0].values.actual.value = 99
  assert.deepEqual(body.assertions[0].items[0], {
    actual: { value: 0, list: [false, null] },
    expect: [],
    method: 'equal',
  })
  e.cleanup()
})
test('test snapshots preserve lossless integer objects without mutating them', () => {
  const e = fixture(),
    source = groups(),
    value = new lossless.LosslessJsonNumber('9007199254740995')
  source[0].assertions[0].values.actual = { id: value }
  const body = e.load('records.ts').testPayload(source)
  assert.notEqual(body.assertions[0].items[0].actual, source[0].assertions[0].values.actual)
  assert.equal(lossless.stringifyLosslessJson(body).includes('9007199254740995'), true)
  assert.equal(lossless.isLosslessJsonNumber(body.assertions[0].items[0].actual.id), true)
  e.cleanup()
})
test('AND/OR groups use the original grouped request and valid failed assertions are shown as results', async () => {
  const e = fixture({
    postSystemAssertionTest: async (p) => {
      e.calls.push(p)
      return result(p, false)
    },
  })
  await e.loadCatalog()
  e.assertionGroups.value = [...groups(), { ...groups()[0], id: 'g2', logic: 'OR' }]
  await e.testAssertion()
  assert.deepEqual(
    e.calls[0].assertions.map((group) => group.logic),
    ['AND', 'OR']
  )
  assert.equal(e.testResult.value.status, false)
  assert.equal(e.testResult.value.groups.length, 2)
  assert.equal(e.testError.value, '')
  e.cleanup()
})
test('duplicate requests are prevented until the actual test settles', async () => {
  const pending = deferred()
  let count = 0,
    request
  const e = fixture({
    postSystemAssertionTest: (p) => {
      request = p
      ++count
      return pending.promise
    },
  })
  await e.loadCatalog()
  e.assertionGroups.value = groups()
  const work = e.testAssertion()
  await e.testAssertion()
  assert.equal(count, 1)
  assert.equal(e.testing.value, true)
  pending.resolve(result(request))
  await work
  assert.equal(e.testing.value, false)
  assert.equal(e.testResult.value.status, true)
  e.cleanup()
})
for (const mode of ['empty', 'missing-method', 'availability', 'runtime'])
  test(mode + ' cannot start a test', async () => {
    const e = fixture()
    await e.loadCatalog()
    e.assertionGroups.value = mode === 'empty' ? [] : groups()
    if (mode === 'missing-method') e.assertionGroups.value[0].assertions[0].method = ''
    if (mode === 'availability')
      e.testAvailability.value = { allowed: false, reason: 'Example unavailable' }
    if (mode === 'runtime') e.assertionGroups.value[0].assertions[0].method = 'runtime'
    await e.testAssertion()
    assert.equal(e.calls.length, 0)
    assert.ok(e.messages.some(([key]) => key === 'warning'))
    e.cleanup()
  })
test('network failure retains inputs and supports explicit retry', async () => {
  let fail = true
  const e = fixture({
    postSystemAssertionTest: async (p) => {
      if (fail) throw Error('offline')
      return result(p)
    },
  })
  await e.loadCatalog()
  e.assertionGroups.value = groups()
  await e.testAssertion()
  assert.ok(e.testError.value)
  assert.equal(e.testing.value, false)
  assert.equal(e.assertionGroups.value[0].assertions[0].values.actual, 0)
  fail = false
  await e.testAssertion()
  assert.equal(e.testError.value, '')
  assert.equal(e.testResult.value.status, true)
  e.cleanup()
})
for (const mode of [
  'code',
  'group-name',
  'group-logic',
  'group-count',
  'item-method',
  'item-status',
  'item-count',
])
  test('mismatched ' + mode + ' result cannot replace current result', async () => {
    const e = fixture({
      postSystemAssertionTest: async (p) => {
        const r = result(p)
        if (mode === 'code') r.code = 500
        if (mode === 'group-name') r.data.groups[0].name = 'Other'
        if (mode === 'group-logic') r.data.groups[0].logic = 'OR'
        if (mode === 'group-count') r.data.groups = []
        if (mode === 'item-method') r.data.groups[0].items[0].method = 'Other'
        if (mode === 'item-status') r.data.groups[0].items[0].status = 1
        if (mode === 'item-count') r.data.groups[0].items = []
        return r
      },
    })
    await e.loadCatalog()
    e.assertionGroups.value = groups()
    await e.testAssertion()
    assert.equal(e.testResult.value, null)
    assert.ok(e.testError.value)
    assert.equal(e.testing.value, false)
    e.cleanup()
  })
test('input A-B-A during in-flight test invalidates result but not physical lock', async () => {
  const pending = deferred()
  let request
  const e = fixture({
    postSystemAssertionTest: (p) => {
      request = p
      return pending.promise
    },
  })
  await e.loadCatalog()
  e.assertionGroups.value = groups()
  const work = e.testAssertion()
  e.assertionGroups.value[0].assertions[0].values.actual = 1
  e.assertionGroups.value[0].assertions[0].values.actual = 0
  assert.equal(e.testing.value, true)
  pending.resolve(result(request))
  await work
  assert.equal(e.testResult.value, null)
  assert.equal(e.testError.value, '')
  assert.equal(e.testing.value, false)
  e.cleanup()
})
test('modifying input after a completed test clears its result', async () => {
  const e = fixture()
  await e.loadCatalog()
  e.assertionGroups.value = groups()
  await e.testAssertion()
  assert.ok(e.testResult.value)
  e.assertionGroups.value[0].logic = 'OR'
  assert.equal(e.testResult.value, null)
  e.cleanup()
})
for (const transition of ['context', 'deactivate', 'unmount'])
  test(transition + ' ignores late test and preserves physical lock until settlement', async () => {
    const pending = deferred()
    let request,
      count = 0
    const e = fixture({
      postSystemAssertionTest: (p) => {
        request = p
        ++count
        return pending.promise
      },
    })
    await e.loadCatalog()
    e.assertionGroups.value = groups()
    const work = e.testAssertion()
    if (transition === 'context') {
      e.user.roleId = 99
      e.user.roleId = 2
    } else e.hooks[transition].forEach((fn) => fn())
    if (transition === 'deactivate') e.hooks.activate.forEach((fn) => fn())
    assert.equal(e.testing.value, true)
    await e.testAssertion()
    assert.equal(count, 1)
    pending.resolve(result(request))
    await work
    assert.equal(e.testing.value, false)
    assert.equal(e.testResult.value, null)
    assert.equal(e.testError.value, '')
    e.cleanup()
  })
test('method card emits only when not disabled', () => {
  const e = harness('MethodClassCard', 'select', {
    base,
    props: { group: tree()[0].children[0], disabled: true },
  })
  e.select(method())
  assert.equal(e.events.length, 0)
  e.props.disabled = false
  e.select(method())
  assert.equal(e.events[0][0], 'test')
  assert.equal(e.events[0][1].value, 'equal')
  e.close()
})
test('shared editor fill/clear/select keeps real zero/false examples and native JSON types', () => {
  const e = harness('AssertionGroupEditor', 'fillExamples,clearValues,setSingleMethod', {
    base,
    filename: path.resolve('src/components/forms/AssertionGroupEditor.vue'),
    props: { modelValue: groups(), methods: tree(), methodScopes: ['public'] },
  })
  e.fillExamples()
  assert.equal(e.events.at(-1)[1][0].assertions[0].values.actual, 0)
  assert.equal(e.events.at(-1)[1][0].assertions[0].values.expect, false)
  e.clearValues()
  assert.equal(e.events.at(-1)[1][0].assertions[0].values.actual, '')
  e.setSingleMethod('equal')
  assert.equal(e.events.at(-1)[1][0].assertions.length, 1)
  e.close()
})
test('page, method card and associated public editors compile scripts/templates/styles', () => {
  for (const filename of [
    path.join(base, 'index.vue'),
    path.join(base, 'components/MethodClassCard.vue'),
    path.resolve('src/components/forms/AssertionGroupEditor.vue'),
    path.resolve('src/components/forms/AssertionParameterEditor.vue'),
  ]) {
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
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
