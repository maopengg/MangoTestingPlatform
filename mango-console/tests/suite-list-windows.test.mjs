import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush, method } from './helpers/case-details-harness.mjs'
import { setupSuiteList } from './helpers/suite-list-harness.mjs'
const base = path.resolve('src/views/functional-test/suite')
const record = (extra = {}) => ({
  id: 11,
  version_no: 2,
  suite: { id: 5 },
  case_no: 'CASE-11',
  title: 'Example',
  test_point: 'Point',
  priority: 0,
  test_types: [0],
  scenario_layer: 0,
  scenario_type: 0,
  scenario_tags: ['smoke'],
  project_product: { id: 2 },
  module: { id: 3 },
  owner: { id: 4, name: 'Original owner' },
  ...extra,
})
function editor(api = {}, modules = {}) {
  const hooks = { stop: [], activate: [], unmount: [] }
  const f = harness(
    'SuiteListCaseEditor',
    'open,save,cancel,onVisibleChange,onProductChange,form,visible,saving,saveError,ownerOptions',
    {
      base,
      props: {
        contextKey: 'one',
        blocked: false,
        users: [],
        usersLoading: false,
        usersError: false,
      },
      api: {
        putManualCase: async (payload) => ({
          data: { ...payload, version_no: (payload.version_no ?? 0) + 1 },
        }),
        ...api,
      },
      modules: {
        vue: {
          ...vue,
          onDeactivated: (fn) => hooks.stop.push(fn),
          onActivated: (fn) => hooks.activate.push(fn),
          onBeforeUnmount: (fn) => hooks.unmount.push(fn),
        },
        ...modules,
      },
    }
  )
  return {
    ...f,
    hooks,
    cleanup() {
      hooks.unmount.forEach((fn) => fn())
      f.close()
    },
  }
}
test('case editor isolates draft, preserves zero enums and emits visibility', () => {
  const e = editor(),
    original = record()
  e.open(original)
  e.form.title = 'Edited'
  e.form.test_types.push(1)
  assert.equal(original.title, 'Example')
  assert.deepEqual(original.test_types, [0])
  assert.equal(e.form.project_product, 2)
  assert.equal(e.form.module, 3)
  assert.equal(e.form.priority, 0)
  assert.equal(e.form.scenario_type, 0)
  assert.ok(e.events.some((event) => event[0] === 'visible' && event[1] === true))
  e.cleanup()
})
test('case save submits only visible fields, fixed source and version; unexposed asset fields are omitted', async () => {
  let payload
  const e = editor({
    putManualCase: async (p) => {
      payload = p
      return { data: { ...p, version_no: 3 } }
    },
  })
  const original = record({
    remark: 'Keep',
    test_steps: [{ action: 'Keep' }],
    category_level_1: 'Keep',
    source_text: 'Keep',
    update_time: 'Readonly',
    precondition: 'Keep',
  })
  e.open(original)
  original.id = 99
  original.suite.id = 99
  original.version_no = 88
  e.form.project_product = [1, '2']
  await e.save()
  assert.equal(payload.id, 11)
  assert.equal(payload.suite, 5)
  assert.equal(payload.version_no, 2)
  assert.equal(payload.project_product, 2)
  for (const key of [
    'remark',
    'test_steps',
    'category_level_1',
    'source_text',
    'update_time',
    'precondition',
  ])
    assert.equal(key in payload, false)
  assert.equal(e.visible.value, false)
  assert.equal(e.saving.value, false)
  assert.ok(e.events.some((event) => event[0] === 'saved' && event[1] === 11))
  e.cleanup()
})
test('orphan case source is saved as null without inventing a requirement', async () => {
  let payload
  const e = editor({
    putManualCase: async (p) => {
      payload = p
      return { data: { ...p, version_no: 3 } }
    },
  })
  e.open(record({ suite: null }))
  await e.save()
  assert.equal(payload.suite, null)
  assert.equal(e.saveError.value, false)
  e.cleanup()
})
test('cancel and reopen reset arrays, errors and drafts', () => {
  const e = editor(),
    original = record()
  e.open(original)
  e.form.title = 'Unsaved'
  e.cancel()
  assert.equal(e.visible.value, false)
  e.open(original)
  assert.equal(e.form.title, 'Example')
  assert.deepEqual(e.form.scenario_tags, ['smoke'])
  e.cleanup()
})
test('module survives same product echo but clears on real product change; owner falls back to original label', () => {
  const e = editor()
  e.open(record())
  e.onProductChange([1, '2'])
  assert.equal(e.form.module, 3)
  assert.equal(e.ownerOptions.value[0].title, 'Original owner')
  e.onProductChange(9)
  assert.equal(e.form.module, null)
  e.props.users = [{ key: '4', title: 'Loaded owner' }]
  assert.equal(e.ownerOptions.value.length, 1)
  assert.equal(e.ownerOptions.value[0].title, 'Loaded owner')
  e.cleanup()
})
test('physical save lock blocks duplicate, close and reopen while payload remains frozen', async () => {
  const pending = deferred()
  let count = 0,
    payload
  const e = editor({
    putManualCase: (p) => {
      count++
      payload = p
      return pending.promise
    },
  })
  e.open(record())
  const saving = e.save()
  e.form.title = 'Late mutation'
  e.cancel()
  e.onVisibleChange(false)
  e.open(record({ id: 12 }))
  await e.save()
  assert.equal(e.visible.value, true)
  assert.equal(count, 1)
  assert.equal(payload.title, 'Example')
  pending.resolve({ data: { ...payload, version_no: 3 } })
  await saving
  assert.equal(e.saving.value, false)
  assert.equal(e.visible.value, false)
  e.cleanup()
})
test('save failure keeps input and permits retry', async () => {
  let fail = true
  const e = editor({
    putManualCase: async (p) => {
      if (fail) throw Error('Offline')
      return { data: { ...p, version_no: 3 } }
    },
  })
  e.open(record())
  e.form.title = 'Keep draft'
  await e.save()
  assert.equal(e.saveError.value, true)
  assert.equal(e.form.title, 'Keep draft')
  assert.equal(e.visible.value, true)
  fail = false
  await e.save()
  assert.equal(e.saveError.value, false)
  assert.equal(e.visible.value, false)
  e.cleanup()
})
for (const transition of ['context', 'context-roundtrip', 'stop', 'stop-activate', 'unmount']) {
  test(`case ${transition} invalidates late save without releasing the pending request lock`, async () => {
    const pending = deferred()
    let payload
    const e = editor({
      putManualCase: (p) => {
        payload = p
        return pending.promise
      },
    })
    e.open(record())
    const saving = e.save()
    if (transition.startsWith('context')) {
      e.props.contextKey = 'two'
      if (transition.endsWith('roundtrip')) e.props.contextKey = 'one'
    } else if (transition === 'unmount') e.hooks.unmount.forEach((fn) => fn())
    else {
      e.hooks.stop.forEach((fn) => fn())
      if (transition.endsWith('activate')) e.hooks.activate.forEach((fn) => fn())
    }
    e.open(record({ id: 12 }))
    assert.equal(e.visible.value, false)
    assert.equal(e.saving.value, true)
    pending.resolve({ data: { ...payload, version_no: 3 } })
    await saving
    assert.equal(e.saving.value, false)
    assert.equal(
      e.events.some((event) => event[0] === 'saved'),
      false
    )
    e.cleanup()
  })
}
for (const invalid of [
  { id: 12 },
  { suite: 99 },
  { project_product: 99 },
  { version_no: 2 },
  { version_no: null },
]) {
  test(`case rejects invalid acknowledgment ${JSON.stringify(invalid)}`, async () => {
    const e = editor({
      putManualCase: async (p) => ({ data: { ...p, version_no: 3, ...invalid } }),
    })
    e.open(record())
    await e.save()
    assert.equal(e.saveError.value, true)
    assert.equal(e.visible.value, true)
    e.cleanup()
  })
}
test('case required fields fail locally and parent blocked state prevents open/save', async () => {
  let count = 0
  const e = editor({
    putManualCase: async () => {
      count++
      return { data: {} }
    },
  })
  e.props.blocked = true
  e.open(record())
  assert.equal(e.visible.value, false)
  e.props.blocked = false
  e.open(record())
  const original = { ...e.form }
  for (const [key, value] of Object.entries({
    case_no: ' ',
    title: '',
    test_point: '',
    project_product: null,
    module: null,
    owner: null,
    test_types: [],
    priority: null,
    scenario_layer: null,
    scenario_type: null,
    scenario_tags: [],
  })) {
    Object.assign(e.form, original)
    e.form[key] = value
    await e.save()
  }
  Object.assign(e.form, original)
  e.props.blocked = true
  await e.save()
  assert.equal(count, 0)
  e.cleanup()
})
for (const kind of ['suite', 'case']) {
  test(`${kind} delete fixes target, blocks duplicate confirmation and closes before refreshing`, async () => {
    const pending = deferred(),
      f = setupSuiteList({
        [kind === 'suite' ? 'deleteManualSuite' : 'deleteManualCase']: () => pending.promise,
      })
    const original = record({ requirement_name: 'Requirement' })
    const remove = kind === 'suite' ? f.deleteSuite : f.deleteCase
    remove(original)
    original.id = 99
    remove(record({ id: 12 }))
    assert.equal(f.dialogs.length, 1)
    assert.equal(f.confirming.value, true)
    const dialog = f.dialogs[0].config,
      deleting = dialog.onBeforeOk()
    assert.equal(dialog.onBeforeCancel(), false)
    await dialog.onBeforeOk()
    assert.equal(f.calls.filter(([name]) => name.startsWith('delete')).length, 1)
    assert.equal(f.calls.find(([name]) => name.startsWith('delete'))[1], 11)
    pending.resolve({
      data: kind === 'suite' ? { deleted_count: 1, deleted_suite_ids: [11] } : { count: 1 },
    })
    assert.equal(await deleting, false)
    assert.equal(f.confirming.value, false)
    assert.equal(f.deleting.value, null)
    assert.ok(f.messages.some(([level, text]) => level === 'success' && text === '删除成功'))
    f.cleanup()
  })
  test(`${kind} failed delete retains confirmation and permits retry`, async () => {
    let fail = true
    const f = setupSuiteList({
      [kind === 'suite' ? 'deleteManualSuite' : 'deleteManualCase']: async () => {
        if (fail) throw Error('Offline')
        return {
          data: kind === 'suite' ? { deleted_count: 1, deleted_suite_ids: [11] } : { count: 1 },
        }
      },
    })
    ;(kind === 'suite' ? f.deleteSuite : f.deleteCase)(record())
    await f.dialogs[0].config.onBeforeOk()
    assert.equal(f.confirming.value, true)
    assert.equal(f.deleting.value, null)
    fail = false
    await f.dialogs[0].config.onBeforeOk()
    assert.equal(f.confirming.value, false)
    f.cleanup()
  })
}
for (const change of ['identity', 'environment', 'route', 'navigation', 'stop']) {
  test(`delete ${change} closes old confirmation and ignores late success while retaining physical lock`, async () => {
    const pending = deferred(),
      f = setupSuiteList({ deleteManualSuite: () => pending.promise })
    f.deleteSuite({ id: 11 })
    const deleting = f.dialogs[0].config.onBeforeOk()
    if (change === 'identity') {
      f.user.userId = 2
      f.user.userId = 1
    } else if (change === 'environment') f.user.selected_environment = 2
    else if (change === 'route') {
      f.route.path = '/other'
      f.route.fullPath = '/other'
    } else if (change === 'navigation')
      f.onNavigationFilterChange({ projectProduct: 9, module: null })
    else {
      f.hooks.stop.forEach((fn) => fn())
      f.hooks.activate.forEach((fn) => fn())
    }
    await flush()
    f.deleteSuite({ id: 12 })
    assert.equal(f.dialogs.length, 1)
    assert.equal(f.confirming.value, false)
    assert.notEqual(f.deleting.value, null)
    pending.resolve({ data: { deleted_count: 1, deleted_suite_ids: [11] } })
    await deleting
    assert.equal(f.deleting.value, null)
    assert.equal(
      f.messages.some(([level]) => level === 'success'),
      false
    )
    f.cleanup()
  })
}
test('cancelled confirmation cannot later submit through its stale callback', async () => {
  const f = setupSuiteList()
  f.deleteSuite({ id: 11 })
  f.dialogs[0].handle.close()
  await f.dialogs[0].config.onBeforeOk()
  assert.equal(
    f.calls.some(([name]) => name.startsWith('delete')),
    false
  )
  f.cleanup()
})
test('save, overview unlink and open editors block conflicting parent mutations', () => {
  const f = setupSuiteList(),
    opened = []
  f.suiteEditor.value = { open: (...args) => opened.push(args) }
  f.caseEditor.value = { open: (...args) => opened.push(args) }
  for (const flag of [f.suiteSaving, f.caseSaving, f.overviewBusy]) {
    flag.value = true
    f.openSuite(record())
    f.openSuiteVersion(record())
    f.openCase(record())
    f.deleteSuite(record())
    f.goSuite({ id: 11 })
    flag.value = false
  }
  assert.equal(opened.length, 0)
  assert.equal(f.dialogs.length, 0)
  f.caseVisible.value = true
  f.deleteCase(record())
  f.openSuite(record())
  assert.equal(opened.length, 0)
  f.caseVisible.value = false
  f.suiteEditorVisible.value = true
  f.openCase(record())
  f.deleteSuite(record())
  assert.equal(opened.length, 0)
  assert.equal(f.dialogs.length, 0)
  f.suiteEditorVisible.value = false
  f.openSuite(record())
  assert.equal(opened.length, 1)
  f.cleanup()
})
test('deletion acknowledgment is checked and refresh failure is reported separately from committed deletion', async () => {
  let valid = false
  const f = setupSuiteList({
    deleteManualSuite: async () => ({
      data: { deleted_count: 1, deleted_suite_ids: [valid ? 11 : 99] },
    }),
    getManualSuite: async () => {
      throw Error('Read failed')
    },
  })
  f.deleteSuite({ id: 11 })
  await f.dialogs[0].config.onBeforeOk()
  assert.equal(f.confirming.value, true)
  assert.equal(
    f.messages.some(([level]) => level === 'success'),
    false
  )
  valid = true
  await f.dialogs[0].config.onBeforeOk()
  assert.equal(f.confirming.value, false)
  assert.ok(f.messages.some(([, text]) => text.includes('删除已完成，列表读取失败')))
  f.cleanup()
})
test('last row deletion moves back one page while retaining filters', async () => {
  const f = setupSuiteList()
  f.suites.value = [{ id: 11 }]
  f.pagination.page = 3
  f.conditionItems[0].value = 'Original filter'
  f.deleteSuite({ id: 11 })
  await f.dialogs[0].config.onBeforeOk()
  assert.equal(f.calls.find(([name]) => name === 'getManualSuite')[1].page, 2)
  assert.equal(
    f.calls.find(([name]) => name === 'getManualSuite')[1].requirement_name,
    'Original filter'
  )
  f.cleanup()
})
test('new editor script, template and styles compile', () => {
  const filename = path.join(base, 'components/SuiteListCaseEditor.vue'),
    source = readFileSync(filename, 'utf8')
  const { descriptor, errors } = parse(source)
  assert.deepEqual(errors, [])
  const script = compileScript(descriptor, { id: 'suite-list-case-editor' })
  assert.deepEqual(
    compileTemplate({
      source: descriptor.template.content,
      filename,
      id: 'suite-list-case-editor',
      compilerOptions: { bindingMetadata: script.bindings },
    }).errors,
    []
  )
  for (const style of descriptor.styles)
    assert.deepEqual(
      compileStyle({ source: style.content, filename, id: 'suite-list-case-editor', scoped: true })
        .errors,
      []
    )
})

for (const kind of ['Suite', 'Case']) {
  test(`${kind} saved refresh does not report an obsolete read failure after context changes`, async () => {
    const pending = deferred(),
      context = vue.ref('one'),
      messages = []
    const saved = method(
      `on${kind}Saved`,
      {
        listGeneration: 1,
        listContextKey: context,
        usersActive: true,
        [kind === 'Suite' ? 'loadSuites' : 'loadCases']: () => pending.promise,
        Message: { error: (text) => messages.push(text) },
      },
      path.join(base, 'index.vue')
    )
    const reading = saved()
    context.value = 'two'
    pending.resolve(false)
    await reading
    assert.deepEqual(messages, [])
  })
}
