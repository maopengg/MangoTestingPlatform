import assert from 'node:assert/strict'
import path from 'node:path'
import test from 'node:test'
import { evaluationComponent } from './helpers/evaluation-harness.mjs'
import { deferred, flush } from './helpers/case-details-harness.mjs'

const row = (grader_key = 'contains', grader_version = 1) => ({ grader_key, grader_version, name: grader_key, category: 'deterministic' })
const grader = (api = {}) => evaluationComponent('index', 'filters,rows,loading,loadError,reload:load,onSearch,reset,pagination,displayedRows,show,visible,selectedGrader,detail,detailError,detailLoading', {
  filename: path.resolve('src/views/evaluation/grader/index.vue'),
  api: { getGraderCatalog: async () => ({ data: { items: [row()] } }), getGrader: async (key, version) => ({ data: row(key, version) }), ...api },
})

test('catalog query cleans empty values and reset restores fresh multi-select state', async () => {
  const queries = []
  const s = grader({ getGraderCatalog: async query => { queries.push(query); return { data: { items: [] } } } })
  try {
    await flush()
    assert.deepEqual(queries[0], {})
    Object.assign(s.filters, { search: 'memory', categories: ['algorithm', 'model'] })
    s.pagination.page = 4
    await s.onSearch()
    assert.equal(s.pagination.page, 1)
    assert.deepEqual(queries.at(-1), { search: 'memory', category__in: 'algorithm,model' })
    const previous = s.filters.categories
    await s.reset()
    assert.deepEqual(queries.at(-1), {})
    assert.deepEqual(s.filters.categories, [])
    assert.notEqual(s.filters.categories, previous)
  } finally { s.dispose() }
})

test('pagination stays local, preserves a valid page on reload and clamps a changed page size', async () => {
  let count = 25, reads = 0
  const s = grader({ getGraderCatalog: async () => { reads++; return { data: { items: Array.from({ length: count }, (_, index) => row(`rule_${index}`)) } } } })
  try {
    await flush()
    s.pagination.page = 2
    s.pagination.onChange()
    assert.equal(s.displayedRows.value.length, 5)
    assert.equal(reads, 1)
    await s.reload()
    assert.equal(s.pagination.page, 2)
    s.pagination.pageSize = 50
    s.pagination.onChange()
    assert.equal(s.pagination.page, 1)
    assert.equal(s.displayedRows.value.length, 25)
    count = 0
    await s.reload()
    assert.equal(s.pagination.pageCount, 0)
    assert.equal(s.pagination.page, 1)
  } finally { s.dispose() }
})

test('latest catalog response wins and old completions cannot release a newer loading state', async () => {
  const first = deferred(), second = deferred()
  let calls = 0
  const s = grader({ getGraderCatalog: () => ++calls === 1 ? first.promise : second.promise })
  try {
    s.filters.search = 'new'
    const task = s.onSearch()
    first.resolve({ data: { items: [row('obsolete')] } })
    await flush()
    assert.equal(s.loading.value, true)
    assert.deepEqual(s.rows.value, [])
    second.resolve({ data: { items: [row('current')] } })
    assert.equal(await task, true)
    assert.equal(s.rows.value[0].grader_key, 'current')
    assert.equal(s.loading.value, false)
  } finally { s.dispose() }
})

test('catalog errors preserve readable rows and support local retry', async () => {
  let fail = false
  const s = grader({ getGraderCatalog: async () => { if (fail) throw Error('offline'); return { data: { items: [row()] } } } })
  try {
    await flush()
    fail = true
    assert.equal(await s.reload(), false)
    assert.equal(s.rows.value.length, 1)
    assert.equal(s.loadError.value, true)
    assert.equal(s.loading.value, false)
    fail = false
    assert.equal(await s.reload(), true)
    assert.equal(s.loadError.value, false)
  } finally { s.dispose() }
})

test('closing a detail invalidates late responses and clears its record and loading state', async () => {
  const pending = deferred()
  const s = grader({ getGrader: () => pending.promise })
  try {
    await flush()
    const task = s.show(row())
    assert.equal(s.visible.value, true)
    assert.equal(s.detailLoading.value, true)
    s.visible.value = false
    pending.resolve({ data: row() })
    assert.equal(await task, false)
    assert.equal(s.detail.value, null)
    assert.equal(s.selectedGrader.value, null)
    assert.equal(s.detailLoading.value, false)
  } finally { s.dispose() }
})

test('detail switching captures the key and version and rejects superseded results', async () => {
  const first = deferred(), second = deferred(), reads = []
  const s = grader({ getGrader: (key, version) => { reads.push([key, version]); return key === 'first' ? first.promise : second.promise } })
  try {
    await flush()
    const selected = row('first', 1)
    const obsolete = s.show(selected)
    selected.grader_key = 'changed'; selected.grader_version = 100
    assert.deepEqual(s.selectedGrader.value, { grader_key: 'first', grader_version: 1 })
    const current = s.show(row('second', 2))
    first.resolve({ data: row('first', 1) })
    assert.equal(await obsolete, false)
    assert.equal(s.detailLoading.value, true)
    assert.equal(s.detail.value, null)
    second.resolve({ data: row('second', 2) })
    assert.equal(await current, true)
    assert.equal(s.detail.value.grader_key, 'second')
    assert.deepEqual(reads, [['first', 1], ['second', 2]])
  } finally { s.dispose() }
})

