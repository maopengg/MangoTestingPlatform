import { loadFeedbackModule } from './helpers/load-feedback-modules.mjs'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { deferred, flush } from './helpers/case-details-harness.mjs'

const filename = 'src/components/business/ProductModuleSelect.vue'
const descriptor = parse(readFileSync(filename, 'utf8'), { filename }).descriptor
const compile = source => ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText
const tree = title => [{ key: 100, title: 'Root', children: [{ key: 200, title: 'Group', children: [{ key: 300, title }] }] }]
const envelope = data => ({ code: 200, data })
function factory(read = async () => envelope(tree('Module'))) {
  const create = new Function(compile(descriptor.script.content) + '\nreturn function(require,defineProps,defineEmits){ const exports = {};\n' +
    compile(descriptor.scriptSetup.content) + '\nreturn {options,loading,failed,cascaderOptions,loadOptions,onPopupVisibleChange,onUpdate,onChange};}')()
  const defaultUser = vue.reactive({ userId: 1, roleId: 1, token: 'fixture-a', selected_environment: 0 })
  const requests = []
  return { requests, user: defaultUser,
    instance(initialProps = {}, user = defaultUser) {
      const props = vue.reactive({ ...initialProps }), events = [], life = { mount: [], unmount: [], activate: [], deactivate: [] }
      const modules = {
        vue: { ...vue, onMounted: fn => life.mount.push(fn), onBeforeUnmount: fn => life.unmount.push(fn), onActivated: fn => life.activate.push(fn), onDeactivated: fn => life.deactivate.push(fn) },
        '@/setting': { fieldNames: { label: 'title', value: 'key', children: 'children' } },
        '@/store/modules/user': { default: () => user },
        '@/api/system/module': { getUserModuleTree: async product => {
          const snapshot = { product, role: user.roleId, environment: user.selected_environment }
          requests.push(snapshot)
          return read(snapshot)
        } },
      }
      const scope = vue.effectScope()
      const result = scope.run(() => create(id => { if (!(id in modules)) { if (['@/utils/load-error', '@/utils/api-response'].includes(id)) return loadFeedbackModule(id); throw new Error('Unmocked dependency ' + id); } return modules[id] }, definitions => {
        for (const [key, definition] of Object.entries(definitions)) {
          if (!(key in props)) props[key] = typeof definition.default === 'function' ? definition.default() : definition.default
        }
        return props
      }, () => (...event) => events.push(event)))
      return { ...result, props, user, events, life,
        mount: () => life.mount.forEach(fn => fn()),
        pause: () => life.deactivate.forEach(fn => fn()), resume: () => life.activate.forEach(fn => fn()),
        close: () => { life.unmount.forEach(fn => fn()); scope.stop() },
      }
    },
  }
}

test('same identity/product consumers share only an in-flight request and preserve independent level filters', async () => {
  const pending = deferred(), f = factory(() => pending.promise)
  const a = f.instance({ projectProductId: 10 }), b = f.instance({ projectProductId: ['1', '10'], excludedKeys: [300] })
  a.mount(); b.mount()
  assert.equal(f.requests.length, 1)
  pending.resolve(envelope(tree('Module'))); await flush()
  assert.equal(a.cascaderOptions.value[0].children[0].children[0].title, 'Module')
  assert.deepEqual(b.cascaderOptions.value, [])
  assert.equal(a.loading.value, false); assert.equal(b.loading.value, false)
  a.onUpdate(100); assert.equal(a.events.some(event => event[0] === 'update:modelValue'), false)
  a.onUpdate(300); assert.deepEqual(a.events.at(-1), ['update:modelValue', 300])
  a.close(); b.close()
})

test('identity A-B-A never reuses the first A promise or accepts old success/error/finalizers', async () => {
  const pending = [deferred(), deferred(), deferred()]
  let index = 0
  const f = factory(() => pending[index++].promise), a = f.instance({ projectProductId: 10 })
  a.mount()
  f.user.roleId = 2; f.user.roleId = 1
  assert.equal(f.requests.length, 3)
  pending[0].resolve(envelope(tree('Old A'))); pending[1].reject(new Error('Old B'))
  await flush()
  assert.deepEqual(a.options.value, [])
  assert.equal(a.failed.value, false)
  assert.equal(a.loading.value, true)
  pending[2].resolve(envelope(tree('New A'))); await flush()
  assert.equal(a.cascaderOptions.value[0].children[0].children[0].title, 'New A')
  assert.equal(a.events.filter(event => event[0] === 'loaded').length, 1)
  a.close()
})

test('user, token and environment changes invalidate existing options and fetch a new identity scope', async () => {
  const f = factory(), a = f.instance({ projectProductId: 10 })
  a.mount(); await flush()
  for (const key of ['userId', 'token', 'selected_environment']) {
    const previous = f.user[key], count = f.requests.length
    f.user[key] = typeof previous === 'string' ? 'fixture-b' : previous + 1
    assert.deepEqual(a.options.value, [])
    assert.equal(f.requests.length, count + 1)
    await flush()
    f.user[key] = previous
    await flush()
  }
  a.close()
})

test('separate store roots do not share request scopes even when numeric identity and product IDs match', async () => {
  const pending = [deferred(), deferred()]
  let index = 0
  const f = factory(() => pending[index++].promise)
  const a = f.instance({ projectProductId: 10 })
  const b = f.instance({ projectProductId: 10 }, vue.reactive({ userId: 1, roleId: 1, token: 'fixture-other', selected_environment: 0 }))
  a.mount(); b.mount()
  assert.equal(f.requests.length, 2)
  pending[0].resolve(envelope(tree('First'))); pending[1].resolve(envelope(tree('Second')))
  await flush()
  assert.notEqual(a.options.value, b.options.value)
  assert.equal(b.cascaderOptions.value[0].children[0].children[0].title, 'Second')
  a.close(); b.close()
})

