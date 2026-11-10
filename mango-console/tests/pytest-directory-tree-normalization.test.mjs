import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import path from 'node:path'
import test from 'node:test'
import * as vue from 'vue'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'
import { harness } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/pytest/case')
const node = (key, type, children = []) => ({ key, title: key, type, children, path: key, breadcrumb: [], repository_id: 1 })
const tree = () => [node('repository', 'repository', [
  node('project', 'project', [node('folder', 'directory', [node('first.py', 'file'), node('second.py', 'file')])]),
  node('other', 'project', [node('third.py', 'file')]),
])]

function setup(props = {}) {
  const jobs = [], mounted = [], activated = [], deactivated = [], unmounted = [], listeners = new Set(), scrolls = []
  globalThis.document = { hidden: false, addEventListener: (_, fn) => listeners.add(fn), removeEventListener: (_, fn) => listeners.delete(fn) }
  let reducedMotion = false
  globalThis.window = { matchMedia: () => ({ matches: reducedMotion }) }
  const h = harness('PytestCaseDirectoryTree', 'keyword,expandedKeys,displayTree,treeContainerRef,onSelect,onExpand,toggleExpansion,revealSelectedNode,nodeCount,fileStateLabel,fileStateTone', {
    base, props: { data: tree(), selectedKey: 'first.py', ...props },
    modules: { vue: { ...vue, nextTick: fn => jobs.push(fn), onMounted: fn => mounted.push(fn), onActivated: fn => activated.push(fn), onDeactivated: fn => deactivated.push(fn), onBeforeUnmount: fn => unmounted.push(fn) } },
  })
  h.treeContainerRef.value = { querySelector: () => ({ scrollIntoView: options => scrolls.push(options) }) }
  mounted.forEach(fn => fn())
  return { ...h, jobs, scrolls, listeners, reduced: () => { reducedMotion = true }, drain: () => { jobs.splice(0).forEach(fn => fn()) }, pause: () => deactivated.forEach(fn => fn()), resume: () => activated.forEach(fn => fn()), hide: () => { document.hidden = true; listeners.forEach(fn => fn()) }, dispose: () => { unmounted.forEach(fn => fn()); h.close() } }
}

test('search preserves matching parent subtrees, prunes unmatched siblings and never edits input', () => {
  const h = setup()
  const original = JSON.stringify(h.props.data)
  h.keyword.value = ' PROJECT '
  assert.equal(h.displayTree.value[0].children[0].children[0].children.length, 2)
  assert.equal(h.displayTree.value[0].children.length, 1)
  h.keyword.value = 'SECOND.PY'
  assert.equal(h.displayTree.value[0].children[0].children[0].children[0].key, 'second.py')
  assert.equal(h.displayTree.value[0].children[0].children[0].children.length, 1)
  assert.equal(JSON.stringify(h.props.data), original)
  h.keyword.value = 'not found'
  assert.deepEqual(h.displayTree.value, [])
  h.keyword.value = ''
  assert.equal(h.displayTree.value, h.props.data)
  h.dispose()
})

test('selected file and expandSelected changes reveal the correct ancestors synchronously', () => {
  const h = setup()
  assert.deepEqual([...h.expandedKeys.value], ['repository', 'project', 'folder'])
  h.props.selectedKey = 'project'
  assert.deepEqual([...h.expandedKeys.value], ['repository'])
  h.props.expandSelected = true
  assert.deepEqual([...h.expandedKeys.value], ['repository', 'project'])
  h.props.selectedKey = 'third.py'
  assert.deepEqual([...h.expandedKeys.value], ['repository', 'other'])
  h.dispose()
})

