import assert from 'node:assert/strict'
import test from 'node:test'
import { evaluationComponent, caseEditor, caseRecord } from './helpers/evaluation-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'

test('editor owns a fresh typed configuration and never edits its initial record', async () => {
  const original = caseRecord(),
    s = caseEditor({}, { initialRecord: original })
  try {
    await flush()
    assert.equal(s.ready.value, true)
    s.config.value.mapping.output.paths.push('$.answer')
    assert.deepEqual(original.config.mapping.output.paths, [])
    assert.equal(s.dirty.value, true)
  } finally {
    s.dispose()
  }
})
test('cancel and attempted reopen keep the physical save locked until the old request settles', async () => {
  const pending = deferred()
  let calls = 0
  const s = caseEditor({
    updateEvaluationCase: () => {
      calls++
      return pending.promise
    },
  })
  try {
    await flush()
    s.config.value.execution.retry_count = 1
    const task = s.flushConfiguration()
    await flush()
    assert.equal(s.saving.value, true)
    s.cancel()
    await s.open(2)
    assert.equal(s.saving.value, true)
    assert.equal(s.ready.value, false)
    pending.resolve({ code: 200 })
    assert.equal(await task, false)
    assert.equal(s.saving.value, false)
    assert.equal(s.events.length, 0)
    assert.equal(calls, 1)
  } finally {
    s.dispose()
  }
})
test('concurrent saves serialize new edits as snapshots without duplicate requests', async () => {
  const pending = deferred(),
    payloads = []
  const s = caseEditor({
    updateEvaluationCase: (value) => {
      payloads.push(value)
      return payloads.length === 1 ? pending.promise : Promise.resolve({ code: 200 })
    },
  })
  try {
    await flush()
    s.config.value.execution.retry_count = 1
    const first = s.flushConfiguration()
    await flush()
    s.config.value.execution.retry_count = 2
    const second = s.flushConfiguration()
    assert.equal(payloads.length, 1)
    pending.resolve({ code: 200 })
    assert.equal(await first, true)
    assert.equal(await second, true)
    assert.deepEqual(
      payloads.map((p) => p.config.execution.retry_count),
      [1, 2]
    )
    assert.equal(s.dirty.value, false)
  } finally {
    s.dispose()
  }
})
test('failed save keeps dirty draft and can retry', async () => {
  let fail = true
  const s = caseEditor({
    updateEvaluationCase: async () => {
      if (fail) throw Error('offline')
      return { code: 200 }
    },
  })
  try {
    await flush()
    s.config.value.execution.retry_count = 1
    assert.equal(await s.flushConfiguration(), false)
    assert.equal(s.saving.value, false)
    assert.equal(s.dirty.value, true)
    fail = false
    assert.equal(await s.flushConfiguration(), true)
    assert.equal(s.saveError.value, '')
  } finally {
    s.dispose()
  }
})
test('deactivated and identity-changed editors suppress late saves and read back on activation', async () => {
  const pending = deferred(),
    s = caseEditor({ updateEvaluationCase: () => pending.promise })
  try {
    await flush()
    s.config.value.execution.retry_count = 1
    const task = s.flushConfiguration()
    await flush()
    s.lifecycle.deactivate()
    s.user.roleId = 2
    pending.resolve({ code: 200 })
    assert.equal(await task, false)
    assert.equal(s.events.length, 0)
    s.lifecycle.activate()
    await flush()
    assert.equal(s.ready.value, true)
    assert.equal(s.config.value.execution.retry_count, 0)
  } finally {
    s.dispose()
  }
})
test('dataset, version and AI errors can retry without resetting the configured draft', async () => {
  let fail = true
  const s = caseEditor({
    getEvaluationDatasets: async () => {
      if (fail) throw Error('offline')
      return { data: [{ id: 2, name: 'Recovered' }] }
    },
    getDatasetVersions: async () => {
      if (fail) throw Error('offline')
      return { data: { items: [{ id: 3, status: 'published' }], count: 1 } }
    },
    getEvaluationAiProfiles: async () => {
      if (fail) throw Error('offline')
      return { data: [{ id: 'profile', name: 'Example', enabled: true }] }
    },
  })
  try {
    await flush()
    assert.equal(s.ready.value, true)
    assert.ok(s.datasetsError.value)
    assert.ok(s.versionsError.value)
    assert.ok(s.aiError.value)
    s.config.value.execution.retry_count = 2
    fail = false
    await Promise.all([s.loadDatasets(), s.loadVersions(), s.loadAiProfiles()])
    assert.equal(s.datasetsError.value + s.versionsError.value + s.aiError.value, '')
    assert.equal(s.config.value.execution.retry_count, 2)
    assert.equal(s.aiProfiles.value.length, 1)
  } finally {
    s.dispose()
  }
})
test('cancel invalidates a late option response', async () => {
  const pending = deferred()
  let delayed = false
  const s = caseEditor({
    getEvaluationDatasets: () =>
      delayed ? pending.promise : Promise.resolve({ data: [{ id: 2, name: 'Original' }] }),
  })
  try {
    await flush()
    delayed = true
    const task = s.loadDatasets('new')
    s.cancel()
    pending.resolve({ data: [{ id: 4, name: 'Stale' }] })
    await task
    assert.equal(s.ready.value, false)
    assert.equal(s.loading.value, false)
    assert.equal(
      s.datasets.value.some((row) => row.id === 4),
      false
    )
  } finally {
    s.dispose()
  }
})
test('grader updates emit replacements and leave parent bindings untouched', () => {
  const row = {
    grader_key: 'exact_match',
    grader_version: 1,
    metric_key: 'accuracy',
    threshold: 100,
    weight: 1,
    enabled: true,
    hard_gate: false,
    parameters: {},
  }
  const s = evaluationComponent('GraderEditor', 'update,add,remove,choose', {
    props: { modelValue: [row], catalog: [] },
  })
  try {
    s.update(0, { threshold: 0 })
    assert.equal(row.threshold, 100)
    assert.equal(s.events[0][1][0].threshold, 0)
    s.props.disabled = true
    s.update(0, { weight: 0 })
    s.add()
    s.remove(0)
    s.choose(0, 'other@2')
    assert.equal(s.events.length, 1)
  } finally {
    s.dispose()
  }
})

