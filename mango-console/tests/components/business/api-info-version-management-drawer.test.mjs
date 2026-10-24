import assert from 'node:assert/strict'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'

import { compileScript, compileStyle, compileTemplate, parse } from '@vue/compiler-sfc'

const componentPath = fileURLToPath(
  new URL('../../../src/components/business/ApiInfoVersionDrawer.vue', import.meta.url)
)
const source = fs.readFileSync(componentPath, 'utf8')
const { descriptor, errors } = parse(source, { filename: componentPath })

assert.equal(errors.length, 0, `SFC parse errors: ${errors.join('\n')}`)
assert.ok(descriptor.template, 'component must include a template block')
assert.ok(descriptor.scriptSetup, 'component must include a script setup block')

const componentId = 'api-info-version-management-drawer'
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
  `template compile errors: ${compiledTemplate.errors.join('\n')}`
)

for (const [index, style] of descriptor.styles.entries()) {
  const compiledStyle = compileStyle({
    id: componentId,
    filename: componentPath,
    source: style.content,
    scoped: style.scoped,
  })
  assert.equal(
    compiledStyle.errors.length,
    0,
    `style ${index} compile errors: ${compiledStyle.errors.join('\n')}`
  )
}

for (const contract of [
  'key="versions"',
  'title="版本"',
  'publishApiInfoRevision',
  'createApiInfoDraftFromRevision',
  'createApiInfoDraft',
  'getApiInfoDraftList',
  '创建首个 Draft',
  '从草稿生成修订',
  '接口 Draft',
  'revisionListRequestSequence',
  'revisionDetailRequestSequence',
  'compareDetailRequestSequence',
  'invalidateRevisionRequests',
  'requestedApiInfoId',
  ':loading="compareLoading"',
  'getRevisionStatus',
  "text: '当前发布'",
  "text: '历史版本'",
  "text: '未发布修订'",
]) {
  assert.ok(source.includes(contract), `component must include ${contract}`)
}

assert.ok(
  !source.includes("item.release ? '已发布' : '草稿'"),
  'published revisions must distinguish the current release from historical releases'
)

for (const removedContract of [
  'import ApiConfigVersionHistoryPanel',
  'activeManagementTab',
  'key="changes"',
  'title="变更记录"',
  'object-type="api_info"',
  'restoreApiInfoRevision',
  '保存当前修订',
]) {
  assert.ok(!source.includes(removedContract), `component must remove ${removedContract}`)
}

const compactScript = descriptor.scriptSetup.content.replace(/\s+/g, '')
assert.ok(
  compactScript.includes(
    'requestSequence!==revisionListRequestSequence||!props.visible||props.apiInfoId!==requestedApiInfoId'
  ),
  'revision list responses must be rejected after close or API object changes'
)
assert.ok(
  compactScript.includes(
    'requestSequence!==revisionDetailRequestSequence||!props.visible||props.apiInfoId!==requestedApiInfoId||selected.value?.id!==revisionId'
  ),
  'revision detail responses must match the visible API object and selected revision'
)
assert.ok(
  compactScript.includes(
    'requestSequence!==compareDetailRequestSequence||!props.visible||props.apiInfoId!==requestedApiInfoId||selected.value?.id!==selectedRevisionId||Number(compareRevisionId.value)!==revisionId'
  ),
  'compare responses must match both the base and comparison revisions'
)
assert.match(
  compactScript,
  /functionpublishSelected\(\).*?constapiInfoId=props\.apiInfoId.*?constrevisionId=selected\.value\.id.*?publishApiInfoRevision\(apiInfoId,revisionId\)/,
  'publish confirmation must capture immutable API and revision ids'
)
assert.match(
  compactScript,
  /functioncreateDraftFromSelected\(\).*?constapiInfoId=props\.apiInfoId.*?constrevisionId=selected\.value\.id.*?createApiInfoDraftFromRevision\(apiInfoId,revisionId\)/,
  'create Draft confirmation must capture immutable API and revision ids'
)

console.log('api info version management drawer contract passed')
