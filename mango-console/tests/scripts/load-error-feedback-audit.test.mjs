import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { auditFeedbackSource, auditLoadErrorFeedback } from '../../scripts/load-error-feedback-audit.mjs'

test('loading failures use public feedback throughout views and shared components', () => {
  assert.deepEqual(auditLoadErrorFeedback(), [])
})

test('audit detects nested, looped, custom and literal request failures', () => {
  for (const template of [
    '<a-alert v-for="item in optionErrors">{{ item.error }}</a-alert>',
    '<div role="alert">{{ tasks.error.value }}<a-button>重试</a-button></div>',
    '<div><strong>{{ errorText }}</strong></div>',
    '<template v-if="noticeState.error" #extra>{{ noticeState.error }}</template>',
    '<a-alert v-if="state.failed" type="error">加载执行记录失败</a-alert>',
    '<p v-if="renderError">图表渲染失败，请重试</p>',
    '<span>{{ error || "没有结果" }}</span>',
    '<MangoRequestFeedback :message="error">{{ error }}</MangoRequestFeedback>',
    '<template v-if="!loadFailed"></template>',
  ]) assert.ok(auditFeedbackSource(`<template>${template}</template>`).length, template)
})

test('notification bridge, empty states, business validation and actual results are allowed', () => {
  for (const template of [
    '<MangoRequestFeedback v-if="error" :message="error"><a-button>重试</a-button></MangoRequestFeedback>',
    '<a-alert data-feedback-kind="execution-result" type="error">{{ result.error_message }}</a-alert>',
    '<span data-feedback-kind="validation" role="alert">{{ modelError }}</span>',
    '<span>{{ loadError ? "" : "暂无数据" }}</span>',
    '<p>授权到期、刷新失败与数据模型异常</p>',
  ]) assert.deepEqual(auditFeedbackSource(`<template>${template}</template>`), [], template)
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
