import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush, method } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/gray/feature')
const record = (extra = {}) => ({
  id: 11,
  project_product: { id: 2, name: 'Example product' },
  module: { id: 3 },
  gray_code: 'example',
  name: 'Example feature',
  config_type: 1,
  feature_key: 'example.enabled',
  yaml_file: { id: 4, name: 'Example YAML' },
  datasource_alias: null,
  enable_sql: null,
  disable_sql: null,
  restore_sql: null,
  enable_code: null,
  disable_code: null,
  restore_code: null,
  default_restore: false,
  status: 0,
  description: null,
  ...extra,
})
const sql = () =>
  record({
    config_type: 2,
    yaml_file: null,
    datasource_alias: { id: 9, name: 'Example SQL', db_type: 0 },
    enable_sql: 'SELECT 1',
    disable_sql: 'SELECT 2',
    restore_sql: 'SELECT 3',
  })
const code = () =>
  record({
    config_type: 3,
    yaml_file: null,
    enable_code: 'def gray(context):\n    return 1',
    disable_code: 'def gray(context):\n    return 2',
    restore_code: 'def gray(context):\n    return 3',
  })
function editor(api = {}, enumApi) {
  const hooks = { deactivate: [], activate: [], unmount: [] },
    calls = [],
    messages = []
  const f = harness(
    'FeatureEditor',
    [
      'open,save,onVisibleChange,onProductChange,visible,saving,saveError,recordId,form',
      'yamlOptions,aliasOptions,yamlLoading,yamlError,aliasesLoading,aliasesError,enumLoading,enumError',
      'loadYaml,loadAliases,loadEnums',
    ].join(','),
    {
      base,
      props: { contextKey: 'one', blocked: false },
      api: {
        getGrayYamlFile: async () => ({
          code: 200,
          data: [
            {
              id: 4,
              name: 'Example YAML',
              project_product: { id: 2, name: 'Product', project: { id: 1, name: 'Project' } },
            },
          ],
        }),
        getDataFactoryDatasourceAlias: async (p) => ({
          code: 200,
          data: [
            { id: 9, name: 'Example SQL', db_type: 0, project_product: { id: p.project_product } },
          ],
        }),
        putGrayFeature: async (p) => {
          calls.push(p)
          return { code: 200, data: p }
        },
        postGrayFeature: async (p) => {
          calls.push(p)
          return { code: 200, data: { ...p, id: 12 } }
        },
        ...api,
      },
      modules: {
        vue: {
          ...vue,
          onDeactivated: (fn) => hooks.deactivate.push(fn),
          onActivated: (fn) => hooks.activate.push(fn),
          onBeforeUnmount: (fn) => hooks.unmount.push(fn),
        },
        '@/store/modules/get-enum': {
          useEnum: () => ({
            data_source_type: [{ key: 0, title: 'MySQL' }],
            getEnum: enumApi || (async () => {}),
          }),
        },
        '@arco-design/web-vue': {
          Message: {
            warning: (value) => messages.push(value),
            success: (value) => messages.push(value),
          },
        },
      },
    }
  )
  return {
    ...f,
    hooks,
    calls,
    messages,
    cleanup() {
      hooks.unmount.forEach((fn) => fn())
      f.close()
    },
  }
}

