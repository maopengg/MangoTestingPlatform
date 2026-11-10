import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import { parse, compileScript, compileTemplate, compileStyle } from '@vue/compiler-sfc'

const base = '../../../src/components/DataFactory/'
for (const name of [
  'CaseConfigPanel.vue',
  'TemplateFieldConfigEditor.vue',
  'DataFactoryDependencyPreview.vue',
  'DataFactoryRelationFlow.vue',
  '../../views/data-factory/template/preview/index.vue',
]) {
  test(`${name} compiles after drawer layout normalization`, () => {
    const filename = new URL(base + name, import.meta.url).pathname
    const { descriptor, errors } = parse(fs.readFileSync(filename, 'utf8'), { filename })
    assert.deepEqual(errors, [])
    const script = compileScript(descriptor, { id: 'factory-config' })
    assert.deepEqual(
      compileTemplate({
        source: descriptor.template.content,
        filename,
        id: 'factory-config',
        compilerOptions: { bindingMetadata: script.bindings },
      }).errors,
      []
    )
    for (const style of descriptor.styles) {
      assert.deepEqual(
        compileStyle({ source: style.content, filename, id: 'factory-config', scoped: true })
          .errors,
        []
      )
    }
  })
}

test('relation header gives description and wrapping legend full width independently of actions', () => {
  const source = fs.readFileSync(
    new URL(base + 'DataFactoryRelationFlow.vue', import.meta.url),
    'utf8'
  )
  const header = source.slice(0, source.indexOf('<mango-panel-spin'))
  assert.match(header, /<slot name="extra"><\/slot>\s*<\/div>\s*<div v-if="subtitle"/)
  assert.match(header, /aria-label="关系线图例"/)
  assert.equal((header.match(/<i class="legend-line /g) || []).length, 4)
  assert.match(source, /grid-template-columns: minmax\(0, 1fr\) auto/)
  for (const name of ['subtitle', 'legend']) {
    assert.match(
      source,
      new RegExp(`\\.mango-relation-flow-${name}\\s*\\{\\s*grid-column: 1 / -1;`)
    )
  }
  assert.match(
    source,
    /\.mango-relation-flow-legend\s*\{[^}]*flex-wrap: wrap;[^}]*justify-content: flex-start;/
  )
})

test('drawer uses global gaps and horizontal forms without duplicate section spacing', () => {
  const source = fs.readFileSync(new URL(base + 'CaseConfigPanel.vue', import.meta.url), 'utf8')
  assert.match(source, /body-class="mango-data-factory-config-body"/)
  assert.match(source, /layout="horizontal"/)
  assert.match(source, /\.mango-data-factory-config-body\)[\s\S]*?padding: var\(--m-page-gap\)/)
  assert.match(
    source,
    /\.mango-template-field-stack > \.mango-section-card \+ \.mango-section-card\s*\{\s*margin-top: 0/
  )
  assert.match(source, /repeat\(auto-fit, minmax\(280px, 1fr\)\)/)
  assert.doesNotMatch(source, /height: calc\(100vh - 118px\)|max-width: 1px/)
  const editor = fs.readFileSync(
    new URL(base + 'TemplateFieldConfigEditor.vue', import.meta.url),
    'utf8'
  )
  assert.match(editor, /class="mango-native-scroll-table"/)
  assert.match(editor, /height: scaleDensityLength\(tableScrollY\)/)
  assert.match(editor, /y: '100%'/)
  assert.match(
    source,
    /\.mango-data-factory-base-card :deep\(\.arco-form-item-label-col\)\s*\{\s*width: 100px;\s*white-space: nowrap;/
  )
})

test('template preview keeps bounded tables and responsive summary without nested spin selectors', () => {
  const page = fs.readFileSync(
    new URL('../../../src/views/data-factory/template/preview/index.vue', import.meta.url),
    'utf8'
  )
  const rules = fs.readFileSync(
    new URL(
      '../../../src/views/data-factory/template/preview/components/EntityRulesDialog.vue',
      import.meta.url
    ),
    'utf8'
  )
  const preview = fs.readFileSync(
    new URL(base + 'DataFactoryDependencyPreview.vue', import.meta.url),
    'utf8'
  )
  assert.match(rules, /class="mango-entity-rule-table-region"/)
  assert.match(rules, /height: min\(460px, 65vh\)/)
  assert.match(rules, /:scroll="\{ x: entityRuleTableScrollWidth, y: '100%' \}"/)
  assert.match(page, /\.mango-preview-spin :deep\(> \.mango-panel-spin__content\)/)
  assert.match(preview, /flex: 1 1 430px;\s*min-width: 0/)
  assert.match(preview, /minmax\(260px, 34%\) minmax\(0, 1fr\)/)
  assert.doesNotMatch(page + preview, /max-width: 1px/)
})

test('field loading and preview table loading are mutually exclusive', () => {
  const source = fs.readFileSync(new URL(base + 'CaseConfigPanel.vue', import.meta.url), 'utf8')
  assert.match(
    source,
    /<mango-panel-spin :loading="fieldLoading" class="mango-template-editor-spin"/
  )
  assert.equal(
    (source.match(/:loading="!fieldLoading && previewLoading === 'form'"/g) || []).length,
    2
  )
  assert.doesNotMatch(source, /:loading="fieldLoading \|\| previewLoading === 'form'"/)
})
