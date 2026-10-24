import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'
import postcss from 'postcss'

const filename = new URL('../../../src/views/timing/tasks/components/TaskGroupManager.vue', import.meta.url).pathname
const { descriptor } = parse(readFileSync(filename, 'utf8'), { filename })
const css = postcss.parse(descriptor.styles[0].content)
function properties(selector) {
  const result = {}
  css.walkRules(selector, rule => {
    if (rule.parent.type !== 'root') return
    rule.walkDecls(decl => { result[decl.prop] = decl.value })
  })
  return result
}

test('task group create/edit dialog is compact and has a separate footer', () => {
  const editor = descriptor.template.content.split('v-model:visible="editorVisible"')[1].split('</a-modal>')[0]
  assert.match(editor, /width="min\(760px, calc\(100vw - 32px\)\)"/)
  assert.match(editor, /class="mango-task-group-editor-modal"/)
  assert.match(editor, /<mango-panel-spin[\s\S]*?<\/a-form>[\s\S]*?<\/mango-panel-spin>[\s\S]*?<template #footer>/)
  assert.match(editor, /v-permission="'timing.tasks:edit'"/)
  assert.doesNotMatch(editor, /:footer="false"/)
})

test('default scrolling is contained in module tree, not the entire form', () => {
  assert.match(descriptor.template.content, /body-class="mango-task-group-editor-body"/)
  assert.equal(properties(':global(.arco-modal-body.mango-task-group-editor-body)').overflow, 'hidden')
  assert.equal(properties('.mango-task-group-editor')['grid-template-rows'], 'minmax(0, auto) minmax(120px, 1fr)')
  assert.equal(properties('.mango-task-group-editor').overflow, 'hidden')
  assert.equal(properties('.mango-task-group-editor').height, '100%')
  assert.equal(properties('.mango-task-group-editor__modules')['min-height'], '0')
  assert.equal(properties('.mango-task-group-editor__tree').overflow, 'auto')
  assert.equal(properties('.mango-task-group-editor__tree').flex, '1')
  assert.equal(properties('.mango-task-group-editor__tree')['min-height'], '0')
  assert.equal(properties('.mango-task-group-editor__grid :deep(.arco-form-item)')['flex-wrap'], 'nowrap')
  css.walkAtRules('media', rule => {
    rule.walkRules(inner => assert.doesNotMatch(inner.selector, /mango-task-group-editor-body|^\.mango-task-group-editor$/))
  })
})

test('teleported modal body selector does not require the page scope attribute', () => {
  const compiled = compileStyle({ source: descriptor.styles[0].content, filename,
    id: 'data-v-task-group-editor', scoped: true })
  assert.deepEqual(compiled.errors, [])
  const bodyRules = []
  postcss.parse(compiled.code).walkRules(rule => {
    if (rule.selector.includes('mango-task-group-editor-body')) bodyRules.push(rule.selector)
  })
  assert.deepEqual(bodyRules, ['.arco-modal-body.mango-task-group-editor-body'])
})

test('group editor compiles with module selection and preview flow intact', () => {
  assert.match(descriptor.template.content, /@check="onModuleCheck"/)
  assert.match(descriptor.template.content, /@click="openPreview"/)
  const script = compileScript(descriptor, { id: 'task-group-editor' })
  assert.deepEqual(compileTemplate({ source: descriptor.template.content, filename,
    id: 'task-group-editor', compilerOptions: { bindingMetadata: script.bindings } }).errors, [])
})
