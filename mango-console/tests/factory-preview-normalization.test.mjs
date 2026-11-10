import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { setupTemplate } from './helpers/factory-template-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { setupPreview } from './helpers/factory-preview-harness.mjs'
const record = (id = 1, extra = {}) => ({
  id,
  name: `Example ${id}`,
  project_product: { id: 10 },
  module: { id: 20 },
  entity: { id: 30 },
  status: 0,
  field_overrides: {},
  output_config: [],
  items: [],
  post_insert_updates: [],
  cleanup_resources: [],
  ...extra,
})
const item = (key, extra = {}) => ({
  id: null,
  _key: key,
  child_template: 2,
  name: key,
  sort: 0,
  field_overrides: {},
  ...extra,
})
const page = (api = {}) =>
  setupPreview(
    'index',
    'templateForm,resetTemplateForm,reloadPageData,templateLoading,templateError,loadPreview,previewResult,previewLoading,previewError,loadEditableFieldDefinitions,fieldsError,fieldRows,fieldLoading,editableFieldsReady,firstPreviewReady,loadSceneTemplateOptions,sceneTemplateOptions,sceneOptionsFailed,sceneOptionsLoading,autoSaveSceneItems,sceneAutoSaveStatus,sceneAutoSaving,saving,saveTemplateConfig,hasUnsavedFieldConfig,snapshotFieldConfig,sceneSavedItemOverrides,reorderSceneItems,removeSceneItem,updateSceneItemOverrides,debugRun,debugRef,syncTemplateFields,confirmSyncTemplateFields,syncLoading,openCleanupResources,cleanupResourceVisible,saveCleanupResources,cleanupResourceSaving,writeBusy,loadEnums,enumError,enumLoading,postUpdateNodes,updatePostUpdates,loadTemplateFields',
    api
  )
const debug = (api = {}) =>
  setupPreview('DebugResultDialog', 'run,close,visible,result,running,cleanup,cleanupLoading', api)
const post = (props) =>
  setupPreview(
    'PostUpdatesDialog',
    'draft,publish,addPostInsertUpdate,removePostInsertUpdate,getPostUpdateValidation,getPostUpdateTargetFieldOptions',
    {},
    props
  )

