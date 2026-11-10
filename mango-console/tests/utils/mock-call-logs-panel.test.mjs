import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { computed, reactive, ref } from 'vue'
import path from 'node:path'
import { harness, deferred, flush } from '../helpers/case-details-harness.mjs'

const root = new URL('../../', import.meta.url)
const panelPath = 'src/views/apitest/mock/components/MockCallLogsPanel.vue'
const panelSource = fs.readFileSync(new URL(panelPath, root), 'utf8')

function createPanel(getMockLogs, extra = {}) {
  let confirmOptions
  const cleared = []
  const panel = harness(
    'MockCallLogsPanel',
    'logs,loadLogs,clearLogs,openLogDetail,exportLogs,listFailed,detailFailed,buildLogQuery,visible',
    {
      base: path.resolve('src/views/apitest/mock'),
      props: { visible: true, mockId: 2, mockKey: 'callback' },
      api: {
        getMockLogs,
        getMockLogDetail: async (id) => ({ data: { id, assertion_results: [] } }),
        getMockAssertionMethods: async () => ({ data: [] }),
        clearMockLogs: async (id) => {
          cleared.push(id)
          return { data: { deleted_count: 1 } }
        },
        ...extra,
      },
      Modal: {
        confirm(options) {
          confirmOptions = options
          return {
            close() {
              options.onClose?.()
            },
          }
        },
      },
    }
  )
  return {
    state: panel,
    props: panel.props,
    cleared,
    opening: flush(),
    change: flush,
    cleanup: panel.close,
    confirm: () => confirmOptions.onBeforeOk(),
  }
}

test('mock list opens the shared panel without navigating to configuration', () => {
  const source = fs.readFileSync(new URL('src/views/apitest/mock/index.vue', root), 'utf8')
  assert.match(source, /label: '调用记录', onClick: \(\) => openLogs\(record\)/)
  assert.match(source, /logsTarget\.value = \{ id: record\.id, mock_key: record\.mock_key \}/)
  assert.doesNotMatch(source, /query: \{ id, logs: 1 \}/)
  for (const path of [
    panelPath,
    'src/views/apitest/mock/index.vue',
    'src/views/apitest/mock/details/index.vue',
  ]) {
    const { descriptor, errors } = parse(fs.readFileSync(new URL(path, root), 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: path })
    const template = compileTemplate({
      source: descriptor.template.content,
      filename: path,
      id: path,
      compilerOptions: { bindingMetadata: script.bindings },
    })
    assert.deepEqual(template.errors, [])
  }
})

test('opening loads the selected mock and changing mock ignores stale responses', async () => {
  const pending = []
  const panel = createPanel((params) => new Promise((resolve) => pending.push({ params, resolve })))
  assert.deepEqual(pending[0].params, { id: 2, page: 1, pageSize: 20 })
  assert.equal(panel.state.logs.loading, true)
  panel.props.mockId = 3
  panel.props.mockKey = 'other-callback'
  const changed = panel.change()
  await flush()
  assert.equal(pending[1].params.id, 3)
  pending[1].resolve({ data: [{ id: 30 }], totalSize: 1 })
  await changed
  pending[0].resolve({ data: [{ id: 20 }], totalSize: 10 })
  await panel.opening
  assert.equal(panel.state.logs.items[0].id, 30)
  assert.equal(panel.state.logs.pagination.pageCount, 1)
  assert.equal(panel.state.logs.loading, false)
  panel.cleanup()
})

test('stale clear confirmation cannot delete after switching the target', async () => {
  const panel = createPanel(async () => ({ data: [{ id: 20 }], totalSize: 1 }))
  await panel.opening
  panel.state.clearLogs()
  panel.props.mockId = 3
  await panel.change()
  await panel.confirm()
  assert.deepEqual(panel.cleared, [])
  assert.equal(panel.state.logs.clearing, false)
  panel.cleanup()
})

test('failed list requests always release loading', async () => {
  const panel = createPanel(async () => {
    throw new Error('test request failure')
  })
  await panel.opening
  assert.equal(panel.state.listFailed.value, true)
  assert.equal(panel.state.logs.loading, false)
  panel.cleanup()
})

test('closing nested details ignores delayed detail and catalog responses', async () => {
  const detail = deferred(),
    panel = createPanel(async () => ({ data: [{ id: 20 }], totalSize: 1 }), {
      getMockLogDetail: () => detail.promise,
    })
  await panel.opening
  const task = panel.state.openLogDetail({ id: 20 })
  panel.state.logs.detailVisible = false
  detail.resolve({ data: { id: 20, request_data: { body: false } } })
  await task
  assert.equal(panel.state.logs.selected, null)
  assert.equal(panel.state.logs.detailLoading, false)
  panel.cleanup()
})
test('failed clear keeps confirmation retryable and freezes original ID', async () => {
  let fail = true
  const calls = [],
    panel = createPanel(async () => ({ data: [{ id: 20 }], totalSize: 1 }), {
      clearMockLogs: async (id) => {
        calls.push(id)
        if (fail) throw Error('delete')
        return { data: { deleted_count: 1 } }
      },
    })
  await panel.opening
  panel.state.clearLogs()
  assert.equal(await panel.confirm(), false)
  assert.equal(panel.state.logs.clearing, false)
  fail = false
  assert.equal(await panel.confirm(), true)
  assert.deepEqual(calls, [2, 2])
  panel.cleanup()
})
test('export rejects duplicates and suppresses late download after closing', async () => {
  const pending = deferred()
  let calls = 0
  const panel = createPanel(async () => ({ data: [{ id: 20 }], totalSize: 1 }), {
    exportMockLogs: () => {
      calls++
      return pending.promise
    },
  })
  await panel.opening
  const task = panel.state.exportLogs()
  await panel.state.exportLogs()
  assert.equal(calls, 1)
  panel.state.visible.value = false
  pending.resolve({ data: new Blob(['csv']), headers: {} })
  await task
  assert.equal(panel.state.logs.exporting, false)
  panel.cleanup()
})
test('query keeps false-like assertion filter and omits empty fields', async () => {
  const panel = createPanel(async () => ({ data: [], totalSize: 0 }))
  await panel.opening
  panel.state.logs.filters.assertion_passed = 0
  assert.deepEqual(panel.state.buildLogQuery(), { id: 2, assertion_passed: 0 })
  panel.cleanup()
})
