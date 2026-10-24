import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

test('a missing configuration enum invalidates an otherwise populated enum cache', async () => {
  const source = readFileSync(new URL('../src/store/modules/get-enum.ts', import.meta.url), 'utf8')
    .replace(/^import .*\n/gm, '').replace('export const useEnum', 'const useEnum')
  const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
  let requests = 0
  let data
  const options = new Function('defineStore', 'getSystemEnum', 'getSystemEnumShare', compiled + ';return useEnum')(
    (_, config) => config, async () => { requests++; return { data } }, async () => ({ data }),
  )
  const state = options.state()
  for (const [key, value] of Object.entries(state)) {
    if (Array.isArray(value)) state[key] = [{ key: 'example', title: '示例' }]
  }
  for (const [key, action] of Object.entries(options.actions)) state[key] = action.bind(state)
  data = { ...state, api_case_configuration_filter: [{ key: 'has_sql', title: '有 SQL' }] }
  await state.getEnum()
  assert.equal(requests, 1)
  await state.getEnum()
  assert.equal(requests, 1, 'complete cached enums do not refetch')
  state.api_case_configuration_filter = []
  assert.equal(state.hasEnumData(), false)
  await state.getEnum()
  assert.equal(requests, 2)
  assert.deepEqual(state.api_case_configuration_filter, data.api_case_configuration_filter)
})
