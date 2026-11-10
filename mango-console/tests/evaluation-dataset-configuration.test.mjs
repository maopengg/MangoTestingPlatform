import assert from 'node:assert/strict'
import test from 'node:test'
import { evaluationComponent } from './helpers/evaluation-harness.mjs'
import { deferred } from './helpers/case-details-harness.mjs'

const version = (id = 8, status = 'draft') => ({
  id, status, schema_snapshot: { input_schema: { properties: { query: { title: '问题' } } } },
})
const drawer = (api = {}) => evaluationComponent('DatasetConfigDrawer',
  'open,closeDrawer:close,save,preview,visible,version,config,sample,previewResult,previewing,saving,error,previewError,inputFieldOptions,readonly', { api })

test('configuration drafts and preview input are isolated from their original records', () => {
  const s = drawer(), original = version(), sample = { query: { text: 'before' } }
  try {
    s.open(original, sample)
    s.config.value.input_schema.properties.query.title = 'Changed'
    s.sample.value.query.text = 'changed'
    assert.equal(original.schema_snapshot.input_schema.properties.query.title, '问题')
    assert.equal(sample.query.text, 'before')
    s.open(version(9))
    assert.deepEqual(s.config.value.input_variables, [{ name: 'case_input', path: '$' }])
  } finally { s.dispose() }
})

test('closing or changing configuration invalidates in-flight previews without stale loading', async () => {
  const first = deferred(), second = deferred()
  let calls = 0
  const s = drawer({ previewDatasetInputs: () => (++calls === 1 ? first.promise : second.promise) })
  try {
    s.open(version(), { query: 'example' })
    const pending = s.preview()
    await s.preview()
    assert.equal(calls, 1)
    s.config.value.input_variables[0].path = '$.query'
    assert.equal(s.previewing.value, false)
    const newer = s.preview()
    first.resolve({ data: { obsolete: true } })
    await pending
    assert.equal(s.previewResult.value, undefined)
    assert.equal(s.previewing.value, true)
    s.visible.value = false
    second.resolve({ data: { obsolete: true } })
    await newer
    assert.equal(s.previewResult.value, undefined)
    assert.equal(s.previewing.value, false)
  } finally { s.dispose() }
})

test('preview load failure leaves no inline error and retry accepts falsy input and results', async () => {
  let calls = 0
  const s = drawer({ previewDatasetInputs: async (_id, payload) => {
    assert.equal(payload.input_data, false)
    if (++calls === 1) throw Error('offline')
    return { data: false }
  } })
  try {
    s.open(version(), false)
    await s.preview()
    assert.equal(s.previewError.value, '')
    assert.equal(s.previewing.value, false)
    await s.preview()
    assert.equal(s.previewError.value, '')
    assert.equal(s.previewResult.value, false)
  } finally { s.dispose() }
})

test('save failure retains the draft and retry submits only the schema snapshot', async () => {
  const writes = []
  const s = drawer({ updateDatasetVersion: async (id, payload) => {
    writes.push({ id, payload })
    if (writes.length === 1) throw Error('offline')
    return { data: { ...version(id), ...payload } }
  } })
  try {
    s.open(version())
    s.config.value.input_variables[0].name = 'question'
    assert.equal(await s.save(), false)
    assert.ok(s.error.value)
    assert.equal(s.visible.value, true)
    assert.equal(s.saving.value, false)
    assert.equal(s.config.value.input_variables[0].name, 'question')
    assert.equal(await s.save(), true)
    assert.deepEqual(Object.keys(writes[1].payload), ['schema_snapshot'])
    assert.equal(writes[1].payload.schema_snapshot.workflow.preparation, 'none')
    assert.equal(s.visible.value, false)
    assert.equal(s.events.length, 1)
  } finally { s.dispose() }
})

