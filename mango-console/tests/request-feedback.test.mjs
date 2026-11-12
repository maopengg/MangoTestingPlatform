import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { loadModule } from './helpers/auth-config-harness.mjs'

const filename = 'src/components/feedback/MangoRequestFeedback.vue'
const source = readFileSync(filename, 'utf8')
const { descriptor } = parse(source, { filename })

function feedbackHarness(initial = '') {
  const previous = globalThis.document
  const listeners = new Map(), lifecycle = {}, messages = []
  globalThis.document = { visibilityState: 'visible', addEventListener: (type, callback) => listeners.set(type, callback), removeEventListener: type => listeners.delete(type) }
  const runtime = { ...vue }
  for (const name of ['onMounted', 'onActivated', 'onDeactivated', 'onBeforeUnmount']) runtime[name] = callback => { lifecycle[name] = callback }
  const script = compileScript(descriptor, { id: 'request-feedback' })
  const code = ts.transpileModule(script.content, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS } }).outputText
  const exports = {}
  new Function('exports', 'require', code)(exports, id => id === 'vue' ? runtime : { reportLoadError: (_cause, message) => messages.push(message) })
  const props = vue.reactive({ message: initial }), scope = vue.effectScope()
  scope.run(() => exports.default.setup(props, { expose() {} }))
  lifecycle.onMounted()
  return { props, messages, listeners, lifecycle,
    hide() { globalThis.document.visibilityState = 'hidden'; listeners.get('visibilitychange')() },
    show() { globalThis.document.visibilityState = 'visible'; listeners.get('visibilitychange')() },
    close() { lifecycle.onBeforeUnmount(); scope.stop(); globalThis.document = previous },
  }
}

test('request feedback only renders retry/action slots, never the error text', () => {
  assert.doesNotMatch(descriptor.template.content, /\{\{|v-text|v-html/)
  assert.match(descriptor.template.content, /<slot\s*\//)
  assert.match(descriptor.template.content, /<slot name="action"/)
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename, id: filename }).errors, [])
})

test('errors notify once, clear on recovery and notify a new attempt', async t => {
  const h = feedbackHarness('保存失败'); t.after(h.close)
  await vue.nextTick(); assert.deepEqual(h.messages, ['保存失败'])
  h.props.message = '保存失败'; await vue.nextTick(); assert.equal(h.messages.length, 1)
  h.props.message = ''; await vue.nextTick()
  h.props.message = '保存失败'; await vue.nextTick(); assert.equal(h.messages.length, 2)
})

test('background and deactivated panels defer only the current error until returning', async t => {
  const h = feedbackHarness(); t.after(h.close)
  h.hide(); h.props.message = '旧失败'; await vue.nextTick(); h.props.message = '新失败'; await vue.nextTick()
  assert.deepEqual(h.messages, []); h.show(); assert.deepEqual(h.messages, ['新失败'])
  h.lifecycle.onDeactivated(); h.props.message = '切页失败'; await vue.nextTick(); assert.equal(h.messages.length, 1)
  h.props.message = ''; await vue.nextTick(); h.lifecycle.onActivated(); assert.equal(h.messages.length, 1)
  h.lifecycle.onDeactivated(); h.props.message = '当前失败'; await vue.nextTick(); h.lifecycle.onActivated(); assert.equal(h.messages.at(-1), '当前失败')
})

test('request-layer errors suppress fallback notifications while state and retry remain intact', () => {
  const notifications = []
  const api = loadModule('src/utils/load-error.ts', { '@arco-design/web-vue': { Message: { error: message => notifications.push(message) } } })
  const cause = Error('request rejected')
  api.reportLoadError(cause, '后端明确的错误')
  assert.equal(api.requestFailureMessage(cause, '删除失败，请重试'), '删除失败，请重试')
  api.reportLoadError(undefined, '删除失败，请重试')
  assert.deepEqual(notifications, ['后端明确的错误'])
  assert.equal(api.requestFailureMessage(Error('network'), true, '保存失败，草稿已保留'), true)
  api.reportLoadError(undefined, '保存失败，草稿已保留')
  assert.deepEqual(notifications, ['后端明确的错误', '保存失败，草稿已保留'])
})
