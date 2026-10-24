import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import test from 'node:test'
import ts from 'typescript'

const source = await readFile(new URL('../src/views/evaluation/case/config.ts', import.meta.url), 'utf8')
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2020 },
}).outputText
const { defaultCaseConfig, isTerminal, pythonTargetTemplate, normalizeCaseInput, caseColumns, configSteps } = await import(`data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`)

test('Case forms have independent nested configurations', () => {
  const first = defaultCaseConfig()
  const second = defaultCaseConfig()
  first.target.parameters.answer = 'changed'
  first.grading.default_graders[0].threshold = 20
  first.data_selection.item_ids.push(101)
  assert.deepEqual(second.target.parameters, {})
  assert.equal(second.grading.default_graders[0].threshold, 100)
  assert.deepEqual(second.data_selection.item_ids, [])
  assert.equal(second.schema_version, 1)
  assert.equal(second.execution.repeat_count, 1)
})

test('execution polling stops only at terminal states', () => {
  for (const state of ['pending', 'preparing', 'running', 'aggregating', 'stopping', undefined]) assert.equal(isTerminal(state), false)
  for (const state of ['completed', 'failed', 'stopped']) assert.equal(isTerminal(state), true)
})

test('new cases select managed interfaces without manual release identifiers', () => {
  assert.equal(defaultCaseConfig().target.type, 'api_info')
  assert.equal(defaultCaseConfig().target.version_ref, null)
  assert.match(pythonTargetTemplate, /def main\(input, context\)/)
})

test('saved aliases become paths and grader references follow extracted values', () => {
  const source = defaultCaseConfig()
  source.mapping.output = { mode: 'select', selectors: { first: 'json.items.0.content' }, collections: { all: { path: 'json.items', value_path: '$', cardinality: 'many' } } }
  source.grading.default_graders[0].parameters = { actual_path: 'all.0.content' }
  source.answering = { memories_path: 'all', question_path: 'query' }
  const result = normalizeCaseInput(source)
  assert.deepEqual(result.mapping.output, { paths: ['$.json.items[0].content', '$.json.items'] })
  assert.equal(result.grading.default_graders[0].parameters.actual_path, '1.0.content')
  assert.deepEqual(result.answering, { question_path: 'query' })
  assert.equal(source.grading.default_graders[0].parameters.actual_path, 'all.0.content')
})

test('decision policy removes duplicate score thresholds and keeps explicit run requirements', () => {
  const source = defaultCaseConfig()
  source.grading.aggregation = { pass_score: 100, warning_score: 70, invalid_policy: 'failed', min_valid_rate: 1, min_effect_pass_rate: 0.85 }
  const normalized = normalizeCaseInput(source)
  assert.deepEqual(normalized.grading.aggregation, { policy_version: 2, min_valid_rate: 1, min_effect_pass_rate: 0.85 })
  assert.equal(source.grading.aggregation.pass_score, 100)
})

test('scenario description is listed after case name and is not a configuration step', () => {
  assert.equal(caseColumns[caseColumns.findIndex(item => item.key === 'name') + 1].key, 'description')
  assert.equal(configSteps.some(item => item.key === 'assessment'), false)
  const config = { ...defaultCaseConfig(), assessment: { objective: 'legacy' } }
  assert.equal('assessment' in normalizeCaseInput(config), false)
  assert.equal(config.assessment.objective, 'legacy')
})