test('detail failure remains retryable without blocking the independently loaded list', async () => {
  let fail = true
  const s = grader({ getGrader: async () => { if (fail) throw Error('rejected'); return { data: row() } } })
  try {
    await flush()
    assert.equal(await s.show(row()), false)
    assert.equal(s.detailError.value, true)
    assert.equal(s.detailLoading.value, false)
    assert.equal(s.loading.value, false)
    assert.equal(s.rows.value.length, 1)
    fail = false
    assert.equal(await s.show(s.selectedGrader.value), true)
    assert.equal(s.detailError.value, false)
    assert.equal(s.detail.value.name, 'contains')
  } finally { s.dispose() }
})

for (const change of ['identity', 'environment', 'route', 'deactivate']) {
  test(`${change} closes detail and suppresses the old response`, async () => {
    const pending = deferred()
    const s = grader({ getGrader: () => pending.promise })
    try {
      await flush()
      s.filters.search = 'old'
      s.filters.categories = ['model']
      const task = s.show(row())
      if (change === 'identity') s.user.roleId++
      if (change === 'environment') s.user.selected_environment++
      if (change === 'route') s.route.path = '/other'
      if (change === 'deactivate') s.lifecycle.deactivate()
      assert.equal(s.visible.value, false)
      assert.equal(s.detailLoading.value, false)
      pending.resolve({ data: row() })
      assert.equal(await task, false)
      assert.equal(s.detail.value, null)
      assert.deepEqual(s.filters.categories, change === 'identity' ? [] : ['model'])
      if (change === 'route' || change === 'deactivate') assert.deepEqual(s.rows.value, [])
    } finally { s.dispose() }
  })
}

test('cached activation reads again while preserving search intent and the local page', async () => {
  let reads = 0
  const queries = []
  const s = grader({ getGraderCatalog: async query => { reads++; queries.push(query); return { data: { items: Array.from({ length: 25 }, (_, i) => row(`r${i}`)) } } } })
  try {
    await flush()
    s.filters.search = 'rule'; s.pagination.page = 2
    s.lifecycle.deactivate()
    s.lifecycle.activate()
    await flush()
    assert.equal(reads, 2)
    assert.equal(queries.at(-1).search, 'rule')
    assert.equal(s.pagination.page, 2)
    assert.equal(s.displayedRows.value.length, 5)
  } finally { s.dispose() }
})

test('invalid detail identities do not request a definition or show a fabricated record', async () => {
  let calls = 0
  const s = grader({ getGrader: async () => { calls++; return { data: row() } } })
  try {
    await flush()
    assert.equal(await s.show(row('', 1)), false)
    assert.equal(await s.show(row('contains', 0)), false)
    assert.equal(await s.show(row('contains', 1.5)), false)
    assert.equal(calls, 0)
    assert.equal(s.detail.value, null)
    assert.equal(s.visible.value, false)
  } finally { s.dispose() }
})

test('typed parameter rows retain nested paths, defaults and independent required fields', () => {
  const s = grader()
  try {
    const { schemaRows } = s.load('components/presentation.ts')
    const rows = schemaRows({ required: ['limit'], properties: {
      limit: { type: 'integer', minimum: 0, default: 0 },
      options: { type: 'array', items: { required: ['enabled'], properties: { enabled: { type: 'boolean', default: false } } } },
      choice: { anyOf: [{ type: 'string' }, { type: 'null' }] },
    } })
    assert.match(rows.find(row => row.path === 'limit').description, /最小 0.*默认：0/)
    assert.equal(rows.find(row => row.path === 'limit').required, true)
    assert.equal(rows.find(row => row.path === 'options').required, false)
    assert.equal(rows.find(row => row.path === 'options[].enabled').required, true)
    assert.match(rows.find(row => row.path === 'options[].enabled').description, /默认：否/)
    assert.equal(rows.find(row => row.path === 'choice').type, '多种类型')
  } finally { s.dispose() }
})

test('guide changes are local and unsupported versions do not reuse a current example', async () => {
  let calls = 0
  const detail = { ...row('memory_qa', 2), category: 'model', parameters_schema: {} }
  const s = evaluationComponent('GraderDetail', 'guide,exampleIndex,example,activeTab,fields,requirements', {
    filename: path.resolve('src/views/evaluation/grader/GraderDetail.vue'), props: { detail },
    api: { getGrader: async () => { calls++ }, getGraderCatalog: async () => { calls++ } },
  })
  try {
    s.exampleIndex.value = 3
    await flush()
    assert.equal(s.example.value.score, null)
    assert.match(s.fields.value.find(field => field.label === '原文证据').value, /广州/)
    s.props.detail.grader_version = 1
    await flush()
    assert.equal(s.activeTab.value, 'configuration')
    assert.equal(s.exampleIndex.value, 0)
    assert.equal(s.guide.value, undefined)
    assert.equal(s.example.value, undefined)
    assert.equal(calls, 0)
  } finally { s.dispose() }
})
