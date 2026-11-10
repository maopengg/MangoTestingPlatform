import assert from 'node:assert/strict'
import test from 'node:test'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { setupTemplate, template as row } from './helpers/factory-template-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'
const page = (api = {}) =>
  setupTemplate(
    'index',
    'rows,listLoading,loadError,pagination,templateConditionItems,onSearch,onResetSearch,onNavigationFilterChange,doRefresh,searchEntityOptions,entityLoading,entityError,loadSearchEntities,copyTemplate,switchTemplateStatus,validateTemplate,removeTemplate,templateActions,busyIds,openTemplate,editorRef,navigationCreateRef,openTemplateDetail,loadOptions,optionsError,optionsLoading',
    api
  )
const editor = (api = {}) =>
  setupTemplate(
    'TemplateEditor',
    'open,close,templateForm,editingId,templateVisible,templateSaving,saveTemplate,loadEntities,templateEntityOptions,entityLoading,entityError,onTemplateProjectChange,onTemplateModuleChange,onTemplateEntityChange',
    api
  )
const dispose = (...states) => states.forEach((s) => s.dispose())
test('page and independent editor compile script and template', () => {
  for (const file of ['index.vue', 'components/TemplateEditor.vue']) {
    const filename = path.resolve('src/views/data-factory/template', file),
      { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file })
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename,
        id: file,
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
  }
})
test('search factory isolates state, converts leaf IDs, cleans empty values and preserves zero/multiple', async () => {
  const calls = [],
    s = page({ getDataFactoryTemplate: async (p) => (calls.push(p), { data: [], totalSize: 0 }) }),
    other = page()
  try {
    const set = (key, value) => (s.templateConditionItems.find((i) => i.key === key).value = value)
    set('project_product', [1, 10])
    set('module', 0)
    set('status', [0, 1])
    set('entity', [2, 3])
    set('usage_scope', [1, 2])
    s.pagination.page = 9
    await s.onSearch()
    assert.deepEqual(calls[0], {
      project_product: 10,
      module: 0,
      status__in: '0,1',
      entity__in: '2,3',
      usage_scope__in: '1,2',
      page: 1,
      pageSize: 20,
    })
    assert.deepEqual(other.templateConditionItems.find((i) => i.key === 'entity').value, [])
    await s.onResetSearch()
    assert.deepEqual(calls.at(-1), { page: 1, pageSize: 20 })
  } finally {
    dispose(s, other)
  }
})
test('navigation clears entity and late entity options cannot overwrite new module', async () => {
  const a = deferred(),
    b = deferred()
  let n = 0
  const s = page({ getDataFactoryEntity: () => (++n === 1 ? a.promise : b.promise) })
  try {
    s.templateConditionItems.find((i) => i.key === 'entity').value = [30]
    await s.onNavigationFilterChange({ projectProduct: 10, module: 20 })
    await s.onNavigationFilterChange({ projectProduct: 10, module: 21 })
    b.resolve({ data: [{ id: 2, name: 'New', table_name: 'new' }] })
    await flush()
    a.resolve({ data: [{ id: 1, name: 'Old' }] })
    await flush()
    assert.equal(s.searchEntityOptions.value[0].id, 2)
    assert.deepEqual(s.templateConditionItems.find((i) => i.key === 'entity').value, [])
    assert.equal(s.entityLoading.value, false)
  } finally {
    dispose(s)
  }
})
test('latest list owns data/loading; failed request retains rows and retries', async () => {
  const a = deferred(),
    b = deferred()
  let n = 0
  const s = page({
    getDataFactoryTemplate: () =>
      ++n === 1 ? a.promise : n === 2 ? b.promise : Promise.reject(Error('fixture')),
  })
  try {
    const first = s.doRefresh(),
      second = s.doRefresh()
    a.resolve({ data: [row(1)], totalSize: 1 })
    await first
    assert.equal(s.listLoading.value, true)
    b.resolve({ data: [row(2)], totalSize: 2 })
    await second
    assert.equal(s.rows.value[0].id, 2)
    await s.doRefresh()
    assert.equal(s.loadError.value, true)
    assert.equal(s.listLoading.value, false)
    assert.equal(s.rows.value[0].id, 2)
  } finally {
    dispose(s)
  }
})
test('independent draft preserves deep config on edit and never mutates list record', async () => {
  const s = editor(),
    record = row(1, {
      field_overrides: { x: { generator_type: 1, generator_config: { value: 'original' } } },
      output_config: [{ field: 'id', key: 'out' }],
    })
  try {
    s.open(record)
    await flush()
    s.templateForm.field_overrides.x.generator_config.value = 'draft'
    s.templateForm.output_config[0].key = 'draft'
    assert.equal(record.field_overrides.x.generator_config.value, 'original')
    assert.equal(record.output_config[0].key, 'out')
    s.close()
    s.open(record)
    await flush()
    assert.equal(s.templateForm.output_config[0].key, 'out')
    assert.equal(s.templateForm.field_overrides.x.generator_config.value, 'original')
    s.onTemplateEntityChange()
    assert.deepEqual(s.templateForm.field_overrides, {})
    assert.deepEqual(s.templateForm.output_config, [])
    s.close()
    s.open(undefined, { projectProduct: 0, module: 0 })
    await flush()
    assert.equal(s.editingId.value, null)
    assert.equal(s.templateForm.project_product, 0)
    assert.equal(s.templateForm.module, 0)
  } finally {
    dispose(s)
  }
})
test('save uses whitelist, detached payload and captured ID, rejects duplicate submission', async () => {
  const pending = deferred(),
    calls = [],
    s = editor({ putDataFactoryTemplate: (p) => (calls.push(p), pending.promise) })
  try {
    s.open(row())
    await flush()
    s.templateForm.extra = 'must not leak'
    const saving = s.saveTemplate()
    assert.equal(s.templateSaving.value, true)
    assert.equal(await s.saveTemplate(), false)
    assert.equal(calls.length, 1)
    assert.equal(calls[0].id, 1)
    assert.equal('extra' in calls[0], false)
    pending.resolve({ data: { config_status: 0 }, msg: 'saved' })
    assert.equal(await saving, true)
    assert.equal(s.templateVisible.value, false)
    assert.deepEqual(
      s.events.filter((e) => e[0] === 'saved'),
      [['saved']]
    )
  } finally {
    dispose(s)
  }
})
test('save failure leaves draft for retry; invalid whitespace name never submits', async () => {
  let n = 0
  const s = editor({
    postDataFactoryTemplate: async () => {
      if (++n === 1) throw Error('fixture')
      return { data: { config_status: 1 }, msg: 'ok' }
    },
  })
  try {
    s.open(undefined, { projectProduct: 10, module: 20 })
    await flush()
    s.templateForm.entity = 30
    s.templateForm.name = '  '
    assert.equal(await s.saveTemplate(), false)
    assert.equal(n, 0)
    s.templateForm.name = 'Example'
    assert.equal(await s.saveTemplate(), false)
    assert.equal(s.templateSaving.value, false)
    assert.equal(s.templateForm.name, 'Example')
    assert.equal(await s.saveTemplate(), true)
    assert.equal(n, 2)
  } finally {
    dispose(s)
  }
})
test('close during entity load invalidates responses and reopening uses current module', async () => {
  const pending = deferred(),
    s = editor({ getDataFactoryEntity: () => pending.promise })
  try {
    s.open(row())
    assert.equal(s.entityLoading.value, true)
    s.close()
    pending.resolve({ data: [{ id: 1, name: 'Old' }] })
    await flush()
    assert.deepEqual(s.templateEntityOptions.value, [])
    assert.equal(s.entityLoading.value, false)
  } finally {
    dispose(s)
  }
})
test('scope changes suppress late writes/events and keep physical save lock until finally', async () => {
  const pending = deferred(),
    s = editor({ putDataFactoryTemplate: () => pending.promise })
  try {
    s.open(row())
    await flush()
    const saving = s.saveTemplate()
    s.user.roleId = 2
    assert.equal(s.templateVisible.value, false)
    s.open(row(2))
    assert.equal(s.templateVisible.value, false)
    pending.resolve({ data: { config_status: 1 }, msg: 'stale' })
    assert.equal(await saving, false)
    assert.equal(s.templateSaving.value, false)
    assert.equal(
      s.events.some((e) => e[0] === 'saved'),
      false
    )
    assert.deepEqual(s.notices, [])
    s.open(row(2))
    await flush()
    assert.equal(s.editingId.value, 2)
  } finally {
    dispose(s)
  }
})
test('entity option error releases loading and explicit retry succeeds without erasing saved config', async () => {
  let fail = true
  const s = editor({
    getDataFactoryEntity: async () => {
      if (fail) throw Error('fixture')
      return { data: [{ id: 30, name: 'Entity', table_name: 'example' }] }
    },
  })
  try {
    s.open(row(1, { output_config: [{ field: 'id', key: 'out' }] }))
    await flush()
    assert.equal(s.entityError.value, true)
    assert.equal(s.entityLoading.value, false)
    fail = false
    await s.loadEntities()
    assert.equal(s.entityError.value, false)
    assert.equal(s.templateEntityOptions.value[0].id, 30)
    assert.equal(s.templateForm.output_config[0].key, 'out')
    s.lifecycle.deactivate()
    s.lifecycle.activate()
    await flush()
    assert.equal(s.templateVisible.value, false)
  } finally {
    dispose(s)
  }
})
test('list identity/environment and KeepAlive invalidate stale requests and resume', async () => {
  const pending = deferred()
  let n = 0
  const s = page({
    getDataFactoryTemplate: () =>
      ++n === 1 ? pending.promise : Promise.resolve({ data: [row(n)], totalSize: 1 }),
  })
  try {
    const first = s.doRefresh()
    s.user.selected_environment = 1
    await flush()
    pending.resolve({ data: [row(99)], totalSize: 99 })
    await first
    assert.notEqual(s.rows.value[0].id, 99)
    s.lifecycle.deactivate()
    assert.deepEqual(s.rows.value, [])
    const before = n
    await s.doRefresh()
    assert.equal(n, before)
    s.lifecycle.activate()
    await flush()
    assert.equal(n, before + 1)
  } finally {
    dispose(s)
  }
})
test('copy, validation and status share per-record lock and failures release it', async () => {
  const pending = deferred(),
    calls = [],
    s = page({
      postDataFactoryTemplateCopy: (p) => (calls.push(p), pending.promise),
      putDataFactoryTemplateStatus: async () => {
        throw Error('fixture')
      },
    })
  try {
    const copying = s.copyTemplate(row())
    assert.equal(s.busyIds.has(1), true)
    assert.equal(await s.copyTemplate(row()), false)
    assert.equal(await s.switchTemplateStatus(false, 1), false)
    assert.equal(calls.length, 1)
    pending.reject(Error('fixture'))
    assert.equal(await copying, false)
    assert.equal(s.busyIds.has(1), false)
    assert.equal(await s.validateTemplate(1), false)
    assert.equal(s.busyIds.has(1), false)
  } finally {
    dispose(s)
  }
})
test('controlled status mutates only after server succeeds and preserves failed state', async () => {
  const pending = deferred(),
    s = page({
      putDataFactoryTemplateStatus: () => pending.promise,
      getDataFactoryTemplate: async () => ({ data: [row(1, { status: 0 })], totalSize: 1 }),
    })
  try {
    s.rows.value = [row()]
    const change = s.switchTemplateStatus(false, 1)
    assert.equal(s.rows.value[0].status, 1)
    pending.resolve({ code: 200, msg: 'ok' })
    assert.equal(await change, true)
    assert.equal(s.rows.value[0].status, 0)
  } finally {
    dispose(s)
  }
})
test('delete confirms captured record; failures keep retryable dialog and danger styling', async () => {
  let n = 0
  const ids = [],
    s = page({
      deleteDataFactoryTemplate: async (id) => {
        ids.push(id)
        if (++n === 1) throw Error('fixture')
        return { code: 200, msg: 'ok' }
      },
    })
  try {
    const record = row()
    s.removeTemplate(record)
    const dialog = s.confirmations[0]
    record.id = 9
    assert.equal(dialog.config.okButtonProps.status, 'danger')
    assert.equal(await dialog.config.onBeforeOk(), false)
    assert.equal(await dialog.config.onBeforeOk(), true)
    assert.deepEqual(ids, [1, 1])
    assert.equal(s.templateActions(row()).find((a) => a.label === '删除').danger, true)
  } finally {
    dispose(s)
  }
})
test('identity invalidates confirmation and action completion without stale notifications', async () => {
  const pending = deferred()
  const s = page({ postDataFactoryTemplateCopy: () => pending.promise })
  try {
    s.removeTemplate(row())
    const dialog = s.confirmations[0]
    const copying = s.copyTemplate(row(2))
    s.user.roleId = 3
    await flush()
    assert.equal(dialog.closed, true)
    assert.equal(await dialog.config.onBeforeOk(), false)
    pending.resolve({ code: 200, msg: 'stale' })
    assert.equal(await copying, false)
    assert.deepEqual(s.notices, [])
  } finally {
    dispose(s)
  }
})
test('options failure retries independently; navigation uses original preview route and record', async () => {
  let fail = true
  const s = page({
    getUserName: async () => {
      if (fail) throw Error('fixture')
      return { data: [{ key: 1, title: 'User' }] }
    },
  })
  try {
    await s.loadOptions()
    assert.equal(s.optionsError.value, true)
    assert.equal(s.optionsLoading.value, false)
    fail = false
    await s.loadOptions()
    assert.equal(s.optionsError.value, false)
    await s.openTemplateDetail(row(4))
    assert.deepEqual(s.navigations, [
      { path: '/data-factory/template/preview', query: { template_id: 4 } },
    ])
    assert.equal(s.records[0].id, 4)
    let defaults
    s.editorRef.value = { open: (record, value) => (defaults = value), close() {} }
    s.navigationCreateRef.value = { getCreateDefaults: () => ({ projectProduct: 10, module: 20 }) }
    s.openTemplate()
    assert.deepEqual(defaults, { projectProduct: 10, module: 20 })
  } finally {
    dispose(s)
  }
})