test('edit owns a finite draft, keeps status/default_restore false and does not mutate source', () => {
  const e = editor(),
    source = record()
  e.open(source)
  e.form.name = 'Changed'
  assert.equal(source.name, 'Example feature')
  assert.equal(e.form.project_product, 2)
  assert.equal(e.form.module, 3)
  assert.equal(e.form.status, 0)
  assert.equal(e.form.default_restore, false)
  e.cleanup()
})
test('create synchronously captures navigation leaf IDs and resets old values on reopen', () => {
  const e = editor()
  e.open(sql())
  e.onVisibleChange(false)
  e.open(undefined, { projectProduct: [1, '2'], module: [1, 2, '3'] })
  assert.equal(e.visible.value, true)
  assert.equal(e.recordId.value, null)
  assert.equal(e.form.project_product, 2)
  assert.equal(e.form.module, 3)
  assert.equal(e.form.config_type, 1)
  assert.equal(e.form.enable_sql, '')
  assert.equal(e.form.default_restore, true)
  e.cleanup()
})
test('same-product component echo preserves edited module and alias; real change clears dependent fields', async () => {
  const e = editor()
  e.open(sql())
  await flush()
  e.onProductChange('2')
  assert.equal(e.form.module, 3)
  assert.equal(e.form.datasource_alias, 9)
  e.onProductChange(7)
  assert.equal(e.form.module, null)
  assert.equal(e.form.datasource_alias, null)
  await flush()
  assert.equal(e.form.project_product, 7)
  e.cleanup()
})
test('YAML white-list payload preserves flags and omits audit, path configuration and nested records', async () => {
  const e = editor()
  e.open(
    record({
      path_config: [{ path: 'feature.enabled' }],
      create_time: 'Readonly',
      last_update_user: 99,
      database: { id: 88 },
    })
  )
  e.form.project_product = [1, '2']
  e.form.module = [1, 2, '3']
  await e.save()
  assert.deepEqual(e.calls, [
    {
      id: 11,
      project_product: 2,
      module: 3,
      gray_code: 'example',
      name: 'Example feature',
      config_type: 1,
      feature_key: 'example.enabled',
      yaml_file: 4,
      datasource_alias: null,
      database: null,
      enable_sql: null,
      disable_sql: null,
      restore_sql: null,
      enable_code: null,
      disable_code: null,
      restore_code: null,
      default_restore: false,
      status: 0,
      description: '',
    },
  ])
  assert.equal(e.visible.value, false)
  assert.deepEqual(
    e.events.filter(([event]) => event === 'saved'),
    [['saved', 11]]
  )
  e.cleanup()
})
for (const [kind, factory] of [
  ['SQL', sql],
  ['code', code],
])
  test(`${kind} retains separate enable/disable/restore values and clears unrelated type fields`, async () => {
    const e = editor(),
      source = factory()
    e.open(source)
    await e.save()
    const p = e.calls[0],
      suffix = kind === 'SQL' ? 'sql' : 'code'
    for (const action of ['enable', 'disable', 'restore'])
      assert.equal(p[`${action}_${suffix}`], source[`${action}_${suffix}`])
    assert.equal(p.yaml_file, null)
    assert.equal(p[suffix === 'sql' ? 'enable_code' : 'enable_sql'], null)
    assert.equal(p[suffix === 'sql' ? 'disable_code' : 'disable_sql'], null)
    e.cleanup()
  })
test('switching types changes only relevant submitted fields and preserves in-progress text drafts', async () => {
  const e = editor()
  e.open(sql())
  e.form.config_type = 1
  e.form.yaml_file = 4
  const { payload } = e.load('editor-form.ts')
  assert.equal(payload(e.form, 11).disable_sql, null)
  e.form.config_type = 2
  assert.equal(payload(e.form, 11).disable_sql, 'SELECT 2')
  assert.equal(e.form.restore_sql, 'SELECT 3')
  e.cleanup()
})
for (const [factory, field, invalid] of [
  [record, 'project_product', null],
  [record, 'module', null],
  [record, 'name', ' '],
  [record, 'gray_code', ' '],
  [record, 'feature_key', ' '],
  [record, 'config_type', 7],
  [record, 'yaml_file', null],
  [sql, 'datasource_alias', null],
  [sql, 'enable_sql', ''],
  [sql, 'disable_sql', ''],
  [sql, 'restore_sql', ''],
  [code, 'enable_code', ''],
  [code, 'disable_code', ''],
  [code, 'restore_code', ''],
])
  test(`required ${field} is validated for type ${factory().config_type}`, async () => {
    const e = editor()
    e.open(factory())
    e.form[field] = invalid
    await e.save()
    assert.equal(e.calls.length, 0)
    assert.equal(e.visible.value, true)
    assert.equal(e.messages.length, 1)
    e.cleanup()
  })
test('physical save lock prevents repeated saves, close, retargeting and payload changes', async () => {
  const pending = deferred(),
    calls = []
  const e = editor({
    putGrayFeature: (p) => {
      calls.push(p)
      return pending.promise
    },
  })
  e.open(sql())
  const work = e.save()
  e.form.name = 'Changed later'
  e.onVisibleChange(false)
  e.open(record())
  await e.save()
  assert.equal(calls.length, 1)
  assert.equal(calls[0].name, 'Example feature')
  assert.equal(calls[0].disable_sql, 'SELECT 2')
  assert.equal(e.visible.value, true)
  pending.resolve({ code: 200, data: calls[0] })
  await work
  assert.equal(e.saving.value, false)
  assert.equal(e.visible.value, false)
  e.cleanup()
})
test('save failure preserves input and allows an explicit retry', async () => {
  let fail = true
  const e = editor({
    putGrayFeature: async (p) => {
      if (fail) throw Error('Network')
      return { code: 200, data: p }
    },
  })
  e.open(code())
  await e.save()
  assert.equal(e.saveError.value, true)
  assert.equal(e.form.disable_code, code().disable_code)
  assert.equal(e.saving.value, false)
  fail = false
  await e.save()
  assert.equal(e.visible.value, false)
  e.cleanup()
})
for (const [field, value] of [
  ['id', 99],
  ['project_product', 99],
  ['module', 99],
  ['config_type', 3],
  ['status', 1],
])
  test(`save rejects a mismatched ${field} acknowledgment`, async () => {
    const e = editor({
      putGrayFeature: async (p) => ({ code: 200, data: { ...p, [field]: value } }),
    })
    e.open(record())
    await e.save()
    assert.equal(e.saveError.value, true)
    assert.equal(e.visible.value, true)
    assert.equal(
      e.events.some(([event]) => event === 'saved'),
      false
    )
    e.cleanup()
  })