test('new-case double submission never releases the first request lock', async () => {
  const pending = deferred()
  let calls = 0
  const s = caseEditor(
    {
      createEvaluationCase: () => {
        calls++
        return pending.promise
      },
    },
    { embedded: false, caseId: undefined }
  )
  try {
    await s.open(undefined, [1, 2])
    s.form.name = 'New example'
    const first = s.save()
    await flush()
    assert.equal(s.saving.value, true)
    await s.save()
    assert.equal(calls, 1)
    assert.equal(s.saving.value, true)
    s.cancel()
    pending.resolve({ code: 200 })
    await first
    assert.equal(s.saving.value, false)
    assert.equal(s.events.length, 0)
  } finally {
    s.dispose()
  }
})
test('quality-gate changes emit immutable values including zero thresholds', () => {
  const row = { key: 'valid_rate', operator: 'gte', threshold: 0.8, severity: 'critical' }
  const s = evaluationComponent('QualityGateEditor', 'update,choose', {
    props: { modelValue: [row] },
  })
  try {
    s.update(0, { operator: 'zero', threshold: 0 })
    assert.equal(row.threshold, 0.8)
    assert.equal(s.events[0][1][0].threshold, 0)
    s.choose(0, 'metric:accuracy')
    assert.equal(row.key, 'valid_rate')
    assert.equal(s.events[1][1][0].metric_key, 'accuracy')
    s.props.disabled = true
    s.choose(0, 'valid_rate')
    assert.equal(s.events.length, 2)
  } finally {
    s.dispose()
  }
})
test('parameter edits preserve false and zero, remove empty fields and honor read-only state', () => {
  const original = { threshold: 1, normalize: true }
  const s = evaluationComponent('ParameterForm', 'set', { props: { modelValue: original } })
  try {
    s.set('threshold', 0)
    s.set('normalize', false)
    s.set('threshold', '')
    assert.equal(s.events[0][1].threshold, 0)
    assert.equal(s.events[1][1].normalize, false)
    assert.equal('threshold' in s.events[2][1], false)
    assert.equal(original.threshold, 1)
    s.props.disabled = true
    s.set('threshold', 2)
    assert.equal(s.events.length, 3)
  } finally {
    s.dispose()
  }
})
test('structured parameter fields emit isolated updates and clone reactive schema defaults', () => {
  const original = { nested: { enabled: true } }
  const s = evaluationComponent('DataFieldsEditor', 'set,remove,setAt,removeAt,initial', {
    props: { modelValue: original, schema: { default: { nested: [] } } },
  })
  try {
    s.set('enabled', false)
    assert.equal('enabled' in original, false)
    assert.equal(s.events[0][1].enabled, false)
    const value = s.initial(s.props.schema)
    value.nested.push(1)
    assert.deepEqual(s.props.schema.default.nested, [])
    s.props.modelValue = [1, 2]
    s.setAt(0, 0)
    assert.deepEqual(s.props.modelValue, [1, 2])
    assert.deepEqual(s.events[1][1], [0, 2])
    s.props.disabled = true
    s.remove('nested')
    s.removeAt(0)
    assert.equal(s.events.length, 2)
  } finally {
    s.dispose()
  }
})
test('item selection reads isolate late responses after version changes', async () => {
  const pending = deferred()
  const s = evaluationComponent('ItemSelectionDrawer', 'open,visible,records,loading', {
    props: { versionId: 3, modelValue: { item_ids: [1] }, saveSelection: async () => true },
    api: { getEvaluationDatasetItems: () => pending.promise },
  })
  try {
    s.open()
    assert.equal(s.loading.value, true)
    s.props.versionId = 4
    pending.resolve({ data: { items: [{ id: 9, enabled: true }], count: 1 } })
    await flush()
    assert.equal(s.visible.value, false)
    assert.equal(s.loading.value, false)
    assert.deepEqual(s.records.value, [])
  } finally {
    s.dispose()
  }
})
test('item selection keeps cross-page choices and leaves parent selection unchanged', async () => {
  const original = { exclude: false, item_ids: [8] }
  const s = evaluationComponent('ItemSelectionDrawer', 'open,select,selected,pageChanged', {
    props: { versionId: 3, modelValue: original, saveSelection: async () => true },
    api: {
      getEvaluationDatasetItems: async () => ({
        data: { items: [{ id: 1, enabled: true }], count: 25 },
      }),
    },
  })
  try {
    s.open()
    await flush()
    s.select([1])
    assert.deepEqual(s.selected.value, [8, 1])
    assert.deepEqual(original.item_ids, [8])
    s.pageChanged(2)
    await flush()
    assert.deepEqual(s.selected.value, [8, 1])
  } finally {
    s.dispose()
  }
})
test('item selection save keeps its lock through identity changes and ignores stale completion', async () => {
  const pending = deferred()
  let calls = 0
  const s = evaluationComponent('ItemSelectionDrawer', 'open,save,visible,saving', {
    props: {
      versionId: 3,
      modelValue: { item_ids: [] },
      saveSelection: () => {
        calls++
        return pending.promise
      },
    },
  })
  try {
    s.open()
    await flush()
    const task = s.save()
    s.user.roleId = 2
    s.open()
    assert.equal(s.visible.value, false)
    assert.equal(s.saving.value, true)
    pending.resolve(false)
    assert.equal(await task, false)
    assert.equal(s.saving.value, false)
    assert.equal(s.notices.length, 0)
    assert.equal(calls, 1)
  } finally {
    s.dispose()
  }
})

