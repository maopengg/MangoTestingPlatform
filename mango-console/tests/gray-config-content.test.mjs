import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush, method } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/gray/config-file')
const source = (extra = {}) => ({
  yamlId: 11,
  bindingId: 21,
  repositoryId: 31,
  title: 'Example config',
  filePath: 'config/example.yml',
  ...extra,
})
const response = (extra = {}) => ({
  code: 200,
  data: {
    yaml_file_id: 11,
    binding_id: 21,
    repository_id: 31,
    file_path: 'config/example.yml',
    content: 'enabled: true',
    ...extra,
  },
})
function drawer(api) {
  const hooks = { deactivate: [], activate: [], unmount: [] }
  const f = harness(
    'YamlContentDrawer',
    'open,closeDrawer,loadContent,onVisibleChange,visible,target,content,filePath,loading,error',
    {
      base,
      props: { contextKey: 'one' },
      api: { getGrayYamlFileContent: api || (async () => response()) },
      modules: {
        vue: {
          ...vue,
          onDeactivated: (fn) => hooks.deactivate.push(fn),
          onActivated: (fn) => hooks.activate.push(fn),
          onBeforeUnmount: (fn) => hooks.unmount.push(fn),
        },
      },
    }
  )
  return {
    ...f,
    hooks,
    cleanup() {
      hooks.unmount.forEach((fn) => fn())
      f.close()
    },
  }
}

test('content opens immediately with a local pending state and a frozen request target', async () => {
  const pending = deferred(),
    calls = []
  const d = drawer((p) => {
    calls.push(p)
    return pending.promise
  })
  const original = source()
  d.open(original)
  original.yamlId = 99
  original.filePath = 'changed.yml'
  assert.equal(d.visible.value, true)
  assert.equal(d.loading.value, true)
  assert.equal(d.filePath.value, 'config/example.yml')
  assert.deepEqual(calls, [{ id: 11, binding_id: 21 }])
  pending.resolve(response())
  await flush()
  assert.equal(d.content.value, 'enabled: true')
  assert.equal(d.loading.value, false)
  assert.equal(d.error.value, '')
  d.cleanup()
})

for (const content of ['', '0', 'enabled: false\n']) {
  test(`content preserves a valid file value ${JSON.stringify(content)}`, async () => {
    const d = drawer(async () => response({ content }))
    d.open(source())
    await flush()
    assert.equal(d.content.value, content)
    assert.equal(d.error.value, '')
    assert.equal(d.loading.value, false)
    d.cleanup()
  })
}

for (const [key, value] of [
  ['yaml_file_id', 12],
  ['binding_id', 22],
  ['repository_id', 32],
  ['file_path', null],
  ['content', null],
]) {
  test(`content rejects mismatched or invalid ${key} without showing the payload`, async () => {
    const d = drawer(async () => response({ [key]: value }))
    d.open(source())
    await flush()
    assert.equal(d.content.value, '')
    assert.ok(d.error.value)
    assert.equal(d.visible.value, true)
    assert.equal(d.loading.value, false)
    d.cleanup()
  })
}

test('non-success envelope cannot be rendered as content', async () => {
  const d = drawer(async () => ({ ...response(), code: 400 }))
  d.open(source())
  await flush()
  assert.ok(d.error.value)
  assert.equal(d.content.value, '')
  d.cleanup()
})

test('read failure remains retryable in the same window and keeps the original target', async () => {
  const calls = []
  const d = drawer(async (p) => {
    calls.push(p)
    if (calls.length === 1) throw Error('Network')
    return response()
  })
  d.open(source())
  await flush()
  assert.ok(d.error.value)
  assert.equal(d.loading.value, false)
  assert.equal(d.visible.value, true)
  await d.loadContent()
  assert.deepEqual(calls, [
    { id: 11, binding_id: 21 },
    { id: 11, binding_id: 21 },
  ])
  assert.equal(d.error.value, '')
  assert.equal(d.content.value, 'enabled: true')
  d.cleanup()
})

