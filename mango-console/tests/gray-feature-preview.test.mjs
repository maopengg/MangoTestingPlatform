import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import * as vue from 'vue'
import { harness, deferred, flush, method } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/gray/feature')
const record = (extra = {}) => ({
  id: 11,
  name: 'Example feature',
  feature_key: 'example.enabled',
  config_type: 1,
  project_product: { id: 2 },
  module: { id: 3 },
  yaml_file: { id: 4, file_path: 'example.yml' },
  datasource_alias: null,
  database: null,
  path_config: [
    { path: 'example.enabled', value_type: 'boolean', original_value: 'false', value: true },
  ],
  ...extra,
})
const preview = (id = 11, extra = {}) => ({
  code: 200,
  data: {
    feature_id: id,
    feature_key: 'example.enabled',
    action: 'enable',
    config_type: 'yaml',
    before_text: 'before',
    after_text: 'after',
    before_snapshot: { example: { enabled: false } },
    file_path: 'example.yml',
    ...extra,
  },
})
function fixture(api = {}, reloadList = async () => true, enumApi = async () => {}) {
  const hooks = { deactivate: [], activate: [], unmount: [] },
    messages = [],
    calls = [],
    reads = []
  const e = harness(
    'FeaturePreviewDrawer',
    [
      'open,save,execute,generate,canCancel,onVisibleChange,addPath,removePath,loadEnums',
      'record,visible,draft,variables,title,needsVariables,canExecute,busy,loading,saving,executing,previewError,saveError,executeError,enumError,enumLoading,beforeText,afterText,pathOptions',
    ].join(','),
    {
      base,
      props: { contextKey: 'A', blocked: false, reloadList },
      api: {
        postGrayFeaturePreview: async (p) => {
          reads.push(p)
          return preview(p.feature_id)
        },
        putGrayFeature: async (p) => {
          calls.push(p)
          return { code: 200, data: { ...p, project_product: 2, module: 3, config_type: 1 } }
        },
        postGrayFeatureExecute: async (p) => {
          calls.push(p)
          return { code: 200, data: { execution_log_id: 99, status: 1 } }
        },
        ...api,
      },
      modules: {
        vue: {
          ...vue,
          onActivated: (fn) => hooks.activate.push(fn),
          onDeactivated: (fn) => hooks.deactivate.push(fn),
          onBeforeUnmount: (fn) => hooks.unmount.push(fn),
        },
        '@/store/modules/get-enum': {
          useEnum: () => ({
            environment_type: [
              { key: 0, title: 'Development' },
              { key: 2, title: '测试环境' },
            ],
            getEnum: enumApi,
          }),
        },
        '@arco-design/web-vue': {
          Message: Object.fromEntries(
            ['error', 'success', 'warning'].map((key) => [
              key,
              (text) => messages.push([key, text]),
            ])
          ),
        },
      },
    }
  )
  return {
    ...e,
    hooks,
    messages,
    calls,
    reads,
    cleanup() {
      hooks.unmount.forEach((fn) => fn())
      e.close()
    },
  }
}
test('open owns detached drafts, resets on close and defaults to test environment', async () => {
  const e = fixture(),
    source = record()
  e.open(source)
  await flush()
  assert.equal(e.visible.value, true)
  assert.equal(e.variables.environment, 2)
  assert.equal(e.canExecute.value, true)
  e.draft.paths[0].value = false
  assert.equal(source.path_config[0].value, true)
  assert.equal(e.canExecute.value, false)
  e.onVisibleChange(false)
  assert.equal(e.visible.value, false)
  assert.equal(e.record.value, null)
  e.open(source)
  await flush()
  assert.equal(e.draft.paths[0].value, true)
  assert.equal(e.canExecute.value, true)
  e.cleanup()
})
test('path mapping preserves false, zero, nested JSON and cascade leaf', () => {
  const e = fixture(),
    h = e.load('preview.ts')
  assert.deepEqual(
    h.normalizePaths([
      { path: ['a', 'a.b'], value_type: 'number', original_value: 0, value: 0 },
      { path: 'c', value_type: 'boolean', value: false },
      { path: [], value: 1 },
    ]),
    [
      { path: 'a.b', value_type: 'number', original_value: '0', value: 0 },
      { path: 'c', value_type: 'boolean', original_value: '', value: false },
    ]
  )
  assert.equal(h.inputValue({ enabled: false }), '{"enabled":false}')
  assert.equal(h.environment(0), 0)
  assert.equal(h.environment('__common__'), null)
  assert.deepEqual(h.pathTree({ a: { b: [] }, list: [1] }), [
    { value: 'a', label: 'a', children: [{ value: 'a.b', label: 'b' }] },
    { value: 'list', label: 'list' },
  ])
  e.cleanup()
})
test('variable source and environment zero are sent without treating zero as empty', async () => {
  const e = fixture()
  e.open(record({ path_config: [{ path: 'example.enabled', value: '${{example}}' }] }))
  await flush()
  assert.equal(e.needsVariables.value, true)
  e.variables.environment = 0
  e.variables.source = 'ui'
  assert.equal(e.canExecute.value, false)
  await e.generate()
  assert.equal(e.reads.at(-1).variable_test_env, 0)
  assert.equal(e.reads.at(-1).variable_source, 'ui')
  e.variables.environment = '__common__'
  await e.generate()
  assert.equal(e.reads.at(-1).variable_test_env, null)
  e.cleanup()
})
test('missing variable source blocks preview with visible feedback', async () => {
  const e = fixture()
  e.open(record({ path_config: [{ path: 'example.enabled', value: '${example}' }] }))
  await flush()
  const count = e.reads.length
  e.variables.source = ''
  await e.generate()
  assert.equal(e.reads.length, count)
  assert.equal(e.canExecute.value, false)
  assert.ok(e.messages.some(([key]) => key === 'warning'))
  e.cleanup()
})
for (const change of ['path', 'type', 'original', 'value', 'source', 'environment'])
  test(change + ' changes invalidate accepted preview immediately', async () => {
    const e = fixture()
    e.open(record())
    await flush()
    assert.equal(e.canExecute.value, true)
    if (change === 'path') e.draft.paths[0].path = ['another']
    if (change === 'type') e.draft.paths[0].value_type = 'number'
    if (change === 'original') e.draft.paths[0].original_value = 'new'
    if (change === 'value') e.draft.paths[0].value = false
    if (change === 'source') e.variables.source = 'ui'
    if (change === 'environment') e.variables.environment = 0
    assert.equal(e.canExecute.value, false)
    assert.equal(e.beforeText.value, '')
    await e.execute()
    assert.equal(e.calls.length, 0)
    e.cleanup()
  })