test('all workspace windows compile and do not reference accidental identifiers', () => {
  for (const file of [
    'index.vue',
    'components/DebugResultDialog.vue',
    'components/PostUpdatesDialog.vue',
  ]) {
    const filename = path.resolve('src/views/data-factory/template/preview', file),
      { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file }),
      compiled = compileTemplate({
        source: descriptor.template.content,
        filename,
        id: file,
        compilerOptions: { bindingMetadata: script.bindings },
      })
    assert.deepEqual(compiled.errors, [])
    assert.doesNotMatch(compiled.code, /_ctx\.mango\b/)
  }
})
test('draft deeply isolates configuration and preserves disabled/zero values', () => {
  const s = page(),
    original = record(1, {
      cleanup_strategy: 0,
      field_overrides: { id: { generator_type: 1, generator_config: { value: 0 } } },
      items: [
        item('a', {
          field_overrides: { x: { generator_type: 1, generator_config: { value: false } } },
        }),
      ],
    })
  try {
    s.resetTemplateForm(original)
    assert.equal(s.templateForm.status, 0)
    assert.equal(s.templateForm.cleanup_strategy, 0)
    s.templateForm.field_overrides.id.generator_config.value = 99
    s.templateForm.items[0].field_overrides.x.generator_config.value = true
    assert.equal(original.field_overrides.id.generator_config.value, 0)
    assert.equal(original.items[0].field_overrides.x.generator_config.value, false)
    assert.equal(
      s.load('form.ts').createDraft(record(0, { entity: 0, project_product: 0 })).entity,
      0
    )
  } finally {
    s.dispose()
  }
})
test('latest template wins; failed load releases loading and remains retryable', async () => {
  const a = deferred(),
    b = deferred()
  let n = 0
  const s = page({
    getDataFactoryTemplate: () =>
      ++n === 1 ? a.promise : n === 2 ? b.promise : Promise.reject(Error('fixture')),
  })
  try {
    const first = s.reloadPageData()
    s.route.query.template_id = '2'
    await flush()
    b.resolve({ data: [record(2)] })
    await flush()
    a.resolve({ data: [record(1)] })
    await first
    await flush()
    assert.equal(s.templateForm.id, 2)
    assert.equal(s.templateLoading.value, false)
    await s.reloadPageData()
    assert.equal(s.templateError.value, true)
    assert.equal(s.templateLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('field and preview failures release masks and retry independently', async () => {
  let fail = true
  const s = page({
    getDataFactoryField: async () => {
      if (fail) throw Error('fixture')
      return { data: [{ name: 'id' }] }
    },
    postDataFactoryTemplatePreview: async () => {
      if (fail) throw Error('fixture')
      return { data: { preview_mode: 'configuration' } }
    },
  })
  try {
    s.resetTemplateForm(record())
    await s.loadEditableFieldDefinitions()
    await s.loadPreview()
    assert.equal(s.fieldsError.value, true)
    assert.equal(s.previewError.value, true)
    assert.equal(s.fieldLoading.value, false)
    assert.equal(s.previewLoading.value, false)
    assert.equal(s.editableFieldsReady.value, true)
    assert.equal(s.firstPreviewReady.value, true)
    fail = false
    await s.loadEditableFieldDefinitions()
    await s.loadPreview()
    assert.equal(s.fieldsError.value, false)
    assert.equal(s.previewError.value, false)
  } finally {
    s.dispose()
  }
})
test('preview discards an obsolete input snapshot and refreshes current draft', async () => {
  const pending = deferred(),
    calls = [],
    s = page({
      postDataFactoryTemplatePreview: (p) => {
        calls.push(p)
        return calls.length === 1
          ? pending.promise
          : Promise.resolve({ data: { preview_mode: 'latest' } })
      },
    })
  try {
    s.resetTemplateForm(record())
    const first = s.loadPreview()
    s.templateForm.output_config = [{ field: 'id', key: 'new' }]
    pending.resolve({ data: { preview_mode: 'stale' } })
    await first
    await flush()
    assert.equal(calls.length, 2)
    assert.equal(s.previewResult.value.preview_mode, 'latest')
  } finally {
    s.dispose()
  }
})
test('arrangement serializes writes and preserves newer names/additions while merging captured IDs', async () => {
  const a = deferred(),
    b = deferred(),
    calls = [],
    s = page({
      putDataFactoryTemplate: (p) => (calls.push(p), calls.length === 1 ? a.promise : b.promise),
    })
  try {
    s.resetTemplateForm(record(1, { items: [item('a')] }))
    const first = s.autoSaveSceneItems()
    s.templateForm.items[0].name = 'new name'
    s.templateForm.items.push(item('b'))
    const second = s.autoSaveSceneItems()
    assert.equal(calls.length, 1)
    a.resolve({ data: { items: [{ ...calls[0].items[0], id: 10 }] } })
    await flush()
    assert.equal(calls.length, 2)
    assert.equal(calls[1].items[0].id, 10)
    assert.equal(calls[1].items[0].name, 'new name')
    b.resolve({ data: { items: calls[1].items.map((v, i) => ({ ...v, id: 10 + i })) } })
    await first
    await second
    assert.deepEqual(
      s.templateForm.items.map((v) => v.name),
      ['new name', 'b']
    )
    assert.equal(s.sceneAutoSaveStatus.value, 'saved')
    assert.equal(s.sceneAutoSaving.value, false)
  } finally {
    s.dispose()
  }
})
test('reordering pending entries cannot assign another entry server ID', async () => {
  const pending = deferred(),
    calls = [],
    s = page({
      putDataFactoryTemplate: (p) => {
        calls.push(p)
        return calls.length === 1 ? pending.promise : Promise.resolve({ data: { items: p.items } })
      },
    })
  try {
    s.resetTemplateForm(record(1, { items: [item('a'), item('b')] }))
    const first = s.autoSaveSceneItems()
    s.reorderSceneItems([s.templateForm.items[1], s.templateForm.items[0]])
    pending.resolve({
      data: {
        items: [
          { ...calls[0].items[0], id: 10 },
          { ...calls[0].items[1], id: 11 },
        ],
      },
    })
    await first
    assert.deepEqual(
      s.templateForm.items.map((v) => v.id),
      [11, 10]
    )
  } finally {
    s.dispose()
  }
})
test('autosave never persists dirty fields; errors release locks and retain explicit retry', async () => {
  let fail = true
  const calls = [],
    s = page({
      putDataFactoryTemplate: async (p) => {
        calls.push(p)
        if (fail) throw Error('fixture')
        return { data: { items: p.items } }
      },
    })
  try {
    s.resetTemplateForm(
      record(1, {
        items: [
          item('a', {
            id: 9,
            field_overrides: { id: { generator_type: 1, generator_config: { value: 'saved' } } },
          }),
        ],
      })
    )
    s.templateForm.items[0].field_overrides.id.generator_config.value = 'draft'
    assert.equal(await s.autoSaveSceneItems(), false)
    assert.equal(s.sceneAutoSaveStatus.value, 'error')
    assert.equal(s.sceneAutoSaving.value, false)
    fail = false
    await s.autoSaveSceneItems()
    assert.equal(calls.at(-1).items[0].field_overrides.id.generator_config.value, 'saved')
    assert.equal(s.templateForm.items[0].field_overrides.id.generator_config.value, 'draft')
    assert.equal(s.hasUnsavedFieldConfig(), true)
  } finally {
    s.dispose()
  }
})
test('manual save captures whitelist and blocks competing writes; later edits remain dirty', async () => {
  const pending = deferred(),
    calls = [],
    s = page({ putDataFactoryTemplate: (p) => (calls.push(p), pending.promise) })
  try {
    s.resetTemplateForm(record())
    s.templateForm.field_overrides = {
      id: { generator_type: 1, generator_config: { value: 'sent' } },
    }
    s.templateForm.extra = 'not saved'
    const saving = s.saveTemplateConfig()
    assert.equal(await s.saveTemplateConfig(), false)
    assert.equal(await s.syncTemplateFields(), false)
    s.templateForm.field_overrides.id.generator_config.value = 'later'
    pending.resolve({ msg: 'saved', data: { config_status: 1, items: [] } })
    assert.equal(await saving, true)
    assert.equal(calls[0].field_overrides.id.generator_config.value, 'sent')
    assert.equal('extra' in calls[0], false)
    assert.equal(s.templateForm.field_overrides.id.generator_config.value, 'later')
    assert.equal(s.hasUnsavedFieldConfig(), true)
  } finally {
    s.dispose()
  }
})
test('identity invalidates late writes but physical lock remains until finally', async () => {
  const pending = deferred(),
    s = page({
      putDataFactoryTemplate: () => pending.promise,
      getDataFactoryTemplate: async () => ({ data: [record(1)] }),
    })
  try {
    s.resetTemplateForm(record())
    const saving = s.saveTemplateConfig()
    s.user.roleId = 2
    await flush()
    assert.equal(s.saving.value, true)
    assert.equal(await s.saveTemplateConfig(), false)
    pending.resolve({ msg: 'stale', data: { items: [] } })
    assert.equal(await saving, false)
    assert.deepEqual(s.notices, [])
  } finally {
    s.dispose()
  }
})
test('ES drawer validates JSON array, retains failed draft and blocks repeated save', async () => {
  let fail = true
  const calls = [],
    pending = deferred(),
    s = page({
      putDataFactoryTemplate: (p) => {
        calls.push(p)
        return fail ? Promise.reject(Error('fixture')) : pending.promise
      },
    })
  try {
    s.resetTemplateForm(record())
    s.openCleanupResources()
    assert.equal(await s.saveCleanupResources('{}'), false)
    assert.equal(calls.length, 0)
    assert.equal(await s.saveCleanupResources('[]'), false)
    assert.equal(s.cleanupResourceVisible.value, true)
    fail = false
    const saving = s.saveCleanupResources('[]')
    assert.equal(await s.saveCleanupResources('[]'), false)
    pending.resolve({ data: { cleanup_resources: [] } })
    assert.equal(await saving, true)
    assert.equal(s.cleanupResourceVisible.value, false)
    assert.equal(calls.at(-1).id, 1)
  } finally {
    s.dispose()
  }
})
test('debug rejects dirty config and keeps explicit environment zero', async () => {
  const calls = [],
    s = page()
  try {
    s.resetTemplateForm(record())
    s.debugRef.value = { run: async (...args) => (calls.push(args), true), close() {} }
    await s.debugRun()
    assert.equal(calls[0][2], 0)
    s.templateForm.output_config = [{ field: 'id', key: 'draft' }]
    assert.equal(await s.debugRun(), false)
    assert.equal(calls.length, 1)
  } finally {
    s.dispose()
  }
})
test('debug result and cleanup capture IDs, prevent overlap and recover from failure', async () => {
  const pending = deferred(),
    calls = [],
    s = debug({
      postDataFactoryTemplateDebugRun: (p) => (calls.push(p), pending.promise),
      postDataFactoryTemplateDebugCleanup: async () => {
        throw Error('fixture')
      },
    })
  try {
    const running = s.run(1, {}, 0)
    assert.equal(await s.run(2, {}, 3), false)
    pending.resolve({ data: { execution_id: 10 } })
    assert.equal(await running, true)
    assert.equal(s.visible.value, true)
    assert.equal(calls[0].test_env, 0)
    assert.equal(await s.cleanup(), false)
    assert.equal(s.cleanupLoading.value, false)
    assert.equal(s.result.value.execution_id, 10)
  } finally {
    s.dispose()
  }
})
test('debug old result cannot reopen after template switch', async () => {
  const pending = deferred(),
    s = debug({ postDataFactoryTemplateDebugRun: () => pending.promise })
  try {
    const running = s.run(1, {}, 0)
    s.route.query.template_id = '2'
    pending.resolve({ data: { execution_id: 10 } })
    assert.equal(await running, false)
    assert.equal(s.visible.value, false)
    assert.equal(s.running.value, false)
  } finally {
    s.dispose()
  }
})
test('post-update editor publishes detached rules and validates safe target fields', () => {
  const props = {
      modelValue: [
        {
          target_node: 'root',
          target_field: 'link',
          source_node: 'item:1',
          source_field: 'id',
          sort: 0,
        },
      ],
      nodes: [
        {
          value: 'root',
          label: 'Root',
          fields: [{ name: 'link', nullable: true, platform_type: 'integer', generator_type: 0 }],
          overrides: {},
        },
        {
          value: 'item:1',
          label: 'Child',
          fields: [{ name: 'id', primary_key: true, platform_type: 'integer', generator_type: 1 }],
          overrides: {},
        },
      ],
      checks: [],
      disabled: false,
      loading: false,
    },
    s = post(props)
  try {
    assert.equal(s.getPostUpdateValidation(s.draft.value[0], 0).type, 'info')
    assert.deepEqual(
      s.getPostUpdateTargetFieldOptions('root').map((v) => v.value),
      ['link']
    )
    s.draft.value[0].sort = 20
    s.publish()
    assert.equal(props.modelValue[0].sort, 0)
    assert.equal(s.events.at(-1)[1][0].sort, 20)
    s.props.disabled = true
    const n = s.events.length
    s.removePostInsertUpdate(0)
    assert.equal(s.events.length, n)
  } finally {
    s.dispose()
  }
})
test('failed manual save preserves draft and releases the physical lock for retry', async () => {
  let fail = true
  const s = page({
    putDataFactoryTemplate: async (p) => {
      if (fail) throw Error('fixture')
      return { msg: 'ok', data: { items: p.items } }
    },
  })
  try {
    s.resetTemplateForm(record())
    s.templateForm.output_config = [{ field: 'id', key: 'out' }]
    assert.equal(await s.saveTemplateConfig(), false)
    assert.equal(s.saving.value, false)
    assert.equal(s.hasUnsavedFieldConfig(), true)
    fail = false
    assert.equal(await s.saveTemplateConfig(), true)
    assert.equal(s.hasUnsavedFieldConfig(), false)
  } finally {
    s.dispose()
  }
})
test('cache deactivation blocks reads and old callbacks; activation reloads current template', async () => {
  const pending = deferred()
  let n = 0
  const s = page({
    getDataFactoryTemplate: () =>
      ++n === 1 ? pending.promise : Promise.resolve({ data: [record()] }),
  })
  try {
    const first = s.reloadPageData()
    s.lifecycle.deactivate()
    pending.resolve({ data: [record(99)] })
    await first
    assert.equal(s.templateForm.id, null)
    await s.reloadPageData()
    assert.equal(n, 1)
    s.lifecycle.activate()
    await flush()
    assert.equal(n, 2)
    assert.equal(s.templateForm.id, 1)
  } finally {
    s.dispose()
  }
})
test('same-route transition guards unsaved fields and pending arrangement writes', () => {
  const originalWindow = globalThis.window,
    s = page()
  try {
    let approved = false
    globalThis.window = { confirm: () => approved }
    s.resetTemplateForm(record())
    s.templateForm.output_config = [{ field: 'id', key: 'draft' }]
    assert.equal(s.lifecycle.leave(), false)
    assert.equal(s.lifecycle.update({ query: { template_id: '2' } }), false)
    approved = true
    assert.equal(s.lifecycle.update({ query: { template_id: '2' } }), true)
  } finally {
    globalThis.window = originalWindow
    s.dispose()
  }
})
test('sync confirmation is tied to the template and only resolves after server success', async () => {
  const pending = deferred(),
    calls = [],
    s = page({ postDataFactoryTemplateSyncFields: (p) => (calls.push(p), pending.promise) })
  try {
    s.resetTemplateForm(record())
    s.confirmSyncTemplateFields()
    const confirm = s.confirmations[0]
    const syncing = confirm.config.onBeforeOk()
    assert.equal(s.syncLoading.value, true)
    assert.equal(calls[0].test_env, 0)
    pending.reject(Error('fixture'))
    assert.equal(await syncing, false)
    assert.equal(s.syncLoading.value, false)
    s.user.roleId = 3
    await flush()
    assert.equal(confirm.closed, true)
    assert.equal(await confirm.config.onBeforeOk(), false)
  } finally {
    s.dispose()
  }
})
test('environment switch preserves environment-independent draft and rejects obsolete sync result', async () => {
  const pending = deferred(),
    s = page({ postDataFactoryTemplateSyncFields: () => pending.promise })
  try {
    s.resetTemplateForm(record())
    s.templateForm.output_config = [{ field: 'id', key: 'draft' }]
    const syncing = s.syncTemplateFields()
    delete s.route.query.test_env
    s.user.selected_environment = 3
    pending.resolve({
      msg: 'old',
      data: { field_overrides: { old: { generator_type: 1, generator_config: { value: 1 } } } },
    })
    assert.equal(await syncing, false)
    assert.equal(s.templateForm.output_config[0].key, 'draft')
    assert.deepEqual(s.templateForm.field_overrides, {})
    assert.equal(s.syncLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('post-update target, type and backend validation errors remain visible', () => {
  const rule = {
      target_node: 'root',
      target_field: 'link',
      source_node: 'item:1',
      source_field: 'id',
      sort: 0,
    },
    props = {
      modelValue: [rule],
      nodes: [
        {
          value: 'root',
          label: 'Root',
          fields: [{ name: 'link', nullable: false, platform_type: 'text', generator_type: 0 }],
          overrides: {},
        },
        {
          value: 'item:1',
          label: 'Child',
          fields: [{ name: 'id', platform_type: 'integer' }],
          overrides: {},
        },
      ],
      checks: [],
      disabled: false,
      loading: false,
    },
    s = post(props)
  try {
    assert.match(s.getPostUpdateValidation(rule, 0).message, /目标字段/)
    s.props.nodes[0].fields[0].nullable = true
    assert.match(s.getPostUpdateValidation(rule, 0).message, /字段类型/)
    s.props.nodes[0].fields[0].platform_type = 'integer'
    s.props.checks = [{ valid: false, message: 'fixture rejection' }]
    assert.equal(s.getPostUpdateValidation(rule, 0).message, 'fixture rejection')
    assert.equal(s.getPostUpdateValidation({ ...rule, target_field: '' }, 0).type, 'warning')
  } finally {
    s.dispose()
  }
})
const filename = path.resolve(
  'src/views/data-factory/template/preview/components/EntityRulesDialog.vue'
)
const rules = (api = {}) =>
  setupTemplate(
    'EntityRulesDialog',
    'open,close,visible,entityRuleLoading,loadError,entityRuleRecord,entityRuleRows,loadRules',
    api,
    {},
    filename
  )

test('independent rules dialog compiles', () => {
  const { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
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
})
test('rules opens before results and loads only the captured entity', async () => {
  const pending = deferred(),
    calls = [],
    s = rules({
      getDataFactoryEntity: async (p) => (calls.push(p), { data: [{ id: 0, name: 'Zero' }] }),
      getDataFactoryField: (p) => (calls.push(p), pending.promise),
    })
  try {
    s.open(0)
    assert.equal(s.visible.value, true)
    assert.equal(s.entityRuleLoading.value, true)
    pending.resolve({ data: [{ name: 'example', generator_type: 1 }] })
    await flush()
    assert.equal(s.entityRuleRecord.value.id, 0)
    assert.equal(s.entityRuleRows.value[0].name, 'example')
    assert.equal(s.entityRuleLoading.value, false)
    assert.deepEqual(calls, [{ id: 0, page: 1, pageSize: 1 }, { entity: 0 }])
  } finally {
    s.dispose()
  }
})
test('latest entity owns data and loading', async () => {
  const a = deferred(),
    b = deferred()
  let n = 0
  const s = rules({
    getDataFactoryEntity: () => (++n === 1 ? a.promise : b.promise),
    getDataFactoryField: async () => ({ data: [] }),
  })
  try {
    s.open(1)
    s.open(2)
    a.resolve({ data: [{ id: 1 }] })
    await flush()
    assert.equal(s.entityRuleLoading.value, true)
    b.resolve({ data: [{ id: 2 }] })
    await flush()
    assert.equal(s.entityRuleRecord.value.id, 2)
    assert.equal(s.entityRuleLoading.value, false)
  } finally {
    s.dispose()
  }
})
test('failed rules retains open dialog with explicit retry', async () => {
  let fail = true
  const s = rules({
    getDataFactoryField: async () => {
      if (fail) throw Error('fixture')
      return { data: [{ name: 'example' }] }
    },
  })
  try {
    s.open(1)
    await flush()
    assert.equal(s.loadError.value, true)
    assert.equal(s.entityRuleLoading.value, false)
    fail = false
    await s.loadRules()
    assert.equal(s.loadError.value, false)
    assert.equal(s.entityRuleRows.value[0].name, 'example')
  } finally {
    s.dispose()
  }
})
test('close and route query changes discard in-flight results', async () => {
  const a = deferred(),
    s = rules({ getDataFactoryField: () => a.promise })
  try {
    s.open(1)
    s.route.query.template_id = '2'
    assert.equal(s.visible.value, false)
    a.resolve({ data: [{ name: 'stale' }] })
    await flush()
    assert.deepEqual(s.entityRuleRows.value, [])
    s.open(2)
    await flush()
    s.close()
    assert.equal(s.entityRuleRecord.value, null)
    assert.deepEqual(s.entityRuleRows.value, [])
  } finally {
    s.dispose()
  }
})
test('identity and cached page deactivate close dialog without automatic reopening', async () => {
  const s = rules()
  try {
    s.open(1)
    await flush()
    s.user.roleId = 3
    assert.equal(s.visible.value, false)
    s.open(2)
    s.lifecycle.deactivate()
    s.open(3)
    assert.equal(s.visible.value, false)
    s.lifecycle.activate()
    await flush()
    assert.equal(s.visible.value, false)
  } finally {
    s.dispose()
  }
})
