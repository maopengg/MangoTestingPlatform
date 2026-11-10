import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import * as vue from 'vue'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'

const base = path.resolve('src/views/functional-test/suite/details')
const record = (overrides = {}) => ({
  id: 11,
  suite: { id: 1 },
  case_no: 'CASE-1',
  title: 'Example',
  version_no: 3,
  project_product: { id: 2 },
  module: { id: 3 },
  owner: { id: 4, name: 'Owner' },
  priority: 0,
  test_types: [0],
  scenario_layer: 0,
  scenario_type: 0,
  scenario_tags: ['routine_regression'],
  precondition: '',
  test_point: 'Scenario',
  test_data: '',
  remark: '',
  ...overrides,
})
function create(name, api = {}, extra = {}) {
  return harness(
    name,
    name === 'SuiteCaseEditor'
      ? 'open,save,cancel,form,visible,saving,saveError,usersError,usersLoading,ownerOptions,loadUsers,onProductChange'
      : 'open,save,onVisibleChange,form,visible,saving,saveError',
    {
      base,
      props: {
        suiteId: 1,
        contextKey: 'one',
        available: true,
        blocked: false,
        defaults: { productId: 2, moduleId: 3, ownerId: 4 },
        typeOptions: [],
      },
      api: {
        getUserName: async () => ({ data: [{ key: 4, title: 'Owner' }] }),
        postManualCase: async () => ({ data: { id: 11, suite: 1 } }),
        putManualCase: async () => ({ data: { id: 11, suite: 1 } }),
        postManualAutomationBind: async (p) => ({ data: { id: 50, manual_case: p.case_id, ...p } }),
        ...api,
      },
      ...extra,
    }
  )
}
const editor = (api, extra) => create('SuiteCaseEditor', api, extra)
const binding = (api, extra) => create('SuiteAutomationBinding', api, extra)

