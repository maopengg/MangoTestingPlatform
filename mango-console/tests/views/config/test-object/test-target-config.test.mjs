import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { computed, effectScope, nextTick, reactive, ref, toRaw, watch } from 'vue'

const source = fs.readFileSync(
  new URL('../../../../src/views/config/test-object/target-config.ts', import.meta.url),
  'utf8'
)
const compiled = ts.transpileModule(source, {
  compilerOptions: { module: ts.ModuleKind.ESNext },
}).outputText
const { emptyTargetConfig, validateTargetConfig } = await import(
  `data:text/javascript;base64,${Buffer.from(compiled).toString('base64')}`
)

test('fixed address and custom variable mapping are valid', () => {
  assert.equal(validateTargetConfig({ ...emptyTargetConfig(), default: 'https://example.com' }), '')
  assert.equal(
    validateTargetConfig({
      ...emptyTargetConfig(),
      default: 'https://common.example.com',
      selector: '租户id',
      mapping: { 1002: 'https://tenant-b.example.com' },
    }),
    ''
  )
})

test('reject incomplete mapping and invalid selector, allow mapping without default', () => {
  assert.ok(validateTargetConfig(emptyTargetConfig()))
  assert.ok(validateTargetConfig({ ...emptyTargetConfig(), selector: '租户id' }))
  assert.ok(validateTargetConfig({ ...emptyTargetConfig(), selector: '租户id' }))
  assert.ok(
    validateTargetConfig({ ...emptyTargetConfig(), selector: '租户id', mapping: { '': '' } })
  )
  assert.equal(
    validateTargetConfig({ ...emptyTargetConfig(), selector: '租户id', mapping: { x: 'url' } }),
    ''
  )
  assert.ok(
    validateTargetConfig({ ...emptyTargetConfig(), selector: '${{租户id}}', mapping: { x: 'url' } })
  )
})

test('editor is categorized, new writes clear legacy value and table uses parsed display', () => {
  const page = fs.readFileSync(
    new URL('../../../../src/views/config/test-object/index.vue', import.meta.url),
    'utf8'
  )
  const editor = fs.readFileSync(
    new URL(
      '../../../../src/views/config/test-object/components/TestObjectEditor.vue',
      import.meta.url
    ),
    'utf8'
  )
  assert.match(editor, /基础信息/)
  assert.match(editor, /被测对象/)
  assert.match(page, /<TestTargetDisplay/)
  assert.match(editor, /<TestTargetEditor/)
  assert.match(editor, /mango-target-editor__grid/)
  assert.match(editor, /:width="760"/)
  const mappingEditor = fs.readFileSync(
    new URL(
      '../../../../src/views/config/test-object/components/TestTargetEditor.vue',
      import.meta.url
    ),
    'utf8'
  )
  assert.match(mappingEditor, /mango-target-mapping-header/)
  assert.match(mappingEditor, /mango-target-mapping-empty/)
})

test('mapping input preserves row identity across reactive parent updates', async () => {
  const editorSource = fs.readFileSync(
    new URL(
      '../../../../src/views/config/test-object/components/TestTargetEditor.vue',
      import.meta.url
    ),
    'utf8'
  )
  const script = editorSource
    .match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1]
    .replace(/^\s*import .*$/gm, '')
  const js = ts.transpileModule(script, {
    compilerOptions: { module: ts.ModuleKind.ESNext },
  }).outputText
  const parent = ref({
    default: 'https://example.com',
    selector: '租户id',
    mapping: { 1001: 'https://tenant.example.com' },
  })
  const scope = effectScope()
  try {
    const editor = scope.run(() =>
      new Function(
        'computed',
        'reactive',
        'ref',
        'toRaw',
        'watch',
        'defineProps',
        'defineEmits',
        `${js}; return { rows, emitConfig, addRow };`
      )(
        computed,
        reactive,
        ref,
        toRaw,
        watch,
        () =>
          reactive({
            get modelValue() {
              return parent.value
            },
          }),
        () => (_event, value) => {
          parent.value = value
        }
      )
    )
    const row = editor.rows.value[0]
    for (const [field, value] of [
      ['key', '1002'],
      ['value', 'https://updated.example.com'],
    ]) {
      row[field] = value
      editor.emitConfig()
      await nextTick()
      assert.equal(editor.rows.value[0], row)
      assert.equal(editor.rows.value[0][field], value)
    }
    editor.addRow()
    editor.addRow()
    await nextTick()
    assert.equal(editor.rows.value.length, 3, 'incomplete duplicate rows remain editable')
    parent.value = { default: 'https://other.example.com', selector: '', mapping: {} }
    await nextTick()
    assert.equal(editor.rows.value.length, 0, 'external configuration still synchronizes')
  } finally {
    scope.stop()
  }
})

test('mapping summary shows default address and labels selector without opening details', () => {
  const display = fs.readFileSync(
    new URL(
      '../../../../src/views/config/test-object/components/TestTargetDisplay.vue',
      import.meta.url
    ),
    'utf8'
  )
  const summary = display.split('<template #content>')[0]
  assert.match(summary, /默认地址<\/span>/)
  assert.match(summary, /条件变量<\/span>/)
  assert.match(summary, /\{\{ defaultAddress \}\}/)
  assert.ok(summary.indexOf('默认地址') < summary.indexOf('<a-popover'))
  assert.doesNotMatch(summary, /<a-button[^>]*>条件变量/)
  assert.match(display, /props.value \|\| props.config\?\.default \|\| '未设置'/)
})