test('draft A-B-A cannot resurrect an in-flight preview', async () => {
  const pending = deferred(),
    e = fixture({ postGrayFeaturePreview: () => pending.promise })
  e.open(record())
  assert.equal(e.loading.value, true)
  e.draft.paths[0].value = false
  e.draft.paths[0].value = true
  pending.resolve(preview())
  await flush()
  assert.equal(e.canExecute.value, false)
  assert.equal(e.beforeText.value, '')
  assert.equal(e.loading.value, false)
  e.cleanup()
})
test('newer preview owns loading, text and execute eligibility', async () => {
  const one = deferred(),
    two = deferred()
  let count = 0
  const e = fixture({ postGrayFeaturePreview: () => (++count === 1 ? one.promise : two.promise) })
  e.open(record())
  const newer = e.generate()
  one.resolve(preview())
  await flush()
  assert.equal(e.loading.value, true)
  assert.equal(e.canExecute.value, false)
  two.resolve(preview(11, { after_text: 'newer' }))
  await newer
  assert.equal(e.loading.value, false)
  assert.equal(e.afterText.value, 'newer')
  assert.equal(e.canExecute.value, true)
  e.cleanup()
})
test('close and reopen isolate pending previews and errors', async () => {
  const pending = deferred()
  let count = 0
  const e = fixture({
    postGrayFeaturePreview: async (p) => (++count === 1 ? pending.promise : preview(p.feature_id)),
  })
  e.open(record())
  e.onVisibleChange(false)
  e.open(record({ id: 12 }))
  await flush()
  pending.reject(Error('old'))
  await flush()
  assert.equal(e.record.value.id, 12)
  assert.equal(e.canExecute.value, true)
  assert.equal(e.previewError.value, false)
  e.cleanup()
})
test('preview failure can retry without losing draft', async () => {
  let fail = true
  const e = fixture({
    postGrayFeaturePreview: async () => {
      if (fail) throw Error('offline')
      return preview()
    },
  })
  e.open(record())
  await flush()
  assert.equal(e.previewError.value, true)
  assert.equal(e.loading.value, false)
  assert.equal(e.draft.paths.length, 1)
  fail = false
  await e.generate()
  assert.equal(e.previewError.value, false)
  assert.equal(e.canExecute.value, true)
  e.cleanup()
})
for (const bad of [
  { feature_id: 12 },
  { feature_key: 'other' },
  { action: 'disable' },
  { config_type: 'sql' },
])
  test(
    'preview identity/type/action mismatch blocks execution ' + JSON.stringify(bad),
    async () => {
      const e = fixture({ postGrayFeaturePreview: async () => preview(11, bad) })
      e.open(record())
      await flush()
      assert.equal(e.previewError.value, true)
      assert.equal(e.canExecute.value, false)
      await e.execute()
      assert.equal(e.calls.length, 0)
      e.cleanup()
    }
  )