test('editing maps only exposed fields and isolates arrays from the original record', async () => {
  let body
  const e = editor({
    putManualCase: async (p) => {
      body = p
      return { data: { id: 11, suite: 1 } }
    },
  })
  const original = record({
    update_user: 99,
    bindings: [{ id: 3 }],
    category_level_1: 'Keep',
    test_steps: [{ action: 'Keep' }],
  })
  e.open(original)
  e.form.test_types.push(1)
  e.form.scenario_tags.push('smoke')
  assert.deepEqual(original.test_types, [0])
  assert.deepEqual(original.scenario_tags, ['routine_regression'])
  await e.save()
  assert.equal(body.version_no, 3)
  assert.equal(body.suite, 1)
  assert.equal(body.project_product, 2)
  assert.equal(body.module, 3)
  assert.equal(body.owner, 4)
  for (const field of ['bindings', 'category_level_1', 'test_steps', 'update_user'])
    assert.equal(field in body, false)
  e.close()
})
test('new draft resets id/version and takes current defaults', async () => {
  let body
  const e = editor({
    postManualCase: async (p) => {
      body = p
      return { data: { id: 12, suite: 1 } }
    },
  })
  e.open(record())
  e.cancel()
  e.open()
  assert.equal(e.form.id, null)
  assert.equal(e.form.version_no, null)
  assert.equal(e.form.project_product, 2)
  assert.equal(e.form.module, 3)
  assert.equal(e.form.owner, 4)
  Object.assign(e.form, {
    case_no: 'NEW',
    title: 'New',
    test_point: 'Scenario',
    scenario_tags: ['smoke'],
  })
  await e.save()
  assert.equal('id' in body, false)
  assert.equal('version_no' in body, false)
  e.close()
})
test('cancel and reopen restore committed values rather than unsaved edits', () => {
  const e = editor()
  const original = record()
  e.open(original)
  e.form.title = 'Draft'
  e.cancel()
  e.open(original)
  assert.equal(e.form.title, 'Example')
  assert.equal(e.form.priority, 0)
  e.close()
})
test('cascade input submits real product ID and only product change clears module', async () => {
  let body
  const e = editor({
    putManualCase: async (p) => {
      body = p
      return { data: { id: 11, suite: 1 } }
    },
  })
  e.open(record())
  e.onProductChange([8, 2])
  assert.equal(e.form.module, 3)
  e.form.project_product = [8, 5]
  e.onProductChange([8, 5])
  assert.equal(e.form.module, null)
  e.form.module = 9
  await e.save()
  assert.equal(body.project_product, 5)
  assert.equal(body.module, 9)
  e.close()
})
test('all existing required fields remain validated and enum zero remains valid', async () => {
  let writes = 0
  const e = editor({
    putManualCase: async () => {
      writes++
      return { data: { id: 11, suite: 1 } }
    },
  })
  for (const [key, value] of [
    ['case_no', ' '],
    ['title', ' '],
    ['test_point', ' '],
    ['project_product', null],
    ['module', null],
    ['owner', null],
    ['test_types', []],
    ['scenario_tags', []],
    ['priority', null],
    ['scenario_layer', null],
    ['scenario_type', null],
  ]) {
    e.open(record())
    e.form[key] = value
    assert.equal(await e.save(), false, key)
  }
  assert.equal(writes, 0)
  e.open(record())
  assert.equal(await e.save(), true)
  assert.equal(writes, 1)
  e.close()
})
test('failed save preserves draft/version, releases lock and permits explicit retry', async () => {
  let count = 0
  const e = editor({
    putManualCase: async () => {
      if (++count === 1) throw Error('conflict')
      return { data: { id: 11, suite: 1 } }
    },
  })
  e.open(record())
  e.form.title = 'Edited'
  assert.equal(await e.save(), false)
  assert.equal(e.form.title, 'Edited')
  assert.equal(e.form.version_no, 3)
  assert.equal(e.saveError.value, true)
  assert.equal(e.saving.value, false)
  assert.equal(e.visible.value, true)
  assert.equal(await e.save(), true)
  assert.equal(e.visible.value, false)
  assert.equal(e.events.filter(([name]) => name === 'changed').length, 1)
  e.close()
})
test('case save snapshots values and physical lock blocks duplicate, cancellation and reopen', async () => {
  const pending = deferred()
  let writes = 0,
    body
  const e = editor({
    putManualCase: (p) => {
      writes++
      body = p
      return pending.promise
    },
  })
  e.open(record())
  const request = e.save()
  e.form.title = 'Later'
  e.form.scenario_tags.push('smoke')
  e.cancel()
  e.open(record({ id: 12 }))
  await e.save()
  assert.equal(e.visible.value, true)
  assert.equal(e.form.id, 11)
  assert.equal(writes, 1)
  assert.equal(body.title, 'Example')
  assert.deepEqual(body.scenario_tags, ['routine_regression'])
  pending.resolve({ data: { id: 11, suite: 1 } })
  await request
  e.close()
})
test('owner options failure retains original owner label and supports retry', async () => {
  let count = 0
  const e = editor({
    getUserName: async () => {
      if (++count === 1) throw Error('offline')
      return { data: [{ key: 5, title: 'Other' }] }
    },
  })
  e.open(record())
  await flush()
  assert.equal(e.usersError.value, true)
  assert.equal(e.usersLoading.value, false)
  assert.deepEqual(e.ownerOptions.value, [{ key: 4, title: 'Owner' }])
  await e.loadUsers()
  assert.equal(e.usersError.value, false)
  assert.equal(e.ownerOptions.value.find((item) => item.key === 4).title, 'Owner')
  e.close()
})
test('malformed owner response is shown as read failure instead of empty success', async () => {
  const e = editor({ getUserName: async () => ({ data: [{ key: 'bad', title: 'Bad' }] }) })
  e.open(record())
  await flush()
  assert.equal(e.usersError.value, true)
  e.close()
})
test('reopened editor ignores late owner options from previous target', async () => {
  const first = deferred(),
    second = deferred()
  let reads = 0
  const e = editor({ getUserName: () => (++reads === 1 ? first.promise : second.promise) })
  e.open(record())
  e.cancel()
  e.open(record({ id: 12, owner: { id: 5, name: 'New owner' } }))
  second.resolve({ data: [{ key: 6, title: 'Latest' }] })
  await flush()
  first.resolve({ data: [{ key: 7, title: 'Old' }] })
  await flush()
  assert.equal(
    e.ownerOptions.value.some((item) => item.key === 7),
    false
  )
  assert.equal(
    e.ownerOptions.value.some((item) => item.key === 6),
    true
  )
  e.close()
})
for (const name of ['SuiteCaseEditor', 'SuiteAutomationBinding']) {
  for (const [label, mutate] of [
    [
      'identity',
      (e) => {
        e.props.contextKey = 'two'
      },
    ],
    [
      'suite',
      (e) => {
        e.props.suiteId = 2
      },
    ],
    [
      'availability',
      (e) => {
        e.props.available = false
      },
    ],
  ]) {
    test(`${name}: ${label} changes suppress late write success without releasing physical lock early`, async () => {
      const pending = deferred()
      const e = create(name, {
        putManualCase: () => pending.promise,
        postManualAutomationBind: () => pending.promise,
      })
      e.open(record(), 1)
      if (name === 'SuiteAutomationBinding') e.form.automation_case_id = 21
      const request = e.save()
      mutate(e)
      await flush()
      assert.equal(e.visible.value, false)
      assert.equal(e.saving.value, true)
      e.open(record(), 1)
      assert.equal(e.visible.value, false)
      pending.resolve({
        data: { id: 11, suite: 1, manual_case: 11, automation_type: 1, automation_case_id: 21 },
      })
      await request
      assert.equal(e.saving.value, false)
      assert.equal(
        e.events.some(([event]) => event === 'changed'),
        false
      )
      e.close()
    })
  }
  test(`${name}: deactivation ignores late response and allows no new writes`, async () => {
    const pending = deferred()
    const e = create(name, {
      putManualCase: () => pending.promise,
      postManualAutomationBind: () => pending.promise,
    })
    e.open(record(), 1)
    if (name === 'SuiteAutomationBinding') e.form.automation_case_id = 21
    const request = e.save()
    e.close()
    pending.resolve({ data: { id: 11, suite: 1 } })
    await request
    assert.equal(
      e.events.some(([event]) => event === 'changed'),
      false
    )
  })
  test(`${name}: foreign suite, unavailable and other operation busy block opening`, () => {
    const e = create(name)
    e.open(record({ suite: { id: 2 } }), 1)
    assert.equal(e.visible.value, false)
    e.props.blocked = true
    e.open(record(), 1)
    assert.equal(e.visible.value, false)
    e.props.blocked = false
    e.props.available = false
    e.open(record(), 1)
    assert.equal(e.visible.value, false)
    e.close()
  })
}
test('binding keeps requested UI type and defaults target ID to empty on reopen', () => {
  const e = binding()
  e.open(record(), 1)
  assert.equal(e.form.automation_type, 1)
  e.form.automation_case_id = 21
  e.onVisibleChange(false)
  e.open(record(), 0)
  assert.equal(e.form.automation_type, 0)
  assert.equal(e.form.automation_case_id, null)
  e.close()
})
test('binding validates target positive integer and type, including API zero', async () => {
  let writes = 0
  const e = binding({
    postManualAutomationBind: async (p) => {
      writes++
      return { data: { id: 50, manual_case: 11, ...p } }
    },
  })
  e.open(record(), 0)
  for (const value of [null, 0, -1, 1.5, NaN, Infinity]) {
    e.form.automation_case_id = value
    await e.save()
  }
  assert.equal(writes, 0)
  e.form.automation_case_id = 21
  e.form.automation_type = 9
  await e.save()
  assert.equal(writes, 0)
  e.form.automation_type = 0
  await e.save()
  assert.equal(writes, 1)
  e.close()
})
test('binding failure preserves inputs and retry uses snapshotted original target', async () => {
  let writes = 0
  const bodies = []
  const e = binding({
    postManualAutomationBind: async (p) => {
      bodies.push(p)
      if (++writes === 1) throw Error('offline')
      return { data: { id: 50, manual_case: 11, ...p } }
    },
  })
  const original = record()
  e.open(original, 1)
  e.form.automation_case_id = 21
  original.id = 99
  await e.save()
  assert.equal(e.saveError.value, true)
  assert.equal(e.visible.value, true)
  assert.equal(e.form.automation_case_id, 21)
  await e.save()
  assert.equal(bodies[1].case_id, 11)
  assert.equal(e.visible.value, false)
  e.close()
})
test('binding lock prevents duplicate save, cancellation and switching records', async () => {
  const pending = deferred()
  let writes = 0
  const e = binding({
    postManualAutomationBind: () => {
      writes++
      return pending.promise
    },
  })
  e.open(record(), 1)
  e.form.automation_case_id = 21
  const request = e.save()
  e.onVisibleChange(false)
  e.open(record({ id: 12 }), 0)
  await e.save()
  assert.equal(writes, 1)
  assert.equal(e.visible.value, true)
  assert.equal(e.form.automation_type, 1)
  pending.resolve({ data: { id: 50, manual_case: 11, automation_type: 1, automation_case_id: 21 } })
  await request
  e.close()
})
test('bad binding acknowledgement preserves window and does not claim success', async () => {
  const e = binding({
    postManualAutomationBind: async () => ({
      data: { id: 50, manual_case: 99, automation_type: 0, automation_case_id: 21 },
    }),
  })
  e.open(record(), 1)
  e.form.automation_case_id = 21
  await e.save()
  assert.equal(e.saveError.value, true)
  assert.equal(e.visible.value, true)
  assert.equal(
    e.events.some(([event]) => event === 'changed'),
    false
  )
  e.close()
})
test('bad case acknowledgement keeps edited values and does not claim success', async () => {
  const e = editor({ putManualCase: async () => ({ data: { id: 99, suite: 2 } }) })
  e.open(record())
  e.form.title = 'Keep'
  assert.equal(await e.save(), false)
  assert.equal(e.form.title, 'Keep')
  assert.equal(e.visible.value, true)
  e.close()
})
for (const name of ['SuiteCaseEditor', 'SuiteAutomationBinding']) {
  test(`${name}: KeepAlive deactivation and reactivation retain the physical write boundary`, async () => {
    let deactivate, activate
    const pending = deferred()
    const e = create(
      name,
      { putManualCase: () => pending.promise, postManualAutomationBind: () => pending.promise },
      {
        modules: {
          vue: {
            ...vue,
            onActivated: (fn) => {
              activate = fn
            },
            onDeactivated: (fn) => {
              deactivate = fn
            },
            onBeforeUnmount() {},
          },
        },
      }
    )
    e.open(record(), 1)
    if (name === 'SuiteAutomationBinding') e.form.automation_case_id = 21
    const request = e.save()
    deactivate()
    activate()
    e.open(record(), 1)
    assert.equal(e.visible.value, false)
    pending.resolve({ data: { id: 11, suite: 1 } })
    await request
    assert.equal(
      e.events.some(([event]) => event === 'changed'),
      false
    )
    e.open(record(), 1)
    assert.equal(e.visible.value, true)
    e.close()
  })
  test(`${name}: synchronous request setup failure also releases busy state`, async () => {
    const e = create(name, {
      putManualCase: () => {
        throw Error('setup')
      },
      postManualAutomationBind: () => {
        throw Error('setup')
      },
    })
    e.open(record(), 1)
    if (name === 'SuiteAutomationBinding') e.form.automation_case_id = 21
    await e.save()
    assert.equal(e.saving.value, false)
    assert.equal(e.saveError.value, true)
    assert.deepEqual(
      e.events.filter(([event]) => event === 'busy'),
      [
        ['busy', true],
        ['busy', false],
      ]
    )
    e.close()
  })
}
test('case save change notification is followed by physical lock release for deferred parent refresh', async () => {
  const e = editor()
  e.open(record())
  await e.save()
  assert.deepEqual(e.events, [
    ['busy', true],
    ['changed', 1],
    ['busy', false],
  ])
  e.close()
})
test('main page and new window scripts/templates/styles compile', () => {
  for (const file of [
    'index.vue',
    'components/SuiteCaseEditor.vue',
    'components/SuiteAutomationBinding.vue',
  ]) {
    const filename = path.join(base, file),
      { descriptor, errors } = parse(readFileSync(filename, 'utf8'))
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: file })
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename,
        id: file,
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
    for (const style of descriptor.styles)
      assert.deepEqual(
        compileStyle({ source: style.content, filename, id: file, scoped: true }).errors,
        []
      )
  }
})
