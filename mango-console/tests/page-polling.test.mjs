import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'

function load(path, require = () => ({})) {
  const exports = {}
  const source = fs.readFileSync(path, 'utf8')
  new Function('exports', 'require', ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText)(exports, require)
  return exports
}
const { createPagePolling, isPendingExecution, PAGE_POLL_INTERVAL } = load('src/utils/page-polling.ts')
const flush = async () => { for (let i = 0; i < 10; i++) await Promise.resolve() }
function fakeClock() {
  let id = 0
  const timers = new Map()
  return {
    timers,
    setTimeout(fn, delay) { timers.set(++id, { fn, delay }); return id },
    clearTimeout(key) { timers.delete(key) },
    async tick() { const [key, timer] = timers.entries().next().value; timers.delete(key); timer.fn(); await flush() },
  }
}

test('queued and running numeric/string states are active; terminal states are not', () => {
  for (const status of [2, 3, '2', '3']) assert.equal(isPendingExecution({ status }), true)
  for (const status of [0, 1, 4, 5, null, undefined]) assert.equal(isPendingExecution({ status }), false)
})

test('all requests use five seconds, retry failures and never overlap slow requests', async () => {
  const clock = fakeClock()
  let calls = 0, finish
  const polling = createPagePolling(() => {
    calls++
    if (calls === 1) throw new Error('temporary failure')
    return new Promise(resolve => { finish = resolve })
  }, () => true, clock)
  assert.equal(PAGE_POLL_INTERVAL, 5000)
  polling.start()
  assert.equal([...clock.timers.values()][0].delay, 5000)
  await clock.tick()
  assert.equal(calls, 1)
  assert.equal([...clock.timers.values()][0].delay, 5000)
  await clock.tick()
  polling.start()
  assert.equal(calls, 2)
  assert.equal(clock.timers.size, 0)
  finish(); await flush()
  assert.equal([...clock.timers.values()][0].delay, 5000)
  polling.stop()
  assert.equal(clock.timers.size, 0)
})

test('pause rejects stale responses; resume waits for outstanding work then runs immediately', async () => {
  const clock = fakeClock()
  let available = true, context, finish
  const polling = createPagePolling(value => { context = value; return new Promise(resolve => { finish = resolve }) }, () => available, clock)
  polling.start(); await clock.tick()
  assert.equal(context.isCurrent(), true)
  available = false; polling.pause()
  assert.equal(context.isCurrent(), false)
  available = true; polling.resume()
  assert.equal(context.isCurrent(), false)
  assert.equal(clock.timers.size, 0)
  finish(); await flush()
  assert.equal([...clock.timers.values()][0].delay, 0)
  await clock.tick()
  polling.dispose()
  assert.equal(context.isCurrent(), false)
  finish(); await flush()
  assert.equal(clock.timers.size, 0)
})

test('Vue page lifecycle, browser visibility and routes pause and resume the same poller', async () => {
  const clock = fakeClock(), hooks = {}, events = new Map()
  const route = { path: '/report/index' }
  const document = { visibilityState: 'visible', addEventListener: (name, fn) => events.set(name, fn), removeEventListener: name => events.delete(name) }
  const vue = Object.fromEntries(['onMounted', 'onActivated', 'onDeactivated', 'onBeforeUnmount'].map(name => [name, fn => { hooks[name] = fn }]))
  vue.watch = (_source, fn) => { hooks.routeChange = fn }
  const exports = {}
  const js = ts.transpileModule(fs.readFileSync('src/hooks/use-page-polling.ts', 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS } }).outputText
  new Function('exports', 'require', 'document', js)(exports, name => name === 'vue' ? vue : name === 'vue-router' ? { useRoute: () => route } : { createPagePolling: (fn, available) => createPagePolling(fn, available, clock) }, document)
  let calls = 0
  const polling = exports.usePagePolling(() => { calls++ })
  hooks.onMounted(); polling.start()
  document.visibilityState = 'hidden'; events.get('visibilitychange')()
  assert.equal(clock.timers.size, 0)
  document.visibilityState = 'visible'; events.get('visibilitychange')()
  assert.equal([...clock.timers.values()][0].delay, 0)
  await clock.tick(); assert.equal(calls, 1)
  hooks.onDeactivated(); assert.equal(clock.timers.size, 0)
  hooks.onActivated(); await clock.tick(); assert.equal(calls, 2)
  route.path = '/another'; hooks.routeChange(); assert.equal(clock.timers.size, 0)
  route.path = '/report/index'; hooks.routeChange(); await clock.tick(); assert.equal(calls, 3)
  hooks.onBeforeUnmount(); assert.equal(events.size, 0); assert.equal(clock.timers.size, 0)
})

test('all affected real Vue pages compile after adopting shared polling', () => {
  for (const path of ['report/index.vue', 'report/details/index.vue', 'apitest/case/index.vue', 'apitest/info/index.vue',
    'apitest/case/details/index.vue', 'uitest/case/index.vue', 'uitest/case/details/index.vue',
    'uitest/page-steps/index.vue', 'pytest/case/index.vue', 'evaluation/components/ExecutionPanel.vue', 'perf/run/details/index.vue']) {
    const filename = `src/views/${path}`
    const { descriptor, errors } = parse(fs.readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [], path)
    const script = compileScript(descriptor, { id: path })
    assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: path, compilerOptions: { bindingMetadata: script.bindings } }).errors, [], path)
  }
})

test('evaluation retries a failed final result fetch silently before stopping polling', async () => {
  const source = fs.readFileSync('src/views/evaluation/components/ExecutionPanel.vue', 'utf8')
  const start = source.indexOf('  async function loadRecord(')
  const end = source.indexOf('  async function loadItems(', start)
  const js = ts.transpileModule(source.slice(start, end), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  const record = { value: { id: 1, status: 'running' } }, recordLoading = { value: false }, calls = []
  let fail = true
  const run = new Function('props', 'record', 'recordLoading', 'getCaseExecution', 'loadItems', 'pagePolling', 'isTerminal', `let generation = 0; ${js}; return loadRecord`)(
    { caseId: 1, history: false }, record, recordLoading,
    async () => ({ data: { id: 1, status: 'completed' } }),
    async silent => { assert.equal(silent, true); if (fail) throw new Error('final items unavailable') },
    { start: () => calls.push('retry'), stop: () => calls.push('stop') }, status => status === 'completed'
  )
  await assert.rejects(run(1, true))
  assert.deepEqual(calls, ['retry'])
  assert.equal(recordLoading.value, false)
  fail = false
  await run(1, true)
  assert.deepEqual(calls, ['retry', 'stop'])
  assert.equal(recordLoading.value, false)
})
