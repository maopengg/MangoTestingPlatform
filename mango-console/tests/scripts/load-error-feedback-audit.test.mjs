import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { auditLoadErrorFeedback } from '../../scripts/load-error-feedback-audit.mjs'

test('loading failures use public feedback throughout views and shared components', () => {
  assert.deepEqual(auditLoadErrorFeedback(), [])
})

test('business validation, publication gates and execution result messages remain visible', () => {
  for (const [filename, expression] of [
    ['src/components/business/ExecutionResultHistoryDrawer.vue', 'selectedErrorMessage && !selectedApiResult'],
    ['src/components/reports/UiCaseExecutionResult.vue', 'executionError'],
    ['src/components/business/CasePublicationReviewModal.vue', 'record.error && !record.loadFailed'],
    ['src/views/evaluation/components/DatasetConfigDrawer.vue', 'previewError'],
    ['src/views/evaluation/components/DatasetConfigDrawer.vue', 'error'],
    ['src/components/DataFactory/CaseConfigPanel.vue', 'readonlyError'],
  ]) {
    const source = readFileSync(filename, 'utf8')
    assert.ok(source.includes(`v-if="${expression}"`) || source.includes(`v-else-if="${expression}"`), `${filename}: ${expression}`)
  }
})