for (const context of ['close', 'identity', 'deactivate']) {
  test(`${context} suppresses stale saves while retaining the physical duplicate lock`, async () => {
    const pending = deferred()
    let calls = 0
    const s = drawer({ updateDatasetVersion: () => { calls++; return pending.promise } })
    try {
      s.open(version())
      const task = s.save()
      if (context === 'close') s.visible.value = false
      if (context === 'identity') s.user.roleId++
      if (context === 'deactivate') s.lifecycle.deactivate()
      s.open(version(9))
      assert.equal(await s.save(), false)
      assert.equal(s.visible.value, false)
      assert.equal(s.saving.value, true)
      pending.resolve({ data: version() })
      assert.equal(await task, false)
      assert.equal(s.saving.value, false)
      assert.equal(s.events.length, 0)
      assert.equal(s.notices.length, 0)
      assert.equal(calls, 1)
      s.open(version(9))
      assert.equal(s.version.value.id, 9)
    } finally { s.dispose() }
  })
}

test('published configuration stays readable and cannot be saved', async () => {
  let calls = 0
  const s = drawer({ updateDatasetVersion: async () => { calls++ } })
  try {
    s.open(version(9, 'published'), { 'a.b': { child: 0 } })
    assert.equal(s.readonly.value, true)
    assert.ok(s.inputFieldOptions.value.some(item => item.value === '$["a.b"].child'))
    assert.equal(await s.save(), false)
    assert.equal(calls, 0)
  } finally { s.dispose() }
})

test('schema edits emit new values and removing a field also removes its required entry', () => {
  const original = { type: 'object', properties: { name: { type: 'string' } }, required: ['name'] }
  const s = evaluationComponent('SchemaEditor', 'update,remove,requireField,replace,newKey,add', { props: { modelValue: original } })
  try {
    s.update('name', { title: 'Name' })
    assert.equal(original.properties.name.title, undefined)
    assert.equal(s.events[0][1].properties.name.title, 'Name')
    s.remove('name')
    assert.deepEqual(s.events[1][1].properties, {})
    assert.deepEqual(s.events[1][1].required, [])
    assert.deepEqual(original.required, ['name'])
    s.replace('name', false)
    assert.equal(s.events.length, 2)
    assert.equal(s.notices.at(-1), '字段约束必须为对象')
  } finally { s.dispose() }
})

for (const flag of ['readonly', 'disabled']) {
  test(`schema ${flag} prevents all mutation methods`, () => {
    const s = evaluationComponent('SchemaEditor', 'update,remove,requireField,replace,newKey,add', { props: {
      modelValue: { properties: { name: { type: 'string' } } }, [flag]: true,
    } })
    try {
      s.newKey.value = 'other'
      s.add()
      s.update('name', { title: 'Name' })
      s.remove('name')
      s.requireField('name', true)
      assert.equal(s.events.length, 0)
      assert.equal(s.newKey.value, 'other')
    } finally { s.dispose() }
  })
}

test('scenario reordering checks boundaries and emits isolated arrays', () => {
  const original = { group_key: 'session', order: 0, turns: [
    { name: 'first', input_data: false, expected_output: {}, context: {}, score: true },
    { name: 'second', input_data: 0, expected_output: {}, context: {}, score: true },
  ] }
  const s = evaluationComponent('ScenarioEditor', 'move,setTurn,remove,addTurn,update', { props: { modelValue: original, sequence: 'timeline' } })
  try {
    s.move(0)
    s.move(2)
    s.remove(-1)
    s.setTurn(5, { name: 'invalid' })
    assert.equal(s.events.length, 0)
    s.move(1)
    assert.deepEqual(s.events[0][1].turns.map(turn => turn.name), ['second', 'first'])
    assert.deepEqual(original.turns.map(turn => turn.name), ['first', 'second'])
    s.setTurn(0, { input_data: 0 })
    assert.equal(s.events[1][1].turns[0].input_data, 0)
    assert.equal(original.turns[0].input_data, false)
    s.props.disabled = true
    s.update({ order: 5 })
    s.addTurn()
    s.setTurn(0, { score: false })
    s.remove(0)
    s.move(1)
    assert.equal(s.events.length, 2)
  } finally { s.dispose() }
})
