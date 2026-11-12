import assert from 'node:assert/strict'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'

import { compileScript, compileStyle, compileTemplate, parse } from '@vue/compiler-sfc'

function compileComponent(relativePath, componentId) {
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
    compilerOptions: { bindingMetadata: compiledScript.bindings },
  })
  assert.equal(
    compiledTemplate.errors.length,
    0,
    `${relativePath} template compile errors: ${compiledTemplate.errors.join('\n')}`
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
      `${relativePath} style ${index} compile errors: ${compiledStyle.errors.join('\n')}`
    )
  }

  return source
}

const versionPanelSource = compileComponent(
  '../../../../../src/views/apitest/case/details/components/ApiCaseVersionPanel.vue',
  'api-case-version-panel-three-column-layout'
)
const detailsPageSource = compileComponent(
  '../../../../../src/views/apitest/case/details/index.vue',
  'api-case-details-three-box-layout'
)
const snapshotSource = compileComponent(
  '../../../../../src/views/apitest/case/details/components/ApiCaseVersionSnapshot.vue',
  'api-case-version-snapshot'
)

for (const contract of ['当前配置', "emit('detail'", "emit('current'", 'defineExpose']) {
  assert.ok(versionPanelSource.includes(contract), `version sidebar must include ${contract}`)
}

assert.ok(
  !versionPanelSource.includes('import ApiCaseVersionSnapshot'),
  'version sidebar must not contain the case/scenario snapshot boxes'
)

for (const contract of [
  'api-case-version-sidebar',
  'ApiCaseOrchestrationPanel',
  'selectedCaseVersionDetail',
  '@detail="showVersionDetail"',
  '@current="showCurrentConfiguration"',
  'selectExecutionVersion',
  'showCurrentConfiguration',
]) {
  assert.ok(detailsPageSource.includes(contract), `details page must include ${contract}`)
}

assert.ok(
  !detailsPageSource.includes('<a-tab-pane key="0" title="版本">'),
  'version must be an independent box instead of a peer editor tab'
)

for (const contract of [
  '用例编排',
  '前置准备',
  '执行编排',
  '后置清理',
  '场景扩展',
  '版本快照',
  '只读',
  'position="left"',
  '全局变量',
  '授权管理',
  '自定义变量',
  'SQL变量',
  '数据工厂',
  '默认请求头',
  'front_custom',
  'front_sql',
  'resolved_front_headers',
  'posterior_sql',
  'revisionPayload.value.api_case_detailed',
  'parametersFor',
  '前置准备',
  '请求配置',
  '响应处理',
  '断言配置',
  '请求头',
  '参数',
  '请求体',
  '<a-table',
  '接口名称',
  '测试结果',
  '前置sql',
  '前置函数',
  '响应JSON提取',
  '响应文本提取',
  '后置SQL',
  '后置函数',
  'json一致断言',
  '文本一致断言',
  '响应字段断言',
  '结构化断言',
  '通用断言',
  'selectedStep',
  'selectStep',
]) {
  assert.ok(snapshotSource.includes(contract), `snapshot view must include ${contract}`)
}

assert.ok(
  !snapshotSource.includes('class="snapshot-step"'),
  'historical steps must reuse the current table presentation instead of custom cards'
)

for (const writeContract of ['增加场景', '编辑', '复制', '删除', 'addParameter', 'putApiCase']) {
  assert.ok(
    !snapshotSource.includes(writeContract),
    `historical snapshot must not expose write action ${writeContract}`
  )
}

assert.ok(
  snapshotSource.includes('grid-template-columns: minmax(340px, 42fr) minmax(460px, 58fr)'),
  'snapshot view must split case orchestration and scenarios into two readable columns'
)

assert.match(snapshotSource, /arco-tabs-content-item/ , 'snapshot tab items must preserve the finite height chain')
assert.match(snapshotSource, /padding-top: 1px/, 'snapshot tab content keeps the requested top padding')
console.log('api case version snapshot layout contract passed')
