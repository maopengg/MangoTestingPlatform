import assert from 'node:assert/strict'
import fs from 'node:fs'
import test from 'node:test'
import ts from 'typescript'
import { effectScope, nextTick, reactive, ref, toRaw, watch } from 'vue'

test('environment name settings are editable and refresh enum titles after saving', () => {
  const settings = fs.readFileSync(new URL('../../../../src/views/system/settings/index.vue', import.meta.url), 'utf8')
  const store = fs.readFileSync(new URL('../../../../src/store/modules/get-enum.ts', import.meta.url), 'utf8')
  assert.match(settings, /<EnvironmentNameOverrides[\s\S]*?v-model="item.value"/)
  assert.match(settings, /groupKeys: \['system', 'email'\]/)
  assert.match(settings, /if \(isEnvironmentDisplayNames\(snapshot\)\) \{\s*try \{\s*await enumStore.getEnum\(true\)/)
  assert.match(settings, /await enumStore.getEnum\(true\)/)
  assert.match(store, /'environment_type_defaults'/)
  assert.match(store, /this.environment_type_defaults.length > 0/)
})

test('environment titles are resolved by enum key rather than display position', () => {
  const source = fs.readFileSync(new URL('../../../../src/views/config/test-object/index.vue', import.meta.url), 'utf8')
  const expression = source.match(/enumStore\.environment_type\.find\([\s\S]*?\)\?\.title/)[0]
  const evaluate = new Function('enumStore', 'record', `return ${expression}`)
  const context = {
    environment_type: [
      { key: 3, title: '开发环境' }, { key: 0, title: '测试环境' },
      { key: 1, title: '预发环境' }, { key: 4, title: '验收环境' },
      { key: 5, title: '蓝环境' }, { key: 2, title: '线上环境' },
    ],
  }
  const find = (value) => evaluate(context, { environment: value })
  assert.equal(find(0), '测试环境')
  assert.equal(find('2'), '线上环境')
  assert.equal(find(3), '开发环境')
  assert.equal(find(null), undefined)
  assert.equal(find(''), undefined)
  assert.equal(find(99), undefined)
})

test('optional overrides support all environments, preserve input identity and delete to restore defaults', async () => {
  const source = fs.readFileSync(new URL('../../../../src/views/system/settings/components/EnvironmentNameOverrides.vue', import.meta.url), 'utf8')
  const script = source.match(/<script setup lang="ts">([\s\S]*?)<\/script>/)[1].replace(/^\s*import .*$/gm, '')
  const js = ts.transpileModule(script, { compilerOptions: { module: ts.ModuleKind.ESNext } }).outputText
  const parent = ref({})
  let saves = 0
  const scope = effectScope()
  try {
    const editor = scope.run(() => new Function('ref', 'toRaw', 'watch', 'defineProps', 'defineEmits', `${js}; return { rows, addRow, removeRow, commit, optionsFor };`)(
      ref, toRaw, watch,
      () => reactive({
        get modelValue() { return parent.value },
        options: ['测试环境', '预发环境', '生产环境', '开发环境', '验收环境', '仿真环境'].map((title, key) => ({ key, title })),
        loading: false,
      }),
      () => (event, value) => { if (event === 'save') saves++; else parent.value = value },
    ))
    assert.equal(editor.rows.value.length, 0)
    editor.addRow()
    const row = editor.rows.value[0]
    assert.equal(editor.optionsFor(row).length, 6)
    assert.equal(editor.optionsFor(row)[2].label, '生产环境')
    row.environment = 2
    editor.commit()
    assert.equal(saves, 0, 'partial row stays local')
    row.name = '正式环境'
    editor.commit()
    await nextTick()
    assert.deepEqual(toRaw(parent.value), { 2: '正式环境' })
    assert.equal(editor.rows.value[0], row, 'saving does not recreate the input')
    editor.addRow()
    assert.equal(editor.optionsFor(editor.rows.value[1])[2].disabled, true)
    editor.removeRow(row.id)
    await nextTick()
    assert.deepEqual(toRaw(parent.value), {})
    assert.equal(editor.rows.value.length, 1, 'deletion keeps the other draft editable')
    parent.value = { 1: '蓝环境' }
    await nextTick()
    assert.equal(editor.rows.value[0].name, '蓝环境', 'external rollback reloads actual saved values')
  } finally {
    scope.stop()
  }
})