for (const finish of ['resolve', 'reject']) {
  test(`closing while reading ignores a late ${finish} and clears content`, async () => {
    const pending = deferred(),
      d = drawer(() => pending.promise)
    d.open(source())
    d.onVisibleChange(false)
    pending[finish](finish === 'resolve' ? response() : Error('Late failure'))
    await flush()
    assert.equal(d.visible.value, false)
    assert.equal(d.target.value, null)
    assert.equal(d.content.value, '')
    assert.equal(d.error.value, '')
    assert.equal(d.loading.value, false)
    d.cleanup()
  })
}

test('switching bindings rejects older results and does not end the new loading state', async () => {
  const first = deferred(),
    second = deferred()
  const d = drawer((p) => (p.binding_id === 21 ? first.promise : second.promise))
  d.open(source())
  d.open(source({ bindingId: 22, repositoryId: 32, filePath: 'next.yml' }))
  first.resolve(response())
  await flush()
  assert.equal(d.content.value, '')
  assert.equal(d.filePath.value, 'next.yml')
  assert.equal(d.loading.value, true)
  second.resolve(
    response({ binding_id: 22, repository_id: 32, file_path: 'next.yml', content: 'next' })
  )
  await flush()
  assert.equal(d.content.value, 'next')
  assert.equal(d.loading.value, false)
  d.cleanup()
})

test('A-B-A context changes invalidate old reads even when the context text returns', async () => {
  const pending = deferred(),
    d = drawer(() => pending.promise)
  d.open(source())
  d.props.contextKey = 'two'
  d.props.contextKey = 'one'
  pending.resolve(response())
  await flush()
  assert.equal(d.visible.value, false)
  assert.equal(d.content.value, '')
  d.cleanup()
})

for (const hook of ['deactivate', 'unmount']) {
  test(`${hook} discards late content and prevents reopening until activated`, async () => {
    const pending = deferred()
    let calls = 0
    const d = drawer(() => {
      calls++
      return calls === 1 ? pending.promise : Promise.resolve(response())
    })
    d.open(source())
    d.hooks[hook].forEach((fn) => fn())
    d.open(source())
    assert.equal(calls, 1)
    pending.resolve(response())
    await flush()
    assert.equal(d.visible.value, false)
    assert.equal(d.content.value, '')
    if (hook === 'deactivate') {
      d.hooks.activate.forEach((fn) => fn())
      d.open(source())
      await flush()
      assert.equal(d.content.value, 'enabled: true')
    }
    d.cleanup()
  })
}

test('reopening the same target creates a new request generation', async () => {
  const first = deferred(),
    second = deferred()
  let calls = 0
  const d = drawer(() => (++calls === 1 ? first.promise : second.promise))
  d.open(source())
  d.closeDrawer()
  d.open(source())
  second.resolve(response({ content: 'new' }))
  await flush()
  first.resolve(response({ content: 'old' }))
  await flush()
  assert.equal(d.content.value, 'new')
  d.cleanup()
})

test('latest retry owns both content and loading after older retry rejection', async () => {
  const first = deferred(),
    second = deferred()
  let calls = 0
  const d = drawer(() => (++calls === 1 ? first.promise : second.promise))
  d.open(source())
  const retry = d.loadContent()
  first.reject(Error('Old failure'))
  await flush()
  assert.equal(d.loading.value, true)
  assert.equal(d.error.value, '')
  second.resolve(response())
  await retry
  assert.equal(d.content.value, 'enabled: true')
  assert.equal(d.loading.value, false)
  d.cleanup()
})

test('invalid target does not trigger a backend read', () => {
  let calls = 0
  const d = drawer(async () => {
    calls++
    return response()
  })
  for (const key of ['yamlId', 'bindingId', 'repositoryId']) d.open(source({ [key]: 0 }))
  assert.equal(calls, 0)
  assert.equal(d.visible.value, false)
  d.cleanup()
})

