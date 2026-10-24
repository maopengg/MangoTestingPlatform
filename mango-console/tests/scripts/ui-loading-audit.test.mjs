import assert from 'node:assert/strict'
import test from 'node:test'
import { auditLoading, findNestedLoading } from '../../scripts/ui-loading-audit.mjs'

test('detects nested table and panel masks but preserves button feedback', () => {
  const issues = findNestedLoading(`<template><a-spin :loading="busy">
    <a-table :loading="busy"/><a-spin :loading="detailBusy"/>
    <a-button :loading="saving"/>
  </a-spin></template>`)
  assert.equal(issues.length, 2)
})

test('accepts mutually exclusive masks and does not flag independent siblings', () => {
  assert.deepEqual(findNestedLoading(`<template>
    <a-spin :loading="busy"><a-table :loading="!busy && tableBusy"/></a-spin>
    <a-spin :loading="otherBusy"/>
    <a-spin :loading="false"><a-spin :loading="detailBusy"/></a-spin>
  </template>`), [])
})

test('does not accept a guard for only one of multiple loading ancestors', () => {
  assert.equal(findNestedLoading(`<template><a-spin :loading="pageBusy">
    <a-spin :loading="!pageBusy && panelBusy"><a-table :loading="!pageBusy && tableBusy"/></a-spin>
  </a-spin></template>`).length, 1)
})

test('all source pages and components have no unexplained nested loading masks', () => {
  const { scanned, findings } = auditLoading()
  assert.ok(scanned > 200)
  assert.deepEqual(findings, [])
})

test('owned panel spinners keep the same loading exclusivity checks', () => {
  assert.equal(findNestedLoading(`<template><mango-panel-spin :loading="busy">
    <a-table :loading="busy"/>
  </mango-panel-spin></template>`).length, 1)
  assert.deepEqual(findNestedLoading(`<template><mango-panel-spin :loading="busy">
    <a-spin :loading="!busy && detailBusy"/>
  </mango-panel-spin></template>`), [])
})
