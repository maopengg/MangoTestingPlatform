import assert from 'node:assert/strict'
import test from 'node:test'
import { hasOwnershipFormatter, ownershipFormattingSource } from '../scripts/lib/navigation-ownership-source.mjs'

const vue = usage => `<script setup lang="ts">import { normalizeRow as normalize } from './rows'; ${usage}</script>`
const helper = `import { formatProjectProductPath, formatModulePath } from '@/utils/business-format';
export function normalizeRow(value: unknown) { const source = value; return { product: formatProjectProductPath(source.project_product), module: formatModulePath(source.module) } }`
test('audit follows the used exported list normalizer and supports local import aliases', () => {
  const reads = []
  const source = ownershipFormattingSource('/fixture/page/index.vue', vue('useCaseLibraryList({normalize})'), file => { reads.push(file); return helper })
  assert.equal(reads[0], '/fixture/page/rows.ts')
  assert.equal(hasOwnershipFormatter(source, 'project_product'), true)
  assert.equal(hasOwnershipFormatter(source, 'module'), true)
})
test('unused imports and unrelated normalize configuration cannot satisfy the audit', () => {
  for (const usage of ['', 'otherList({normalize})']) {
    let reads = 0
    const source = ownershipFormattingSource('/fixture/page/index.vue', vue(usage), () => { ++reads; return helper })
    assert.equal(reads, 0); assert.equal(hasOwnershipFormatter(source, 'project_product'), false)
  }
})
test('missing exports, missing files and counterfeit formatter imports remain failures', () => {
  for (const code of [helper.replace('export function', 'function'), helper.replace('@/utils/business-format', './fake')]) {
    const source = ownershipFormattingSource('/fixture/page/index.vue', vue('useCaseLibraryList({normalize})'), () => code)
    assert.equal(hasOwnershipFormatter(source, 'module'), false)
  }
  const source = ownershipFormattingSource('/fixture/page/index.vue', vue('useCaseLibraryList({normalize})'), () => { throw Error('Missing') })
  assert.equal(hasOwnershipFormatter(source, 'module'), false)
})
test('a used helper missing one formatter still fails that ownership field', () => {
  const code = helper.replace('formatModulePath(source.module)', 'source.module.name')
  const source = ownershipFormattingSource('/fixture/page/index.vue', vue('useCaseLibraryList({normalize})'), () => code)
  assert.equal(hasOwnershipFormatter(source, 'project_product'), true); assert.equal(hasOwnershipFormatter(source, 'module'), false)
  assert.equal(hasOwnershipFormatter('formatModulePath(record.module_data)', 'module'), true)
})
