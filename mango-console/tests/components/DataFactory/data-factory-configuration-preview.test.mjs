import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'
import ts from 'typescript'

const source = readFileSync(
  new URL('../../../src/components/DataFactory/CaseConfigPanel.vue', import.meta.url),
  'utf8'
)
const editor = readFileSync(
  new URL('../../../src/components/DataFactory/TemplateFieldConfigEditor.vue', import.meta.url),
  'utf8'
)

test('automatic case configuration preview does not depend on selected environment', () => {
  const preview = source.slice(
    source.indexOf('function loadCasePreview()'),
    source.indexOf('watch(', source.indexOf('function loadCasePreview()'))
  )
  assert.match(preview, /preview_mode: 'configuration'/)
  assert.doesNotMatch(preview, /test_env|selected_environment/)
  assert.match(source, /scheduleCasePreview\(\)/)
})

test('runtime-only values are displayed as pending instead of fake IDs', () => {
  assert.match(editor, /display_value/)
  assert.match(editor, /deferred.*待执行/)
})

test('standalone template page previews configuration but debug still selects an environment', () => {
  const page = readFileSync(
    new URL('../../../src/views/data-factory/template/preview/index.vue', import.meta.url),
    'utf8'
  )
  const payload = page.slice(
    page.indexOf('function buildPreviewPayload()'),
    page.indexOf('function resetTemplateForm')
  )
  assert.match(payload, /preview_mode: 'configuration'/)
  assert.doesNotMatch(payload, /test_env|selected_environment/)
  const debug = page.slice(
    page.indexOf('function debugRun()'),
    page.indexOf('function saveTemplateConfig()')
  )
  assert.match(debug, /debugRef.value\?\.run/)
  const runner = readFileSync(
    new URL(
      '../../../src/views/data-factory/template/preview/components/DebugResultDialog.vue',
      import.meta.url
    ),
    'utf8'
  )
  assert.match(runner, /test_env: environment/)
  assert.doesNotMatch(debug, /!previewResult.value.can_debug_run/)
  assert.match(page, /loadPreview\(\), loadEditableFieldDefinitions\(\)/)
})

const page = readFileSync(
  new URL('../../../src/views/data-factory/template/preview/index.vue', import.meta.url),
  'utf8'
)

test('candidate templates cannot block the scene panel or initial page load', () => {
  const reload = page.slice(
    page.indexOf('function reloadPageData()'),
    page.indexOf('function loadEditableFieldDefinitions()')
  )
  assert.doesNotMatch(reload, /loadSceneTemplateOptions\(\)/)
  assert.match(
    page,
    /scenePanelLoading = computed\(\(\) => !initialPageLoading.value && templateLoading.value\)/
  )
  assert.match(page, /@dropdown-reach-bottom="loadMoreSceneTemplateOptions"/)
  assert.match(page, /加载失败，点击重试/)
  assert.match(page, /sceneSelectOptions.value.find/)
})

function candidateLoader(request) {
  const state = {
    templateForm: { id: 268, project_product: 3 },
    sceneTemplateOptions: { value: [] },
    sceneOptionsKeyword: { value: '' },
    sceneOptionsPage: { value: 0 },
    sceneOptionsHasMore: { value: false },
    sceneOptionsFailed: { value: false },
    sceneOptionsLoading: { value: false },
    getDataFactoryTemplate: request,
    scope: { isActive: () => true },
    currentContext: () => ({}),
    isCurrent: () => true,
  }
  const implementation = ts.transpileModule(
    page.slice(
      page.indexOf('function loadSceneTemplateOptions('),
      page.indexOf('function normalizeSceneItems(')
    ),
    { compilerOptions: { target: ts.ScriptTarget.ES2022 } }
  ).outputText
  const load = new Function(
    ...Object.keys(state),
    `let sceneOptionsRequest = 0; ${implementation}; return loadSceneTemplateOptions`
  )(...Object.values(state))
  return { state, load }
}

test('candidate search is bounded, paginated and excludes the current template', async () => {
  const calls = []
  const { state, load } = candidateLoader(async (params, timeout) => {
    calls.push({ params, timeout })
    return { data: [{ id: 268 }, { id: params.page }], totalSize: 61 }
  })
  await load('评分', 1)
  await load('评分', 2)
  assert.deepEqual(calls[0], {
    params: { project_product: 3, name: '评分', page: 1, pageSize: 30 },
    timeout: 30000,
  })
  assert.deepEqual(
    state.sceneTemplateOptions.value.map((row) => row.id),
    [1, 2]
  )
  assert.equal(state.sceneOptionsHasMore.value, true)
  assert.equal(state.sceneOptionsLoading.value, false)
})

test('candidate failure releases loading and allows retry', async () => {
  let failed = true
  const { state, load } = candidateLoader(async () => {
    if (failed) throw new Error('timeout')
    return { data: [{ id: 1 }], totalSize: 1 }
  })
  await load()
  assert.equal(state.sceneOptionsFailed.value, true)
  assert.equal(state.sceneOptionsLoading.value, false)
  failed = false
  await load()
  assert.equal(state.sceneOptionsFailed.value, false)
  assert.equal(state.sceneTemplateOptions.value.length, 1)
})

test('a stale candidate response cannot overwrite a newer search', async () => {
  const pending = []
  const { state, load } = candidateLoader(() => new Promise((resolve) => pending.push(resolve)))
  const older = load('旧')
  const newer = load('新')
  pending[1]({ data: [{ id: 2 }], totalSize: 1 })
  await newer
  pending[0]({ data: [{ id: 1 }], totalSize: 1 })
  await older
  assert.deepEqual(
    state.sceneTemplateOptions.value.map((row) => row.id),
    [2]
  )
  assert.equal(state.sceneOptionsLoading.value, false)
})