test('negative save envelope does not apply valid-looking data', async () => {
  const e = editor({ putGrayFeature: async (p) => ({ code: 400, data: p }) })
  e.open(record())
  await e.save()
  assert.equal(e.saveError.value, true)
  e.cleanup()
})
test('external write guard blocks opening and saving without erasing an existing draft', async () => {
  const e = editor()
  e.props.blocked = true
  e.open(record())
  assert.equal(e.visible.value, false)
  e.props.blocked = false
  e.open(record())
  e.props.blocked = true
  await e.save()
  assert.equal(e.calls.length, 0)
  assert.equal(e.form.name, 'Example feature')
  e.cleanup()
})
test('context A-B-A force-closes logical editor but keeps physical save lock until the request ends', async () => {
  const pending = deferred()
  let body
  const e = editor({
    putGrayFeature: (p) => {
      body = p
      return pending.promise
    },
  })
  e.open(record())
  const work = e.save()
  e.props.contextKey = 'two'
  e.props.contextKey = 'one'
  assert.equal(e.visible.value, false)
  assert.equal(e.saving.value, true)
  e.open(record())
  assert.equal(e.visible.value, false)
  pending.resolve({ code: 200, data: body })
  await work
  assert.equal(
    e.events.some(([event]) => event === 'saved'),
    false
  )
  assert.equal(e.saving.value, false)
  e.cleanup()
})
for (const hook of ['deactivate', 'unmount'])
  test(`${hook} discards late save acknowledgments and prevents premature unlocking`, async () => {
    const pending = deferred()
    let body
    const e = editor({
      putGrayFeature: (p) => {
        body = p
        return pending.promise
      },
    })
    e.open(record())
    const work = e.save()
    e.hooks[hook].forEach((fn) => fn())
    e.hooks.activate.forEach((fn) => fn())
    e.open(record())
    assert.equal(e.visible.value, false)
    assert.equal(e.saving.value, true)
    pending.resolve({ code: 200, data: body })
    await work
    assert.equal(
      e.events.some(([event]) => event === 'saved'),
      false
    )
    if (hook === 'deactivate') {
      e.open(record())
      assert.equal(e.visible.value, true)
    }
    e.cleanup()
  })