for (const [number, type] of [
  [1, 'yaml'],
  [2, 'sql'],
  [3, 'code'],
])
  test(type + ' preview keeps empty text and executes fixed enable payload', async () => {
    const e = fixture({
      postGrayFeaturePreview: async () =>
        preview(11, { config_type: type, before_text: '', after_text: '' }),
    })
    e.open(record({ config_type: number }))
    await flush()
    assert.equal(e.beforeText.value, '')
    assert.equal(e.afterText.value, '')
    assert.equal(e.canExecute.value, true)
    await e.execute()
    assert.equal(e.calls[0].feature_id, 11)
    assert.equal(e.calls[0].action, 'enable')
    assert.equal(e.calls[0].target_value, '')
    assert.equal(e.visible.value, false)
    e.cleanup()
  })
test('YAML snapshot fallback stays supported', async () => {
  const e = fixture({
    postGrayFeaturePreview: async () =>
      preview(11, {
        before_text: undefined,
        after_text: undefined,
        after_snapshot: { example: true },
      }),
  })
  e.open(record())
  await flush()
  assert.equal(e.canExecute.value, true)
  assert.equal(JSON.parse(e.afterText.value).example, true)
  e.cleanup()
})
test('path save submits only ID and normalized paths, then re-previews', async () => {
  const e = fixture()
  e.open(record())
  await flush()
  e.draft.paths[0].value = false
  await e.save()
  assert.deepEqual(Object.keys(e.calls[0]).sort(), ['id', 'path_config'])
  assert.equal(e.calls[0].path_config[0].value, false)
  assert.equal(e.canExecute.value, true)
  assert.equal(e.reads.length, 2)
  assert.equal(e.saveError.value, false)
  e.cleanup()
})
test('save locks close, open, execute and duplicate save until request completes', async () => {
  const pending = deferred()
  let payload,
    calls = 0
  const e = fixture({
    putGrayFeature: (p) => {
      payload = p
      ++calls
      return pending.promise
    },
  })
  e.open(record())
  await flush()
  const first = e.save()
  assert.equal(e.busy.value, true)
  assert.equal(e.canCancel(), false)
  e.onVisibleChange(false)
  e.open(record({ id: 12 }))
  await e.execute()
  await e.save()
  assert.equal(e.record.value.id, 11)
  assert.equal(calls, 1)
  pending.resolve({
    code: 200,
    data: { ...payload, project_product: 2, module: 3, config_type: 1 },
  })
  await first
  assert.equal(e.busy.value, false)
  assert.equal(e.canExecute.value, true)
  e.cleanup()
})
test('failed save retains drafts and retries', async () => {
  let fail = true
  const e = fixture({
    putGrayFeature: async (p) =>
      fail
        ? { code: 500 }
        : { code: 200, data: { ...p, project_product: 2, module: 3, config_type: 1 } },
  })
  e.open(record())
  await flush()
  e.draft.paths[0].value = false
  await e.save()
  assert.equal(e.saveError.value, true)
  assert.equal(e.draft.paths[0].value, false)
  assert.equal(e.busy.value, false)
  fail = false
  await e.save()
  assert.equal(e.saveError.value, false)
  assert.equal(e.canExecute.value, true)
  e.cleanup()
})
for (const field of ['id', 'project_product', 'module', 'config_type', 'path_config'])
  test('save acknowledgment mismatch retains draft ' + field, async () => {
    const e = fixture({
      putGrayFeature: async (p) => ({
        code: 200,
        data: {
          ...p,
          project_product: 2,
          module: 3,
          config_type: 1,
          [field]: field === 'path_config' ? [] : 99,
        },
      }),
    })
    e.open(record())
    await flush()
    await e.save()
    assert.equal(e.saveError.value, true)
    assert.equal(e.canExecute.value, false)
    assert.equal(e.visible.value, true)
    e.cleanup()
  })
