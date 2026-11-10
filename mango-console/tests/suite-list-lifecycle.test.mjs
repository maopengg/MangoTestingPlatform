import test from 'node:test'
import assert from 'node:assert/strict'
import { deferred, flush } from './helpers/case-details-harness.mjs'
import { setupSuiteList as setup, page } from './helpers/suite-list-harness.mjs'
test('suite and case loading are independent; zero total is retained', async () => {
  const pending = deferred(),
    f = setup({ getManualSuite: () => pending.promise, getManualCase: async () => page([], 0) })
  const reading = f.loadSuites()
  await f.loadCases()
  assert.equal(f.suiteLoading.value, true)
  assert.equal(f.caseLoading.value, false)
  assert.equal(f.casePagination.pageCount, 0)
  pending.resolve(page([{ id: 1 }], 12))
  await reading
  assert.equal(f.pagination.pageCount, 12)
  assert.equal(f.suiteLoading.value, false)
  f.cleanup()
})
for (const kind of ['suite', 'case']) {
  test(`${kind} read failure preserves current data and allows retry`, async () => {
    let failing = false
    const name = kind === 'suite' ? 'getManualSuite' : 'getManualCase'
    const f = setup({
      [name]: async () => {
        if (failing) throw Error('offline')
        return page([{ id: 1 }])
      },
    })
    const load = kind === 'suite' ? f.loadSuites : f.loadCases
    const rows = kind === 'suite' ? f.suites : f.cases
    const error = kind === 'suite' ? f.suiteError : f.caseError
    assert.equal(await load(), true)
    failing = true
    assert.equal(await load(), false)
    assert.equal(rows.value[0].id, 1)
    assert.equal(error.value, true)
    failing = false
    await load()
    assert.equal(error.value, false)
    f.cleanup()
  })
  test(`${kind} latest request wins without stale loading/error changes`, async () => {
    const a = deferred(),
      b = deferred()
    let count = 0
    const f = setup({
      [kind === 'suite' ? 'getManualSuite' : 'getManualCase']: () =>
        (++count === 1 ? a : b).promise,
    })
    const load = kind === 'suite' ? f.loadSuites : f.loadCases
    const first = load(),
      second = load()
    b.resolve(page([{ id: 2 }]))
    await second
    a.reject(Error('old failure'))
    await first
    assert.equal((kind === 'suite' ? f.suites : f.cases).value[0].id, 2)
    assert.equal((kind === 'suite' ? f.suiteError : f.caseError).value, false)
    assert.equal((kind === 'suite' ? f.suiteLoading : f.caseLoading).value, false)
    f.cleanup()
  })
}
for (const field of ['userId', 'roleId', 'token', 'selected_environment']) {
  test(`${field} A-B-A invalidates all pending rows, options and windows`, async () => {
    const pending = deferred()
    const f = setup({ getManualSuite: () => pending.promise, getManualCase: () => pending.promise })
    const reading = Promise.all([f.loadSuites(), f.loadCases(), f.loadRequirementOptions()])
    f.overviewVisible.value = true
    f.caseVisible.value = true
    const old = f.user[field]
    f.user[field] = field === 'token' ? 'example-other-token' : 2
    f.user[field] = old
    pending.resolve(page([{ id: 1, requirement_name: 'Old' }]))
    await reading
    assert.deepEqual(f.suites.value, [])
    assert.deepEqual(f.cases.value, [])
    assert.deepEqual(f.requirementOptions.value, [])
    assert.equal(f.overviewVisible.value, false)
    assert.equal(f.caseVisible.value, false)
    assert.equal(f.suiteLoading.value, false)
    assert.equal(f.requirementLoading.value, false)
    f.cleanup()
  })
}
test('deactivation ignores a late read and activation reloads; unmount prevents further reads', async () => {
  const pending = deferred()
  let first = true
  const f = setup({
    getManualSuite: () => {
      if (first) {
        first = false
        return pending.promise
      }
      return page([{ id: 2 }])
    },
  })
  const reading = f.loadSuites()
  f.hooks.stop.forEach((fn) => fn())
  pending.resolve(page([{ id: 1 }]))
  await reading
  assert.deepEqual(f.suites.value, [])
  f.hooks.activate.forEach((fn) => fn())
  await flush()
  assert.equal(f.suites.value[0].id, 2)
  f.hooks.unmount.forEach((fn) => fn())
  const count = f.calls.length
  await f.loadSuites()
  await f.loadCases()
  await f.loadRequirementOptions()
  assert.equal(f.calls.length, count)
  f.cleanup()
})
test('route exit clears state and ignores pending requests', async () => {
  const pending = deferred(),
    f = setup({ getManualSuite: () => pending.promise })
  const reading = f.loadSuites()
  f.route.path = '/other/index'
  f.route.fullPath = '/other/index'
  pending.resolve(page([{ id: 1 }]))
  await reading
  assert.deepEqual(f.suites.value, [])
  f.cleanup()
})
test('input edits during pending read do not show results for the old query', async () => {
  const pending = deferred(),
    f = setup({ getManualSuite: () => pending.promise })
  const reading = f.loadSuites()
  f.conditionItems[0].value = 'Edited'
  pending.resolve(page([{ id: 1 }]))
  await reading
  assert.deepEqual(f.suites.value, [])
  assert.equal(f.suiteLoading.value, false)
  f.cleanup()
})
test('search resets page while pagination reload preserves it; filters use real leaf product ID and zero', async () => {
  const f = setup()
  f.pagination.page = 7
  f.conditionItems.find((item) => item.key === 'sync_status').value = [0, 1]
  await f.searchSuites()
  assert.equal(f.calls.at(-1)[1].page, 1)
  assert.equal(f.calls.at(-1)[1].sync_status__in, '0,1')
  f.pagination.page = 3
  await f.loadSuites()
  assert.equal(f.calls.at(-1)[1].page, 3)
  f.caseFilter.project_product = [1, '9']
  f.caseFilter.scenario_type = 0
  const query = f.buildCaseQuery()
  assert.equal(query.project_product, 9)
  assert.equal(query.scenario_type, 0)
  f.cleanup()
})
test('bounded requirement options preserve current selection and discard old product responses', async () => {
  const pending = deferred()
  let first = true
  const f = setup({
    getManualSuite: () => {
      if (first) {
        first = false
        return pending.promise
      }
      return page([
        { id: 2, requirement_name: 'New' },
        { id: 3, requirement_name: 'New' },
      ])
    },
  })
  f.caseFilter.requirement_name = 'Selected outside first page'
  const old = f.loadRequirementOptions()
  f.caseFilter.project_product = 9
  await f.loadRequirementOptions()
  pending.resolve(page([{ id: 1, requirement_name: 'Old' }]))
  await old
  assert.deepEqual(
    f.requirementOptions.value.map((item) => item.value),
    ['New', 'Selected outside first page']
  )
  assert.equal(f.caseFilter.requirement_name, 'Selected outside first page')
  assert.equal(f.requirementLoading.value, false)
  f.cleanup()
})
test('requirement option failure is local and retryable', async () => {
  let fail = true
  const f = setup({
    getManualSuite: async () => {
      if (fail) throw Error('offline')
      return page([{ id: 1, requirement_name: 'Recovered' }])
    },
  })
  await f.loadRequirementOptions()
  assert.equal(f.requirementError.value, true)
  assert.equal(f.requirementLoading.value, false)
  fail = false
  await f.loadRequirementOptions()
  assert.equal(f.requirementError.value, false)
  assert.equal(f.requirementOptions.value[0].value, 'Recovered')
  f.cleanup()
})
test('malformed list response is an error rather than an empty successful result', async () => {
  const f = setup({ getManualSuite: async () => ({ data: { id: 1 }, totalSize: 1 }) })
  assert.equal(await f.loadSuites(), false)
  assert.equal(f.suiteError.value, true)
  assert.equal(f.suiteLoading.value, false)
  f.cleanup()
})