test('file selection emits the full node while directory selection only toggles its branch', () => {
  const h = setup()
  h.onSelect(['second.py'])
  assert.equal(h.events[0][0], 'select')
  assert.equal(h.events[0][1], h.props.data[0].children[0].children[0].children[1])
  h.onSelect(['other'])
  assert.equal(h.events[1][0], 'directory-toggle')
  assert.deepEqual([...h.expandedKeys.value], ['repository', 'other'])
  h.onSelect(['other'])
  assert.deepEqual([...h.expandedKeys.value], ['repository'])
  h.onSelect([])
  h.onSelect(['unknown'])
  h.props.loading = true
  h.onSelect(['first.py'])
  assert.equal(h.events.length, 3)
  h.dispose()
})

test('search expands visible branches and selection outside results does not reveal hidden branches', () => {
  const h = setup()
  h.keyword.value = 'third'
  assert.deepEqual([...h.expandedKeys.value], ['repository', 'other'])
  h.drain()
  assert.equal(h.scrolls.length, 0)
  h.onExpand([], { node: h.props.data[0], expanded: false })
  assert.deepEqual([...h.expandedKeys.value], [])
  h.keyword.value = ''
  assert.deepEqual([...h.expandedKeys.value], ['repository', 'project', 'folder'])
  h.dispose()
})

test('rapid A-B-A selection allows only the latest scheduled scroll and respects reduced motion', () => {
  const h = setup()
  h.props.selectedKey = 'third.py'
  h.props.selectedKey = 'first.py'
  h.reduced()
  h.drain()
  assert.deepEqual(h.scrolls, [{ block: 'nearest', behavior: 'auto' }])
  h.dispose()
})

test('manual collapse or expand cancels scheduled reveal; locate can reopen current selection', () => {
  const h = setup()
  h.toggleExpansion()
  h.drain()
  assert.deepEqual([...h.expandedKeys.value], [])
  assert.equal(h.scrolls.length, 0)
  h.toggleExpansion()
  h.onExpand([], { node: h.props.data[0], expanded: false })
  h.drain()
  assert.equal(h.scrolls.length, 0)
  h.toggleExpansion()
  h.drain()
  assert.equal(h.scrolls.length, 1)
  h.dispose()
})

test('replacement data clears old expanded keys and invalidates stale scroll', () => {
  const h = setup()
  h.props.data = [node('new', 'repository')]
  h.drain()
  assert.deepEqual([...h.expandedKeys.value], [])
  assert.equal(h.scrolls.length, 0)
  h.props.selectedKey = ''
  h.dispose()
})

test('background, KeepAlive deactivation and unmount stop deferred DOM work and clean listener', () => {
  const h = setup()
  h.hide()
  document.hidden = false
  h.drain()
  assert.equal(h.scrolls.length, 0)
  h.revealSelectedNode()
  h.pause()
  h.onSelect(['second.py'])
  h.drain()
  assert.equal(h.scrolls.length, 0)
  assert.equal(h.events.length, 0)
  h.resume()
  h.drain()
  assert.equal(h.scrolls.length, 1)
  h.revealSelectedNode()
  h.dispose()
  h.drain()
  assert.equal(h.scrolls.length, 1)
  assert.equal(h.listeners.size, 0)
})

test('counts preserve explicit zero and source failure has priority over asset state', () => {
  const h = setup()
  assert.equal(h.nodeCount({ count: 0, case_count: 9 }), 0)
  assert.equal(h.fileStateLabel({ source_status: 2, asset_status: 3 }), '缺失')
  assert.equal(h.fileStateTone({ source_status: 2, asset_status: 3 }), 'danger')
  assert.equal(h.fileStateLabel({ source_status: 0, asset_status: 3 }), '归档')
  h.dispose()
})

test('directory tree script and template compile', () => {
  const filename = path.join(base, 'components/PytestCaseDirectoryTree.vue')
  const { descriptor } = parse(readFileSync(filename, 'utf8'))
  const script = compileScript(descriptor, { id: 'directory-tree' })
  const compiled = compileTemplate({ source: descriptor.template.content, filename, id: 'directory-tree', compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(compiled.errors, [])
})