test('product A-B-A discards old responses and honors autoClear=false without changing scalar API parameters', async () => {
  const pending = [deferred(), deferred(), deferred()]
  let index = 0
  const f = factory(() => pending[index++].promise), a = f.instance({ projectProductId: 10, autoClear: false })
  a.mount(); a.props.projectProductId = 20; a.props.projectProductId = 10
  assert.deepEqual(f.requests.map(request => request.product), [10, 20, 10])
  pending[1].resolve(envelope(tree('Wrong product'))); await flush()
  assert.equal(a.loading.value, true)
  pending[0].resolve(envelope(tree('Old product A'))); await flush()
  assert.equal(a.loading.value, true)
  assert.deepEqual(a.options.value, [])
  pending[2].resolve(envelope(tree('Correct product'))); await flush()
  assert.equal(a.cascaderOptions.value[0].children[0].children[0].title, 'Correct product')
  assert.equal(a.events.some(event => event[0] === 'update:modelValue'), false)
  a.close()
})

test('business and malformed failures are distinct from empty data; reopening dropdown retries after cache removal', async () => {
  let result = { code: 400, data: [] }
  const f = factory(async () => result), a = f.instance({ projectProductId: 10 })
  a.mount(); await flush()
  assert.equal(a.failed.value, true)
  assert.equal(a.loading.value, false)
  assert.equal(a.events.some(event => event[0] === 'loaded'), false)
  result = { code: 200, data: null }
  a.onPopupVisibleChange(true); await flush()
  assert.equal(a.failed.value, true)
  result = envelope([{ key: 100, title: 'Bad tree', children: [null] }])
  a.onPopupVisibleChange(true); await flush()
  assert.equal(a.failed.value, true)
  assert.deepEqual(a.options.value, [])
  result = envelope([])
  a.onPopupVisibleChange(true); await flush()
  assert.equal(a.failed.value, false)
  assert.deepEqual(a.events.at(-1), ['loaded', []])
  assert.equal(f.requests.length, 4)
  a.close()
})

test('refreshToken keeps selection but reloads; all-option, level and display rules remain unchanged', async () => {
  const f = factory(), a = f.instance({ projectProductId: null, selectableLevel: 0, maxSelectableLevel: 1, maxDisplayLevel: 2, showAllOption: true })
  a.mount(); await flush()
  assert.equal(f.requests[0].product, null)
  assert.equal(a.cascaderOptions.value[0].key, '__all__')
  assert.equal(a.cascaderOptions.value[1].children[0].selectionDisabledByLevel, true)
  assert.equal(a.cascaderOptions.value[1].children[0].children, undefined)
  a.onChange('__all__'); assert.deepEqual(a.events.at(-1), ['change', '__all__'])
  const updates = a.events.filter(event => event[0] === 'update:modelValue').length
  a.props.refreshToken++
  await flush()
  assert.equal(f.requests.length, 2)
  assert.equal(a.events.filter(event => event[0] === 'update:modelValue').length, updates)
  a.close()
})

test('unmount invalidates only its own consumer; a mounted sibling still receives the shared response', async () => {
  const pending = deferred(), f = factory(() => pending.promise)
  const a = f.instance({ projectProductId: 10 }), b = f.instance({ projectProductId: 10 })
  a.mount(); b.mount(); a.close()
  pending.resolve(envelope(tree('Sibling'))); await flush()
  assert.deepEqual(a.options.value, [])
  assert.equal(a.events.some(event => event[0] === 'loaded'), false)
  assert.equal(b.options.value.length, 1)
  b.close()
})

test('new window instance starts a fresh read instead of borrowing the closed instance promise', async () => {
  const pending = [deferred(), deferred()]
  let index = 0
  const f = factory(() => pending[index++].promise), old = f.instance({ projectProductId: 10 })
  old.mount(); old.close()
  const current = f.instance({ projectProductId: 10 })
  current.mount()
  assert.equal(f.requests.length, 2)
  pending[0].resolve(envelope(tree('Closed instance'))); await flush()
  assert.deepEqual(current.options.value, [])
  assert.equal(current.loading.value, true)
  pending[1].resolve(envelope(tree('Current instance'))); await flush()
  assert.equal(current.cascaderOptions.value[0].children[0].children[0].title, 'Current instance')
  current.close()
})

test('KeepAlive defers identity reads while inactive, then resumes without accepting the paused response', async () => {
  const pending = deferred()
  let index = 0
  const f = factory(() => ++index === 1 ? pending.promise : envelope(tree('Resumed'))), a = f.instance({ projectProductId: 10 })
  a.mount(); a.pause()
  f.user.roleId = 2
  assert.equal(f.requests.length, 1)
  pending.resolve(envelope(tree('Paused'))); await flush()
  assert.deepEqual(a.options.value, [])
  a.resume(); await flush()
  assert.equal(f.requests.length, 2)
  assert.equal(a.cascaderOptions.value[0].children[0].children[0].title, 'Resumed')
  a.close()
})

test('public selector SFC compiles with both script blocks and unchanged external selection events', () => {
  const script = compileScript(descriptor, { id: filename })
  const template = compileTemplate({ source: descriptor.template.content, filename, id: filename, compilerOptions: { bindingMetadata: script.bindings } })
  assert.deepEqual(template.errors, [])
  assert.ok(script.bindings.onPopupVisibleChange)
})
