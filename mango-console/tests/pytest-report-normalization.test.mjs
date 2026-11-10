import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'
import { harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/components/reports')
const attachment = (name, source, type = 'application/json') => ({ name, source, type })
const step = (name, attachments = [], steps = []) => ({ name, attachments, steps })
function report(resultData) {
  return harness('PytestTestReport', 'report,attachments,collectedAttachments,labels,httpEvidence,uiOperations,uiElementAttachments,hasApiEvidence,hasUiEvidence,hasLineage,lineageGraph,activeTab,statusText,statusColor,startTime,parseSource,formatElapsed,formatTimestamp,operationTarget,operationMethod,attachmentSummary,shouldExpandAttachmentJson', { base, filename: path.join(base, 'PytestTestReport.vue'), props: { resultData } })
}
let uid = 1
function lineage(graph) {
  const instanceUid = uid++
  return harness('PytestDataLineage', 'lineage,nodes,edges,summary,selectedNodeId,selectedNode,positionedNodes,visibleEdges,canvasWidth,canvasHeight,nodeSubtitle,edgePath,edgeLabelPosition,markerId', { base, filename: path.join(base, 'PytestDataLineage.vue'), props: { graph }, modules: { vue: { ...vue, getCurrentInstance: () => ({ uid: instanceUid }) } } })
}

test('malformed report fields are narrowed without altering raw input', () => {
  const input = { name: {}, start: false, status: false, labels: [null, false, { name: 'tag', value: 0 }, { name: 'tag', value: 'valid' }], attachments: [null, false, { name: 'data', type: {}, source: 12 }], statusDetails: { message: {}, trace: 'trace' } }
  const snapshot = JSON.stringify(input), h = report(input)
  assert.equal(h.report.value.name, '')
  assert.equal(h.startTime.value, '-')
  assert.equal(h.statusText.value, '未测试')
  assert.deepEqual(h.labels.value, [{ name: 'tag', value: 'valid' }])
  assert.deepEqual(h.attachments.value, [{ name: 'data', type: '', source: '' }])
  assert.equal(h.report.value.statusDetails.trace, 'trace')
  assert.equal(JSON.stringify(input), snapshot)
  for (const value of [null, false, 7, [], 'bad']) {
    h.props.resultData = value
    assert.deepEqual(h.httpEvidence.value, [])
    assert.deepEqual(h.uiOperations.value, [])
  }
  h.close()
})

test('Allure nested steps and fixture evidence retain DFS order, phase and full context', () => {
  const h = report({ attachments: [attachment('root', 'false')], steps: [step('parent', [attachment('parent', '0')], [step('child', [attachment('child', 'null')])])], fixtures: { befores: [step('prepare', [attachment('setup', '{}')])], afters: [step('cleanup', [attachment('cleanup', '{}')])] } })
  assert.deepEqual(h.collectedAttachments.value.map(item => item.name), ['root', 'parent', 'child', 'setup', 'cleanup'])
  assert.deepEqual(h.collectedAttachments.value.map(item => item.phase), ['用例', '步骤', '步骤', '前置', '清理'])
  assert.equal(h.collectedAttachments.value[2].context, 'parent / child')
  assert.equal(new Set(h.collectedAttachments.value.map(item => item.key)).size, 5)
  assert.equal(h.parseSource('false'), false)
  assert.equal(h.parseSource('0'), 0)
  assert.equal(h.parseSource('null'), null)
  h.close()
})

test('deep and cyclic step input cannot overflow traversal', () => {
  const h = report(null), { readPytestReport } = h.load('pytest-report.ts')
  const cyclic = step('cycle'); cyclic.steps.push(cyclic)
  assert.equal(readPytestReport({ steps: [cyclic] }).steps.length, 1)
  let root = step('leaf')
  for (let index = 0; index < 1200; index++) root = step('nested', [], [root])
  assert.equal(readPytestReport({ steps: [root] }).steps.length, 1201)
  h.close()
})

test('HTTP evidence preserves response zero/false/null and reports missing historical attachment', () => {
  const h = report({ steps: [step('HTTP GET https://example.com/api', [attachment('请求信息', '{"method":"GET","url":"https://example.com/api","headers":{}}'), attachment('响应信息', '{"status":200,"elapsed_ms":0,"body":false,"nullable":null}')])] })
  const evidence = h.httpEvidence.value[0]
  assert.equal(evidence.available, true)
  assert.equal(evidence.url, 'https://example.com/api')
  assert.equal(evidence.response.body, false)
  assert.equal(evidence.response.nullable, null)
  assert.equal(h.formatElapsed(evidence.elapsed), '0.00 ms')
  h.props.resultData = { steps: [step('HTTP POST https://example.com/api', [attachment('请求信息', ''), attachment('响应信息', 'missing-attachment.json')])] }
  assert.equal(h.httpEvidence.value[0].available, false)
  assert.equal(h.httpEvidence.value[0].method, 'POST')
  h.close()
})

test('legacy root HTTP attachments and UI element zero text remain supported', () => {
  const h = report({ attachments: [attachment('请求方法', 'GET'), attachment('请求URL', 'https://example.org/'), attachment('响应数据', 'false'), attachment('HTTP状态码', '200'), attachment('响应时长(ms)', '0')] })
  assert.equal(h.httpEvidence.value[0].response.body, false)
  assert.equal(h.httpEvidence.value[0].status, '200')
  h.props.resultData = { attachments: [attachment('element', '元素表达式：#example\n元素定位方法：css\n元素下标：0\n元素个数：0\n元素文本内容：0', 'text/plain')] }
  assert.equal(h.hasUiEvidence.value, true)
  assert.equal(h.uiElementAttachments.value[0].index, '0')
  assert.equal(h.uiElementAttachments.value[0].count, '0')
  assert.equal(h.uiElementAttachments.value[0].text, '0')
  h.close()
})

test('UI evidence is finite for display while raw arguments and result retain false and zero', () => {
  const h = report({ fixtures: { befores: [step('UI 操作 · w_input', [attachment('操作信息', '{"operation":"w_input","arguments":[0],"keyword_arguments":{"text":false}}'), attachment('操作结果', '{"status":"passed","duration_ms":0,"data":false}')])] } })
  const operation = h.uiOperations.value[0]
  assert.equal(operation.phase, '前置')
  assert.equal(operation.status, 'passed')
  assert.equal(h.operationTarget(operation), '0')
  assert.equal(h.operationMethod(operation), 'w_input')
  assert.equal(operation.result.data, false)
  assert.equal(h.formatElapsed(operation.duration), '0.00 ms')
  assert.equal(h.operationTarget({ input: { named_elements: {}, arguments: {}, keyword_arguments: {} } }), '')
  h.close()
})

test('broken/failed/numeric zero are failures; absent time stays absent and epoch zero is valid', () => {
  const h = report({ status: 'broken' })
  assert.equal(h.statusText.value, '测试失败')
  assert.equal(h.statusColor.value, 'red')
  for (const status of [0, 'failed', 'FAILED']) { h.props.resultData = { status }; assert.equal(h.statusColor.value, 'red') }
  h.props.resultData = { status: 3 }
  assert.equal(h.statusText.value, '进行中')
  for (const value of [null, undefined, false, true, '', ' ', NaN, 1e30]) assert.equal(h.formatTimestamp(value), '-')
  assert.notEqual(h.formatTimestamp(0), '-')
  assert.equal(h.formatElapsed(false), '-')
  h.close()
})

test('same UUID refresh retains local tab, new report and removed evidence reset to available content', () => {
  const input = { uuid: 'one', steps: [step('HTTP GET https://example.net/', [attachment('请求信息', '{}')])] }
  const h = report(input)
  assert.equal(h.activeTab.value, 'http')
  h.activeTab.value = 'raw'
  h.props.resultData = { ...input, status: 'passed' }
  assert.equal(h.activeTab.value, 'raw')
  h.props.resultData = { ...input, uuid: 'two' }
  assert.equal(h.activeTab.value, 'http')
  h.props.resultData.steps = []
  assert.equal(h.activeTab.value, 'raw')
  h.props.resultData = { statusDetails: { message: 'failure' } }
  assert.equal(h.activeTab.value, 'logs')
  h.close()
})

test('lineage graph input validates IDs, duplicates, dangling edges and retains explicit summary zeros', () => {
  const h = lineage({ nodes: [{ id: 0, kind: 'factory', entity_id: 0, data: false }, { id: 'entity', kind: 'entity', data: null }, { id: 'entity' }, null], edges: [{ source: 0, target: 'entity' }, { source: 'missing', target: 'entity' }], summary: { factories: 0, operations: 0, entities: 0, relations: 0 } })
  assert.equal(h.lineage.value.malformed, true)
  assert.equal(h.nodes.value.length, 2)
  assert.equal(h.edges.value.length, 1)
  assert.deepEqual({ ...h.summary.value }, { factories: 0, operations: 0, entities: 0, relations: 0 })
  assert.equal(h.nodes.value[0].data, false)
  assert.equal(h.nodes.value[1].data, null)
  assert.equal(h.nodeSubtitle(h.nodes.value[0]), '数据工厂 #0')
  h.close()
})

test('lineage selection follows graph updates without mutating props; unusual string IDs are safe', () => {
  const input = { nodes: [{ id: '__proto__', kind: 'factory' }, { id: 'constructor', kind: 'entity' }], edges: [{ source: '__proto__', target: 'constructor' }] }
  const snapshot = JSON.stringify(input), h = lineage(input)
  h.selectedNodeId.value = 'constructor'
  assert.equal(h.visibleEdges.value.length, 1)
  assert.match(h.edgePath(h.edges.value[0]), /^M/)
  assert.ok(Number.isFinite(h.edgeLabelPosition(h.edges.value[0]).x))
  assert.equal(JSON.stringify(input), snapshot)
  h.props.graph = { nodes: [{ id: 'other', data: 0 }], edges: [] }
  assert.equal(h.selectedNode.value.id, 'other')
  h.props.graph = null
  assert.equal(h.selectedNode.value, null)
  assert.equal(h.selectedNodeId.value, '')
  h.close()
})

test('lineage instances use separate markers and finite viewBox geometry with intrinsic scaled height', () => {
  const input = { nodes: [{ id: 'factory', kind: 'factory' }, { id: 'entity', kind: 'entity' }], edges: [{ source: 'factory', target: 'entity' }] }
  const first = lineage(input), second = lineage(input)
  assert.notEqual(first.markerId, second.markerId)
  assert.equal(first.canvasWidth, 940)
  assert.ok(first.canvasHeight.value >= 220)
  assert.ok(!first.edgePath(first.edges.value[0]).includes('NaN'))
  first.close(); second.close()
})

test('lineage attachment switches to the graph tab, invalid graph is explicit and raw view remains intact', () => {
  const h = report({ attachments: [attachment('数据血缘', '{"nodes":[{"id":"factory","kind":"factory"}],"edges":[],"summary":{"factories":0}}')] })
  assert.equal(h.hasLineage.value, true)
  assert.equal(h.activeTab.value, 'lineage')
  h.props.resultData = { attachments: [attachment('数据血缘', 'false')] }
  assert.equal(h.hasLineage.value, true)
  const g = lineage(h.lineageGraph.value)
  assert.equal(g.lineage.value.malformed, true)
  g.close(); h.close()
})

test('both actual report scripts/templates compile and the SVG preserves user-coordinate font sizes', () => {
  for (const name of ['PytestTestReport', 'PytestDataLineage']) {
    const filename = path.join(base, `${name}.vue`), source = readFileSync(filename, 'utf8'), { descriptor } = parse(source)
    const script = compileScript(descriptor, { id: name })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: name, compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
    if (name === 'PytestDataLineage') {
      assert.doesNotMatch(descriptor.template.content, /canvasHeight.*px/)
      assert.match(descriptor.template.content, /font-size="12"/)
      assert.match(descriptor.styles[0].content, /height: auto/)
    }
  }
})
