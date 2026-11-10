import test from 'node:test'
import assert from 'node:assert/strict'
import { mkdtempSync, writeFileSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'
import { auditSimpleModals, modalInventory } from '../../scripts/simple-modal-layout-audit.mjs'

const modal = content => `<template><a-modal><a-form>${content}</a-form></a-modal></template>`

test('plain field grids are ordinary forms, while classified settings retain their layout', () => {
  assert.equal(modalInventory(modal('<div><a-form-item label="名称" /></div>'))[0].kind, 'simple')
  for (const content of [
    '<section><header>基础信息</header><a-form-item /></section>',
    '<div class="mango-task-form-group"><a-form-item /></div>',
    '<a-tabs><a-tab-pane title="基础"><a-form-item /></a-tab-pane></a-tabs>',
  ]) assert.equal(modalInventory(modal(content))[0].kind, 'grouped')
  assert.equal(modalInventory(modal('<a-form-item /><a-table />'))[0].kind, 'workbench')
})

test('all ordinary form dialogs opt in and grouped dialogs stay outside the shared styling', () => {
  const result = auditSimpleModals()
  assert.ok(result.counts.simple >= 70)
  assert.ok(result.counts.grouped >= 6)
  assert.deepEqual(result.issues, [])
})

test('a marked modal cannot pass the audit with an unmarked field', () => {
  const root = mkdtempSync(path.join(tmpdir(), 'mango-modal-audit-'))
  try {
    writeFileSync(path.join(root, 'Editor.vue'), `<template>
      <a-modal modal-class="mango-simple-form-modal" :width="560">
        <a-form auto-label-width class="mango-simple-form" layout="horizontal" :model="{}">
          <a-form-item label="名称"><a-input /></a-form-item>
        </a-form>
      </a-modal>
    </template>`)
    assert.equal(auditSimpleModals(root).issues.length, 1)
    assert.match(auditSimpleModals(root).issues[0], /普通表单字段未接入统一布局/)
  } finally { rmSync(root, { recursive: true, force: true }) }
})