test('save succeeded but preview refresh failed does not report save failed', async () => {
  let count = 0
  const e = fixture({
    postGrayFeaturePreview: async () => {
      if (++count > 1) throw Error('offline')
      return preview()
    },
  })
  e.open(record())
  await flush()
  await e.save()
  assert.equal(e.saveError.value, false)
  assert.equal(e.previewError.value, true)
  assert.ok(e.messages.some(([key]) => key === 'success'))
  e.cleanup()
})
test('execute requires preview and is physically deduplicated', async () => {
  const pending = deferred()
  let count = 0
  const e = fixture({
    postGrayFeatureExecute: () => {
      ++count
      return pending.promise
    },
  })
  await e.execute()
  assert.equal(count, 0)
  e.open(record())
  await flush()
  const first = e.execute()
  await e.execute()
  await e.save()
  e.onVisibleChange(false)
  assert.equal(e.visible.value, true)
  assert.equal(count, 1)
  pending.resolve({ code: 200, data: { execution_log_id: 77, status: 1 } })
  await first
  assert.equal(e.visible.value, false)
  assert.equal(e.busy.value, false)
  assert.equal(e.canExecute.value, false)
  e.cleanup()
})
for (const response of [
  { code: 500, data: {} },
  { code: 200, data: { status: 1 } },
  { code: 200, data: { execution_log_id: 99, status: 99 } },
])
  test('unconfirmed execute requires fresh preview ' + JSON.stringify(response), async () => {
    const e = fixture({ postGrayFeatureExecute: async () => response })
    e.open(record())
    await flush()
    await e.execute()
    assert.equal(e.executeError.value, true)
    assert.equal(e.visible.value, true)
    assert.equal(e.canExecute.value, false)
    e.cleanup()
  })
test('valid failed execution log closes and reports execution failure', async () => {
  const e = fixture({
    postGrayFeatureExecute: async () => ({ code: 200, data: { execution_log_id: 99, status: 2 } }),
  })
  e.open(record())
  await flush()
  await e.execute()
  assert.equal(e.visible.value, false)
  assert.ok(e.messages.some(([, text]) => text.includes('执行失败')))
  e.cleanup()
})
for (const action of ['save', 'execute'])
  for (const transition of ['context', 'deactivate', 'unmount'])
    test(
      action + ' keeps physical lock across ' + transition + ' and ignores stale completion',
      async () => {
        const pending = deferred()
        const e = fixture({
          [action === 'save' ? 'putGrayFeature' : 'postGrayFeatureExecute']: () => pending.promise,
        })
        e.open(record())
        await flush()
        const promise = e[action]()
        if (transition === 'context') {
          e.props.contextKey = 'B'
          e.props.contextKey = 'A'
        } else e.hooks[transition].forEach((fn) => fn())
        if (transition === 'deactivate') e.hooks.activate.forEach((fn) => fn())
        assert.equal(e.busy.value, true)
        e.open(record({ id: 12 }))
        assert.equal(e.visible.value, false)
        pending.resolve(
          action === 'save'
            ? {
                code: 200,
                data: {
                  id: 11,
                  project_product: 2,
                  module: 3,
                  config_type: 1,
                  path_config: record().path_config,
                },
              }
            : { code: 200, data: { execution_log_id: 99, status: 1 } }
        )
        await promise
        assert.equal(e.busy.value, false)
        assert.equal(e.visible.value, false)
        assert.equal(e.messages.length, 0)
        e.cleanup()
      }
    )
