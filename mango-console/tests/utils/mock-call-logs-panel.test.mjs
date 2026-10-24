import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { computed, reactive, ref } from 'vue'
import ts from 'typescript'

const root = new URL('../../', import.meta.url)
const panelPath = 'src/views/apitest/mock/components/MockCallLogsPanel.vue'
const panelSource = fs.readFileSync(new URL(panelPath, root), 'utf8')

function createPanel(getMockLogs) {
  const { descriptor } = parse(panelSource)
  const source = descriptor.scriptSetup.content.replace(/^\s*import .*$/gm, '')
  const code = ts.transpileModule(source, {
    compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.None },
  }).outputText
  const props = { visible: true, mockId: 2, mockKey: 'callback' }
  let changed
  let cleanup
  let opening
  let confirmOptions
  const cleared = []
  const api = {
    getMockLogs,
    getMockLogDetail: async (id) => ({ data: { id, assertion_results: [] } }),
    getMockAssertionMethods: async () => ({ data: [] }),
    clearMockLogs: async (id) => { cleared.push(id); return { data: { deleted_count: 1 } } },
    exportMockLogs: async () => {},
  }
  const injections = {
    computed, reactive, ref, ...api,
    watch: (_sources, callback) => { changed = callback; opening = callback([props.visible]) },
    onBeforeUnmount: (callback) => { cleanup = callback },
    defineProps: () => props,
    defineEmits: () => (_event, value) => { props.visible = value },
    Message: { success() {}, error() {} },
    Modal: { confirm(options) { confirmOptions = options } },
  }
  const setup = new Function(...Object.keys(injections), code + '\nreturn { logs, loadLogs, clearLogs, openLogDetail }')
  const state = setup(...Object.values(injections))
  return {
    state, props, opening, cleared,
    change: () => changed([props.visible]),
    cleanup: () => cleanup(),
    confirm: () => confirmOptions.onOk(),
  }
}

test('mock list opens the shared panel without navigating to configuration', () => {
  const source = fs.readFileSync(new URL('src/views/apitest/mock/index.vue', root), 'utf8')
  assert.match(source, /label: '调用记录', onClick: \(\) => openLogs\(record\)/)
  assert.match(source, /logsTarget\.value = \{ id: record\.id, mock_key: record\.mock_key \}/)
  assert.doesNotMatch(source, /query: \{ id, logs: 1 \}/)
  for (const path of [panelPath, 'src/views/apitest/mock/index.vue', 'src/views/apitest/mock/details/index.vue']) {
    const { descriptor, errors } = parse(fs.readFileSync(new URL(path, root), 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: path })
    const template = compileTemplate({ source: descriptor.template.content, filename: path, id: path,
      compilerOptions: { bindingMetadata: script.bindings } })
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

test('clear confirmation keeps its original mock identity after selection changes', async () => {
  const panel = createPanel(async () => ({ data: [{ id: 20 }], totalSize: 1 }))
  await panel.opening
  panel.state.clearLogs()
  panel.props.mockId = 3
  await panel.change()
  await panel.confirm()
  assert.deepEqual(panel.cleared, [2])
  assert.equal(panel.state.logs.clearing, false)
  panel.cleanup()
})

test('failed list requests always release loading', async () => {
  const panel = createPanel(async () => { throw new Error('test request failure') })
  await assert.rejects(panel.opening, /test request failure/)
  assert.equal(panel.state.logs.loading, false)
  panel.cleanup()
})
