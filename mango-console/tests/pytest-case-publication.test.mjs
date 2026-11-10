import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse } from '@vue/compiler-sfc'

const root = new URL('../', import.meta.url)
const read = path => fs.readFileSync(new URL(path, root), 'utf8')
const source = read('src/views/pytest/case/index.vue')
const file = ts.createSourceFile('setup.ts', parse(source).descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
const config = ts.createSourceFile('config.ts', read('src/views/pytest/case/config.ts'), ts.ScriptTarget.Latest, true)
function functionSource(name, tree = file) {
  const declaration = tree.statements.find(node => ts.isFunctionDeclaration(node) && node.name.text === name)
  return ts.transpileModule(declaration.getText(tree).replace('export function', 'function'), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
}

test('Pytest search remains in the workbench and uses per-instance configuration', () => {
  assert.match(source, /<template #search>/)
  assert.doesNotMatch(source, /:show-search="false"|<template #tabs>/)
  assert.match(source, /@search="onSearchRefresh"/)
  assert.match(source, /const conditionItems = createSearchItems\(\)/)
  assert.match(read('src/views/pytest/case/config.ts'), /enableMultiSelectSearch\(items\)/)
  assert.match(source, /:multiple="item.multiple"/)
})

test('search reset clears text and uses fresh empty multiselect arrays', () => {
  const run = new Function(functionSource('resetSearchItems', config) + ';return resetSearchItems')()
  const previous = [0, 2], items = [{ type: 'input', key: 'name', value: 'Fixture' }, { type: 'select', key: 'status', value: previous }]
  run(items)
  assert.equal(items[0].value, ''); assert.deepEqual(items[1].value, []); assert.notEqual(items[1].value, previous)
  assert.deepEqual(previous, [0, 2])
})

test('search omits empty conditions but keeps zero, multiselect parameters and normalized ID lists', () => {
  const run = new Function(functionSource('searchQuery', config) + ';return searchQuery')()
  assert.deepEqual(run([{ type: 'input', key: 'id', value: '5574,5577,5574,' }, { type: 'input', key: 'name', value: '' },
    { type: 'select', key: 'status', value: [0, 2] }, { type: 'select', key: 'publication_status', value: [] }]),
  { id__in: '5574,5577', status__in: '0,2' })
})

test('publication keeps passed/prepublished business guards and delegates approval without frontend role hiding', () => {
  const warnings = [], reviews = [], confirms = []
  const change = new Function('available', 'mutationBusy', 'publicationReviewRef', 'Message', 'Modal', 'pageVersion',
    'let confirmation = null; let confirmationVersion = 0;' + functionSource('onPublicationChange') + ';return onPublicationChange')(
      () => true, { value: false }, { value: { open: (...args) => reviews.push(args) } },
      { warning: message => warnings.push(message) }, { confirm: options => confirms.push(options) }, { value: 1 })
  change({ id: 1, status: 0, publication_status: 'unpublished' }, 'prepublished')
  change({ id: 1, status: 1, publication_status: 'unpublished' }, 'published')
  assert.equal(warnings.length, 2); assert.equal(confirms.length, 0); assert.equal(reviews.length, 0)
  change({ id: 1, status: 1, publication_status: 'prepublished' }, 'published')
  assert.deepEqual(reviews, [['pytest', [1]]])
  assert.doesNotMatch(source, /is_product_owner|v-permission|is_published/)
  assert.match(read('src/api/pytest/case.ts'), /target_status: targetStatus/)
  const batch = read('src/views/pytest/case/components/PytestCaseBatchEditor.vue')
  assert.match(batch, /:options="assetStatusOptions\(record\)"/)
  assert.match(batch, /row.publication_status === 'prepublished'/)
})
