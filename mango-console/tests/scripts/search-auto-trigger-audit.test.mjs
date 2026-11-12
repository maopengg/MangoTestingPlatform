import test from 'node:test'
import assert from 'node:assert/strict'
import { auditAutomaticSearch, auditAutomaticSearchSource } from '../../scripts/search-auto-trigger-audit.mjs'

test('all repaired search controls use the shared 500ms scheduling boundary', () => {
  const result = auditAutomaticSearch()
  assert.equal(result.controls, 67)
  assert.deepEqual(result.issues, [])
})

test('search audit detects missing events without touching editor controls', () => {
  const result = auditAutomaticSearchSource('<template><TableHeader><a-input v-model="name" /></TableHeader><ModalDialog><a-input v-model="draft.name" /></ModalDialog></template>', 'example.vue')
  assert.equal(result.count, 1)
  assert.equal(result.issues.length, 4)
})
