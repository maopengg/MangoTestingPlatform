import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { runInNewContext } from 'node:vm'
import ts from 'typescript'

const source = readFileSync(new URL('../src/utils/asset-load-recovery.ts', import.meta.url), 'utf8')
const { outputText } = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.CommonJS },
})

function harness() {
  const exports = {}, listeners = {}, prompts = [], reports = []
  class Script { constructor(src) { this.src = src } }
  class Link { constructor(href) { this.href = href } }
  let routeError, reloads = 0, now = 0
  runInNewContext(outputText, {
    exports, Error, URL,
    Date: { now: () => now },
    HTMLScriptElement: Script,
    HTMLLinkElement: Link,
    window: {
      location: { origin: 'https://example.com', reload: () => { reloads++ } },
      addEventListener: (name, listener) => { listeners[name] = listener },
    },
    require(name) {
      if (name === '@arco-design/web-vue') return { Modal: { warning: config => prompts.push(config) } }
      if (name === './system-error-reporter') return { reportFrontendError: (...args) => reports.push(args) }
      throw new Error(`Unexpected dependency: ${name}`)
    },
  })
  exports.setupAssetLoadRecovery({ onError: listener => { routeError = listener } })
  return {
    prompts, reports,
    routeError: error => routeError(error),
    resourceError: (url, type = Script) => listeners.error({ target: new type(url) }),
    rejection: reason => listeners.unhandledrejection({ reason }),
    Link,
    tick: amount => { now += amount },
    get reloads() { return reloads },
  }
}

test('module failures offer recovery but never reload without confirmation', () => {
  const h = harness()
  for (const message of [
    'Failed to fetch dynamically imported module: https://example.com/assets/index.abcdef12.js',
    'error loading dynamically imported module',
    'Importing a module script failed.',
    'Unable to preload CSS for /assets/index.abcdef12.css',
  ]) h.routeError(new TypeError(message))
  assert.equal(h.prompts.length, 1)
  assert.equal(h.reloads, 0)
  assert.equal(h.reports.length, 4)
  assert.match(h.prompts[0].content, /未保存/)
  assert.equal(h.prompts[0].hideCancel, true)
  assert.equal(h.prompts[0].closable, false)
  assert.equal(h.prompts[0].maskClosable, false)
  assert.equal(h.prompts[0].escToClose, false)
  assert.equal(h.prompts[0].cancelText, undefined)
  h.prompts[0].onOk()
  assert.equal(h.reloads, 1)
})

test('same-origin hashed JS and CSS resource failures offer one deduplicated prompt', () => {
  const h = harness()
  h.resourceError('https://example.com/assets/index.abcdef12.js')
  h.resourceError('https://example.com/assets/index.abcdef12.css', h.Link)
  h.rejection(new Error('Failed to fetch dynamically imported module'))
  assert.equal(h.prompts.length, 1)
  h.prompts[0].onClose()
  h.resourceError('/assets/index.abcdef12.js')
  assert.equal(h.prompts.length, 1)
  h.tick(60_000)
  h.resourceError('/assets/index.abcdef12.js')
  assert.equal(h.prompts.length, 2)
  assert.equal(h.reloads, 0)
})

test('business errors, API failures and unrelated resources do not prompt or reload', () => {
  const h = harness()
  h.routeError(new Error('Cannot convert undefined or null to object'))
  h.rejection(new Error('Network Error'))
  h.resourceError('https://example.org/assets/index.abcdef12.js')
  h.resourceError('/uploads/image.png')
  h.resourceError('/api/system/tasks')
  h.resourceError('/assets/index.abcdef12.png')
  assert.equal(h.prompts.length, 0)
  assert.equal(h.reports.length, 0)
  assert.equal(h.reloads, 0)
})