test('parent only hands off a binding owned by the selected configuration with a valid repository', () => {
  const f = harness('YamlContentDrawer', '', { base })
  const { selectionId } = f.load('forms.ts')
  const calls = [],
    warnings = []
  const deps = {
    yamlSaving: vue.ref(false),
    bindingSaving: vue.ref(false),
    actionLoading: vue.ref(''),
    yamlEditorVisible: vue.ref(false),
    bindingEditorVisible: vue.ref(false),
    bindingDrawer: {
      visible: true,
      record: { id: 11, name: 'Example config' },
      dataList: [{ id: 21, yaml_file: 11, file_path: 'config/example.yml' }],
    },
    actionBlocked: () => false,
    contentDrawerRef: vue.ref({ open: (target) => calls.push(target) }),
    selectionId,
    Message: { warning: (value) => warnings.push(value) },
  }
  deps.bindingTarget = method(
    'bindingTarget',
    { bindingDrawer: deps.bindingDrawer },
    path.join(base, 'index.vue')
  )
  const open = method('onBindingContent', deps, path.join(base, 'index.vue'))
  const record = { id: 21, yaml_file: 11, repository: { id: 31 }, file_path: 'config/example.yml' }
  open(record)
  assert.deepEqual(calls, [source()])
  open({ ...record, yaml_file: 12 })
  open({ ...record, repository: null })
  assert.equal(calls.length, 1)
  assert.equal(warnings.length, 2)
  deps.bindingDrawer.visible = false
  open(record)
  assert.equal(calls.length, 1)
  f.close()
})

test('parent context invalidates content when ownership, windows, identity or environment changes', () => {
  const user = vue.reactive({ userId: 1, roleId: 2, token: 'test-token', selected_environment: 0 })
  const route = vue.reactive({ fullPath: '/gray/config-file/index' })
  const f = harness(
    'index',
    'contentScopeKey,bindingDrawer,query,yamlEditorVisible,bindingEditorVisible',
    {
      base,
      modules: {
        '@/store/modules/user': { default: () => user },
        'vue-router': { useRoute: () => route },
        '@/hooks/table': {
          useTable: () => ({ tableLoading: vue.ref(false) }),
          usePagination: () => ({ page: 1, pageSize: 20, setTotalSize() {} }),
        },
        '@/hooks/use-latest-request': {
          useLatestRequest: () => ({ beginRequest() {}, isLatestRequest() {} }),
        },
      },
    }
  )
  const d = drawer(() => deferred().promise)
  const stop = vue.watch(
    f.contentScopeKey,
    (key) => {
      d.props.contextKey = key
    },
    { flush: 'sync', immediate: true }
  )
  f.bindingDrawer.visible = true
  f.bindingDrawer.record = { id: 11, name: 'Example config' }
  for (const change of [
    () => {
      f.bindingDrawer.visible = false
    },
    () => {
      f.bindingDrawer.record = { id: 12, name: 'Next config' }
    },
    () => {
      f.query.project_product = 9
    },
    () => {
      f.yamlEditorVisible.value = true
    },
    () => {
      f.bindingEditorVisible.value = true
    },
    () => {
      user.userId = 2
    },
    () => {
      user.roleId = 3
    },
    () => {
      user.token = 'next-test-token'
    },
    () => {
      user.selected_environment = 1
    },
    () => {
      route.fullPath = '/gray/execution-log/index'
    },
  ]) {
    d.open(source())
    assert.equal(d.visible.value, true)
    change()
    assert.equal(d.visible.value, false)
    assert.equal(d.loading.value, false)
  }
  stop()
  d.cleanup()
  f.close()
})

test('parent and content drawer compile script, template and styles', () => {
  for (const relative of ['index.vue', 'components/YamlContentDrawer.vue']) {
    const filename = path.join(base, relative)
    const { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: 'gray-content' })
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename,
        id: 'gray-content',
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
    for (const style of descriptor.styles)
      assert.deepEqual(
        compileStyle({
          source: style.content,
          filename,
          id: 'gray-content',
          scoped: style.scoped,
          preprocessLang: style.lang,
        }).errors,
        []
      )
  }
})
