import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { parse } from '@vue/compiler-sfc'

const root = new URL('../', import.meta.url)
const read = (path) => fs.readFileSync(new URL(path, root), 'utf8')

test('API prepublication can be returned by non-owners while approval remains owner-only', () => {
  const panel = read('src/views/apitest/case/details/components/ApiCaseVersionPanel.vue')
  const buttons = panel.match(/<a-button\b[\s\S]*?<\/a-button>/g)
  const revert = buttons.find(button => button.includes('@click="revertPrepublication"'))
  const approve = buttons.find(button => button.includes('@click="approvePrepublication"'))
  assert.match(revert, /v-if="selectedRevision\?\.is_prepublished"/)
  assert.doesNotMatch(revert, /is_product_owner/)
  assert.match(approve, /selectedRevision.is_product_owner/)
})

for (const domain of ['apitest', 'uitest']) {
  test(`${domain} has exactly four publication tabs and no status search dropdown`, () => {
    const config = read(`src/views/${domain}/case/config.ts`)
    const file = ts.createSourceFile('config.ts', config, ts.ScriptTarget.Latest, true)
    let tabs
    for (const statement of file.statements) {
      if (!ts.isVariableStatement(statement)) continue
      for (const declaration of statement.declarationList.declarations) {
        if (declaration.name.getText(file) === 'publicationTabs') {
          tabs = new Function(`return ${declaration.initializer.getText(file)}`)()
        }
      }
    }
    assert.deepEqual(tabs.map((tab) => [tab.key, tab.title]), [
      ['all', '全部'], ['published', '已发布'], ['prepublished', '预发布'], ['unpublished', '未发布'],
    ])
    const conditions = config.slice(config.indexOf('export const conditionItems'), config.indexOf('enableMultiSelectSearch(conditionItems)'))
    assert.doesNotMatch(conditions, /key: 'publication_status'/)
    assert.match(read(`src/views/${domain}/case/index.vue`), /<template #tabs>/)
    const { descriptor } = parse(read(`src/views/${domain}/case/index.vue`))
    assert.equal((descriptor.template.content.match(/<TableTabs\b/g) || []).length, 1)
    assert.doesNotMatch(descriptor.template.content, /<template #toolbar>|<a-tabs\b/)
    assert.match(descriptor.template.content, /<TableTabs[^>]*:active-key="activePublicationStatus"[^>]*@tab-click="switchPublicationTab"/)
    assert.match(descriptor.template.content, /<template #extra>/)
  })

  test(`${domain} switching tabs resets pagination and selection and reloads`, () => {
    const { descriptor } = parse(read(`src/views/${domain}/case/index.vue`))
    const file = ts.createSourceFile('setup.ts', descriptor.scriptSetup.content, ts.ScriptTarget.Latest, true)
    const declaration = file.statements.find((node) => ts.isFunctionDeclaration(node) && node.name.text === 'switchPublicationTab')
    const source = ts.transpileModule(declaration.getText(file), { compilerOptions: { target: ts.ScriptTarget.ES2022 } }).outputText
    const activePublicationStatus = { value: 'all' }
    const pagination = { page: 5 }
    const selectedRowKeys = { value: [11, 12] }
    const calls = []
    const switchTab = new Function('activePublicationStatus', 'pagination', 'selectedRowKeys', 'doRefresh',
      source + '\nreturn switchPublicationTab')(activePublicationStatus, pagination, selectedRowKeys, (...args) => calls.push(args))
    switchTab('prepublished')
    assert.equal(activePublicationStatus.value, 'prepublished')
    assert.equal(pagination.page, 1)
    assert.deepEqual(selectedRowKeys.value, [])
    assert.deepEqual(calls, [[null, false, true]])
  })
}

test('API tabs filter only their mutually exclusive publication status', () => {
  const source = read('src/views/apitest/case/index.vue')
  assert.match(source, /value.publication_status = activePublicationStatus.value/)
  assert.doesNotMatch(source, /unpublished,draft_changed/)
})

test('UI uses target status rather than the legacy direct publication boolean', () => {
  const api = read('src/api/uitest/case.ts')
  assert.match(api, /target_status: targetStatus/)
  assert.doesNotMatch(api, /is_published: isPublished/)
  const source = read('src/views/uitest/case/index.vue')
  assert.match(source, /permission: 'ui.case:change'/)
  assert.match(source, /!record.is_product_owner/)
  assert.match(source, /isLatestRequest\(requestId\)/)
})
