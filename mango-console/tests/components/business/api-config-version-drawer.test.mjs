import assert from 'node:assert/strict'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'

import { compileScript, compileStyle, compileTemplate, parse } from '@vue/compiler-sfc'

const componentPath = fileURLToPath(
  new URL('../../../src/components/business/ApiConfigVersionHistoryPanel.vue', import.meta.url)
)
const source = fs.readFileSync(componentPath, 'utf8')
const { descriptor, errors } = parse(source, { filename: componentPath })

assert.equal(errors.length, 0, `SFC parse errors: ${errors.join('\n')}`)
assert.ok(descriptor.template, 'component must include a template block')
assert.ok(descriptor.scriptSetup, 'component must include a script setup block')
assert.ok(descriptor.styles.length > 0, 'component must include a style block')

const componentId = 'api-config-version-history-panel'
const compiledScript = compileScript(descriptor, { id: componentId })
const compiled = compileTemplate({
  id: componentId,
  filename: componentPath,
  source: descriptor.template.content,
  compilerOptions: {
    bindingMetadata: compiledScript.bindings,
  },
})
assert.equal(compiled.errors.length, 0, `template compile errors: ${compiled.errors.join('\n')}`)

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
  'getApiConfigVersionList',
  'getApiConfigVersionDetail',
  'maskApiConfigVersionSnapshotPair',
  'formatApiConfigVersionDiffValue',
  'pageSize = 20',
  'mango-empty-state',
  '字段差异',
  '变更前快照',
  '变更后快照',
  'lazy-load',
  'aria-current',
]) {
  assert.ok(source.includes(contract), `component must include ${contract}`)
}

const compactTemplate = descriptor.template.content.replace(/\s+/g, '')
const compactScript = descriptor.scriptSetup.content.replace(/\s+/g, '')
assert.ok(
  compactScript.includes(
    'constmaskedSnapshotPair=computed(()=>maskApiConfigVersionSnapshotPair(detail.value?.before_snapshot??null,detail.value?.after_snapshot??null))'
  ),
  'maskedSnapshotPair must derive both snapshots in one pair call'
)
assert.match(
  compactScript,
  /constbeforeSnapshot=computed\(\(\)=>\{.*?returnmaskedSnapshotPair\.value\[0\].*?\}\)/,
  'beforeSnapshot must read pair index 0'
)
assert.match(
  compactScript,
  /constafterSnapshot=computed\(\(\)=>\{.*?returnmaskedSnapshotPair\.value\[1\].*?\}\)/,
  'afterSnapshot must read pair index 1'
)
assert.ok(
  compactTemplate.includes('<JsonDisplayv-if="beforeSnapshot!==null":data="beforeSnapshot"'),
  'before JsonDisplay must bind beforeSnapshot'
)
assert.ok(
  compactTemplate.includes('<JsonDisplayv-if="afterSnapshot!==null":data="afterSnapshot"'),
  'after JsonDisplay must bind afterSnapshot'
)

for (const [label, contract] of [
  [
    'before diff',
    'formatApiConfigVersionDiffValue(diffItem.before,diffItem.path,detail.before_snapshot)',
  ],
  [
    'after diff',
    'formatApiConfigVersionDiffValue(diffItem.after,diffItem.path,detail.after_snapshot)',
  ],
]) {
  assert.ok(compactTemplate.includes(contract), `${label} must use its matching snapshot`)
}

console.log('api config version history drawer contract passed')
