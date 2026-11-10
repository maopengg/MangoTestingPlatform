import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush } from '../helpers/case-details-harness.mjs'
import { setup, row, ok } from '../helpers/system-jobs-harness.mjs'

test('system jobs exposes text filters and multi-select trigger/status filters', t => {
  const h = setup(); t.after(h.close); const items = h.conditionItems
  assert.deepEqual(items.map(item => item.key), ['key', 'name', 'description', 'cron', 'source_type', 'latest_status', 'latest_error_message'])
  for (const item of items.filter(item => item.type === 'select')) {
    assert.equal(item.multiple, true)
    assert.equal(item.searchOperator, 'in')
    assert.deepEqual(item.value, [])
  }
  assert.ok(items.find(item => item.key === 'latest_status').optionItems.some(item => item.value === 'untriggered'))
})

test('system jobs search compiles with global search and reset actions', () => {
  const filename = 'src/views/timing/system-jobs/index.vue', source = readFileSync(filename, 'utf8')
  const { descriptor, errors } = parse(source, { filename })
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'system-job-search' })
  const template = compileTemplate({ source: descriptor.template.content, filename,
    id: 'system-job-search', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
  assert.match(source, /@search="onSearch" @reset-search="onResetSearch"/)
  assert.match(source, /:multiple="item.multiple"/)
  assert.match(source, /:max-tag-count="1"/)
})

test('search resets pagination, trims conditions, ignores stale responses, resets all fields and retains good data on failure', async t => {
  const requests = [], h = setup({ read(params) { const request = deferred(); requests.push({ params, ...request }); return request.promise } }); t.after(h.close)
  h.mount(); await flush(); requests[0].resolve(ok([], 0)); await flush()
  h.conditionItems.find(item => item.key === 'name').value = ' 清理 '
  h.pagination.page = 3; const first = h.onSearch(); await flush()
  assert.equal(h.pagination.page, 1)
  assert.deepEqual(requests[1].params, { name: '清理', page: 1, pageSize: 20 })
  h.conditionItems.find(item => item.key === 'key').value = 'clean_sql'
  h.conditionItems.find(item => item.key === 'source_type').value = [2, 4]
  h.conditionItems.find(item => item.key === 'latest_status').value = [0, 4, 'untriggered']
  const second = h.onSearch(); await flush()
  assert.equal(requests[2].params.source_type__in, '2,4')
  assert.equal(requests[2].params.latest_status__in, '0,4,untriggered')
  requests[1].resolve(ok([row({ key: 'stale' })])); await first
  assert.deepEqual(h.rows.value, []); assert.equal(h.listLoading.value, true)
  requests[2].resolve(ok([row({ key: 'clean_sql' })])); await second
  assert.equal(h.rows.value[0].key, 'clean_sql'); assert.equal(h.listLoading.value, false)
  h.pagination.page = 4; const reset = h.onResetSearch(); await flush()
  assert.ok(h.conditionItems.every(item => item.multiple ? Array.isArray(item.value) && item.value.length === 0 : item.value === ''))
  assert.deepEqual(requests[3].params, { page: 1, pageSize: 20 })
  requests[3].reject(new Error('example request failure')); await reset
  assert.equal(h.rows.value[0].key, 'clean_sql'); assert.equal(h.pagination.pageCount, 1)
  assert.match(h.listError.value, /重试/); assert.equal(h.listLoading.value, false)
})
