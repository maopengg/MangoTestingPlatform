import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse } from '@vue/compiler-sfc'
import { reactive, ref } from 'vue'

const config = ts.createSourceFile('config.ts', readFileSync('src/views/apitest/auth-config/config.ts', 'utf8'), ts.ScriptTarget.Latest, true)
const source = readFileSync('src/views/apitest/auth-config/index.vue', 'utf8')
const script = ts.createSourceFile('auth.ts', parse(source).descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
function declaration(ast, name) {
  return ast.statements.flatMap(node => ts.isVariableStatement(node) ? [...node.declarationList.declarations] : [])
    .find(node => node.name.getText(ast) === name)
}
function compile(ast, name) {
  return ts.transpileModule(`const ${declaration(ast, name).getText(ast)}`, {
    compilerOptions: { target: ts.ScriptTarget.ES2022 },
  }).outputText
}
const sections = new Function(compile(config, 'authFormSections') + ';return authFormSections')()
const items = new Function('reactive', 'ref', compile(config, 'formItems') + ';return formItems')(reactive, ref)

test('authorization groups contain each form field once and preserve optional target', () => {
  assert.deepEqual(sections.map(item => item.title), ['基础信息', '认证配置', '刷新策略'])
  const keys = sections.flatMap(item => item.itemKeys)
  assert.equal(new Set(keys).size, keys.length)
  assert.deepEqual([...keys].sort(), items.map(item => item.key).sort())
  assert.equal(items.find(item => item.key === 'target_address').required, false)
  assert.match(source, /:width="760"/)
  assert.match(source, /class="mango-section-title mango-auth-form-section__header"/)
})

test('groups only render currently visible controls in every auth and refresh mode', () => {
  for (const authType of [0, 1]) {
    for (const refreshMode of [0, 1, 2, 3, 4]) {
      const visible = new Function('computed', 'formItems', 'authTypeItem', 'refreshModeItem', 'isExecutionCheckRefreshMode',
        compile(script, 'visibleFormItems') + ';return visibleFormItems')(
          fn => ({ value: fn() }), items, ref({ value: authType }), ref({ value: refreshMode }),
          ref([0, 2].includes(refreshMode)),
        )
      // The page refs contain form-item objects rather than refs to the numeric enum.
      const selected = new Function('computed', 'visibleFormItems', 'authFormSections',
        compile(script, 'authFormGroups') + ';return authFormGroups')(
          fn => fn(), visible, sections,
        )
      const keys = selected.flatMap(group => group.items.map(item => item.key))
      assert.deepEqual([...keys].sort(), visible.value.map(item => item.key).sort())
      assert.equal(keys.includes('custom_code'), authType === 1)
      assert.equal(keys.includes('api_info'), authType === 0)
      assert.equal(keys.includes('time_task'), [1, 2].includes(refreshMode))
      assert.equal(keys.includes('notice_group'), refreshMode === 4)
    }
  }
})