test('initial mount reads the list without waiting for slow enums or failed user options', async () => {
  const pending = deferred()
  const f = setup(
    {
      getUserName: async () => {
        throw Error('User read failed')
      },
    },
    {
      enums: () => pending.promise,
      products: async () => {
        throw Error('Navigation unavailable')
      },
    }
  )
  f.hooks.mount.forEach((fn) => fn())
  await flush()
  assert.equal(f.suites.value[0].id, 1)
  assert.equal(f.suiteLoading.value, false)
  assert.equal(f.usersError.value, true)
  assert.equal(f.enumsLoading.value, true)
  pending.resolve()
  await flush()
  assert.equal(f.enumsLoading.value, false)
  f.cleanup()
})
test('enum failure is local and retryable without resetting loaded records', async () => {
  let fail = true
  const f = setup(
    {},
    {
      enums: async () => {
        if (fail) throw Error('Enums unavailable')
      },
    }
  )
  await f.loadPage()
  assert.equal(f.enumsError.value, true)
  assert.equal(f.enumsLoading.value, false)
  assert.equal(f.suites.value[0].id, 1)
  fail = false
  await f.loadEnums()
  assert.equal(f.enumsError.value, false)
  assert.equal(f.suites.value[0].id, 1)
  f.cleanup()
})
test('late enum failure after identity roundtrip does not mark the new context failed', async () => {
  const pending = deferred(),
    f = setup({}, { enums: () => pending.promise })
  const reading = f.loadEnums()
  f.user.roleId = 2
  f.user.roleId = 1
  pending.reject(Error('Old failure'))
  await reading
  assert.equal(f.enumsError.value, false)
  assert.equal(f.enumsLoading.value, false)
  f.cleanup()
})
test('user options normalize numeric IDs and ignore context roundtrip', async () => {
  const pending = deferred()
  let first = true
  const f = setup({
    getUserName: async () => (first ? pending.promise : { data: [{ key: '7', title: 'Owner' }] }),
  })
  const old = f.loadUsers()
  f.user.userId = 2
  f.user.userId = 1
  first = false
  await f.loadUsers()
  pending.resolve({ data: [{ key: 9, title: 'Old owner' }] })
  await old
  assert.deepEqual(f.userOptions.value, [{ key: 7, title: 'Owner' }])
  assert.equal(f.usersLoading.value, false)
  f.cleanup()
})
test('malformed user options fail locally without replacing the last valid options', async () => {
  let invalid = false
  const f = setup({
    getUserName: async () => ({ data: [{ key: 7, title: invalid ? null : 'Owner' }] }),
  })
  await f.loadUsers()
  invalid = true
  await f.loadUsers()
  assert.equal(f.usersError.value, true)
  assert.equal(f.usersLoading.value, false)
  assert.equal(f.userOptions.value[0].title, 'Owner')
  invalid = false
  await f.loadUsers()
  assert.equal(f.usersError.value, false)
  f.cleanup()
})
test('mount and initial activation read once; cached return refreshes all independent data', async () => {
  let enums = 0
  const f = setup(
    {},
    {
      enums: async () => {
        enums++
      },
    }
  )
  f.hooks.mount.forEach((fn) => fn())
  f.hooks.activate.forEach((fn) => fn())
  await flush()
  assert.equal(f.calls.filter(([name]) => name === 'getManualSuite').length, 1)
  assert.equal(enums, 1)
  f.hooks.stop.forEach((fn) => fn())
  f.hooks.activate.forEach((fn) => fn())
  await flush()
  assert.equal(f.calls.filter(([name]) => name === 'getManualSuite').length, 2)
  assert.equal(enums, 2)
  f.cleanup()
})
test('finite record mappings preserve displayed data and actual binding IDs without spreading unknown fields', () => {
  const f = setup(),
    mapping = f.load('list-records.ts')
  const suite = mapping.parseSuiteListRow({
    id: 1,
    status: 0,
    priority: 0,
    requirement_name: 'Requirement',
    requirement: { id: 9, requirement_key: 'REQ-9' },
    project_product: { id: 2, name: 'Product', project: { id: 10, name: 'Project' } },
    module: { id: 3, name: 'Child', full_path: 'Parent/Child', level: 2 },
    owner: { id: 4, name: 'Owner' },
    iteration_ref: { id: 5, name: 'Sprint' },
    test_metrics: { total: 10, executed: 4, progress: 40, pass_rate: 75 },
    sync_status: 0,
    last_sync_time: '2026-11-07 10:00:00',
    unrelated_blob: { keepOut: true },
  })
  assert.equal(suite.priority, 0)
  assert.equal(suite.status, 0)
  assert.equal(suite.module.full_path, 'Parent/Child')
  assert.equal(suite.iteration_ref.name, 'Sprint')
  assert.equal(suite.test_metrics.progress, 40)
  assert.equal('unrelated_blob' in suite, false)
  const item = mapping.parseCaseListRow({
    id: 11,
    version_no: 2,
    suite: null,
    test_types: [0],
    scenario_tags: ['smoke'],
    bindings: [
      { id: 6, automation_type: 0, api_case: 7, ui_case: null, automation_case_id: 70 },
      { id: 8, automation_type: 1, ui_case: 9, automation_case_id: 90 },
    ],
  })
  assert.equal(item.suite, null)
  assert.deepEqual(item.test_types, [0])
  assert.deepEqual(
    f.automationCaseLinks(item).map((value) => value.id),
    [7, 9]
  )
  assert.equal(f.enumTitle([], 0), 0)
  f.cleanup()
})

test('navigation changes refresh the list without refetching identity-wide user options', async () => {
  const f = setup()
  f.hooks.mount.forEach((fn) => fn())
  await flush()
  const count = f.calls.filter(([name]) => name === 'getUserName').length
  f.onNavigationFilterChange({ projectProduct: 9, module: 3 })
  await flush()
  assert.equal(f.calls.filter(([name]) => name === 'getUserName').length, count)
  assert.equal(f.calls.filter(([name]) => name === 'getManualSuite').at(-1)[1].project_product, 9)
  f.cleanup()
})
