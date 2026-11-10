import test from 'node:test'
import assert from 'node:assert/strict'
import path from 'node:path'
import { readFileSync } from 'node:fs'
import * as vue from 'vue'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import { harness, deferred, flush } from './helpers/case-details-harness.mjs'
const base = path.resolve('src/views/functional-test/suite')
const record = (values = {}) => ({
  id: 11,
  requirement: { id: 55 },
  requirement_name: 'Example',
  project_product: { id: 2 },
  module: { id: 3 },
  owner: { id: 4, name: 'Owner' },
  iteration_ref: { id: 5, name: 'Current Sprint' },
  development_owner: { id: 6, name: 'Developer' },
  priority: 0,
  status: 2,
  planned_start_date: '2026-11-01',
  planned_submit_date: '2026-11-05',
  ...values,
})
function editor(api = {}, modules = {}) {
  return harness(
    'SuiteEditorDialog',
    'open,save,onVisibleChange,form,mode,visible,saving,saveError,iterationLoading,iterationError,loadIterations,onProductChange,sprintOptions,userOptions',
    {
      base,
      props: {
        contextKey: 'one',
        blocked: false,
        users: [],
        usersLoading: false,
        usersError: false,
        priorityOptions: [],
        statusOptions: [],
      },
      api: {
        getFunctionalIterations: async () => ({
          data: [{ id: 5, iteration_no: 'SPR-1', name: 'Current Sprint' }],
        }),
        putManualSuite: async () => ({ data: { id: 11, project_product: 2 } }),
        postManualSuite: async () => ({ data: { id: 12, project_product: 2 } }),
        ...api,
      },
      modules,
    }
  )
}
test('edit draft is isolated, nullable fields normalized and zero priority retained', () => {
  const e = editor(),
    original = record({ description: 'Keep', update_user: 99 })
  e.open('edit', original)
  e.form.requirement_name = 'Edited'
  assert.equal(original.requirement_name, 'Example')
  assert.equal(e.form.priority, 0)
  assert.equal(e.form.project_product, 2)
  assert.equal(e.form.module, 3)
  assert.equal(e.form.owner, 4)
  assert.equal('description' in e.form, false)
  assert.equal('update_user' in e.form, false)
  e.close()
})
test('create uses synchronous navigation defaults and does not wait for Sprint request to show', () => {
  const pending = deferred(),
    e = editor({ getFunctionalIterations: () => pending.promise })
  e.open('create', undefined, { projectProduct: 2, module: 3 })
  assert.equal(e.visible.value, true)
  assert.equal(e.iterationLoading.value, true)
  assert.equal(e.form.project_product, 2)
  assert.equal(e.form.module, 3)
  assert.equal(e.form.status, 1)
  assert.equal(e.form.owner, null)
  pending.resolve({ data: [] })
  e.close()
})
test('new version directly copies source fields, resets dates/status and excludes old ID/version', async () => {
  let payload
  const original = record({ version_no: 9, description: 'Readonly', update_user: 8 })
  const e = editor({
    postManualSuite: async (p) => {
      payload = p
      return { data: { id: 12, project_product: 2 } }
    },
  })
  e.open('version', original)
  assert.equal(e.form.requirement_name, 'Example')
  assert.equal(e.form.planned_start_date, null)
  assert.equal(e.form.planned_submit_date, null)
  assert.equal(e.form.status, 1)
  assert.equal(e.form.iteration_ref, 5)
  original.id = 99
  original.requirement.id = 999
  await e.save()
  assert.equal(payload.requirement, 55)
  assert.equal(payload.previous_version, 11)
  for (const key of ['id', 'version_no', 'description', 'update_user'])
    assert.equal(key in payload, false)
  assert.equal(payload.iteration, '')
  e.close()
})
test('editing submits only visible fields without modifying requirement ownership', async () => {
  let payload
  const e = editor({
    putManualSuite: async (p) => {
      payload = p
      return { data: { id: 11, project_product: 2 } }
    },
  })
  e.open('edit', record({ update_time: 'Readonly', case_count: 99 }))
  await e.save()
  assert.equal(payload.id, 11)
  assert.equal(payload.owner, 4)
  for (const key of ['update_time', 'case_count', 'requirement', 'previous_version', 'version_no'])
    assert.equal(key in payload, false)
  assert.deepEqual(
    e.events.filter(([event]) => event === 'visible'),
    [
      ['visible', true],
      ['visible', false],
    ]
  )
  assert.deepEqual(
    e.events.filter(([event]) => event !== 'visible'),
    [
      ['busy', true],
      ['saved', 11],
      ['busy', false],
    ]
  )
  e.close()
})
test('cancel and reopen restores original values and create drops previous edit fields', () => {
  const e = editor()
  e.open('edit', record())
  e.form.requirement_name = 'Draft'
  e.onVisibleChange(false)
  e.open('edit', record())
  assert.equal(e.form.requirement_name, 'Example')
  e.onVisibleChange(false)
  e.open('create')
  assert.equal(e.form.requirement_name, '')
  assert.equal(e.form.iteration_ref, null)
  e.close()
})
test('original owner, developer and Sprint remain visible when options omit them', async () => {
  const e = editor({ getFunctionalIterations: async () => ({ data: [] }) })
  e.open('edit', record())
  await flush()
  assert.equal(e.userOptions.value.find((o) => o.key === 4).title, 'Owner')
  assert.equal(e.userOptions.value.find((o) => o.key === 6).title, 'Developer')
  assert.equal(e.sprintOptions.value.find((o) => o.value === 5).label, 'Current Sprint')
  e.close()
})
test('changing product clears module and Sprint, but initialization echo does not', async () => {
  const e = editor()
  e.open('edit', record())
  e.onProductChange([1, 2])
  assert.equal(e.form.module, 3)
  assert.equal(e.form.iteration_ref, 5)
  e.form.project_product = [1, 9]
  e.onProductChange([1, 9])
  assert.equal(e.form.module, null)
  assert.equal(e.form.iteration_ref, null)
  e.close()
})
test('Sprint responses cannot cross product changes or replace current loading state', async () => {
  const first = deferred(),
    second = deferred()
  let reads = 0
  const e = editor({
    getFunctionalIterations: () => (++reads === 1 ? first.promise : second.promise),
  })
  e.open('edit', record())
  e.form.project_product = 9
  e.onProductChange(9)
  first.resolve({ data: [{ id: 77, name: 'Old' }] })
  await flush()
  assert.equal(e.iterationLoading.value, true)
  assert.equal(
    e.sprintOptions.value.some((o) => o.value === 77),
    false
  )
  second.resolve({ data: [{ id: 88, name: 'New' }] })
  await flush()
  assert.equal(e.sprintOptions.value[0].value, 88)
  e.close()
})
test('Sprint failure leaves editor usable, preserves existing selection and supports retry', async () => {
  let reads = 0
  const e = editor({
    getFunctionalIterations: async () => {
      if (++reads === 1) throw Error('offline')
      return { data: [{ id: 5, name: 'Recovered' }] }
    },
  })
  e.open('edit', record())
  await flush()
  assert.equal(e.iterationError.value, true)
  assert.equal(e.iterationLoading.value, false)
  assert.equal(e.form.iteration_ref, 5)
  assert.equal(e.visible.value, true)
  await e.loadIterations()
  assert.equal(e.iterationError.value, false)
  assert.equal(e.sprintOptions.value[0].label, 'Recovered')
  e.close()
})
test('closing and reopening invalidates pending Sprint request', async () => {
  const first = deferred(),
    second = deferred()
  let reads = 0
  const e = editor({
    getFunctionalIterations: () => (++reads === 1 ? first.promise : second.promise),
  })
  e.open('edit', record())
  e.onVisibleChange(false)
  e.open('create', undefined, { projectProduct: 9, module: null })
  second.resolve({ data: [{ id: 88, name: 'New' }] })
  await flush()
  first.resolve({ data: [{ id: 77, name: 'Old' }] })
  await flush()
  assert.equal(e.sprintOptions.value[0].value, 88)
  e.close()
})
test('empty or malformed Sprint reply is surfaced as failure rather than success', async () => {
  const e = editor({
    getFunctionalIterations: async () => ({ data: [{ id: 'invalid', name: 'Bad' }] }),
  })
  e.open('edit', record())
  await flush()
  assert.equal(e.iterationError.value, true)
  e.close()
})
test('existing required fields prevent submission until corrected', async () => {
  let writes = 0
  const e = editor({
    putManualSuite: async () => {
      writes++
      return { data: { id: 11, project_product: 2 } }
    },
  })
  for (const [key, value] of [
    ['requirement_name', ' '],
    ['project_product', null],
    ['module', null],
    ['owner', null],
    ['iteration_ref', null],
  ]) {
    e.open('edit', record())
    e.form[key] = value
    await e.save()
  }
  assert.equal(writes, 0)
  e.open('edit', record())
  await e.save()
  assert.equal(writes, 1)
  e.close()
})
test('save freezes payload and physical lock prevents duplicate, cancel and reopen', async () => {
  const pending = deferred()
  let writes = 0,
    payload
  const e = editor({
    putManualSuite: (p) => {
      writes++
      payload = p
      return pending.promise
    },
  })
  const original = record()
  e.open('edit', original)
  const request = e.save()
  e.form.requirement_name = 'Later'
  original.id = 99
  e.onVisibleChange(false)
  e.open('create')
  await e.save()
  assert.equal(writes, 1)
  assert.equal(e.visible.value, true)
  assert.equal(payload.id, 11)
  assert.equal(payload.requirement_name, 'Example')
  pending.resolve({ data: { id: 11, project_product: 2 } })
  await request
  e.close()
})
test('save failure keeps draft and releases physical lock for explicit retry', async () => {
  let writes = 0
  const e = editor({
    putManualSuite: async () => {
      if (++writes === 1) throw Error('offline')
      return { data: { id: 11, project_product: 2 } }
    },
  })
  e.open('edit', record())
  e.form.requirement_name = 'Keep'
  await e.save()
  assert.equal(e.visible.value, true)
  assert.equal(e.saveError.value, true)
  assert.equal(e.form.requirement_name, 'Keep')
  assert.equal(e.saving.value, false)
  await e.save()
  assert.equal(e.visible.value, false)
  e.close()
})
test('context change during save suppresses old success without unlocking early', async () => {
  const pending = deferred()
  const e = editor({ putManualSuite: () => pending.promise })
  e.open('edit', record())
  const request = e.save()
  e.props.contextKey = 'two'
  await flush()
  assert.equal(e.visible.value, false)
  assert.equal(e.saving.value, true)
  e.open('create')
  assert.equal(e.visible.value, false)
  pending.resolve({ data: { id: 11, project_product: 2 } })
  await request
  assert.equal(
    e.events.some(([event]) => event === 'saved'),
    false
  )
  e.open('create')
  assert.equal(e.visible.value, true)
  e.close()
})
test('KeepAlive deactivation and activation cannot replay a prior save', async () => {
  let activate, deactivate
  const pending = deferred(),
    e = editor(
      { putManualSuite: () => pending.promise },
      {
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
      }
    )
  e.open('edit', record())
  const request = e.save()
  deactivate()
  activate()
  e.open('create')
  assert.equal(e.visible.value, false)
  pending.resolve({ data: { id: 11, project_product: 2 } })
  await request
  assert.equal(
    e.events.some(([event]) => event === 'saved'),
    false
  )
  e.open('create')
  assert.equal(e.visible.value, true)
  e.close()
})
test('unmount invalidates in-flight options', async () => {
  const pending = deferred(),
    e = editor({ getFunctionalIterations: () => pending.promise })
  e.open('edit', record())
  e.close()
  pending.resolve({ data: [{ id: 88, name: 'Late' }] })
  await flush()
  assert.equal(e.visible.value, false)
  assert.deepEqual(e.sprintOptions.value, [])
})
test('invalid acknowledgement preserves edited values and does not emit success', async () => {
  const e = editor({ putManualSuite: async () => ({ data: { id: 99, project_product: 8 } }) })
  e.open('edit', record())
  await e.save()
  assert.equal(e.visible.value, true)
  assert.equal(e.saveError.value, true)
  assert.equal(
    e.events.some(([event]) => event === 'saved'),
    false
  )
  e.close()
})
test('synchronous request exception also releases busy state', async () => {
  const e = editor({
    putManualSuite: () => {
      throw Error('setup')
    },
  })
  e.open('edit', record())
  await e.save()
  assert.equal(e.saving.value, false)
  assert.deepEqual(
    e.events.filter(([event]) => event !== 'visible'),
    [
      ['busy', true],
      ['busy', false],
    ]
  )
  e.close()
})
test('blocked edits and incomplete version source cannot open a new write window', () => {
  const e = editor()
  e.props.blocked = true
  e.open('edit', record())
  assert.equal(e.visible.value, false)
  e.props.blocked = false
  e.open('version', record({ requirement: null }))
  assert.equal(e.visible.value, false)
  e.close()
})
test('main page and editor scripts/templates/styles compile', () => {
  for (const file of ['index.vue', 'components/SuiteEditorDialog.vue']) {
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