test('YAML and datasource/enum options load independently and retain saved-name fallbacks', async () => {
  const pending = deferred(),
    enums = deferred()
  const e = editor({ getGrayYamlFile: () => pending.promise }, () => enums.promise)
  e.open(record())
  await flush()
  assert.equal(e.yamlLoading.value, true)
  assert.equal(e.aliasesLoading.value, false)
  assert.equal(e.enumLoading.value, true)
  assert.deepEqual(e.yamlOptions.value, [{ value: 4, label: 'Example YAML' }])
  pending.resolve({ code: 200, data: [] })
  enums.resolve()
  await flush()
  assert.equal(e.yamlLoading.value, false)
  assert.equal(e.enumLoading.value, false)
  assert.equal(e.form.yaml_file, 4)
  e.cleanup()
})
test('YAML option failure and retry keep the selected record and its name', async () => {
  let fail = true
  const e = editor({
    getGrayYamlFile: async () => {
      if (fail) throw Error('Network')
      return { code: 200, data: [] }
    },
  })
  e.open(record())
  await flush()
  assert.equal(e.yamlError.value, true)
  assert.equal(e.yamlOptions.value[0].label, 'Example YAML')
  fail = false
  await e.loadYaml()
  assert.equal(e.yamlError.value, false)
  assert.equal(e.form.yaml_file, 4)
  e.cleanup()
})
test('datasource option failure and retry preserve selected SQL alias and type zero', async () => {
  let fail = true
  const e = editor({
    getDataFactoryDatasourceAlias: async (p) => {
      if (fail) throw Error('Network')
      return {
        code: 200,
        data: [{ id: 9, name: 'Example SQL', db_type: 0, project_product: p.project_product }],
      }
    },
  })
  e.open(sql())
  await flush()
  assert.equal(e.aliasesError.value, true)
  assert.equal(e.aliasOptions.value[0].label, 'Example SQL / MySQL')
  fail = false
  await e.loadAliases()
  assert.equal(e.aliasesError.value, false)
  assert.equal(e.form.datasource_alias, 9)
  e.cleanup()
})
test('datasource option response checks product ownership and filters non-SQL types', async () => {
  let wrong = true
  const e = editor({
    getDataFactoryDatasourceAlias: async (p) => ({
      code: 200,
      data: [
        { id: 9, name: 'Example SQL', db_type: 0, project_product: wrong ? 7 : p.project_product },
        { id: 10, name: 'Example Redis', db_type: 3, project_product: p.project_product },
      ],
    }),
  })
  e.open(sql())
  await flush()
  assert.equal(e.aliasesError.value, true)
  wrong = false
  await e.loadAliases()
  assert.equal(e.aliasesError.value, false)
  assert.deepEqual(e.aliasOptions.value, [{ value: 9, label: 'Example SQL / MySQL', db_type: 0 }])
  e.cleanup()
})
test('product switch rejects old datasource options and does not end the new loading state', async () => {
  const first = deferred(),
    second = deferred()
  const e = editor({
    getDataFactoryDatasourceAlias: (p) =>
      p.project_product === 2 ? first.promise : second.promise,
  })
  e.open(sql())
  e.onProductChange(7)
  first.resolve({ code: 200, data: [{ id: 9, name: 'Old', db_type: 0, project_product: 2 }] })
  await flush()
  assert.equal(e.aliasesLoading.value, true)
  assert.deepEqual(e.aliasOptions.value, [])
  second.resolve({ code: 200, data: [{ id: 10, name: 'New', db_type: 0, project_product: 7 }] })
  await flush()
  assert.equal(e.aliasOptions.value[0].value, 10)
  e.cleanup()
})
test('closing/reopening invalidates pending YAML options and an old failure does not mark the new editor', async () => {
  const old = deferred()
  let calls = 0
  const e = editor({
    getGrayYamlFile: () => (++calls === 1 ? old.promise : Promise.resolve({ code: 200, data: [] })),
  })
  e.open(record())
  e.onVisibleChange(false)
  e.open(undefined)
  old.reject(Error('Old'))
  await flush()
  assert.equal(e.yamlError.value, false)
  assert.equal(e.yamlLoading.value, false)
  assert.deepEqual(e.yamlOptions.value, [])
  e.cleanup()
})
test('parent create hands off navigation defaults synchronously and respects active preview or writes', () => {
  const opened = [],
    deps = {
      editorSaving: vue.ref(false),
      editorVisible: vue.ref(false),
      actionLoading: vue.ref(''),
      previewVisible: vue.ref(false),
      previewBusy: vue.ref(false),
      navigationCreateRef: vue.ref({ getCreateDefaults: () => ({ projectProduct: 2, module: 3 }) }),
      editorRef: vue.ref({ open: (...args) => opened.push(args) }),
    }
  const onAdd = method('onAdd', deps, path.join(base, 'index.vue'))
  onAdd()
  assert.deepEqual(opened, [[undefined, { projectProduct: 2, module: 3 }]])
  deps.previewVisible.value = true
  onAdd()
  deps.previewVisible.value = false
  deps.editorSaving.value = true
  onAdd()
  assert.equal(opened.length, 1)
})
test('stable context getter detects parent A-B-A without a prop identity change', async () => {
  const context = vue.ref('A'),
    pending = deferred()
  let body
  const e = editor({
    putGrayFeature: (p) => {
      body = p
      return pending.promise
    },
  })
  e.props.contextKey = () => context.value
  e.open(record())
  const work = e.save()
  context.value = 'B'
  context.value = 'A'
  assert.equal(e.visible.value, false)
  assert.equal(e.saving.value, true)
  pending.resolve({ code: 200, data: body })
  await work
  assert.equal(
    e.events.some(([event]) => event === 'saved'),
    false
  )
  assert.equal(e.saving.value, false)
  e.cleanup()
})
test('parent and editor scripts, templates and styles compile', () => {
  for (const relative of [
    'index.vue',
    'components/FeatureEditor.vue',
    'components/FeaturePreviewDrawer.vue',
  ]) {
    const filename = path.join(base, relative),
      { descriptor, errors } = parse(readFileSync(filename, 'utf8'), { filename })
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
