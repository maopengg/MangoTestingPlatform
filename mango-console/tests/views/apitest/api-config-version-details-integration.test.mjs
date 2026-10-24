import assert from 'node:assert/strict'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'

import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'

function compileDetailsPage(relativePath, componentId) {
  const componentPath = fileURLToPath(new URL(relativePath, import.meta.url))
  const source = fs.readFileSync(componentPath, 'utf8')
  const { descriptor, errors } = parse(source, { filename: componentPath })

  assert.equal(errors.length, 0, `${relativePath} SFC parse errors: ${errors.join('\n')}`)
  assert.ok(descriptor.template, `${relativePath} must include a template block`)
  assert.ok(descriptor.scriptSetup, `${relativePath} must include a script setup block`)

  const compiledScript = compileScript(descriptor, { id: componentId })
  const compiledTemplate = compileTemplate({
    id: componentId,
    filename: componentPath,
    source: descriptor.template.content,
    compilerOptions: {
      bindingMetadata: compiledScript.bindings,
    },
  })

  assert.equal(
    compiledTemplate.errors.length,
    0,
    `${relativePath} template compile errors: ${compiledTemplate.errors.join('\n')}`
  )

  return source
}

function assertContracts(source, pageName, contracts) {
  for (const contract of contracts) {
    assert.ok(source.includes(contract), `${pageName} must include ${contract}`)
  }
}

const apiInfoSource = compileDetailsPage(
  '../../../src/views/apitest/info/details/index.vue',
  'api-info-details-version-history-integration'
)
const apiCaseSource = compileDetailsPage(
  '../../../src/views/apitest/case/details/index.vue',
  'api-case-details-version-history-integration'
)
const apiCaseVersionPanelSource = compileDetailsPage(
  '../../../src/views/apitest/case/details/components/ApiCaseVersionPanel.vue',
  'api-case-version-release-guidance-integration'
)
const apiCaseConfigSource = fs.readFileSync(
  fileURLToPath(new URL('../../../src/views/apitest/case/details/config.ts', import.meta.url)),
  'utf8'
)

assertContracts(apiInfoSource, 'API info details', [
  'import ApiInfoVersionPanel',
  '<ApiInfoVersionPanel',
  ':api-info-id="apiInfoId"',
  '@select="handleApiVersionSelect"',
  'apiVersionReadOnly',
  'handleApiVersionSelect',
])
assert.ok(
  !apiInfoSource.includes('ApiInfoVersionDrawer'),
  'API info details must use a persistent version panel instead of a drawer'
)
assert.ok(
  !apiInfoSource.includes('版本管理'),
  'API info details must not require a version-management entry button'
)
const apiInfoVersionPanelSource = compileDetailsPage(
  '../../../src/views/apitest/info/details/components/ApiInfoVersionPanel.vue',
  'api-info-version-panel-integration'
)
assertContracts(apiInfoVersionPanelSource, 'API info version panel', [
  '当前配置',
  '当前工作区，可直接编辑',
  '调试通过后可生成修订',
  "await createApiInfoRevision(props.apiInfoId, '从当前配置生成修订')",
  '当前发布',
])
assert.ok(
  !apiInfoVersionPanelSource.includes('创建首个 Draft'),
  'API entry must automatically guarantee its editing Draft'
)
assertContracts(apiCaseSource, 'API case details', [
  'pinned_api_info_revision',
  'loadApiInfoRevisions',
  "if (!executionVersion && pageData.record?.publication_status === 'unpublished')",
  "pageData.record?.publication_status === 'unpublished'",
  'versionPanelRef',
  'selectPreferredRevision',
  '当前用例尚未发布，已定位到版本盒子',
  'Number(res.code) === 1125',
  'applyCaseVersionPayload',
  'snapshotParametersByStep',
  'getSnapshotApiInfoId',
  'step.api_info_id',
])
assert.ok(
  !apiCaseSource.includes('<ApiCaseVersionSnapshot'),
  'selecting a published case version must keep the normal orchestration and scenario layout'
)
assert.ok(
  !apiCaseSource.includes('v-if="!selectedCaseVersionDetail"'),
  'normal case panels must remain mounted when a version is selected'
)
assertContracts(apiCaseConfigSource, 'API case step form', [
  '接口版本',
  'pinned_api_info_revision',
  '请选择接口版本',
])
for (const removedContract of [
  'import ApiConfigVersionHistoryDrawer',
  'versionHistoryVisible',
  '版本历史',
  'title="用例版本历史"',
]) {
  assert.ok(
    !apiCaseSource.includes(removedContract),
    `API case details must remove ${removedContract}`
  )
}
assertContracts(apiCaseVersionPanelSource, 'API case version panel', [
  '执行通过并确认断言后可生成修订',
  'createApiCaseRevision({',
  "summary: '从当前配置生成修订'",
  'class="version-card"',
  '<strong>当前配置</strong>',
  '当前工作区，可直接编辑',
])
for (const removedReleaseHint of [
  '当前用例尚未发布',
  '先创建修订并确认快照，再发布 V1',
  '列表批量执行和定时任务仅使用已发布版本',
]) {
  assert.ok(
    !apiCaseVersionPanelSource.includes(removedReleaseHint),
    `case version panel must remove duplicated release hint: ${removedReleaseHint}`
  )
}
assert.ok(
  !apiCaseVersionPanelSource.includes('创建独立 Draft'),
  'normal case entry must not require a manual create Draft button'
)
assert.ok(
  !apiCaseVersionPanelSource.includes('执行此版本'),
  'version panel must use the page-level execute button instead of a duplicate execute action'
)
for (const removedCardSubtitle of [
  'editingDraft.step_count',
  "item.summary || '用例配置快照'",
]) {
  assert.ok(
    !apiCaseVersionPanelSource.includes(removedCardSubtitle),
    `case version cards must remove subtitle: ${removedCardSubtitle}`
  )
}
assert.ok(
  !apiCaseVersionPanelSource.includes('createApiCaseDraft'),
  'editing the current case must not create a Draft or Revision automatically'
)

console.log('api config version details integration contract passed')
