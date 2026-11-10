import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse } from '@vue/compiler-sfc'

const source = readFileSync(new URL('../../../../../src/views/apitest/case/details/index.vue', import.meta.url), 'utf8')
const script = parse(source).descriptor.scriptSetup.content
const ast = ts.createSourceFile('details.ts', script, ts.ScriptTarget.Latest, true)

function loadFunction(name, dependencies) {
  let declaration = ast.statements.find(node => ts.isFunctionDeclaration(node) && node.name?.text === name)
  if (!declaration) {
    declaration = ast.statements.filter(ts.isVariableStatement)
      .flatMap(node => [...node.declarationList.declarations]).find(node => node.name.getText(ast) === name)
  }
  assert.ok(declaration, `${name} must exist`)
  const code = ts.transpileModule(
    ts.isFunctionDeclaration(declaration) ? declaration.getText(ast) : `const ${declaration.getText(ast)}`,
    { compilerOptions: { target: ts.ScriptTarget.ES2022 } },
  ).outputText
  return new Function(...Object.keys(dependencies), `${code}; return ${name}`)(...Object.values(dependencies))
}

test('published and editing results ignore execution environment but retain revision isolation', async () => {
  for (const environment of [0, 2, 3, null]) {
    for (const version of [{ revisionId: 4205, releaseId: 3549 }, null]) {
      const calls = []
      const resultData = { steps: [], test_env: 2 }
      const getLatest = loadFunction('getLatestCaseExecutionResult', {
        apiCaseId: { value: 2014 },
        userStore: { selected_environment: environment },
        selectedExecutionVersion: { value: version },
        getExecutionResultList: async query => {
          calls.push(query)
          return { data: [{ id: 27064, test_env: 2 }] }
        },
        getExecutionResultDetailResolved: async id => {
          assert.equal(id, 27064)
          return { data: { result_data: resultData } }
        },
      })
      const result = await getLatest()
      assert.deepEqual(calls, [{
        target_type: 'api_case', target_id: 2014, page: 1, pageSize: 1,
        ...(version ? { revision_id: 4205 } : { revision_id_isnull: 1 }),
      }])
      assert.equal(result.summary.test_env, 2)
      assert.equal(result.resultData, resultData)
    }
  }
})

test('case execution still uses the selected execution environment', async () => {
  const calls = []
  const noop = () => {}
  const run = loadFunction('caseRun', {
    apiCaseId: { value: 2014 },
    selectedExecutionVersion: { value: { revisionId: 4205, releaseId: 3549 } },
    userStore: { selected_environment: 3 },
    caseExecutionActive: { value: false },
    caseRequestPending: { value: false },
    caseRunning: { value: false },
    lastTraceId: { value: '' },
    clearAssertionVerifyResults: noop,
    startCaseRunLoadingLimit: noop,
    stopCaseRunLoadingLimit: noop,
    syncCaseRunRefreshByRows: noop,
    caseSteps: { value: [] },
    requests: { capture: () => () => true },
    saveStepDebugContextId: noop,
    refreshCaseDetailAfterRun: async () => {},
    Message: { success: noop },
    getApiCaseRunRaw: async (...args) => {
      calls.push(args)
      return { data: { code: 200, data: {} } }
    },
  })
  await run(null)
  assert.deepEqual(calls, [[2014, 3, null, 4205, 3549]])
})
