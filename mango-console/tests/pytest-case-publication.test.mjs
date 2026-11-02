import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse } from '@vue/compiler-sfc'

const root = new URL('../', import.meta.url)
const read = (path) => fs.readFileSync(new URL(path, root), 'utf8')
const source = read('src/views/pytest/case/index.vue')
const { descriptor } = parse(source)
const file = ts.createSourceFile('setup.ts', descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
function functionSource(name) {
  const declaration = file.statements.find((node) => ts.isFunctionDeclaration(node) && node.name.text === name)
  return ts.transpileModule(declaration.getText(file), {
    compilerOptions: { target: ts.ScriptTarget.ES2022 },
  }).outputText
}

test('Pytest uses workbench search instead of publication tabs', () => {
  assert.match(source, /<template #search>/)
  assert.doesNotMatch(source, /:show-search="false"|<template #tabs>/)
  assert.match(source, /@search="onSearchRefresh"/)
  const config = read('src/views/pytest/case/config.ts')
  assert.match(config, /key: 'publication_status'/)
  assert.match(config, /enableMultiSelectSearch\(conditionItems\)/)
  assert.match(source, /:multiple="item.multiple"/)
  assert.match(source, /'source_status', 'asset_status', 'level', 'case_people'/)
})

test('search clears pagination and stale selection before reloading the directory', () => {
  const pagination = { page: 4 }
  const selectedRowKeys = { value: [1] }
  const selectedDirectoryNode = { value: {} }
  const activeDirectoryNode = { value: {} }
  const explorerSourceLoading = { value: true }
  const calls = []
  const run = new Function('pagination', 'selectedRowKeys', 'selectedDirectoryNode', 'activeDirectoryNode',
    'explorerSourceLoading', 'clearPollingTimer', 'loadDirectoryTree',
    `let explorerSourceRequestId = 2; let initialFileSelectionPending = false;
     ${functionSource('onSearchRefresh')}
     onSearchRefresh(); return [explorerSourceRequestId, initialFileSelectionPending]`)
  assert.deepEqual(run(pagination, selectedRowKeys, selectedDirectoryNode, activeDirectoryNode,
    explorerSourceLoading, () => calls.push('stop'), () => calls.push('load')), [3, true])
  assert.equal(pagination.page, 1)
  assert.deepEqual(selectedRowKeys.value, [])
  assert.equal(selectedDirectoryNode.value, null)
  assert.equal(activeDirectoryNode.value, null)
  assert.equal(explorerSourceLoading.value, false)
  assert.deepEqual(calls, ['stop', 'load'])
})

test('search omits empty conditions but keeps zero and multiselect parameters', () => {
  const run = new Function('getFormItems', 'conditionItems',
    functionSource('buildCaseSearchParams') + '\nreturn buildCaseSearchParams()')
  assert.deepEqual(run(() => ({ status: 0, name: '', module: null, level: undefined,
    tags: [], publication_status__in: 'prepublished,published' }), []),
  { status: 0, publication_status__in: 'prepublished,published' })
  assert.match(source, /params: Record<string, any> = buildCaseSearchParams\(\)/)
})

test('publication actions use dedicated permission, product owner and passed guards', () => {
  assert.match(source, /v-permission="'pytest.case:change'"/)
  assert.match(source, /selectedExplorerRecord.is_product_owner/)
  assert.match(functionSource('onPublicationChange'), /record.status !== 1/)
  const api = read('src/api/pytest/case.ts')
  assert.match(api, /target_status: targetStatus/)
  assert.doesNotMatch(api, /is_published: isPublished/)
  const batch = read('src/views/pytest/case/components/PytestCaseBatchEditor.vue')
  assert.match(batch, /:options="assetStatusOptions\(record\)"/)
  assert.match(batch, /row.publication_status === 'prepublished'/)
  assert.doesNotMatch(source, /is_published/)
  assert.doesNotMatch(batch, /is_published/)
})