test('list read failure after saved config or execution is reported independently', async () => {
  const e = fixture({}, async () => false)
  e.open(record())
  await flush()
  await e.save()
  assert.equal(e.saveError.value, false)
  assert.ok(e.messages.some(([, text]) => text.includes('列表读取失败')))
  await e.execute()
  assert.equal(e.executeError.value, false)
  assert.equal(e.visible.value, false)
  e.cleanup()
})
test('environment options failure is local and retryable', async () => {
  let fail = true
  const e = fixture(
    {},
    async () => true,
    async () => {
      if (fail) throw Error('offline')
    }
  )
  e.open(record())
  await flush()
  assert.equal(e.enumError.value, true)
  assert.equal(e.canExecute.value, true)
  fail = false
  await e.loadEnums()
  assert.equal(e.enumError.value, false)
  assert.equal(e.enumLoading.value, false)
  e.cleanup()
})
test('parent preview opening uses only bounded handle and respects sibling mutation/window', () => {
  const opened = [],
    deps = {
      interactionBlocked: vue.ref(true),
      previewRef: vue.ref({ open: (r) => opened.push(r) }),
    },
    onPreview = method('onPreview', deps, path.join(base, 'index.vue'))
  onPreview(record())
  assert.equal(opened.length, 0)
  deps.interactionBlocked.value = false
  onPreview(record())
  assert.equal(opened[0].id, 11)
})
for (const transition of ['context', 'deactivate', 'unmount'])
  test(
    'preview and enum requests cannot repopulate closed context after ' + transition,
    async () => {
      const pending = deferred(),
        enums = deferred(),
        e = fixture(
          { postGrayFeaturePreview: () => pending.promise },
          async () => true,
          () => enums.promise
        )
      e.open(record())
      assert.equal(e.loading.value, true)
      assert.equal(e.enumLoading.value, true)
      if (transition === 'context') {
        e.props.contextKey = 'B'
        e.props.contextKey = 'A'
      } else e.hooks[transition].forEach((fn) => fn())
      pending.resolve(preview())
      enums.reject(Error('old'))
      await flush()
      assert.equal(e.visible.value, false)
      assert.equal(e.loading.value, false)
      assert.equal(e.enumLoading.value, false)
      assert.equal(e.enumError.value, false)
      assert.equal(e.canExecute.value, false)
      assert.equal(e.beforeText.value, '')
      e.cleanup()
    }
  )
test('adding and removing paths invalidates preview and resets on reopening', async () => {
  const e = fixture()
  e.open(record())
  await flush()
  e.addPath()
  assert.equal(e.draft.paths.length, 2)
  assert.equal(e.canExecute.value, false)
  e.removePath(0)
  assert.equal(e.draft.paths.length, 1)
  assert.deepEqual(e.draft.paths[0].path, [])
  e.onVisibleChange(false)
  e.open(record())
  await flush()
  assert.equal(e.draft.paths.length, 1)
  assert.deepEqual(e.draft.paths[0].path, ['example', 'example.enabled'])
  e.cleanup()
})
test('stable parent context getter observes same-tick A-B-A before prop rendering', async () => {
  const context = vue.ref('A'),
    pending = deferred(),
    e = fixture({ postGrayFeaturePreview: () => pending.promise })
  e.props.contextKey = () => context.value
  e.open(record())
  context.value = 'B'
  context.value = 'A'
  assert.equal(e.visible.value, false)
  pending.resolve(preview())
  await flush()
  assert.equal(e.canExecute.value, false)
  assert.equal(e.beforeText.value, '')
  e.cleanup()
})