test('a late initial catalogue refresh survives a slower selected-interface lookup', async () => {
  const pending = deferred(),
    record = caseRecord()
  record.config.target = { type: 'api_info', ref_id: 4, version_ref: null, parameters: {} }
  const s = caseEditor(
    { getEvaluationInterfaces: () => pending.promise },
    { initialRecord: record }
  )
  try {
    await flush()
    s.props.initialCatalog = [{ grader_key: 'fixture', grader_version: 1, name: 'Latest' }]
    await flush()
    pending.resolve({
      data: { items: [{ id: 4, name: 'Example', published: true, protocol_type: 'http' }] },
    })
    await flush()
    assert.equal(s.ready.value, true)
    assert.equal(s.catalog.value[0].name, 'Latest')
  } finally {
    s.dispose()
  }
})

test('metadata edit avoids execution assets and preserves an unsupported configuration', async () => {
  let assetReads = 0
  const writes = [], original = { ...caseRecord(), project_product: 2, module: 3, config: { schema_version: 99, mapping: { output: { template: { legacy: 'preserve' } } } } }
  const asset = async () => { assetReads++; throw Error('must not load configuration assets') }
  const s = caseEditor({ getEvaluationCase: async () => ({ data: original }), getEvaluationAiProfiles: asset, getCaseGraderCatalog: asset, getEvaluationDatasets: asset, getDatasetVersions: asset, updateEvaluationCase: async value => writes.push(value) }, { embedded: false, caseId: undefined })
  try { await s.open(1); assert.equal(s.ready.value, true); s.form.name = 'Renamed'; assert.equal(await s.flushConfiguration(), true); assert.equal(assetReads, 0); assert.deepEqual(writes, [{ id: 1, name: 'Renamed', description: '', project_product: 2, module: 3 }]); assert.equal(original.config.schema_version, 99) } finally { s.dispose() }
})
